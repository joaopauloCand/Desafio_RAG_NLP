# Embedding Script

Este script gera embeddings para os chunks já preparados em `chunks/chunks.jsonl` e salva os vetores em um banco vetorial Chroma persistido em `banco_chroma/`.

## O que o script faz

- lê os chunks do arquivo `chunks/chunks.jsonl`;
- converte cada registro em um `Document` do LangChain;
- gera embeddings com `GoogleGenerativeAIEmbeddings`;
- grava os vetores no diretório `banco_chroma/`;
- mantém um checkpoint em `embedding_checkpoint.txt` para retomar a execução de onde parou;
- exibe progresso com `tqdm`;
- usa retry exponencial quando a API falha ou atinge limite temporário.

## Arquivos usados

Entrada:

- `chunks/chunks.jsonl`
- `chunks/total_chunks_gerados.txt`
- `embedding_checkpoint.txt`

Saída:

- `banco_chroma/`
- `embedding_checkpoint.txt`

## Dependências

O script usa principalmente:

- `langchain-google-genai`
- `langchain-chroma`
- `langchain-core`
- `python-dotenv`
- `tqdm`

Para evitar instalar pacotes desnecessários para quem só usa etapas posteriores do pipeline, esta pasta possui um arquivo dedicado:

- `embedding/requirements.txt`

Instale apenas se quiser executar/refazer esta etapa:

```bash
pip install -r embedding/requirements.txt
```

## Configuração necessária

Antes de executar, configure a variável de ambiente `GEMINI_API_KEY` em um arquivo `.env` na raiz do projeto:

```env
GEMINI_API_KEY="sua_chave_aqui"
```

O script carrega automaticamente o `.env` com `load_dotenv()`.

## Execução

Na raiz do projeto, execute:

```bash
python embedding/embedding.py
```

## Comportamento do checkpoint

O progresso é salvo em `embedding_checkpoint.txt` após cada lote processado.

Se o valor do checkpoint já for maior ou igual ao total esperado de chunks, o script encerra sem processar nada.

## Parâmetros importantes

Valores definidos no script:

- tamanho do lote: `100`
- diretório do Chroma: `banco_chroma`
- arquivo JSONL de entrada: `chunks/chunks.jsonl`
- modelo de embeddings: `models/gemini-embedding-001`

## Observações

- O script assume que os chunks já foram gerados antes da etapa de embeddings.
- Se ocorrer uma falha temporária na API, o lote é tentado novamente até 8 vezes.
- O diretório `banco_chroma/` precisa existir ou ser criado pela execução do Chroma.
