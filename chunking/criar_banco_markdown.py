import json
from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def processar_json_aneel_markdown(json_data):
    chunks_totais = []
    
    # 1. Extraímos as informações globais e guardamos diretamente nos METADADOS
    metadados_base = {
        "titulo_global": json_data.get('titulo', 'Sem título'),
        "ementa_global": json_data.get('ementa', 'Sem ementa'),
        "id_processo": json_data.get('id', 'sem_id'),
        "data_publicacao": json_data.get('data_publicacao', ''),
        "assunto": json_data.get('assunto', ''),
        "autor": json_data.get('autor', '')
    }
    
    # 2. Configuração do Splitter Estrutural (Markdown)
    headers_para_fatiar = [
        ("#", "Titulo_Principal"),
        ("##", "Secao"),
        ("###", "Subsecao"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_para_fatiar)
    
    # 3. Configuração do Splitter de Segurança (O seu Recursive)
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=154,
        separators=["\n\n", "\n", ".", " ", ""],
        add_start_index=True
    )
    
    # 4. Iteração sobre a lista de documentos (anexos)
    lista_documentos = json_data.get('documentos', [])
    
    for indice, doc in enumerate(lista_documentos):
        # Pega o Markdown, com fallback para texto puro
        conteudo_md = doc.get('texto_extraido_md', doc.get('texto_extraido', ''))
        
        # Prevenção: pula se o texto estiver vazio
        if not conteudo_md.strip():
            continue
            
        # 5. Clonamos os metadados base e adicionamos dados específicos do anexo
        metadados_especificos = metadados_base.copy()
        metadados_especificos["url_documento"] = doc.get('url', 'Sem URL')
        metadados_especificos["indice_documento"] = indice + 1
        
        # 6. Passo A: Fatiamento inteligente pelos títulos do Markdown
        chunks_md = markdown_splitter.split_text(conteudo_md)
        
        # 7. Passo B: Injeção de metadados e Fatiamento de Segurança
        for chunk in chunks_md:
            # O chunk.metadata já contém as seções do Markdown (ex: {"Secao": "DECISÃO"}).
            # O comando .update() funde as seções do Markdown com os nossos metadados globais.
            chunk.metadata.update(metadados_especificos)
            
            # Passamos o bloco pelo RecursiveSplitter para garantir que nenhum passe de 1024 caracteres
            sub_chunks = recursive_splitter.split_documents([chunk])
            
            # Adicionamos à lista final
            chunks_totais.extend(sub_chunks)
            
    return chunks_totais

def salvar_chunks_em_disco(lista_de_chunks, caminho_arquivo="chunks/chunks_markdown.jsonl"):
    """
    Salva os chunks no disco, garantindo que a pasta exista.
    """
    # Cria a pasta 'chunks' automaticamente se ela não existir
    caminho_path = Path(caminho_arquivo)
    caminho_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(caminho_path, 'a', encoding='utf-8') as f:
        for chunk in lista_de_chunks:
            chunk_dict = {
                "texto": chunk.page_content,
                "metadados": chunk.metadata
            }
            f.write(json.dumps(chunk_dict, ensure_ascii=False) + '\n')

def main():
    arquivos_sucesso = 0
    arquivos_falha = 0
    total_chunks_gerados = 0
    arquivos_erro_json = []
    
    pasta_json = Path("json_teste")
    arquivos_json = sorted(pasta_json.glob("*.json"))
    
    arquivo_saida = "chunks/chunks_markdown.jsonl"
    for caminho_json in arquivos_json:
        try:
            with open(caminho_json, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
            chunks = processar_json_aneel_markdown(json_data)
            
            if chunks: # Só salva se o documento gerou algum conteúdo
                salvar_chunks_em_disco(chunks, arquivo_saida)
                
            arquivos_sucesso += 1
            total_chunks_gerados += len(chunks)
            print(f"[OK] {caminho_json.name} processado. +{len(chunks)} chunks.")
            
        except Exception as e:
            arquivos_falha += 1
            print(f"[ERRO] Falha ao processar {caminho_json.name}: {e}")
            arquivos_erro_json.append(caminho_json.name)
            
    print("-" * 30)
    print("Resumo da Execução:")
    print(f"Arquivos processados com sucesso: {arquivos_sucesso}")
    print(f"Arquivos com falha: {arquivos_falha}")
    print(f"Total de chunks salvos no JSONL: {total_chunks_gerados}")
    
    if arquivos_erro_json:
        with open("erros_processamento.txt", 'w', encoding='utf-8') as f:
            for nome_arquivo in arquivos_erro_json:
                f.write(nome_arquivo + '\n')

if __name__ == "__main__":
    main()