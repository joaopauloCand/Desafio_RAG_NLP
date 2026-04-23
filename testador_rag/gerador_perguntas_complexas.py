import os
from dotenv import load_dotenv
import json
import time
import random
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env, se existir

def carregar_textos_dos_jsons(pasta_arquivos: str, limite:int=50) -> list[dict]:
    """Carrega os textos dos arquivos JSON da pasta especificada."""
    documentos = []
    print(f"Buscando arquivos na pasta '{pasta_arquivos}'...")
    arquivos = [f for f in os.listdir(pasta_arquivos) if f.endswith('.json')][:limite]
    
    for nome_arquivo in arquivos:
        caminho_completo = os.path.join(pasta_arquivos, nome_arquivo)
        with open(caminho_completo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            texto = dados.get('documentos', [{}])[0].get('texto_extraido_md', 
                    dados.get('documentos', [{}])[0].get('texto_extraido', 'Texto não encontrado'))
            
            documentos.append({
                "id": dados.get("id", nome_arquivo),
                "texto": texto
            })
            
    print(f"{len(documentos)} documentos carregados.")
    return documentos

def gerar_perguntas_multihop() -> None:
    """Função principal que gera perguntas complexas de múltiplos saltos (Multi-hop) a partir dos documentos da ANEEL."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.4)
    
    # prompt força a IA a cruzar as informações
    template = """Você é um Engenheiro de Dados Sênior testando um sistema RAG.
    Abaixo, forneço um lote com {num_docs} documentos diferentes da ANEEL.
    
    Sua tarefa é gerar EXATAMENTE {qtd_perguntas} pergunta(s) de "Multi-hop" (Múltiplos Saltos).
    
    REGRA DE OURO: A pergunta NÃO PODE ser respondida lendo apenas um dos documentos. Ela deve OBRIGATORIAMENTE exigir que o analista extraia uma parte da informação do "Documento A" e cruze com outra informação do "Documento B" (ou C) para chegar à resposta final.
    
    Retorne APENAS um array JSON válido. Sem formatação markdown, sem crases (```json).

    Estrutura EXATA do JSON esperado:
    [
      {{
        "tipo": "Multi-hop (Cruzamento)",
        "pergunta": "...",
        "resposta_esperada": "...",
        "documentos_fonte": ["ID_DO_DOC_1", "ID_DO_DOC_2"] 
      }}
    ]

    LOTE DE DOCUMENTOS PARA ANÁLISE:
    {textos_concatenados}
    """
    
    prompt = PromptTemplate(template=template, input_variables=["num_docs", "qtd_perguntas", "textos_concatenados"])
    
    pasta_originais = "json_teste" # <-- ALTERE PARA A SUA PASTA
    meus_documentos = carregar_textos_dos_jsons(pasta_originais)
    
    dataset_final = []
    TOTAL_PERGUNTAS_DESEJADAS = 25
    
    print("-" * 40)
    print("Iniciando a geração de perguntas Multi-hop...")
    
    # O loop agora roda até batermos a meta de 25 perguntas
    while len(dataset_final) < TOTAL_PERGUNTAS_DESEJADAS:
        perguntas_faltantes = TOTAL_PERGUNTAS_DESEJADAS - len(dataset_final)
        
        # Sorteia 3 documentos aleatórios da base para a IA tentar cruzar
        tamanho_lote = 3
        amostra_docs = random.sample(meus_documentos, tamanho_lote)
        
        # Prepara os textos dos 3 documentos sorteados com marcações claras
        textos_juntos = ""
        for doc in amostra_docs:
            textos_juntos += f"\n\n--- INÍCIO DO DOCUMENTO [ID: {doc['id']}] ---\n{doc['texto'][:3000]}\n--- FIM DO DOCUMENTO ---\n"
        
        # Pede 2 perguntas por vez (ou 1, se só faltar 1 para dar 25)
        perguntas_a_pedir = min(2, perguntas_faltantes)
        
        print(f"Sorteados {tamanho_lote} documentos. Pedindo {perguntas_a_pedir} pergunta(s). (Progresso: {len(dataset_final)}/25)")
        
        prompt_pronto = prompt.format(
            num_docs=tamanho_lote, 
            qtd_perguntas=perguntas_a_pedir, 
            textos_concatenados=textos_juntos
        )
        
        sucesso = False
        tentativas = 0
        try:
            while not sucesso and tentativas < 3:
                try:
                    resposta = llm.invoke(prompt_pronto)
                    
                    # A blindagem que fizemos antes
                    conteudo = resposta.content
                    if isinstance(conteudo, list):
                        texto_bruto = "".join([parte.get("text", "") for parte in conteudo if isinstance(parte, dict)])
                    else:
                        texto_bruto = str(conteudo)
                    
                    texto_limpo = texto_bruto.replace("```json", "").replace("```", "").strip()
                    
                    perguntas_geradas = json.loads(texto_limpo)
                    dataset_final.extend(perguntas_geradas)
                    
                    sucesso = True
                    time.sleep(15) # Pausa segura
                    
                except json.JSONDecodeError:
                    print("⚠️ Falha na formatação do JSON. Tentando novamente este lote...")
                    tentativas += 1
                    time.sleep(5)
                except Exception as e:
                    erro_str = str(e)
                    if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                        tentativas += 1
                        espera = 15 * tentativas 
                        print(f"🛑 Radar apitou. Tentativa {tentativas}/3. Pausando por {espera}s...")
                        time.sleep(espera)
                    else:
                        print(f"❌ Erro fatal: {e}")
                        break
            # 2. O Escudo Mágico: Captura o Ctrl+C
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupção manual detectada (Ctrl+C)!")
            print("Abortando o loop com segurança e pulando para o salvamento...")
    # Corta o array se por acaso o LLM tiver se empolgado e gerado 26 em vez de 25
    dataset_final = dataset_final[:TOTAL_PERGUNTAS_DESEJADAS]
    
    arquivo_saida = "gabarito_rag_comp_25.json"
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(dataset_final, f, ensure_ascii=False, indent=4)
        
    print("-" * 40)
    print(f"✅ Geração Multi-Hop concluída com sucesso! {len(dataset_final)} perguntas salvas em {arquivo_saida}.")

if __name__ == "__main__":
    gerar_perguntas_multihop()