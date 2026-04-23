from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env, se existir

def consultar_assistente_aneel(pergunta_usuario: str) -> tuple[str, list[Document]]:
    """Função principal que orquestra a consulta ao assistente especializado da ANEEL."""
    # ---------------------------------------------------------
    # FASE 1: BUSCA HÍBRIDA DIRETA
    # ---------------------------------------------------------
    caminho_banco = "meu_banco_chroma_markdown"

    embeddings_google = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    banco_vetorial = Chroma(persist_directory=caminho_banco, embedding_function=embeddings_google)
    
    dados_chroma = banco_vetorial.get() 

    # 1. BM25 (Elasticsearch Local)
    documentos_para_bm25 = []
    for i in range(len(dados_chroma['ids'])):
        doc = Document(page_content=dados_chroma['documents'][i], metadata=dados_chroma['metadatas'][i])
        documentos_para_bm25.append(doc)
        
    retriever_palavra_chave = BM25Retriever.from_documents(documentos_para_bm25)
    retriever_palavra_chave.k = 6 # Busca os 6 documentos mais relevantes segundo o BM25 (palavra-chave) para garantir que termos exatos sejam priorizados, especialmente nomes de usinas e CNPJs.
    
    # 2. ChromaDB - utilizando mmr para trazer diversidade sem perder relevância
    retriever_vetorial = banco_vetorial.as_retriever(
        search_type="mmr", 
        search_kwargs={"k": 6, "fetch_k": 20}
    )
    
    # 3. O Gerente
    # Damos 60% de peso para a palavra exata (BM25), pois em despachos o nome da usina/CNPJ importa mais que a semântica
    retriever_hibrido = EnsembleRetriever(
        retrievers=[retriever_palavra_chave, retriever_vetorial],
        weights=[0.6, 0.4] 
    )
    
    print("🔎 Realizando Busca Híbrida Direta...")
    documentos_recuperados = retriever_hibrido.invoke(pergunta_usuario)
    
    # Extraímos apenas o texto dos chunks e juntamos tudo em uma única string
    textos_extraidos = [doc.page_content for doc in documentos_recuperados]
    contexto_injetado = "\n\n---\n\n".join(textos_extraidos)

    # ---------------------------------------------------------
    # FASE 2: AUGMENTATION (Aumento / Construção do Prompt)
    # ---------------------------------------------------------
    template = """Você é um assistente técnico especializado na análise de Despachos e Documentos da ANEEL.
    Sua tarefa é responder à pergunta do usuário utilizando EXCLUSIVAMENTE os trechos de documentos fornecidos abaixo.
    
    Regras estritas:
    1. Se a resposta não estiver contida nos trechos abaixo, responda EXATAMENTE: "Desculpe, mas não encontrei essa informação nos documentos analisados."
    2. Não invente valores, datas ou dados que não estejam no contexto.
    3. Seja direto, claro e profissional.
    
    DOCUMENTOS RECUPERADOS (Contexto):
    {contexto}
    
    PERGUNTA DO USUÁRIO: 
    {pergunta}
    
    RESPOSTA:"""
    
    # Criamos o molde do prompt e substituímos as variáveis
    prompt = PromptTemplate(template=template, input_variables=["contexto", "pergunta"])
    prompt_final = prompt.format(contexto=contexto_injetado, pergunta=pergunta_usuario)

    # ---------------------------------------------------------
    # FASE 3: GENERATION (Geração via LLM)
    # ---------------------------------------------------------
    print("🧠 Consultando os documentos e gerando a resposta...")
    
    # Instanciamos o LLM de texto do Google
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
    
    resposta = llm.invoke(prompt_final)
    
    return resposta.content, documentos_recuperados

# ==========================================
# TESTANDO O PIPELINE COMPLETO
# ==========================================

def main():
    pergunta = "Qual é o montante de garantia física de energia definido para a Central Geradora Hidrelétrica CGH Enercol, e qual é a sua potência instalada?"
    
    resposta_texto, fontes_utilizadas = consultar_assistente_aneel(pergunta)
    
    print("\n" + "="*50)
    print("🤖 RESPOSTA DO ASSISTENTE:")
    print("="*50)
    print(resposta_texto)
    
    print("\n" + "-"*50)
    print("📚 FONTES UTILIZADAS PARA ESTA RESPOSTA:")
    print("-"*50)
    
    # Mostra de onde tirou a informação, evita repetir o mesmo documento várias vezes caso ele tenha gerado múltiplos chunks
    ids_vistos = set()
    for doc in fontes_utilizadas:
        id_doc = doc.metadata.get('id_processo', 'ID Desconhecido')
        url = doc.metadata.get('url_documento', 'URL não disponível')
        
        if id_doc not in ids_vistos:
            print(f"📄 Documento: {id_doc} | Link: {url}")
            ids_vistos.add(id_doc)

if __name__ == "__main__":
    main()