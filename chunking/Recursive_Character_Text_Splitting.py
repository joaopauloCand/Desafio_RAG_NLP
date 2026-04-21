import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
def processar_json_aneel(json_data):
    chunks_totais = [] # Lista principal que vai acumular todos os pedaços
    
    # 1. Extraímos as informações globais que valem para todo o JSON
    titulo = json_data.get('titulo', 'Sem título')
    ementa = json_data.get('ementa', 'Sem ementa')
    
    # Metadados base (comuns a todos os documentos deste JSON)
    metadados_base = {
        "id_processo": json_data.get('id', 'sem_id'),
        "data_publicacao": json_data.get('data_publicacao', ''),
        "assunto": json_data.get('assunto', ''),
        "autor": json_data.get('autor', '')
    }
    
    # 2. Configuração do Splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=154,
        separators=["\n\n", "\n", ".", " ", ""],
        add_start_index=True
    )
    
    # 3. Iteração sobre a lista de documentos (pode ter 1 ou vários)
    lista_documentos = json_data.get('documentos', [])
    
    for indice, doc in enumerate(lista_documentos):
        # Prioriza o Markdown (para preservar tabelas), faz fallback pro texto normal
        conteudo_base = doc.get('texto_extraido_md', doc.get('texto_extraido', ''))
        
        # Prevenção de erro: se o documento estiver vazio, pula para o próximo
        if not conteudo_base:
            continue
            
        # Injetamos o contexto global em cada subdocumento
        texto_completo = f"Título: {titulo}\nEmenta: {ementa}\nAnexo/Parte {indice + 1}:\n\n{conteudo_base}"
        
        # 4. Clonamos os metadados base e adicionamos dados específicos deste documento
        metadados_especificos = metadados_base.copy()
        metadados_especificos["url_documento"] = doc.get('url', 'Sem URL')
        metadados_especificos["indice_documento"] = indice + 1
        
        # 5. Criamos os chunks deste documento específico
        chunks_do_documento = splitter.create_documents([texto_completo], metadatas=[metadados_especificos])
        
        # 6. Adicionamos à lista principal (extend em vez de append para manter a lista plana)
        chunks_totais.extend(chunks_do_documento)
        
    return chunks_totais

def salvar_chunks_em_disco(lista_de_chunks, caminho_arquivo="chunks\\chunks_recursive.jsonl"):
    """
    Pega os objetos Document da RAM e salva no disco.
    Usamos 'a' (append) para ir adicionando no fim do arquivo sem apagar o que já tem.
    """
    with open(caminho_arquivo, 'a', encoding='utf-8') as f:
        for chunk in lista_de_chunks:
            # Transformamos o objeto Document de volta em um dicionário comum
            chunk_dict = {
                "texto": chunk.page_content,
                "metadados": chunk.metadata
            }
            # Escrevemos a linha e pulamos para a próxima
            f.write(json.dumps(chunk_dict, ensure_ascii=False) + '\n')

def main():
    arquivos_sucesso = 0
    arquivos_falha = 0
    total_chunks_gerados = 0
    arquivos_erro_json = []
    pasta_json = Path("json_teste")
    arquivos_json = sorted(pasta_json.glob("*.json"))

    for caminho_json in arquivos_json:
        try:
            with open(caminho_json, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            chunks = processar_json_aneel(json_data)
            salvar_chunks_em_disco(chunks)
            arquivos_sucesso += 1
            total_chunks_gerados += len(chunks)
            print(f"[OK] {caminho_json.name} processado. +{len(chunks)} chunks.")
        except Exception as e:
            arquivos_falha += 1
            print(f"[ERRO] Falha ao processar {caminho_json.name}: {e}")
            arquivos_erro_json.append(caminho_json.name)
    print("-" * 30)
    print(f"Resumo da Execução:")
    print(f"Arquivos processados com sucesso: {arquivos_sucesso}")
    print(f"Arquivos com falha: {arquivos_falha}")
    print(f"Total de chunks salvos no JSONL: {total_chunks_gerados}")
    if arquivos_erro_json:
        with open("erros_processamento.txt", 'w', encoding='utf-8') as f:
            for nome_arquivo in arquivos_erro_json:
                f.write(nome_arquivo + '\n')

if __name__ == "__main__":
    main()