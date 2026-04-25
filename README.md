# Pipeline RAG

Este repositório contém o pipeline de construção de um sistema RAG desenvolvido para um desafio do Grupo de Estudos de NLP da Universidade Federal de Goiás.

O projeto reúne os scripts utilizados nas etapas de coleta, normalização, parsing, chunking, geração de embeddings, indexação e execução de uma versão local do RAG ainda não adaptada para API.

A API que encapsula este sistema está armazenada em outro repositório:

Link do repositório da API: ([api_rag](https://github.com/kelvin-de-oliveira/api-rag))

## Visão geral

O pipeline trabalha com documentos da ANEEL e organiza o fluxo de preparação dos dados até a consulta em um sistema RAG.

Este repositório inclui:

- scripts para download de arquivos PDF, HTML e HTM;
- script para limpeza e normalização de metadados;
- script para extração de texto dos documentos;
- script para divisão dos textos em chunks;
- script para geração de embeddings e armazenamento em banco vetorial;
- script para indexação lexical no Elasticsearch;
- script com uma versão local do RAG ainda não encapsulada em API.

## Módulos principais

### Coleta de documentos

Disponível em `parsing/scrapping`:

- `scrapper.py`
- `html_downloader.py`

#### `scrapper.py`

Script responsável pelo download dos PDFs a partir dos arquivos JSON de entrada.

Ele percorre os registros presentes nos JSONs, identifica os documentos associados a cada registro e tenta baixar os arquivos PDF encontrados.

Neste módulo, `cloudscraper` é usado para criar uma sessão HTTP com comportamento semelhante ao de um navegador. A biblioteca `requests` é usada como base para as requisições HTTP, enquanto `urllib3 Retry` e `HTTPAdapter` são utilizados para configurar retentativas automáticas em casos de falhas temporárias, como erros 429, 500, 502, 503 e 504.

O `ThreadPoolExecutor` é utilizado para permitir downloads em paralelo, conforme a quantidade de workers configurada.

Além do download dos arquivos, o script também gera relatórios de execução. Em caso de falhas, são produzidos relatórios em CSV e JSON com informações como URL, nome do arquivo, data do registro, título, tipo do PDF, tipo do erro, mensagem de erro, status HTTP, número de tentativas e prévia da resposta recebida.

#### `html_downloader.py`

Script responsável pelo download de arquivos HTML e HTM a partir de um CSV contendo as colunas `url` e `data_registro`.

Esse CSV foi gerado a partir do relatório de erro do `scrapper.py`, contemplando documentos que não foram obtidos como PDF e precisaram ser tratados como páginas HTML/HTM.

Neste módulo, `cloudscraper` também é usado para criar uma sessão HTTP com características de navegador. Quando essa criação não é possível, o script usa `requests.Session` como alternativa. O `Retry` e o `HTTPAdapter` são utilizados para configurar retentativas em falhas temporárias de requisição.

O script salva os arquivos HTML/HTM em pastas organizadas pela data do registro. Ele também faz controle de tentativas em caso de falhas HTTP, como 403, 429 e 503, aplica pausas entre requisições e evita baixar novamente arquivos que já existem no diretório de destino.

### Normalização de metadados

Disponível em `parsing`:

- `clean_and_normalize_metadata.py`

Script responsável por normalizar os metadados dos registros da ANEEL para o modelo utilizado nas próximas etapas do pipeline.

Ele normaliza tipos de documentos, datas, ementa, assunto, situação e demais campos presentes nos registros.

### Parsing

Disponível em `parsing`:

- `extracting_text_mp.py`

Script responsável pela extração de texto dos arquivos PDF, HTML e HTM.

A extração é feita com uma abordagem híbrida: para arquivos PDF, utiliza `fitz` e `pdfplumber`; para arquivos HTML e HTM, utiliza `BeautifulSoup`. O script também usa `sqlite3` para controle de progresso, `logging` para geração de logs, `argparse` para receber os diretórios de entrada e saída, e `multiprocessing` para processamento paralelo.

As extensões suportadas pelo módulo são `.pdf`, `.html` e `.htm`.

Em PDFs, o script detecta páginas com tabelas usando `fitz` e extrai tabelas com `pdfplumber`, convertendo-as para Markdown quando necessário. Em HTML/HTM, o script remove tags como `script`, `style`, `nav`, `header` e `footer`, extrai o texto com `BeautifulSoup` e também converte tabelas HTML para Markdown.

O resultado da extração é salvo de volta nos JSONs, preenchendo os campos `texto_extraido`, `texto_extraido_md` e `tem_tabela`. O processamento é feito com workers configuráveis, e o progresso é registrado em SQLite pelo processo principal.

### Chunking

Disponível em `chunking`:

- `chunking.py`

Script responsável pela divisão dos textos extraídos em chunks.

Ele usa `MarkdownHeaderTextSplitter` e `RecursiveCharacterTextSplitter`, ambos de `langchain_text_splitters`.

O processo é feito em duas etapas:

1. divisão estrutural por cabeçalhos Markdown;
2. divisão recursiva de segurança com `chunk_size=1024` e `chunk_overlap=154`.

Os chunks são salvos no arquivo `chunks/chunks.jsonl`, mantendo `page_content` e `metadata` em formato compatível com LangChain.

O script também possui controle de checkpoints, registro de erros e contagem total de chunks gerados.

### Embedding

Disponível em `embedding`:

- `embedding.py`

Script responsável por gerar embeddings a partir dos chunks salvos em `chunks/chunks.jsonl`.

Ele usa:

- `langchain_google_genai`;
- `GoogleGenerativeAIEmbeddings`;
- `langchain_chroma`;
- `Chroma`;
- `langchain_core.documents.Document`;
- `dotenv`;
- `tqdm`.

O modelo configurado para embeddings é `models/gemini-embedding-001`.

O banco vetorial é persistido no diretório `banco_chroma`.

O processamento é feito em lotes de 100 documentos, com checkpoint em `embedding_checkpoint.txt`. O script também possui retry exponencial para lidar com erros ou limites da API.

### Indexação lexical

Disponível em `gerador_elasticsearch`:

- `gerador_elasticsearch.py`

Script responsável por popular um índice do Elasticsearch a partir do arquivo `chunks/chunks.jsonl`.

Ele usa `langchain_elasticsearch.ElasticsearchStore` com estratégia `BM25RetrievalStrategy`.

Configurações presentes no arquivo:

- URL do Elasticsearch: `http://localhost:9200`;
- nome do índice: `aneel_lexical`;
- tamanho do lote: `500`;
- arquivo de entrada: `chunks/chunks.jsonl`.

### Versão local do RAG

Disponível em `RAG`:

- `RAG.py`

Este arquivo contém uma versão local do sistema RAG ainda não adaptada para API.

Ele usa recuperação híbrida, combinando busca lexical com Elasticsearch/BM25 e busca vetorial com ChromaDB/Gemini Embeddings.

O modelo generativo configurado é `gemini-2.5-flash`, e o modelo de embedding configurado é `models/gemini-embedding-001`.
