# Parsing e Normalização de Metadados

Esta pasta contém dois scripts complementares para preparar dados antes do chunking:

- `clean_and_normalize_metadata.py`: normaliza metadados brutos da ANEEL;
- `extracting_text_mp.py`: extrai texto de PDF/HTML/HTM com multiprocessing.

## Ordem recomendada

1. Executar `clean_and_normalize_metadata.py` para gerar JSONs normalizados.
2. Executar `extracting_text_mp.py` usando os JSONs normalizados e os arquivos baixados.

## 1) clean_and_normalize_metadata.py

### Objetivo

- limpar campos textuais;
- normalizar `tipo` de documento (PDF/anexo);
- converter datas para formato `YYYY-MM-DD`;
- gerar `id` estável por registro;
- salvar um JSON por registro em estrutura organizada por arquivo de origem.

### Entrada

Diretório com JSONs brutos, por exemplo `json_teste/` ou outra pasta de metadados coletados.

### Saída

Diretório com subpastas por arquivo de entrada, contendo os registros normalizados em `.json`.

### Argumentos CLI

- `--input-dir` (`-i`) obrigatório: pasta com JSONs de entrada;
- `--output-dir` (`-o`) opcional: pasta de saída. Padrão no script: `D:/clean_metadata`.

### Execução

Na raiz do projeto:

```bash
python parsing/clean_and_normalize_metadata.py -i json_teste -o clean_metadata
```

### Campos principais no JSON de saída

- `id`
- `data_publicacao`
- `titulo`
- `autor`
- `material`
- `esfera`
- `situacao`
- `assinatura`
- `publicacao`
- `assunto`
- `ementa`
- `documentos` (com `tipo`, `tipo_original`, `url`, `arquivo_origem`, `texto_extraido`)

## 2) extracting_text_mp.py

### Objetivo

- processar os JSONs normalizados;
- localizar arquivos no disco por `data_publicacao/arquivo_origem`;
- extrair texto de `.pdf`, `.html` e `.htm`;
- detectar tabelas e produzir também uma versão em Markdown;
- registrar progresso em SQLite para retomada segura.

### Entrada

- `metadata-dir`: pasta com JSONs normalizados;
- `files-dir`: pasta com os arquivos baixados (PDF/HTML/HTM), organizados por data.

### Saída

- JSONs completos com campos preenchidos:
  - `texto_extraido`
  - `texto_extraido_md`
  - `tem_tabela`
- logs em arquivo (`log-dir`);
- banco SQLite de progresso (`--db`).

### Argumentos CLI

- `--metadata-dir` (`-m`) obrigatório;
- `--files-dir` (`-f`) obrigatório;
- `--output-dir` (`-o`) opcional, padrão: `json_parsed`;
- `--log-dir` (`-l`) opcional, padrão: `./logs`;
- `--db` opcional, padrão: `./parsing_progresso.db`;
- `--workers` (`-w`) opcional, padrão: `4`.

### Execução

Na raiz do projeto:

```bash
python parsing/extracting_text_mp.py -m clean_metadata -f aneel_pdfs -o json_parsed -l logs -w 4
```

## Dependências

Dependências usadas diretamente por estes scripts:

- `beautifulsoup4`
- `PyMuPDF` (importado como `fitz`)
- `pdfplumber`

Para evitar instalar pacotes desnecessários para quem só usa etapas posteriores do pipeline, esta pasta possui um arquivo dedicado:

- `parsing/requirements.txt`

Instale apenas se quiser executar/refazer esta etapa:

```bash
pip install -r parsing/requirements.txt
```

## Observações operacionais

- o parsing ignora documentos sem `arquivo_origem` válido;
- apenas extensões `.pdf`, `.html` e `.htm` são processadas;
- o status de cada JSON é salvo em SQLite e evita reprocessar itens com status `OK`;
- o script de extração foi desenhado para processamento em lote com retomada após interrupções.