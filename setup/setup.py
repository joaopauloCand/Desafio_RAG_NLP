import argparse
import os
import sys
import zipfile
import subprocess
from pathlib import Path
import requests
from tqdm import tqdm

# --- CONFIGURAÇÕES ---
URL_DOWNLOAD_BANCO_GEMINI = "https://huggingface.co/datasets/joaopauloCand/Embeddings_RAG_ANEEL/resolve/main/banco_chroma.zip?download=true"
URL_DOWNLOAD_BANCO_BGE_M3 = "https://huggingface.co/datasets/joaopauloCand/Embeddings_RAG_ANEEL/resolve/main/banco_chroma_bgem3.zip?download=true"
PLACEHOLDER_URL_BANCO_BGE_M3 = "https://huggingface.co/datasets/joaopauloCand/Embeddings_RAG_ANEEL/resolve/main/banco_chroma_bgem3.zip?download=true"
URL_DOWNLOAD_CHUNKS = "https://huggingface.co/datasets/joaopauloCand/Embeddings_RAG_ANEEL/resolve/main/chunks.zip?download=true"
URL_DOWNLOAD_JSON_PARSED = "https://huggingface.co/datasets/joaopauloCand/Embeddings_RAG_ANEEL/resolve/main/json_parsed.zip?download=true"
NOME_ZIP_BANCO_GEMINI = "banco_chroma.zip"
NOME_ZIP_BANCO_BGE_M3 = "banco_chroma_bgem3.zip"
NOME_ZIP_CHUNKS = "chunks.zip"
NOME_ZIP_JSON_PARSED = "json_parsed.zip"
PASTA_BANCO_GEMINI = "banco_chroma"
PASTA_BANCO_BGE_M3 = "banco_chroma_bgem3"
ARQUIVO_CHUNKS = "chunks\\chunks.jsonl"
PASTA_JSON_PARSED = "json_parsed"
FICHEIRO_ENV = ".env"
REQUISITOS = "requirements.txt"
REQUISITOS_EMBEDDING_OS_CPU = "embedding_os\\requirements_cpu.txt"
EMBEDDING_MODEL_PADRAO = "GEMINI"
EMBEDDING_MODEL_BGE_M3 = "BAAI/bge-m3"


def ler_variavel_env_local(chave: str) -> str | None:
    """Lê uma variável simples do arquivo .env sem depender de bibliotecas externas."""
    env_path = Path(FICHEIRO_ENV)
    if not env_path.exists():
        return None

    try:
        for linha in env_path.read_text(encoding="utf-8").splitlines():
            texto = linha.strip()
            if not texto or texto.startswith("#") or "=" not in texto:
                continue
            nome, valor = texto.split("=", 1)
            if nome.strip() == chave:
                return valor.strip().strip('"').strip("'")
    except Exception:
        return None

    return None


def obter_embedding_model_setup() -> str:
    """Obtém o modelo de embedding do sistema/.env com fallback para GEMINI."""
    valor = os.environ.get("EMBEDDING_MODEL") or ler_variavel_env_local("EMBEDDING_MODEL")
    if not valor:
        return EMBEDDING_MODEL_PADRAO

    valor = valor.strip()
    if valor in (EMBEDDING_MODEL_PADRAO, EMBEDDING_MODEL_BGE_M3):
        return valor

    print_status(
        f"EMBEDDING_MODEL='{valor}' inválido. A usar rota padrão {EMBEDDING_MODEL_PADRAO}.",
        False,
    )
    return EMBEDDING_MODEL_PADRAO


def obter_config_banco_vetorial_setup() -> tuple[str, str, str]:
    """Retorna URL, nome do ZIP e pasta alvo do banco vetorial conforme EMBEDDING_MODEL."""
    modelo = obter_embedding_model_setup()
    if modelo == EMBEDDING_MODEL_BGE_M3:
        return (
            URL_DOWNLOAD_BANCO_BGE_M3,
            NOME_ZIP_BANCO_BGE_M3,
            PASTA_BANCO_BGE_M3,
        )

    return (
        URL_DOWNLOAD_BANCO_GEMINI,
        NOME_ZIP_BANCO_GEMINI,
        PASTA_BANCO_GEMINI,
    )

def baixar_banco_de_dados()-> bool:
    """Baixa o arquivo ZIP do banco de dados vetorial automaticamente se não existir na máquina."""
    url_download, nome_zip_banco, pasta_banco_nome = obter_config_banco_vetorial_setup()
    arquivo_zip = Path(nome_zip_banco)
    pasta_banco = Path(pasta_banco_nome)

    if PLACEHOLDER_URL_BANCO_BGE_M3 in url_download:
        print_status(
            "URL_DOWNLOAD_BANCO_BGE_M3 ainda nao foi configurada no setup.py.",
            False,
        )
        return False

    # Se a pasta já existir, não precisa baixar nem extrair
    if pasta_banco.exists() and pasta_banco.is_dir():
        print_status(f"'{pasta_banco_nome}' já está pronto.")
        return True

    # Se o ZIP já existir, só vai extrair no próximo passo
    if arquivo_zip.exists():
        print_status(f"'{nome_zip_banco}' já está pronto.")
        return True

    print(f"A baixar o banco de dados vetorial...")
    print("Isso pode demorar dependendo da sua ligação à internet.")
    
    try:
        # Faz a requisição em modo 'stream' para não estourar a RAM
        resposta = requests.get(url_download, stream=True)
        resposta.raise_for_status() # Verifica se o link está válido
        
        # Pega o tamanho total do arquivo para a barra de progresso
        tamanho_total = int(resposta.headers.get('content-length', 0))
        
        # Cria a barra de progresso com o tqdm
        with open(arquivo_zip, 'wb') as ficheiro, tqdm(
            desc=nome_zip_banco,
            total=tamanho_total,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as barra:
            for chunk in resposta.iter_content(chunk_size=8192):
                tamanho = ficheiro.write(chunk)
                barra.update(tamanho)
                
        print_status("Download do banco de dados concluído com sucesso!")
        return True
        
    except requests.exceptions.RequestException as e:
        print_status(f"Erro ao tentar baixar o banco de dados: {e}", False)
        # Apaga o arquivo corrompido se o download cair no meio
        if arquivo_zip.exists():
            arquivo_zip.unlink()
        print_status("Download do banco de dados falhou.", False)
        return False

def baixar_chunks()-> bool:
    """Baixa o arquivo ZIP de chunks se não existir na máquina."""
    arquivo_zip = Path(NOME_ZIP_CHUNKS)
    pasta_chunks = Path(ARQUIVO_CHUNKS).parent

    # Se a pasta já existir, não precisa baixar nem extrair
    if pasta_chunks.exists() and pasta_chunks.is_dir():
        print_status(f"Os chunks '{ARQUIVO_CHUNKS}' já estão prontos.")
        return True

    # Se o ZIP já existir, só vai extrair no próximo passo
    if arquivo_zip.exists():
        print_status(f"O arquivo zip de '{ARQUIVO_CHUNKS}' já está pronto.")
        return True

    print(f"A baixar os chunks...")
    print("Isso pode demorar dependendo da sua ligação à internet.")

    try:
        # Faz a requisição em modo 'stream' para não estourar a RAM
        resposta = requests.get(URL_DOWNLOAD_CHUNKS, stream=True)
        resposta.raise_for_status() # Verifica se o link está válido

        # Pega o tamanho total do arquivo para a barra de progresso
        tamanho_total = int(resposta.headers.get('content-length', 0))

        # Cria a barra de progresso com o tqdm
        with open(arquivo_zip, 'wb') as ficheiro, tqdm(
            desc=NOME_ZIP_CHUNKS,
            total=tamanho_total,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as barra:
            for chunk in resposta.iter_content(chunk_size=8192):
                tamanho = ficheiro.write(chunk)
                barra.update(tamanho)

        print_status("Download dos chunks concluído com sucesso!")
        return True

    except requests.exceptions.RequestException as e:
        print_status(f"Erro ao tentar baixar os chunks: {e}", False)
        # Apaga o arquivo corrompido se o download cair no meio
        if arquivo_zip.exists():
            arquivo_zip.unlink()
        print_status("Download dos chunks falhou.", False)
        return False

def baixar_json_parsed()-> bool:
    """Baixa o ZIP de json_parsed para iniciar pipeline a partir de chunking."""
    if "<ADICIONAR_LINK_DO_ZIP_JSON_PARSED_AQUI>" in URL_DOWNLOAD_JSON_PARSED:
        print_status(
            "URL_DOWNLOAD_JSON_PARSED ainda nao foi configurada no setup.py.",
            False,
        )
        return False

    arquivo_zip = Path(NOME_ZIP_JSON_PARSED)
    pasta_jsons = Path(PASTA_JSON_PARSED)

    if pasta_jsons.exists() and pasta_jsons.is_dir():
        print_status(f"'{PASTA_JSON_PARSED}' já está pronto.")
        return True

    if arquivo_zip.exists():
        print_status(f"'{NOME_ZIP_JSON_PARSED}' já está pronto.")
        return True

    print("A baixar os JSONs parseados...")
    print("Isso pode demorar dependendo da sua ligação à internet.")

    try:
        resposta = requests.get(URL_DOWNLOAD_JSON_PARSED, stream=True)
        resposta.raise_for_status()

        tamanho_total = int(resposta.headers.get('content-length', 0))

        with open(arquivo_zip, 'wb') as ficheiro, tqdm(
            desc=NOME_ZIP_JSON_PARSED,
            total=tamanho_total,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as barra:
            for chunk in resposta.iter_content(chunk_size=8192):
                tamanho = ficheiro.write(chunk)
                barra.update(tamanho)

        print_status("Download dos JSONs parseados concluído com sucesso!")
        return True

    except requests.exceptions.RequestException as e:
        print_status(f"Erro ao tentar baixar os JSONs parseados: {e}", False)
        if arquivo_zip.exists():
            arquivo_zip.unlink()
        print_status("Download dos JSONs parseados falhou.", False)
        return False

def print_status(mensagem: str, sucesso: bool = True) -> None:
    """Imprime uma mensagem de status formatada com um símbolo visual para sucesso ou falha."""
    prefixo = "OK" if sucesso else "ERRO"
    print(f"{prefixo} {mensagem}")

def extrair_banco_de_dados()-> bool:
    """Extrai o banco de dados vetorial se a pasta não existir."""
    _, nome_zip_banco, pasta_banco_nome = obter_config_banco_vetorial_setup()
    caminho_banco = Path(pasta_banco_nome)
    arquivo_zip = Path(nome_zip_banco)

    if caminho_banco.exists() and caminho_banco.is_dir():
        print_status(f"O banco de dados '{pasta_banco_nome}' já está pronto.")
        return True

    if not arquivo_zip.exists():
        print_status(f"Ficheiro '{nome_zip_banco}' não encontrado. Certifique-se de que o ZIP está na raiz.", False)
        return False

    print(f"A descompactar o banco de dados vetorial... Isto pode demorar um pouco.")
    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zip_ref:
            zip_ref.extractall(".")
        print_status("Descompactação concluída com sucesso.")
        return True
    except Exception as e:
        print_status(f"Erro ao extrair o banco: {e}", False)
        return False

def extrair_chunks_jsonl()-> bool:
    """Extrai o arquivo JSONL com os chunks fatiados, se não existir."""
    arquivo_jsonl = Path(ARQUIVO_CHUNKS)
    arquivo_zip = Path(NOME_ZIP_CHUNKS)

    if arquivo_jsonl.exists() and arquivo_jsonl.is_file():
        print_status(f"O arquivo '{ARQUIVO_CHUNKS}' já está pronto.")
        return True

    if not arquivo_zip.exists():
        print_status(f"Ficheiro '{NOME_ZIP_CHUNKS}' não encontrado. Certifique-se de que o ZIP está na raiz.", False)
        return False

    print(f"A descompactar o arquivo JSONL... Isto pode demorar um pouco.")
    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zip_ref:
            zip_ref.extractall(".")
        print_status("Descompactação concluída com sucesso.")
        return True
    except Exception as e:
        print_status(f"Erro ao extrair o arquivo: {e}", False)
        return False

def extrair_json_parsed()-> bool:
    """Extrai o ZIP com json_parsed quando iniciar o setup pela fase de chunking."""
    pasta_jsons = Path(PASTA_JSON_PARSED)
    arquivo_zip = Path(NOME_ZIP_JSON_PARSED)

    if pasta_jsons.exists() and pasta_jsons.is_dir():
        print_status(f"A pasta '{PASTA_JSON_PARSED}' já está pronta.")
        return True

    if not arquivo_zip.exists():
        print_status(
            f"Ficheiro '{NOME_ZIP_JSON_PARSED}' não encontrado. Certifique-se de que o ZIP está na raiz.",
            False,
        )
        return False

    print("A descompactar os JSONs parseados... Isto pode demorar um pouco.")
    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zip_ref:
            zip_ref.extractall(".")
        print_status("Descompactação dos JSONs parseados concluída com sucesso.")
        return True
    except Exception as e:
        print_status(f"Erro ao extrair os JSONs parseados: {e}", False)
        return False

def verificar_api_key()-> bool:
    """Verifica se a GEMINI_API_KEY está configurada no sistema ou no .env."""
    # 1. Tenta Variável de Ambiente do Sistema
    key = os.environ.get("GEMINI_API_KEY")
    
    if key and key.strip() and key != "cole_sua_chave_aqui":
        print_status("Chave de API detetada nas variáveis de ambiente do sistema.")
        return True

    # 2. Tenta Ficheiro .env
    env_path = Path(FICHEIRO_ENV)
    if env_path.exists():
        with open(env_path, 'r') as f:
            conteudo = f.read()
            print(conteudo)  # Debug: Verificar o conteúdo do .env
            if "GEMINI_API_KEY" in conteudo and "cole_sua_chave_aqui" not in conteudo:
                print_status("Chave de API detetada no ficheiro .env.")
                return True

    # 3. Se nada funcionar, cria o template
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write('GEMINI_API_KEY="cole_sua_chave_aqui"\n')
        print_status(f"Ficheiro '{FICHEIRO_ENV}' criado. Insira a sua chave lá.", False)
    else:
        print_status("A chave de API no ficheiro .env parece estar vazia ou é o valor padrão.", False)
    
    return False

def instalar_dependencias()-> bool:
    """Instala as bibliotecas Python necessárias."""
    print("A instalar dependências do Python...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUISITOS])

        modelo_embedding = obter_embedding_model_setup()
        if modelo_embedding == EMBEDDING_MODEL_BGE_M3:
            print("A instalar dependências do embedding open source (BAAI/bge-m3)...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", REQUISITOS_EMBEDDING_OS_CPU]
            )

        print_status("Dependências instaladas.")
        return True
    except Exception as e:
        print_status(f"Falha ao instalar dependências: {e}", False)
        return False

def executar_chunking()-> bool:
    """Executa a etapa de chunking a partir de json_parsed/."""
    print("A executar a etapa de chunking...")
    try:
        subprocess.check_call([sys.executable, "chunking/chunking.py"])
        print_status("Chunking concluído com sucesso.")
        return True
    except Exception as e:
        print_status(f"Falha ao executar chunking: {e}", False)
        return False

def executar_embedding()-> bool:
    """Executa a etapa de geração de embeddings."""
    print("A executar a etapa de embedding...")
    modelo_embedding = obter_embedding_model_setup()

    script_embedding = "embedding/embedding.py"
    if modelo_embedding == EMBEDDING_MODEL_BGE_M3:
        script_embedding = "embedding_os/embedding_os.py"

    try:
        subprocess.check_call([sys.executable, script_embedding])
        print_status(f"Embedding concluído com sucesso ({modelo_embedding}).")
        return True
    except Exception as e:
        print_status(f"Falha ao executar embedding: {e}", False)
        return False

def executar_elasticsearch()-> bool:
    """Executa a etapa de indexação no Elasticsearch."""
    print("A executar a etapa de indexação lexical (Elasticsearch)...")
    try:
        subprocess.check_call([sys.executable, "gerador_elasticsearch/gerador_elasticsearch.py"])
        print_status("Indexação no Elasticsearch concluída com sucesso.")
        return True
    except Exception as e:
        print_status(f"Falha ao executar indexação no Elasticsearch: {e}", False)
        return False

def obter_passos_chunking_em_diante(etapa_inicial: str) -> list[tuple[str, callable]]:
    """Retorna os passos do fluxo chunking->embedding->elasticsearch a partir da etapa escolhida."""
    passos = [
        ("Download de JSONs Parseados", baixar_json_parsed, "download-jsons"),
        ("Extração de JSONs Parseados", extrair_json_parsed, "extract-jsons"),
        ("Verificação de Credenciais", verificar_api_key, "credentials"),
        ("Instalação de Bibliotecas", instalar_dependencias, "install"),
        ("Etapa de Chunking", executar_chunking, "chunking"),
        ("Etapa de Embedding", executar_embedding, "embedding"),
        ("Etapa de Elasticsearch", executar_elasticsearch, "elasticsearch"),
    ]

    inicio = next((i for i, item in enumerate(passos) if item[2] == etapa_inicial), None)
    if inicio is None:
        return []

    return [(nome, acao) for nome, acao, _ in passos[inicio:]]

#Função não utilizada no momento, já que a utilização do Docker foi deixada para o script de deploy. Mantida aqui para referência futura caso queira integrar a gestão do Docker no setup.
""" def gerir_docker() -> bool:
    #Inicia os serviços via Docker Compose.
    print("A preparar a infraestrutura Docker...")
    try:
        # Verifica se o Docker está a correr
        subprocess.check_call(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Sobe os contentores (Elasticsearch + App)
        subprocess.check_call(["docker-compose", "up", "-d"])
        print_status("Contentores Docker em execução.")
        return True
    except Exception:
        print_status("Docker não detetado ou desligado. Instale o Docker Desktop para usar o Elasticsearch.", False)
        return False """

def main():
    parser = argparse.ArgumentParser(
        description="Setup do projeto RAG ANEEL."
    )
    grupo_from = parser.add_mutually_exclusive_group()
    grupo_from.add_argument(
        "--from-download-jsons",
        action="store_true",
        help="Inicia no download de JSONs parseados (fluxo chunking em diante).",
    )
    grupo_from.add_argument(
        "--from-extract-jsons",
        action="store_true",
        help="Inicia na extração de JSONs parseados (fluxo chunking em diante).",
    )
    grupo_from.add_argument(
        "--from-credentials",
        action="store_true",
        help="Inicia na verificação de credenciais (fluxo chunking em diante).",
    )
    grupo_from.add_argument(
        "--from-install",
        action="store_true",
        help="Inicia na instalação de bibliotecas (fluxo chunking em diante).",
    )
    grupo_from.add_argument(
        "--from-chunking",
        action="store_true",
        help="Inicia na etapa de chunking (fluxo chunking -> embedding -> elasticsearch).",
    )
    grupo_from.add_argument(
        "--from-embedding",
        action="store_true",
        help="Inicia na etapa de embedding (fluxo embedding -> elasticsearch).",
    )
    grupo_from.add_argument(
        "--from-elasticsearch",
        action="store_true",
        help="Inicia na etapa de indexação no Elasticsearch.",
    )
    args = parser.parse_args()
    modelo_embedding = obter_embedding_model_setup()

    print("\n" + "="*50)
    print("SISTEMA DE SETUP - RAG ANEEL")
    print("="*50 + "\n")
    print_status(f"Rota de embedding ativa no setup: {modelo_embedding}")

    # Ordem de execução
    etapa_inicial = None
    if args.from_download_jsons:
        etapa_inicial = "download-jsons"
    elif args.from_extract_jsons:
        etapa_inicial = "extract-jsons"
    elif args.from_credentials:
        etapa_inicial = "credentials"
    elif args.from_install:
        etapa_inicial = "install"
    elif args.from_chunking:
        etapa_inicial = "chunking"
    elif args.from_embedding:
        etapa_inicial = "embedding"
    elif args.from_elasticsearch:
        etapa_inicial = "elasticsearch"

    if etapa_inicial is not None:
        passos = obter_passos_chunking_em_diante(etapa_inicial)
    else:
        passos = [
            ("Download de Dados", baixar_banco_de_dados),
            ("Download de Chunks", baixar_chunks),
            ("Extração de Dados", extrair_banco_de_dados),
            ("Extração de Chunks", extrair_chunks_jsonl),
            ("Verificação de Credenciais", verificar_api_key),
            ("Instalação de Bibliotecas", instalar_dependencias),
            #("Inicialização da Infraestrutura", gerir_docker)
        ]

    for nome, acao in passos:
        if not acao():
            print(f"\nERRO O passo '{nome}' falhou. Resolva o problema acima para continuar.")
            if nome == "Verificação de Credenciais":
                print("Dica: Obtenha a sua chave em https://aistudio.google.com/")
            return
        print("="*50 + "\n")

    print("TUDO PRONTO!")

if __name__ == "__main__":
    main()