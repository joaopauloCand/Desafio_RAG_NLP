from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env, se existir

def consultar_assistente_aneel(pergunta_usuario):
    # ---------------------------------------------------------
    # FASE 1: RETRIEVAL (Recuperação)
    # ---------------------------------------------------------
    embeddings_google = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    banco_vetorial = Chroma(
        persist_directory="./meu_banco_chroma",
        embedding_function=embeddings_google
    )
    
    # Buscamos os 4 chunks mais relevantes
    documentos_recuperados = banco_vetorial.similarity_search(pergunta_usuario, k=4)
    
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
    
    # temperature=0.2 deixa a IA mais "fria" e analítica (ideal para dados exatos)
    resposta = llm.invoke(prompt_final)
    
    return resposta.content, documentos_recuperados

# ==========================================
# TESTANDO O PIPELINE COMPLETO
# ==========================================
if __name__ == "__main__":
    pergunta = "Qual é o montante de garantia física de energia definido para a Central Geradora Hidrelétrica CGH Enercol, e qual é a sua potência instalada?"
    
    resposta_texto, fontes_utilizadas = consultar_assistente_aneel(pergunta)
    
    print("\n" + "="*50)
    print("🤖 RESPOSTA DO ASSISTENTE:")
    print("="*50)
    print(resposta_texto)
    
    print("\n" + "-"*50)
    print("📚 FONTES UTILIZADAS PARA ESTA RESPOSTA:")
    print("-"*50)
    
    # Um bom RAG sempre mostra de onde tirou a informação!
    ids_vistos = set()
    for doc in fontes_utilizadas:
        id_doc = doc.metadata.get('id_processo', 'ID Desconhecido')
        url = doc.metadata.get('url_documento', 'URL não disponível')
        
        if id_doc not in ids_vistos:
            print(f"📄 Documento: {id_doc} | Link: {url}")
            ids_vistos.add(id_doc)