import json
import time
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

import sys
from pathlib import Path

pasta_atual = Path(__file__).resolve().parent
raiz_projeto = pasta_atual.parent

# Garante que a raiz do projeto esteja no caminho de importacao.
if str(raiz_projeto) not in sys.path:
    sys.path.append(str(raiz_projeto))

try:
    # Forma preferida: importa como modulo dentro da pasta rag_final.
    from rag_final.rag_final import consultar_assistente_aneel
except ModuleNotFoundError:
    # Fallback para ambientes em que rag_final e tratado como arquivo direto.
    pasta_modulo_rag = raiz_projeto / "rag_final"
    if str(pasta_modulo_rag) not in sys.path:
        sys.path.append(str(pasta_modulo_rag))
    from rag_final import consultar_assistente_aneel

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env, se existir

def avaliar_rag_com_juiz(arquivo_dataset, arquivo_saida):
    # 1. Instanciando o Juiz
    # Usamos temperature=0.0 para que o juiz seja totalmente determinístico, frio e analítico.
    juiz_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
    
    # 2. O Prompt da Tríade do RAG
    template_juiz = """Você é um auditor de qualidade técnico, estrito e imparcial.
    Sua tarefa é avaliar uma resposta gerada por um sistema RAG com base em Despachos da ANEEL.

    PERGUNTA DO USUÁRIO: {pergunta}
    GABARITO ESPERADO: {gabarito}
    CONTEXTO RECUPERADO PELO BANCO: {contexto}
    RESPOSTA DO RAG A SER AVALIADA: {resposta_rag}

    Avalie a RESPOSTA DO RAG dando uma nota estrita de 1 a 5 para cada métrica:
    1. "fidelidade": A resposta alucinou informações? (5 = 100% fiel ao contexto. 1 = Inventou dados).
    2. "relevancia_resposta": Respondeu diretamente à pergunta, cruzando corretamente com o gabarito? (5 = Perfeita. 1 = Evasiva/Incorreta).
    3. "relevancia_contexto": O contexto fornecido pelo banco tinha a informação necessária? (5 = Tinha tudo. 1 = Trouxe documentos inúteis).

    Retorne APENAS um objeto JSON válido, sem formatação markdown (```json).
    {{
      "fidelidade": {{"nota": 5, "justificativa": "..."}},
      "relevancia_resposta": {{"nota": 4, "justificativa": "..."}},
      "relevancia_contexto": {{"nota": 5, "justificativa": "..."}}
    }}
    """
    prompt = PromptTemplate(
        template=template_juiz, 
        input_variables=["pergunta", "gabarito", "contexto", "resposta_rag"]
    )

    # 3. Carregar o arquivo da prova (o seu JSON gerado anteriormente)
    print(f"Carregando o dataset: {arquivo_dataset}...")
    with open(arquivo_dataset, 'r', encoding='utf-8') as f:
        perguntas_teste = json.load(f)

    resultados_finais = []
    
    print(f"⚖️ Iniciando o Tribunal da IA para {len(perguntas_teste)} perguntas...")
    print("💡 DICA: Use Ctrl+C para parar a qualquer momento e salvar o relatório parcial.")
    
    try:
        for i, item in enumerate(perguntas_teste, 1):
            pergunta = item["pergunta"]
            gabarito = item["resposta_esperada"]
            
            print(f"\n[{i}/{len(perguntas_teste)}] Testando: {pergunta[:70]}...")
            
            # ==========================================
            # PASSO A: O SEU RAG PRESTA A PROVA
            # ==========================================
            resposta_rag, documentos_recuperados = consultar_assistente_aneel(pergunta)
            
            # Junta os textos recuperados para o Juiz poder analisar se a busca foi boa
            contexto_str = "\n\n".join([doc.page_content for doc in documentos_recuperados])
            
            # ==========================================
            # PASSO B: O JUIZ CORRIGE A PROVA
            # ==========================================
            prompt_pronto = prompt.format(
                pergunta=pergunta, gabarito=gabarito, 
                contexto=contexto_str, resposta_rag=resposta_rag
            )
            
            sucesso = False
            tentativas = 0
            
            while not sucesso and tentativas < 3:
                try:
                    resposta_juiz = juiz_llm.invoke(prompt_pronto)
                    
                    # Blindagem do JSON
                    conteudo = resposta_juiz.content
                    if isinstance(conteudo, list):
                        texto_bruto = "".join([p.get("text", "") for p in conteudo if isinstance(p, dict)])
                    else:
                        texto_bruto = str(conteudo)
                        
                    texto_limpo = texto_bruto.replace("```json", "").replace("```", "").strip()
                    avaliacao = json.loads(texto_limpo)
                    
                    # Salva todas as informações em uma linha da nossa futura tabela
                    resultados_finais.append({
                        "Pergunta": pergunta,
                        "Tipo": item.get("tipo", "Normal"),
                        "Gabarito": gabarito,
                        "Resposta_do_RAG": resposta_rag,
                        "Nota_Fidelidade": avaliacao["fidelidade"]["nota"],
                        "Just_Fidelidade": avaliacao["fidelidade"]["justificativa"],
                        "Nota_Rel_Resposta": avaliacao["relevancia_resposta"]["nota"],
                        "Just_Rel_Resposta": avaliacao["relevancia_resposta"]["justificativa"],
                        "Nota_Rel_Contexto": avaliacao["relevancia_contexto"]["nota"],
                        "Just_Rel_Contexto": avaliacao["relevancia_contexto"]["justificativa"]
                    })
                    
                    sucesso = True
                    print(f"✅ Notas -> Fid: {avaliacao['fidelidade']['nota']} | Rel. Resp: {avaliacao['relevancia_resposta']['nota']} | Rel. Ctx: {avaliacao['relevancia_contexto']['nota']}")
                    
                    # Pausa suave para não acionar o rate limit nem na busca, nem na avaliação
                    time.sleep(4)
                    
                except Exception as e:
                    erro_str = str(e)
                    if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                        tentativas += 1
                        espera = 15 * tentativas
                        print(f"🛑 Radar do Juiz apitou. Pausando por {espera}s...")
                        time.sleep(espera)
                    else:
                        print(f"⚠️ Erro ao decodificar JSON do juiz: {e}. Tentando novamente...")
                        tentativas += 1
                        time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupção manual (Ctrl+C). Fechando o tribunal e salvando os votos...")

    # ==========================================
    # PASSO C: GERAR O BOLETIM DE NOTAS (CSV)
    # ==========================================
    if resultados_finais:
        df = pd.DataFrame(resultados_finais)
        # utf-8-sig garante que os acentos do português fiquem perfeitos ao abrir no Excel
        df.to_csv(arquivo_saida, index=False, encoding='utf-8-sig') 
        
        print(f"\n📊 Relatório salvo com sucesso em: {arquivo_saida}")
        
        print("\n" + "=" * 40)
        print("🏆 BOLETIM DE DESEMPENHO MÉDIO:")
        print("=" * 40)
        print(f"Fidelidade (Não Alucinar): {df['Nota_Fidelidade'].mean():.2f} / 5.0")
        print(f"Precisão da Resposta:      {df['Nota_Rel_Resposta'].mean():.2f} / 5.0")
        print(f"Qualidade do ChromaDB:     {df['Nota_Rel_Contexto'].mean():.2f} / 5.0")
        print("=" * 40)
    else:
        print("Nenhum resultado foi processado.")

if __name__ == "__main__":
    # Vamos começar testando o dataset simples primeiro
    arquivo_entrada = "gabarito_rag_comp_25.json" # Altere para o nome exato do seu arquivo
    arquivo_relatorio = "relatorio_complexo_com_es_e_sem_multq_k6.csv"
    
    avaliar_rag_com_juiz(arquivo_entrada, arquivo_relatorio)