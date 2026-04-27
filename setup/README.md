# 🚀 Setup e Orquestração do RAG ANEEL

Este diretório concentra o script `setup.py`, um orquestrador para preparar o ambiente de IA, gerir bancos vetoriais e executar o pipeline por etapas.

**Importante**: primeiro baixe as depedências em requirements.txt na raiz.

---

## 🏗️ Nota de Arquitetura: A Fase de Parsing
> **Aviso Importante:** O processo de extração bruta de textos dos PDFs originais da ANEEL (a fase de *Parsing* e OCR) **não** é executado por este script. 
> 
> **Porquê?** A etapa de *parsing* é computacionalmente agressiva, sujeita a quebras estruturais de PDFs e adicionaria uma complexidade desnecessária ao *setup* de infraestrutura. Para garantir a estabilidade e reprodutibilidade deste ambiente, o script assume que os documentos já passaram pelo *parser* e consome os dados a partir do formato `.jsonl` estruturado.

---

## ⚙️ O Que Este Script Faz?

Dependendo de como é executado, o `setup.py` gerencia automaticamente:
1. **Verificação de Ambiente:** Valida dependências e chaves de API (`GEMINI_API_KEY`, com compatibilidade para `GOOGLE_API_KEY` no embedding).
2. **Gestão de Dependências:** instalação das bibliotecas corretas (PyTorch, LangChain, HuggingFace, etc.).
3. **Download de Artefatos:** Baixa os bancos vetoriais pré-processados (Gemini e BGE-M3) e *chunks* diretamente do Hugging Face.
4. **Execução de Pipeline ML:** Fatiamento de textos (*Chunking*) e criação de vetores (*Embedding*).
5. **Infraestrutura Lexical:** Executa a etapa de indexação no Elasticsearch.

---

## 🛠️ Como Executar

Antes de iniciar, certifique-se de que o ficheiro `.env` contém a sua chave da API e que as dependências da raiz já foram instaladas.

Para a etapa de Elasticsearch, mantenha seu ambiente Docker/Elasticsearch disponível localmente antes de executar o setup.

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

> **Atenção:** se você pretende usar GPU na fase de `embedding_os`, aplique as modificações descritas em [embedding_os/README.md](../embedding_os/README.md). É lá que estão os ajustes necessários para alternar para `cuda` e adequar o consumo de memória.

Comportamento de checkpoint no modo de teste:

- se o banco vetorial ainda não existir, o setup ajusta `embedding_checkpoint.txt` para `0`;
- se o banco vetorial já existir, o checkpoint atual é preservado para retomar progresso sem retrabalho.

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
| `(sem flags)` | **Fluxo Padrão (Produção):** Baixa os bancos de dados prontos da nuvem, extrai, instala bibliotecas e executa a etapa de Elasticsearch (com serviço já ativo). |
| `-h, --help` | Exibe a mensagem de ajuda e sai. |
| `--testar-pipeline` | Seleciona 25 JSONs aleatórios em `json_parsed` e executa um teste rápido do fluxo completo (*chunking* ➔ *embedding* ➔ *elasticsearch*). |
| `--from-download-jsons`| Inicia no download de JSONs parseados. |
| `--from-extract-jsons` | Inicia na extração de JSONs parseados. |
| `--from-credentials` | Inicia na verificação de credenciais de API. |
| `--from-install` | Inicia na instalação de bibliotecas do projeto. |
| `--from-chunking` | Inicia na etapa de chunking (fluxo: *chunking* ➔ *embedding* ➔ *elasticsearch*). |
| `--from-embedding` | Inicia na etapa de embedding (fluxo: *embedding* ➔ *elasticsearch*). |
| `--from-elasticsearch` | Inicia na etapa de indexação no Elasticsearch. |

Observação adicional sobre checkpoint:

- no fluxo padrão (sem flags), o setup restaura `embedding_checkpoint.txt` para `297858`.

---

## 🚨 Solução de Problemas Comuns

* **Erro: "Chave API não encontrada"**
  Verifique se o ficheiro `.env` está na raiz do projeto e contém `GEMINI_API_KEY=sua_chave_aqui`.
* **Erro: "Docker Compose failed" ou "Connection Refused"**
  O Elasticsearch não está acessível localmente. Garanta Docker/Elasticsearch ativos e tente novamente.
* **Erro de Memória (GPU/OOM)**
  Se usar a *flag* `--from-embedding` ou `--testar-pipeline` com um modelo pesado (como o BGE-M3), certifique-se de que o seu hardware suporta o `batch_size` configurado.
```