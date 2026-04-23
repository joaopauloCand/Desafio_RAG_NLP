import json
import time
import hashlib
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

def gerar_id_chunk(doc: Document) -> str:
    """
    Gera um ID único e determinístico para o chunk baseado em seu conteúdo e metadados.
    Rodar o script duas vezes com o mesmo chunk produz o mesmo ID, evitando duplicação no Chroma.
    """
    chave = (
        doc.page_content +
        str(doc.metadata.get('id_processo', '')) +
        str(doc.metadata.get('indice_documento', '')) +
        str(doc.metadata.get('start_index', ''))  # quando um mesmo documento gera vários chunks
    )
    return hashlib.md5(chave.encode('utf-8')).hexdigest()

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
    MAX_TENTATIVAS_TRANSITORIAS = 5
    
    print(f"Escudo Anti-Erro 429...")
    
    for i in range(0, len(meus_documentos), TAMANHO_LOTE):
        lote_atual = meus_documentos[i : i + TAMANHO_LOTE]
        
        ids_lote = [gerar_id_chunk(doc) for doc in lote_atual]

        sucesso = False
        espera_punicao = 15 # Se der erro, espera 15 segundos iniciais
        tentativas_transitorias = 0

        # Este loop garante que o script NÃO avance até que o lote atual seja aceito
        while not sucesso:
            try:
                print(f"⏳ Processando chunks {i + 1} a {min(i + TAMANHO_LOTE, len(meus_documentos))} de {len(meus_documentos)}...")
                
                banco_vetorial.add_documents(lote_atual, ids=ids_lote)
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
                    
                #erros transitórios de rede (timeout, conexão caiu) — tenta algumas vezes by: kelvin
                elif any(termo in erro_str.lower() for termo in ["timeout", "connection", "network", "unavailable", "deadline"]):
                    tentativas_transitorias += 1
                    if tentativas_transitorias >= MAX_TENTATIVAS_TRANSITORIAS:
                        print(f"Excedido limite de {MAX_TENTATIVAS_TRANSITORIAS} tentativas após erro transitório. Abortando.")
                        print(f"   Último erro: {e}")
                        raise  # Propaga o erro e para o script para evitar perder lotes silenciosamente by: kelvin
                    espera_transitoria = 10 * tentativas_transitorias
                    print(f"⚠️ Erro transitório (tentativa {tentativas_transitorias}/{MAX_TENTATIVAS_TRANSITORIAS}): {e}")
                    print(f"   Aguardando {espera_transitoria}s antes de tentar novamente...")
                    time.sleep(espera_transitoria)   

                else:
                    # Se for outro erro (ex: internet caiu), mostramos o erro e paramos o lote by: kelvin
                    print(f"❌ Erro fatal desconhecido: {e}")
                    print(f" Lote {i + 1}-{min(i + TAMANHO_LOTE, len(meus_documentos))} não foi indexado.")
                    raise # João, acho melhor parar e investigar do que continuar com lotes faltando by: kelvin

    print("✅ Todos os vetores gerados e banco salvo no disco.")
    return banco_vetorial

def main():
    criar_banco_vetorial("chunking\\chunks\\chunks_markdown.jsonl","./meu_banco_chroma_markdown") # <-- Ajuste o caminho conforme necessário

if __name__ == "__main__":
    main()