import json
import importlib
import math
import os
import time

from langchain_chroma import Chroma
from langchain_core.documents import Document
from tqdm import tqdm


def carregar_classe_hf_embeddings():
    """Resolve HuggingFaceEmbeddings em pacotes LangChain novos e antigos."""
    modulos_candidatos = [
        "langchain_huggingface",
        "langchain_community.embeddings",
    ]

    for modulo in modulos_candidatos:
        try:
            return getattr(importlib.import_module(modulo), "HuggingFaceEmbeddings")
        except Exception:
            continue

    raise ImportError(
        "Nao foi possivel importar HuggingFaceEmbeddings. "
        "Instale 'langchain-huggingface' ou atualize dependencias do LangChain."
    )

# ==========================================
# CONFIGURACOES
# ==========================================
ARQUIVO_JSONL = "chunks\\chunks.jsonl"
DIRETORIO_CHROMA = "banco_chroma_bgem3"
ARQUIVO_CHECKPOINT = "embedding_checkpoint_os.txt"

TAMANHO_LOTE = 200
MAX_TENTATIVAS = 8
DISPOSITIVO = "cpu"  # Troque para "cuda" se houver GPU compatÃ­vel.


def carregar_linha_atual(arquivo_checkpoint: str) -> int:
    """Carrega a ultima linha processada do checkpoint (0 se inexistente/invalido)."""
    if not os.path.exists(arquivo_checkpoint):
        return 0

    try:
        with open(arquivo_checkpoint, "r", encoding="utf-8") as f:
            valor = f.read().strip()
            return int(valor) if valor else 0
    except Exception as e:
        print(f"Aviso: checkpoint invalido ({e}). A reiniciar do zero.")
        return 0


def salvar_linha_atual(numero_linha: int, arquivo_checkpoint: str) -> None:
    """Persiste a ultima linha processada para permitir retomada segura."""
    with open(arquivo_checkpoint, "w", encoding="utf-8") as f:
        f.write(str(numero_linha))


def contar_linhas_jsonl(caminho_arquivo: str) -> int:
    """Conta o total de linhas/chunks do JSONL para calcular progresso."""
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def gerador_de_lotes(caminho_arquivo: str, linha_inicio: int, tamanho_lote: int):
    """Le o JSONL a partir de linha_inicio e gera lotes de Document."""
    lote_atual = []

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        for _ in range(linha_inicio):
            try:
                next(f)
            except StopIteration:
                return

        for numero_linha, linha in enumerate(f, start=linha_inicio + 1):
            try:
                dados = json.loads(linha)
                doc = Document(
                    page_content=dados["page_content"],
                    metadata=dados["metadata"],
                )
                lote_atual.append(doc)
            except Exception as e:
                print(f"Aviso: linha {numero_linha} ignorada por erro de parse: {e}")
                continue

            if len(lote_atual) == tamanho_lote:
                yield lote_atual
                lote_atual = []

        if lote_atual:
            yield lote_atual


def processar_embeddings(
    arquivo_jsonl: str = ARQUIVO_JSONL,
    diretorio_chroma: str = DIRETORIO_CHROMA,
    arquivo_checkpoint: str = ARQUIVO_CHECKPOINT,
) -> None:
    """Executa ingestao com checkpoint, retries e retomada segura."""
    print(f"Iniciando ingestao a partir de '{arquivo_jsonl}'...")

    if not os.path.exists(arquivo_jsonl):
        raise FileNotFoundError(f"Arquivo JSONL nao encontrado: {arquivo_jsonl}")

    print("Carregando modelo open source BAAI/bge-m3...")
    hf_embeddings_cls = carregar_classe_hf_embeddings()
    embeddings_os = hf_embeddings_cls(
        model_name="BAAI/bge-m3",
        model_kwargs={"device": DISPOSITIVO},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 16},
    )

    banco_vetorial = Chroma(
        persist_directory=diretorio_chroma,
        embedding_function=embeddings_os,
    )

    total_chunks_esperados = contar_linhas_jsonl(arquivo_jsonl)
    linha_inicio = carregar_linha_atual(arquivo_checkpoint)

    if linha_inicio >= total_chunks_esperados:
        print("Banco vetorial ja esta 100% completo.")
        return

    print(f"Retomando a partir da linha/chunk {linha_inicio}...")

    lotes = gerador_de_lotes(arquivo_jsonl, linha_inicio, TAMANHO_LOTE)
    total_lotes = math.ceil((total_chunks_esperados - linha_inicio) / TAMANHO_LOTE)
    linha_atual = linha_inicio

    try:
        for lote in tqdm(lotes, total=total_lotes, desc="Vetorizacao local"):
            sucesso_no_lote = False
            tentativas = 0

            while not sucesso_no_lote and tentativas < MAX_TENTATIVAS:
                try:
                    banco_vetorial.add_documents(lote)
                    sucesso_no_lote = True
                except Exception as e:
                    tentativas += 1
                    tempo_espera = 2**tentativas
                    print(f"\nErro ao inserir lote: {str(e)[:200]}")
                    print(
                        f"Aguardando {tempo_espera}s para retry "
                        f"(tentativa {tentativas}/{MAX_TENTATIVAS})..."
                    )
                    time.sleep(tempo_espera)

            if not sucesso_no_lote:
                print(
                    f"\nFalha irreversivel apos {MAX_TENTATIVAS} tentativas. "
                    "Abortando com seguranca."
                )
                break

            linha_atual += len(lote)
            salvar_linha_atual(linha_atual, arquivo_checkpoint)

    except KeyboardInterrupt:
        print("\n\nProcesso interrompido pelo usuario (Ctrl+C).")
        print(f"Progresso salvo. O banco tem {linha_atual} chunks processados.")

    print("\n" + "=" * 50)
    print("Sessao de vetorizacao encerrada.")
    print(
        f"Total de chunks injetados no ChromaDB: "
        f"{linha_atual} / {total_chunks_esperados}"
    )
    print("=" * 50)


if __name__ == "__main__":
    processar_embeddings()