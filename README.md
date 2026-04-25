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
- 🧠 Gera embeddings vetoriais com Google Gemini
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
NLP/
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
├── embedding/                    # Geração de embeddings vetoriais
│   ├── embedding.py
│   ├── requirements.txt
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

**Pasta:** `embedding/`

**Arquivo:** `embedding.py`

Gera embeddings com `GoogleGenerativeAIEmbeddings` (modelo: `models/gemini-embedding-001`).

- **Entrada:** `chunks/chunks.jsonl`
- **Saída:** `banco_chroma/` (banco vetorial persistido)
- **Checkpoint:** `embedding_checkpoint.txt` (para retomar execução)

Processamento em lotes de 100 documentos com retry exponencial.

**Veja:** [embedding/README.md](embedding/README.md)

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

- **Python 3.10+**
- **Elasticsearch** rodando em `http://localhost:9200`
- **Google Generative AI API key** (de https://ai.google.dev)

### 1. Configuração Inicial

```bash
# Acesse o repositório
cd NLP

# Crie um arquivo .env na raiz com sua chave de API
echo 'GEMINI_API_KEY="sua_chave_aqui"' > .env

# Instale as dependências globais
pip install -r requirements.txt
```

### 2. Prepare os Dados (Sequencialmente)

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
