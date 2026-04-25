# Elasticsearch Generator

Este script popula um índice do Elasticsearch com os chunks já gerados em `chunks/chunks.jsonl`, usando a estratégia BM25 para busca lexical.

## O que o script faz

- lê o arquivo `chunks/chunks.jsonl` de forma preguiçosa para evitar alto consumo de memória;
- converte cada linha em um `Document` do LangChain;
- agrupa os documentos em lotes;
- envia os lotes para o Elasticsearch;
- mostra o progresso com `tqdm`.

## Entrada

O script espera o arquivo:

- `chunks/chunks.jsonl`

Cada linha deve conter um objeto JSON com pelo menos os campos:

- `page_content`
- `metadata`

## Saída

O resultado da execução é a indexação dos chunks no Elasticsearch no índice:

- `aneel_lexical`

## Configurações principais

Valores definidos no script:

- tamanho do lote: `500`
- URL do Elasticsearch: `http://localhost:9200`
- nome do índice: `aneel_lexical`
- arquivo de entrada: `chunks/chunks.jsonl`

## Dependências

O script usa principalmente:

- `langchain-elasticsearch`
- `langchain-core`
- `tqdm`

A lista completa de dependências está em `requirements.txt`.

## Execução

Na raiz do projeto, execute:

```bash
python gerador_elasticsearch/gerador_elasticsearch.py
```

## Observações

- O Elasticsearch precisa estar acessível em `http://localhost:9200` antes da execução.
- O script calcula o total de chunks para exibir a barra de progresso, então o arquivo JSONL precisa existir e conter linhas válidas.