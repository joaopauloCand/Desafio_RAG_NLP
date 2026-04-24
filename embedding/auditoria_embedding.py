from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# Conectando ao gigante
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", task_type="RETRIEVAL_DOCUMENT")
vectorstore = Chroma(persist_directory="banco_chroma", embedding_function=embeddings)

# 1. FORMA CORRETA DE CONTAR (Sem carregar nada na RAM)
total_registros = vectorstore._collection.count() 
print(f"✅ Total de chunks no banco: {total_registros}")
print("-" * 30)

# 2. AUDITORIA POR AMOSTRAGEM (OFFSET)
# Vamos pegar 3 registros do início e 3 lá do meio do banco para garantir a consistência
def auditar_amostra(posicao_inicial, quantidade):
    # O Chroma não tem offset direto no .get() do LangChain, então acessamos a coleção bruta
    amostra = vectorstore._collection.get(
        limit=quantidade,
        offset=posicao_inicial,
        include=["documents", "metadatas"]
    )
    
    for i in range(len(amostra['documents'])):
        print(f"📍 Posição no Banco: {posicao_inicial + i}")
        print(f"📄 Texto: {amostra['documents'][i][:100]}...")
        print(f"🔑 Metadados: {amostra['metadatas'][i]}")
        print("-" * 30)

print("🔍 Auditando os primeiros registros:")
auditar_amostra(0, 3)

if total_registros > 5000:
    print("\n🔍 Auditando amostra lá do meio (Ponto 5000):")
    auditar_amostra(5000, 2)