# 🔍 Pipeline RAG - ANEEL

Sistema completo de RAG (Retrieval-Augmented Generation) para consultas sobre documentos da ANEEL, com recuperação híbrida (lexical + vetorial) e interface interativa.

O pipeline foi desenvolvido para documentos da ANEEL, mas pode ser adaptado para outras fontes.

Desenvolvido para um desafio do Grupo de Estudos de NLP da Universidade Federal de Goiás.

A API que encapsula este sistema está armazenada em outro repositório:

Link do repositório da API: ([api_rag](https://github.com/kelvin-de-oliveira/api-rag))

Todos os dados utilizados aqui podem ser encontrados em: ([dataset_huggingface](https://huggingface.co/datasets/joaopauloCand/Embeddings_RAG_ANEEL/tree/main))

Desenvolvido para um desafio do Grupo de Estudos de NLP da Universidade Federal de Goiás.

## O que o pipeline faz

- 📥 Coleta documentos em PDF, HTML e HTM da ANEEL
- 🧹 Normaliza e limpa metadados dos registros
- 📄 Extrai texto dos documentos com abordagem híbrida
- ✂️ Divide os textos em chunks estruturados com overlap
- 🧠 Gera embeddings vetoriais com Google Gemini ou BGE-M3
- 🔎 Indexa os chunks lexicalmente no Elasticsearch
- 💬 Consulta o RAG de forma interativa via terminal
- 📚 Retorna respostas com citações de fontes e metadados

---

## 🏗️ Arquitetura do Pipeline

O sistema segue um fluxo bem definido de preparação e consulta de dados:

```
Documentos Brutos (PDF/HTML/HTM)
       ↓
Limpeza de Metadados
       ↓
Extração de Texto
       ↓
Chunking com Overlap
       ↓
Embeddings Vetoriais (Gemini)    ←→    Indexação Lexical (Elasticsearch)
       ↓                                      ↓
ChromaDB (Banco Vetorial)        +      Índice BM25
       ↓                                      ↓
       └─────→ Recuperação Híbrida ←────────┘
                     ↓
         LLM Generation (Gemini 2.5)
                     ↓
         Resposta com Citações e Fontes
```

---

## 📂 Estrutura de Diretórios

```
Desafio_RAG_NLP/
├── parsing/                      # Coleta, limpeza e extração de texto
│   ├── scrapping/
│   │   ├── scrapper.py          # Download de PDFs
│   │   └── html_downloader.py   # Download de HTML/HTM
│   ├── clean_and_normalize_metadata.py
│   ├── extracting_text_mp.py    # Extração com multiprocessing
│   └── README.md
├── chunking/                     # Divisão em chunks
│   ├── chunking.py
│   ├── requirements.txt
│   └── README.md
├── embedding/                    # Geração de embeddings vetoriais (Gemini embedding 001)
│   ├── embedding.py
│   ├── requirements.txt
│   └── README.md
├── embedding_os/                 # Geração de embeddings open source (BAAI/bge-m3)
│   ├── embedding_os.py
│   ├── requirements_cpu.txt
│   ├── requirements_cuda.txt
│   └── README.md
├── gerador_elasticsearch/        # Indexação lexical
│   ├── gerador_elasticsearch.py
│   └── README.md
├── RAG/                          # Sistema RAG interativo
│   ├── RAG.py                   # Execução local interativa
│   └── README.md
├── json_parsed/                  # Documentos JSON normalizados
├── chunks/                       # Chunks gerados
├── banco_chroma/                 # Banco vetorial ChromaDB
├── embedding_checkpoint.txt      # Checkpoint do embedding
├── setup.py                      # Setup automatizado
├── requirements.txt              # Dependências globais
└── README.md
```

---

## 📋 Sequência de Módulos

### 1️⃣ Coleta de Documentos

**Pasta:** `parsing/scrapping/`

**Descrição:** Download de arquivos PDF, HTML e HTM da ANEEL com retry automático e relatórios.

- `scrapper.py`: Download paralelo de PDFs com tratamento de erros
- `html_downloader.py`: Download de HTML/HTM como fallback

Gera relatórios de erro em CSV e JSON com informações detalhadas de falhas.

**Veja:** [parsing/README.md](parsing/README.md) para mais detalhes.

---

### 2️⃣ Normalização de Metadados

**Pasta:** `parsing/`

**Arquivo:** `clean_and_normalize_metadata.py`

Normaliza campos como tipo de documento, datas, ementa, assunto, situação e demais campos dos registros para um modelo consistente.

---

### 3️⃣ Extração de Texto

**Pasta:** `parsing/`

**Arquivo:** `extracting_text_mp.py`

Extração híbrida com processamento paralelo:

- **PDFs:** `fitz` + `pdfplumber` (inclui detecção e extração de tabelas)
- **HTML/HTM:** `BeautifulSoup` (converte tabelas para Markdown)

Converte tabelas em Markdown, usa SQLite para controle de progresso e suporta multiprocessing.

**Extensões suportadas:** `.pdf`, `.html`, `.htm`

---

### 4️⃣ Chunking

**Pasta:** `chunking/`

**Arquivo:** `chunking.py`

Divisão em duas etapas:

1. **Separação estrutural** por cabeçalhos Markdown (`#`, `##`, `###`)
2. **Divisão recursiva** com `chunk_size=1024` e `chunk_overlap=154`

- **Entrada:** `json_parsed/`
- **Saída:** `chunks/chunks.jsonl` (formato LangChain)

Inclui controle de checkpoints e registro de erros.

**Veja:** [chunking/README.md](chunking/README.md)

---

### 5️⃣ Embeddings Vetoriais

**Pastas:** `embedding/` e `embedding_os/`

**Arquivos:** `embedding.py` e `embedding_os.py`

Gera embeddings com `GoogleGenerativeAIEmbeddings` (modelo: `models/gemini-embedding-001`) ou com o modelo open source `BAAI/bge-m3`.

- **Entrada:** `chunks/chunks.jsonl`
- **Saída:** `banco_chroma/` ou `banco_chroma_bgem3/` (banco vetorial persistido)
- **Checkpoint:** `embedding_checkpoint.txt` (para retomar execução)

Processamento em lotes de 100 documentos com retry exponencial.

> **Nota de atenção:** embora o pipeline também seja compatível com o modelo open source `BAAI/bge-m3`, o fluxo com Gemini é o que oferece a melhor eficiência no contexto deste projeto e foi o mais validado na prática. O modelo open source foi adicionado como alternativa sem custo e para garantir reprodutibilidade total.

**Veja:** [embedding/README.md](embedding/README.md)
**Veja:** [embedding_os/README.md](embedding_os/README.md)
---

### 6️⃣ Indexação Lexical

**Pasta:** `gerador_elasticsearch/`

**Arquivo:** `gerador_elasticsearch.py`

Popula índice Elasticsearch com estratégia BM25 para busca lexical.

- **URL Elasticsearch:** `http://localhost:9200`
- **Índice:** `aneel_lexical`
- **Tamanho de lote:** `500`
- **Entrada:** `chunks/chunks.jsonl`

**Veja:** [gerador_elasticsearch/README.md](gerador_elasticsearch/README.md)

---

### 7️⃣ Consulta RAG Interativa

**Pasta:** `RAG/`

**Arquivo:** `RAG.py`

Sistema RAG completo com recuperação híbrida e interface interativa:

- **Recuperação:** 60% lexical (Elasticsearch BM25) + 40% vetorial (ChromaDB)
- **LLM:** `gemini-2.5-flash`
- **Embeddings:** `models/gemini-embedding-001`
- **Interface:** Terminal interativo com loop de perguntas (nesse protótipo)

Retorna respostas com citações de fontes e metadados dos documentos consultados.

**Veja:** [RAG/README.md](RAG/README.md)

---

## 🚀 Como Começar

### Pré-requisitos

- **Python 3.10+** (sistema feito no python:3.12)
- **Elasticsearch** rodando em `http://localhost:9200`
- **Google Gemini API key** (de https://ai.google.dev)

### 1. Configuração Inicial

```bash
# Acesse o repositório
cd Desafio_RAG_NLP

# Crie um arquivo .env na raiz com sua chave de API
echo 'GEMINI_API_KEY="sua_chave_aqui"' > .env

# Instale as dependências globais
pip install -r requirements.txt

# Inicia o Docker que irá conter o ElasticSearch
docker-compose up -d 
```

### 2. Prepare os Dados (Sequencialmente)

#### Opção A: Setup Automatizado (`setup.py`)

O projeto inclui um setup com duas estratégias:

1. Fluxo padrão (já existente): baixa `banco_chroma` e `chunks` e prepara o ambiente.
2. Fluxo por etapa (`--from-*`): inicia do ponto desejado em diante.

Execução padrão:

```bash
python setup/setup.py
```

Compatibilidade legada mantida:

```bash
python setup.py
```

Seleção de rota de embedding no setup:

- padrão (se não definir nada): GEMINI
- alternativo: BAAI/bge-m3

Exemplo no `.env` (ou variável de ambiente do sistema):

```env
EMBEDDING_MODEL="BAAI/bge-m3"
```

Quando `EMBEDDING_MODEL="BAAI/bge-m3"`, o setup usa `embedding_os/embedding_os.py` na etapa de embedding.
Se o valor for inválido, o setup volta automaticamente para GEMINI.

No fluxo padrão de setup (`python setup.py`), o download do banco vetorial também segue `EMBEDDING_MODEL`:

- `GEMINI`: baixa e prepara `banco_chroma`.
- `BAAI/bge-m3`: baixa e prepara `banco_chroma_bgem3`.

Execução a partir de uma etapa específica:

```bash
python setup.py --from-download-jsons
python setup.py --from-extract-jsons
python setup.py --from-credentials
python setup.py --from-install
python setup.py --from-chunking
python setup.py --from-embedding
python setup.py --from-elasticsearch
```

Observações do modo `--from-*`:

- usa o ZIP de `json_parsed` configurado em `URL_DOWNLOAD_JSON_PARSED` dentro de `setup.py`;
- executa da etapa escolhida até o final (não executa etapas anteriores);
- ideal para retomar execução sem repetir todo o bootstrap.

#### Opção B: Execução Manual por Etapas

```bash
# 1. Normalizar metadados
python parsing/clean_and_normalize_metadata.py

# 2. Extrair texto dos documentos
python parsing/extracting_text_mp.py

# 3. Gerar chunks
python chunking/chunking.py

# 4. Gerar embeddings (pode demorar bastante)
python embedding/embedding.py

# 5. Indexar no Elasticsearch (requer ES rodando)
python gerador_elasticsearch/gerador_elasticsearch.py
```

### 3. Use o RAG

```bash
# Modo interativo
python RAG/RAG.py
```

**Como usar:**
- Digite sua pergunta
- Pressione Enter
- Receba resposta com citações de fontes
- Repita ou pressione **Ctrl+C** para sair

---

## 📦 Dependências

### Globais (requirements.txt)

```
langchain
langchain-core
langchain-community
langchain-text-splitters
langchain-google-genai
langchain-chroma
langchain-elasticsearch
python-dotenv
tqdm
```

### Específicas por Etapa

Algumas pastas possuem seu próprio `requirements.txt`. Para instalar apenas as dependências de um módulo:

```bash
pip install -r embedding/requirements.txt      # Apenas embedding
pip install -r chunking/requirements.txt       # Apenas chunking
pip install -r parsing/requirements.txt
```

---

## 📊 Fluxo de Dados (Entrada/Saída)

| Etapa | Entrada | Saída |
|-------|---------|-------|
| Coleta | URLs (CSV/JSON) | Arquivos PDF/HTML/HTM |
| Normalização | JSON brutos | `json_parsed/` (JSON normalizados) |
| Extração | PDF/HTML/HTM | JSON com `texto_extraido` e `texto_extraido_md` |
| Chunking | `json_parsed/` | `chunks/chunks.jsonl` |
| Embeddings | `chunks/chunks.jsonl` | `banco_chroma/` |
| Elasticsearch | `chunks/chunks.jsonl` | Índice `aneel_lexical` |
| RAG | Pergunta (terminal) | Resposta + Fontes + Metadados |

---

## 📝 Observações

- ✅ O pipeline foi desenvolvido para documentos da ANEEL, mas pode ser adaptado para outras fontes
- ✅ A qualidade das respostas do RAG depende diretamente da qualidade da indexação e dos chunks
- ✅ Os modelos Gemini requerem conexão com internet
- ✅ É perfeitamente possível utilizar esse RAG com o Nível Gratuito do Gemini
- ✅ O Elasticsearch deve estar rodando antes de executar a indexação

---

## 👥 Desenvolvimento

Desenvolvido como projeto de aprendizado e pesquisa em NLP pelo Grupo de Estudos de NLP da UFG.
