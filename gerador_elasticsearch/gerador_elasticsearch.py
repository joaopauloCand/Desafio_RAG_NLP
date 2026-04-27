import json
import math
import os
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_elasticsearch import ElasticsearchStore

# Configurações
TAMANHO_LOTE = 500  # Quantidade de documentos a serem enviados por lote para o Elasticsearch
DOCKER_ELASTICSEARCH_URL = "http://localhost:9200"
ELASTICSEARCH_INDEX_NAME = "aneel_lexical"
ARQUIVO_JSONL = "chunks\\chunks.jsonl"
ARQUIVO_CHECKPOINT = "elasticsearch_checkpoint.txt"

def carregar_linha_atual(arquivo_checkpoint: str) -> int:
    """Carrega a ultima linha processada do checkpoint (0 se inexistente/invalido)."""
    if not os.path.exists(arquivo_checkpoint):
        return 0

    try:
        with open(arquivo_checkpoint, "r", encoding="utf-8") as f:
            valor = f.read().strip()
            return int(valor) if valor else 0
    except Exception:
        return 0


def salvar_linha_atual(numero_linha: int, arquivo_checkpoint: str) -> None:
    """Salva a ultima linha processada para retomada segura."""
    with open(arquivo_checkpoint, "w", encoding="utf-8") as f:
        f.write(str(numero_linha))


def gerador_de_lotes_es(caminho_arquivo: str, linha_inicio: int, tamanho_lote: int) -> iter:
    """Lê o JSONL de forma preguiçosa para não sobrecarregar a RAM do VS Code."""
    lote_atual = []
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        for _ in range(linha_inicio):
            try:
                next(f)
            except StopIteration:
                return

        for linha in f:
            dados = json.loads(linha)
            doc = Document(page_content=dados["page_content"], metadata=dados["metadata"])
            lote_atual.append(doc)
            
            if len(lote_atual) == tamanho_lote:
                yield lote_atual
                lote_atual = []
        if lote_atual:
            yield lote_atual

def inserir_elasticsearch(
    arquivo_jsonl: str = ARQUIVO_JSONL,
    nome_indice: str = ELASTICSEARCH_INDEX_NAME,
    url_es: str = DOCKER_ELASTICSEARCH_URL,
    tamanho_lote: int = TAMANHO_LOTE,
    arquivo_checkpoint: str = ARQUIVO_CHECKPOINT,
) -> None:
    """Função principal para popular o Elasticsearch com os chunks do JSONL."""
    print("Iniciando ingestão no Elasticsearch (Busca Lexical/BM25)...")

    # Conecta ao ES e define a estratégia EXCLUSIVA de BM25
    banco_lexical = ElasticsearchStore(
        es_url=url_es,
        index_name=nome_indice,
        strategy=ElasticsearchStore.BM25RetrievalStrategy()
    )
    
    # Contamos o total de linhas apenas para a barra de progresso
    with open(arquivo_jsonl, 'r', encoding='utf-8') as f:
        total_chunks = sum(1 for _ in f)

    linha_inicio = carregar_linha_atual(arquivo_checkpoint)
    if linha_inicio >= total_chunks:
        print("Elasticsearch já está 100% indexado com base no checkpoint.")
        return

    print(f"Retomando a partir da linha/chunk {linha_inicio}...")
        
    total_lotes = math.ceil((total_chunks - linha_inicio) / tamanho_lote) if total_chunks else 0
    lotes = gerador_de_lotes_es(arquivo_jsonl, linha_inicio, tamanho_lote)
    
    linha_atual = linha_inicio
    chunks_novos = 0

    for lote in tqdm(lotes, total=total_lotes, desc="Enviando para o Elasticsearch"):
        banco_lexical.add_documents(lote)
        linha_atual += len(lote)
        chunks_novos += len(lote)
        salvar_linha_atual(linha_atual, arquivo_checkpoint)
        
    print(f"\nConcluído! {chunks_novos} novos chunks indexados no Elasticsearch.")

if __name__ == "__main__":
    inserir_elasticsearch()