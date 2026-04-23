from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever 
from langchain_core.documents import Document
import re

load_dotenv()  # Carrega variáveis de ambiente do ficheiro .env, se existir

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
    retriever_palavra_chave.k = 6 

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
    
    # ---------------------------------------------------------
    # FASE 2: AUGMENTATION (Aumento / Construção do Prompt)
    # ---------------------------------------------------------
    # Formatamos os documentos para injetar a tag [1], [2], etc.
    textos_extraidos = []
    for i, doc in enumerate(documentos_recuperados):
        # Tenta extrair um ID do metadado (ajuste 'id_processo' para a chave que usar no seu Markdown)
        id_doc = doc.metadata.get('id_processo', 'Documento sem ID') 
        texto_formatado = f"--- Documento [{i+1}] ---\nID: {id_doc}\nTexto: {doc.page_content}"
        textos_extraidos.append(texto_formatado)
        
    contexto_injetado = "\n\n".join(textos_extraidos)

    #Prompt:

    template = """Você é um assistente técnico especializado na análise de Despachos e Documentos da ANEEL.
    Sua tarefa é responder à pergunta do usuário utilizando EXCLUSIVAMENTE os trechos de documentos fornecidos abaixo.
    
    Regras estritas:
    1. Se a resposta não estiver contida nos trechos abaixo, responda EXATAMENTE: "Desculpe, mas não encontrei essa informação nos documentos analisados."
    2. Não invente valores, datas ou dados que não estejam no contexto.
    3. Seja direto, claro e profissional.
    
    REGRA DE CITAÇÃO OBRIGATÓRIA:
    Sempre que utilizar uma informação de um documento, VOCÊ DEVE citar a fonte no final da frase correspondente, usando o número do documento entre colchetes.
    Exemplo: A potência instalada da usina é de 50kW [1].
    
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
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
    resposta = llm.invoke(prompt_final)
    resposta_texto = resposta.content
    
    # ---------------------------------------------------------
    # FASE 4: FILTRAGEM E AGRUPAMENTO DE CONTEXTO QUE FOI REALMENTE UTILIZADO
    # ---------------------------------------------------------

    # 1. Captura tudo que estiver dentro de colchetes (ex: "1", "1, 2", "1 e 3")
    conteudos_entre_colchetes = re.findall(r'\[(.*?)\]', resposta_texto)
    
    # 2. Extrai apenas os números isolados lá de dentro
    citacoes = set()
    for conteudo in conteudos_entre_colchetes:
        numeros_encontrados = re.findall(r'\d+', conteudo)
        citacoes.update(numeros_encontrados)
    
    # Dicionário para agrupar as citações pelo ID do documento
    # Formato interno: { "ID_DO_DOC": {"indices": [1, 3], "url": "http...", "documento_base": doc} }
    documentos_agrupados = {}
    
    if citacoes:
        for num_str in citacoes:
            indice_array = int(num_str) - 1 # Transforma [1] no índice 0
            if 0 <= indice_array < len(documentos_recuperados):
                doc = documentos_recuperados[indice_array]

                # Resgata os metadados (garanta que essas chaves existam no seu Markdown)
                id_doc = doc.metadata.get('id_processo', 'Documento sem ID')
                url_doc = doc.metadata.get('url_documento', 'Link não disponível')
                
                # Lógica de Agrupamento
                if id_doc not in documentos_agrupados:
                    documentos_agrupados[id_doc] = {
                        "indices": [],
                        "url": url_doc,
                        "documento_base": doc # Guardamos 1 cópia física do documento
                    }
                # Adiciona o número da citação à lista deste documento
                documentos_agrupados[id_doc]["indices"].append(int(num_str))

    # 2. Constrói a lista deduplicada e a String formatada de referências
    documentos_utilizados_final = []
    referencias_formatadas = []

    for id_doc, info in documentos_agrupados.items():
        # Ordena os índices para ficar estético (ex: [1] [3])
        indices_ordenados = sorted(info["indices"])
        tags_citacao = " ".join([f"[{i}]" for i in indices_ordenados])
        
        # Cria a string exata no formato que você solicitou
        ref_str = f"{tags_citacao} 📄 Documento: {id_doc} | Link: {info['url']}"
        referencias_formatadas.append(ref_str)
        
        # Guarda apenas 1 via do documento na lista final de retorno
        documentos_utilizados_final.append(info["documento_base"])

    # 3. Anexa as referências bonitas no final da resposta do LLM (se houver fontes)
    if referencias_formatadas:
        resposta_texto += "\n\n**Fontes Consultadas:**\n" + "\n".join(referencias_formatadas)
    
    # Devolve a resposta pronta para a tela e os objetos deduplicados
    return resposta_texto, documentos_utilizados_final

# ==========================================
# TESTANDO O PIPELINE COMPLETO
# ==========================================

def main():
    pergunta = "Qual o período exato de vigência da prorrogação da jornada de trabalho reduzida para a servidora Luciana Sachetto Nascimento?"
    
    resposta_texto, fontes_utilizadas = consultar_assistente_aneel(pergunta)
    
    print("\n" + "="*50)
    print("🤖 RESPOSTA DO ASSISTENTE:")
    print("="*50)
    print(resposta_texto)
    
    print("\n" + "-"*50)
    print("📚 FONTES UTILIZADAS PARA ESTA RESPOSTA:")
    print("-"*50)
    
    # Exibe os documentos que foram devolvidos como fontes, mostrando o ID e um link (se disponível)
    for doc in fontes_utilizadas:
        id_doc = doc.metadata.get('id_processo', 'ID Desconhecido')
        url = doc.metadata.get('url_documento', 'URL não disponível')
        print(f"📄 Documento: {id_doc} | Link: {url}")

if __name__ == "__main__":
    main()