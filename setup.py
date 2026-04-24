import os
import sys
import zipfile
import subprocess
from pathlib import Path

# --- CONFIGURAÇÕES ---
NOME_ZIP_BANCO = "banco_chroma.zip"
NOME_ZIP_CHUNKS = "chunks.zip"
PASTA_BANCO = "banco_chroma"
ARQUIVO_CHUNKS = "chunks\\chunks.jsonl"
FICHEIRO_ENV = ".env"
REQUISITOS = "requirements.txt"

def print_status(mensagem: str, sucesso: bool = True) -> None:
    """Imprime uma mensagem de status formatada com um símbolo visual para sucesso ou falha."""
    simbolo = "✅" if sucesso else "⚠️"
    print(f"{simbolo} {mensagem}")

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

    print(f"📦 A descompactar o banco de dados vetorial... Isto pode demorar um pouco.")
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

    print(f"📦 A descompactar o arquivo JSONL... Isto pode demorar um pouco.")
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
    print("🛠️ A instalar dependências do Python...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUISITOS])
        print_status("Dependências instaladas.")
        return True
    except Exception as e:
        print_status(f"Falha ao instalar dependências: {e}", False)
        return False

def gerir_docker() -> bool:
    """Inicia os serviços via Docker Compose."""
    print("🐳 A preparar a infraestrutura Docker...")
    try:
        # Verifica se o Docker está a correr
        subprocess.check_call(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Sobe os contentores (Elasticsearch + App)
        subprocess.check_call(["docker-compose", "up", "-d"])
        print_status("Contentores Docker em execução.")
        return True
    except Exception:
        print_status("Docker não detetado ou desligado. Instale o Docker Desktop para usar o Elasticsearch.", False)
        return False

def main():
    print("\n" + "="*50)
    print("SISTEMA DE SETUP - RAG ANEEL")
    print("="*50 + "\n")

    # Ordem de execução
    passos = [
        ("Extração de Dados", extrair_banco_de_dados),
        ("Extração de Chunks", extrair_chunks_jsonl),
        ("Verificação de Credenciais", verificar_api_key),
        ("Instalação de Bibliotecas", instalar_dependencias)#,
        #("Inicialização da Infraestrutura", gerir_docker)
    ]

    for nome, acao in passos:
        if not acao():
            print(f"\n❌ O passo '{nome}' falhou. Resolva o problema acima para continuar.")
            if nome == "Verificação de Credenciais":
                print("Dica: Obtenha a sua chave em https://aistudio.google.com/")
            return
        print("="*50 + "\n")

    print("✨ TUDO PRONTO! ✨")
    print("A aplicação deve estar disponível em: http://localhost:8501")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()