from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env, se existir
#testar a busca no banco vetorial, sem passar pelo LLM. Apenas para validar se os documentos estão sendo recuperados corretamente.
#similarity_search
def testar_recuperacao():
    # 1. Carregamos o mesmo modelo de matemática que usamos antes
    embeddings_google = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    
    # 2. Apontamos para a pasta onde o banco está salvo
    pasta_do_banco = "./meu_banco_chroma"
    banco_vetorial = Chroma(
        persist_directory=pasta_do_banco,
        embedding_function=embeddings_google
    )
    
    print("Banco carregado com sucesso! Vamos testar a busca.")
    print("-" * 40)
    
    # 3. A Pergunta do Usuário
    pergunta = "Qual é o montante de garantia física de energia definido para a Central Geradora Hidrelétrica CGH Enercol, e qual é a sua potência instalada?"
    
    # 4. Fazemos a busca de similaridade (trazendo os 3 chunks mais relevantes)
    resultados = banco_vetorial.similarity_search(pergunta, k=3)
    
    print(f"Pergunta: '{pergunta}'\n")
    
    for i, doc in enumerate(resultados, 1):
        print(f"--- RESULTADO {i} ---")
        print(f"Metadados: {doc.metadata}")
        # Mostramos apenas os primeiros 200 caracteres para não poluir a tela
        print(f"Trecho Encontrado: {doc.page_content[:200]}...\n")

if __name__ == "__main__":
    testar_recuperacao()