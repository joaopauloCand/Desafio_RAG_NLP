# Setup

Este diretorio concentra o script principal de bootstrap do projeto.

## Arquivos
- `setup.py`: script principal do setup (fluxos de download, extracao, instalacao e execucao por etapa).

## Como executar
A partir da raiz do projeto (`Desafio_RAG_NLP`):

```bash
python setup/setup.py
```

## Compatibilidade com fluxo antigo
O arquivo `setup.py` na raiz continua disponivel como ponte de compatibilidade.
Assim, este comando continua funcionando:

```bash
python setup.py
```

## Opcoes disponiveis
```bash
python setup/setup.py --help
```

As opcoes `--from-*` permanecem as mesmas da versao anterior.
