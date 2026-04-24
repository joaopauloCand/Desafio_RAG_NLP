import json
import math
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_elasticsearch import ElasticsearchStore

TAMANHO_LOTE = 500 #Quantidade de documentos a serem enviados por lote para o Elasticsearch (ajuste conforme necessário)

def gerador_de_lotes_es(caminho_arquivo: str, tamanho_lote: int) -> iter:
    """Lê o JSONL de forma preguiçosa para não sobrecarregar a RAM do VS Code."""
    lote_atual = []
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            dados = json.loads(linha)
            doc = Document(page_content=dados["page_content"], metadata=dados["metadata"])
            lote_atual.append(doc)
            
            if len(lote_atual) == tamanho_lote:
                yield lote_atual
                lote_atual = []
        if lote_atual:
            yield lote_atual

def popular_elasticsearch(arquivo_jsonl: str, nome_indice: str, url_es: str = "http://localhost:9200", tamanho_lote: int = TAMANHO_LOTE) -> None:
    """Função principal para popular o Elasticsearch com os chunks do JSONL."""
    print("🚀 Iniciando ingestão no Elasticsearch (Busca Lexical/BM25)...")
    
    # Conecta ao ES e define a estratégia EXCLUSIVA de BM25
    banco_lexical = ElasticsearchStore(
        es_url=url_es,
        index_name=nome_indice,
        strategy=ElasticsearchStore.BM25RetrievalStrategy()
    )
    
    # Contamos o total de linhas apenas para a barra de progresso
    with open(arquivo_jsonl, 'r', encoding='utf-8') as f:
        total_chunks = sum(1 for _ in f)
        
    total_lotes = math.ceil(total_chunks / tamanho_lote) if total_chunks else 0
    lotes = gerador_de_lotes_es(arquivo_jsonl, tamanho_lote)
    
    chunks_inseridos = 0
    for lote in tqdm(lotes, total=total_lotes, desc="Enviando para o Elasticsearch"):
        banco_lexical.add_documents(lote)
        chunks_inseridos += len(lote)
        
    print(f"\n✅ Concluído! {chunks_inseridos} chunks indexados no Elasticsearch.")

if __name__ == "__main__":
    arquivo_jsonl = "chunks\\chunks.jsonl"  # O arquivo JSONL gerado pelo chunking.py
    nome_indice = "aneel_lexical"  # Nome do índice no Elasticsearch
    popular_elasticsearch(arquivo_jsonl, nome_indice)