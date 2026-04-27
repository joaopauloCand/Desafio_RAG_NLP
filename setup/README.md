# 🚀 Setup e Orquestração do RAG ANEEL

Este diretório concentra o script `setup.py`, ele é um orquestrador desenhado para preparar o ambiente de Inteligência Artificial, gerenciar bancos de dados vetoriais e provisionar a infraestrutura local (Docker).

---

## 🏗️ Nota de Arquitetura: A Fase de Parsing
> **Aviso Importante:** O processo de extração bruta de textos dos PDFs originais da ANEEL (a fase de *Parsing* e OCR) **não** é executado por este script. 
> 
> **Porquê?** A etapa de *parsing* é computacionalmente agressiva, sujeita a quebras estruturais de PDFs e adicionaria uma complexidade desnecessária ao *setup* de infraestrutura. Para garantir a estabilidade e reprodutibilidade deste ambiente, o script assume que os documentos já passaram pelo *parser* e consome os dados a partir do formato `.jsonl` estruturado.

---

## ⚙️ O Que Este Script Faz?

Dependendo de como é executado, o `setup.py` gerencia automaticamente:
1. **Verificação de Ambiente:** Valida a presença do Python, Docker e chaves de API (`GOOGLE_API_KEY`).
2. **Gestão de Dependências:** instalação das bibliotecas corretas (PyTorch, LangChain, HuggingFace, etc.).
3. **Download de Artefatos:** Baixa os bancos vetoriais pré-processados (Gemini e BGE-M3) e *chunks* diretamente do Hugging Face.
4. **Execução de Pipeline ML:** Fatiamento de textos (*Chunking*) e criação de vetores (*Embedding*).
5. **Infraestrutura Lexical:** Levanta o banco de dados Elasticsearch utilizando Docker Compose.

---

## 🛠️ Como Executar

Antes de iniciar, certifique-se que você tem o **Docker Desktop** no seu computador e que o ficheiro `.env` contém a sua chave da API.

Lembre-se também de executar **'docker-compose up -d** para carregar e criar a imagem Docker necessária para nossa aplicação Elasticsearch.

A partir da raiz do projeto (`Desafio_RAG_NLP`), você tem três abordagens principais:

### 1. O Caminho Rápido (Default - Produção)
Ideal para iniciar a aplicação instantaneamente. Este fluxo ignora o processamento pesado de Machine Learning; em vez disso, ele **baixa os bancos vetoriais já prontos** da nuvem, extrai os ficheiros, instala as bibliotecas e levanta o Elasticsearch.

```bash
python setup/setup.py
```
*(Nota: O comando `python setup.py` na raiz também funciona como ponte de compatibilidade).*

### 2. O Caminho de Teste
Para validar se a arquitetura está a funcionar sem gastar horas a vetorizar a base completa. Esta flag seleciona uma amostra reduzida de JSONs (25 arquivos) e executa o pipeline de ponta a ponta (Chunking ➔ Embedding ➔ ElasticSearch) em poucos minutos.

```bash
python setup/setup.py --testar-pipeline
```

### 3. Recriação Completa
Ideal para processar a base de dados inteira do zero. Utilizando as *flags* `--from-*`, você diz ao script para ignorar os downloads dos bancos prontos e reprocessar os dados localmente, etapa por etapa.

* **Começar do Zero (Apenas com os JSONs parseados):**
  Fará o fatiamento (*chunking*), gerará todos os *embeddings* localmente e levantará o banco.
  ```bash
  python setup/setup.py --from-chunking
  ```

* **Começar dos Chunks Prontos:**
  Pula o fatiamento, assume que o ficheiro `chunks.jsonl` existe, gera os *embeddings* e levanta o banco.
  ```bash
  python setup/setup.py --from-embedding
  ```

* **Apenas Subir a Infraestrutura Lexical:**
  Pula todo o ecossistema vetorial e garante apenas que o Elasticsearch está a rodar no Docker.
  ```bash
  python setup/setup.py --from-elasticsearch
  ```

---

## 📋 Resumo dos Argumentos e Flags

Abaixo estão todos os parâmetros aceitos pelo script de orquestração para personalizar a etapa de início da execução do pipeline:

| Comando / Flag | Descrição do Fluxo Executado |
| :--- | :--- |
| `(sem flags)` | **Fluxo Padrão (Produção):** Baixa os bancos de dados prontos da nuvem, extrai, instala bibliotecas e sobe a infraestrutura. |
| `-h, --help` | Exibe a mensagem de ajuda e sai. |
| `--testar-pipeline` | Seleciona 25 JSONs aleatórios em `json_parsed` e executa um teste rápido do fluxo completo (*chunking* ➔ *embedding* ➔ *elasticsearch*). |
| `--from-download-jsons`| Inicia no download de JSONs parseados. |
| `--from-extract-jsons` | Inicia na extração de JSONs parseados. |
| `--from-credentials` | Inicia na verificação de credenciais de API. |
| `--from-install` | Inicia na instalação de bibliotecas do projeto. |
| `--from-chunking` | Inicia na etapa de chunking (fluxo: *chunking* ➔ *embedding* ➔ *elasticsearch*). |
| `--from-embedding` | Inicia na etapa de embedding (fluxo: *embedding* ➔ *elasticsearch*). |
| `--from-elasticsearch` | Inicia na etapa de indexação no Elasticsearch. |

---

## 🚨 Solução de Problemas Comuns

* **Erro: "Chave API não encontrada"**
  Verifique se o ficheiro `.env` está na raiz do projeto e contém `GOOGLE_API_KEY=sua_chave_aqui`.
* **Erro: "Docker Compose failed" ou "Connection Refused"**
  O Docker não está a rodar. Abra o aplicativo Docker Desktop e tente rodar o script novamente.
* **Erro de Memória (GPU/OOM)**
  Se usar a *flag* `--from-embedding` ou `--testar-pipeline` com um modelo pesado (como o BGE-M3), certifique-se de que o seu hardware suporta o `batch_size` configurado.
```