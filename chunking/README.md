# Chunking Script

Este script transforma os JSONs já extraídos em chunks prontos para as etapas seguintes do pipeline RAG.

## O que o script faz

- percorre os arquivos `.json` em `json_parsed/`;
- lê o conteúdo textual já extraído em `texto_extraido_md` ou `texto_extraido`;
- combina os metadados do documento com os metadados de cada anexo;
- faz o chunking em duas etapas:
  - separação estrutural por cabeçalhos Markdown;
  - divisão recursiva de segurança para limitar o tamanho dos trechos;
- grava os chunks em formato JSONL compatível com LangChain;
- mantém controle de arquivos processados, erros e contagem total de chunks gerados.

## Entradas

O script lê os arquivos da pasta:

- `json_parsed/`

Campos esperados nos JSONs:

- `titulo`
- `ementa`
- `id`
- `data_publicacao`
- `assunto`
- `autor`
- `documentos[]`
- `texto_extraido_md`
- `texto_extraido`
- `url`

## Saídas

Arquivos gerados ou atualizados:

- `chunks/chunks.jsonl`
- `chunks/checkpoints_chunking.txt`
- `chunks/erros_chunking.txt`
- `chunks/total_chunks_gerados.txt`

## Estratégia de chunking

O processamento usa dois splitters do LangChain:

- `MarkdownHeaderTextSplitter`, com os cabeçalhos `#`, `##` e `###`;
- `RecursiveCharacterTextSplitter`, com `chunk_size=1024` e `chunk_overlap=154`.

Essa combinação preserva a estrutura do texto quando possível e ainda aplica uma divisão de segurança para evitar chunks grandes demais.

## Controle de progresso

O script evita reprocessar arquivos já concluídos por meio de `chunks/checkpoints_chunking.txt`.

Se ocorrer erro durante o processamento de um arquivo, o nome dele é registrado em `chunks/erros_chunking.txt`.

Ao final, o total de chunks gerados é acumulado em `chunks/total_chunks_gerados.txt`.

## Execução

Na raiz do projeto, execute:

```bash
python chunking/chunking.py
```

## Dependências

O script usa principalmente:

- `langchain-text-splitters`
- `tqdm`

Para evitar instalar pacotes desnecessários para quem só usa etapas posteriores do pipeline, esta pasta possui um arquivo dedicado:

- `chunking/requirements.txt`

Instale apenas se quiser executar/refazer esta etapa:

```bash
pip install -r chunking/requirements.txt
```

## Observações

- O script assume que a etapa de extração de texto já foi concluída.
- Apenas arquivos com extensão `.json` em `json_parsed/` são processados.
- Cada chunk é salvo com `page_content` e `metadata` para uso direto nas próximas etapas do pipeline.