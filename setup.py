import os
import sys
import zipfile
import subprocess
from pathlib import Path
import requests
from tqdm import tqdm

# --- CONFIGURAÇÕES ---
URL_DOWNLOAD_BANCO = "https://huggingface.co/datasets/joaopauloCand/Embeddings_RAG_ANEEL/resolve/main/banco_chroma.zip?download=true"
URL_DOWNLOAD_CHUNKS = "https://huggingface.co/datasets/joaopauloCand/Embeddings_RAG_ANEEL/resolve/main/chunks.zip?download=true"
NOME_ZIP_BANCO = "banco_chroma.zip"
NOME_ZIP_CHUNKS = "chunks.zip"
PASTA_BANCO = "banco_chroma"
ARQUIVO_CHUNKS = "chunks\\chunks.jsonl"
FICHEIRO_ENV = ".env"
REQUISITOS = "requirements.txt"

def baixar_banco_de_dados()-> bool:
    """Baixa o arquivo ZIP do banco de dados vetorial automaticamente se não existir na máquina."""
    arquivo_zip = Path(NOME_ZIP_BANCO)
    pasta_banco = Path(PASTA_BANCO)

    # Se a pasta já existir, não precisa baixar nem extrair
    if pasta_banco.exists() and pasta_banco.is_dir():
        print_status(f"'{PASTA_BANCO}' já está pronto.")
        return True

    # Se o ZIP já existir, só vai extrair no próximo passo
    if arquivo_zip.exists():
        print_status(f"'{NOME_ZIP_BANCO}' já está pronto.")
        return True

    print(f"A baixar o banco de dados vetorial...")
    print("Isso pode demorar dependendo da sua ligação à internet.")
    
    try:
        # Faz a requisição em modo 'stream' para não estourar a RAM
        resposta = requests.get(URL_DOWNLOAD_BANCO, stream=True)
        resposta.raise_for_status() # Verifica se o link está válido
        
        # Pega o tamanho total do arquivo para a barra de progresso
        tamanho_total = int(resposta.headers.get('content-length', 0))
        
        # Cria a barra de progresso com o tqdm
        with open(arquivo_zip, 'wb') as ficheiro, tqdm(
            desc=NOME_ZIP_BANCO,
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

def print_status(mensagem: str, sucesso: bool = True) -> None:
    """Imprime uma mensagem de status formatada com um símbolo visual para sucesso ou falha."""
    prefixo = "OK" if sucesso else "ERRO"
    print(f"{prefixo} {mensagem}")

def extrair_banco_de_dados()-> bool:
    """Extrai o banco de dados vetorial se a pasta não existir."""
    caminho_banco = Path(PASTA_BANCO)
    arquivo_zip = Path(NOME_ZIP_BANCO)

    if caminho_banco.exists() and caminho_banco.is_dir():
        print_status(f"O banco de dados '{PASTA_BANCO}' já está pronto.")
        return True

    if not arquivo_zip.exists():
        print_status(f"Ficheiro '{NOME_ZIP_BANCO}' não encontrado. Certifique-se de que o ZIP está na raiz.", False)
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
        print_status("Dependências instaladas.")
        return True
    except Exception as e:
        print_status(f"Falha ao instalar dependências: {e}", False)
        return False

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
    print("\n" + "="*50)
    print("SISTEMA DE SETUP - RAG ANEEL")
    print("="*50 + "\n")

    # Ordem de execução
    passos = [
        ("Download de Dados", baixar_banco_de_dados),
        ("Download de Chunks", baixar_chunks),
        ("Extração de Dados", extrair_banco_de_dados),
        ("Extração de Chunks", extrair_chunks_jsonl),
        ("Verificação de Credenciais", verificar_api_key),
        ("Instalação de Bibliotecas", instalar_dependencias)#,
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