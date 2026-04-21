from dotenv import load_dotenv
import os
import json
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env, se existir

def carregar_textos_dos_jsons(pasta_arquivos, limite=10):
    """
    Lê os arquivos JSON originais da ANEEL e extrai o texto para análise.
    """
    documentos = []
    print(f"Buscando arquivos na pasta '{pasta_arquivos}'...")
    
    arquivos = [f for f in os.listdir(pasta_arquivos) if f.endswith('.json')]
    arquivos = arquivos[:limite] # Pega apenas os 'limite' primeiros para o teste
    
    for nome_arquivo in arquivos:
        caminho_completo = os.path.join(pasta_arquivos, nome_arquivo)
        with open(caminho_completo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            # Tenta pegar o texto formatado, fallback pro texto normal
            texto = dados.get('documentos', [{}])[0].get('texto_extraido_md', 
                    dados.get('documentos', [{}])[0].get('texto_extraido', 'Texto não encontrado'))
            
            documentos.append({
                "id": dados.get("id", nome_arquivo),
                "texto": texto
            })
            
    print(f"{len(documentos)} documentos carregados.")
    return documentos

def gerar_perguntas_gabarito():
    # 1. Configurando o LLM
    # temperature=0.3 para manter o modelo criativo nas perguntas, mas rigoroso nos fatos
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
    
    # 2. O Prompt de Engenharia Reversa (Exatamente o que definimos)
    template = """Você é um Engenheiro de Dados Sênior especializado em criar datasets de avaliação (Ground Truth) para sistemas RAG jurídicos e administrativos.
    Sua tarefa é ler o documento (Despacho da ANEEL) fornecido abaixo e realizar a "Engenharia Reversa": gerar 3 perguntas realistas que um analista faria para encontrar as informações contidas neste texto.

    REGRAS ESTABELECIDAS:
    1. Ancoragem Estrita: A resposta DEVE estar explicitamente contida no texto fornecido.
    2. Tipos de Perguntas: Crie 1 Pergunta de Fato Direto, 1 de Cruzamento/Raciocínio e 1 de Resumo.
    3. Retorne APENAS um array JSON válido. Sem formatação markdown, sem crases (```json).

    Estrutura EXATA do JSON esperado:
    [
      {{
        "tipo": "Fato Direto",
        "pergunta": "...",
        "resposta_esperada": "...",
        "id_documento_fonte": "{id_doc}"
      }},
      ...
    ]

    DOCUMENTO PARA ANÁLISE:
    {texto_documento}
    """
    
    prompt = PromptTemplate(template=template, input_variables=["id_doc", "texto_documento"])
    
    # 3. Carregando os dados
    pasta_originais = "./json_teste" # <-- ALTERE PARA A PASTA ONDE ESTÃO SEUS JSONS
    meus_documentos = carregar_textos_dos_jsons(pasta_originais)
    
    dataset_final = []
    
    print("-" * 40)
    print("Iniciando a geração do Ground Truth...")
    
    # 4. O Loop de Geração com Proteção (Rate Limit)
    for i, doc in enumerate(meus_documentos, 1):
        print(f"[{i}/{len(meus_documentos)}] Analisando documento: {doc['id']}...")
        
        prompt_pronto = prompt.format(id_doc=doc["id"], texto_documento=doc["texto"][:4000]) # Limita a 4000 caracteres para segurança
        
        sucesso = False
        tentativas = 0
        
        while not sucesso and tentativas < 3:
            try:
                # Chama o Gemini
                resposta = llm.invoke(prompt_pronto)
                
                # --- INÍCIO DA CORREÇÃO ---
                conteudo = resposta.content
                
                # Verifica se o LangChain devolveu uma lista de blocos multimodais
                if isinstance(conteudo, list):
                    # Extrai a string de dentro do bloco de texto
                    texto_bruto = "".join([parte.get("text", "") for parte in conteudo if isinstance(parte, dict)])
                else:
                    # Se já for string pura, segue o jogo
                    texto_bruto = str(conteudo)
                
                # Agora sim limpamos a string com total segurança
                texto_limpo = texto_bruto.replace("```json", "").replace("```", "").strip()
                # --- FIM DA CORREÇÃO ---
                
                # Converte a string retornada em uma lista de dicionários Python
                perguntas_geradas = json.loads(texto_limpo)
                dataset_final.extend(perguntas_geradas)
                
                sucesso = True
                time.sleep(3)
                
            except json.JSONDecodeError:
                print(f"⚠️ O modelo não retornou um JSON limpo no doc {doc['id']}. Tentando novamente...")
                tentativas += 1
                time.sleep(5)
            except Exception as e:
                erro_str = str(e)
                # Verifica se é erro de limite de cota
                if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                    tentativas += 1 # <-- AQUI ESTAVA O MEU ERRO! Faltava essa linha.
                    
                    # Calcula o tempo de espera: 15s na primeira, 30s na segunda, 45s na terceira
                    espera = 15 * tentativas 
                    
                    print(f"🛑 Radar apitou (Erro 429). Tentativa {tentativas}/3. Pausando por {espera}s...")
                    time.sleep(espera)
                else:
                    print(f"❌ Erro fatal desconhecido: {e}")
                    break
        
        # Se saiu do loop while e não teve sucesso, avisa e pula para o próximo arquivo
        if not sucesso:
            print(f"⏭️ Pulando o documento {doc['id']} após falhar 3 vezes consecutivas. Pode ser limite diário.")
    
    # 5. Salvando o Gabarito no Disco
    arquivo_saida = "gabarito_rag_10_docs.json"
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(dataset_final, f, ensure_ascii=False, indent=4)
        
    print("-" * 40)
    print(f"✅ Geração concluída! {len(dataset_final)} perguntas geradas.")
    print(f"Dataset salvo com sucesso em: {arquivo_saida}")

if __name__ == "__main__":
    # Certifique-se de alterar a variável 'pasta_originais' na linha 53 antes de rodar!
    gerar_perguntas_gabarito()