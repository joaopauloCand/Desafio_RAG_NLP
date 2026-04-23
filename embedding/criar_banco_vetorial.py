import json
import time
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env, se existir

def carregar_chunks_do_disco(caminho_arquivo: str) -> list[Document]:
    """Lê o arquivo JSONL e recria os objetos Document do LangChain."""
    documentos = []
    print(f"Lendo chunks do arquivo {caminho_arquivo}...")
    
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            dados = json.loads(linha)
            doc = Document(page_content=dados['texto'], metadata=dados['metadados'])
            documentos.append(doc)
            
    print(f"Total de {len(documentos)} chunks carregados na memória.")
    return documentos

def criar_banco_vetorial(caminho_arquivo: str, pasta_do_banco: str) -> Chroma:
    """Cria um banco vetorial usando Chroma e as embeddings do gemini-embedding-001."""
    embeddings_google = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    meus_documentos = carregar_chunks_do_disco(caminho_arquivo) 
    
    print(f"Preparando o banco vetorial em: {pasta_do_banco}")
    banco_vetorial = Chroma(
        embedding_function=embeddings_google,
        persist_directory=pasta_do_banco
    )
    
    # Reduzimos o lote drasticamente para não estourar o limite de conexões simultâneas
    TAMANHO_LOTE = 5 
    
    print(f"Escudo Anti-Erro 429...")
    
    for i in range(0, len(meus_documentos), TAMANHO_LOTE):
        lote_atual = meus_documentos[i : i + TAMANHO_LOTE]
        
        sucesso = False
        espera_punicao = 15 # Se der erro, espera 15 segundos iniciais
        
        # Este loop garante que o script NÃO avance até que o lote atual seja aceito
        while not sucesso:
            try:
                print(f"⏳ Processando chunks {i + 1} a {min(i + TAMANHO_LOTE, len(meus_documentos))} de {len(meus_documentos)}...")
                
                banco_vetorial.add_documents(lote_atual)
                sucesso = True # Se passou da linha de cima deu certo
                
                # Uma pausa de 3 segundos entre os lotes que deram certo
                time.sleep(3) 
                
            except Exception as e:
                erro_str = str(e)
                if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                    print(f"🛑 Radar do Google apitou (Erro 429)! Pausando por {espera_punicao} segundos...")
                    time.sleep(espera_punicao)
                    
                    # Backoff: Se falhar de novo, a próxima espera será maior (ex: 15, 30, 45...)
                    espera_punicao += 15 
                else:
                    # Se for outro erro (ex: internet caiu), mostramos o erro e paramos o lote
                    print(f"❌ Erro fatal desconhecido: {e}")
                    break

    print("✅ Todos os vetores gerados e banco salvo no disco.")
    return banco_vetorial

def main():
    criar_banco_vetorial("chunking\\chunks\\chunks_markdown.jsonl","./meu_banco_chroma_markdown") # <-- Ajuste o caminho conforme necessário

if __name__ == "__main__":
    main()