# Scrapping (Opcional)

Esta pasta contém scripts da fase de coleta/download de documentos da ANEEL.

Na prática, podem ignorar esta etapa> Porque os resultados dessa fase já estão prontos, e como o objetivo é avaliar um RAG sempre utilizaremos os arquivos que já foram obtidos nessa fase no lugar de fazer tudo novamente.

## Scripts da pasta

### 1) urls.py

Filtra URLs `.htm` e `.html` a partir de um arquivo TSV e gera um CSV com colunas:

- `url`
- `data_registro`

Execução:

```bash
python parsing/scrapping/urls.py -i entrada.tsv -o urls_html.csv
```

### 2) scrapper.py

Lê um ou mais JSONs de metadados brutos, extrai os itens de PDF e faz download em disco com retry.

Saídas principais:

- arquivos PDF organizados por data de registro;
- logs de execução;
- relatórios de erro em CSV e JSON quando houver falhas.

O script usa `cloudscraper` com fallback para `requests`, além de retentativas HTTP para erros temporários.

### 3) html_downloader.py

Lê um CSV com `url` e `data_registro` e baixa arquivos HTML/HTM em disco.

Saídas principais:

- arquivos `.html`/`.htm` organizados por data;
- cópia de amostras em `htm_html_testes`;
- logs de execução.

Execução:

```bash
python parsing/scrapping/html_downloader.py -c urls_html.csv -o D:/aneel_pdfs -l logs
```

## Dependências da fase

Para manter o pipeline leve para quem usa apenas as etapas posteriores, esta pasta tem dependências próprias:

- `parsing/scrapping/requirements.txt`

Instale apenas se for executar esta fase:

```bash
pip install -r parsing/scrapping/requirements.txt
```

## Observações

- Esta etapa é opcional no fluxo padrão do projeto.
- Se os dados já estiverem disponíveis localmente, siga direto para normalização/parsing/chunking.