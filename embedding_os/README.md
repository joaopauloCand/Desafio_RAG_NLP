# embedding_os

Script para gerar embeddings open source (BAAI/bge-m3) e persistir no ChromaDB com checkpoint e retomada.

## Arquivos
- `embedding_os.py`: pipeline principal de vetorizacao.
- `requirements_cpu.txt`: dependencias para execucao em CPU (padrao).
- `requirements_cuda.txt`: dependencias para execucao em GPU (CUDA 12.1, testado em RTX 3050).

## Como executar

### Instalacao em CPU (recomendado para compatibilidade):
```bash
pip install -r embedding_os/requirements_cpu.txt
python embedding_os/embedding_os.py
```

### Instalacao em GPU (CUDA 12.1):
```bash
pip install -r embedding_os/requirements_cuda.txt
# Atualize DISPOSITIVO = "cuda" em embedding_os.py
python embedding_os/embedding_os.py
```

Para usar GPU com segurança, verifique estes pontos no `embedding_os.py`:
- `DISPOSITIVO`: troque de `cpu` para `cuda`.
- `TAMANHO_LOTE`: reduza se a GPU tiver pouca VRAM ou se ocorrer OOM.
- `encode_kwargs`: ajuste `batch_size` para um valor menor caso a alocacao de memoria fique alta.

## Comportamento de resiliencia
- Retoma progresso pelo arquivo `embedding_checkpoint_os.txt`.
- Processa em lotes para evitar alto consumo de memoria.
- Faz retry exponencial em falhas temporarias de insercao no banco vetorial.
- Permite interrupcao com `Ctrl+C` sem perder progresso ja salvo.

## Configuracoes principais
No arquivo `embedding_os.py`, ajuste se necessario:
- `ARQUIVO_JSONL`: Caminho para arquivo de chunks em JSONL
- `DIRETORIO_CHROMA`: Diretorio persistente do ChromaDB
- `ARQUIVO_CHECKPOINT`: Arquivo para rastrear progresso
- `DISPOSITIVO`: `cpu` ou `cuda` (use `cuda` apos instalar requirements_cuda.txt)
