from __future__ import annotations

import random
import shutil
from pathlib import Path

def selecionar_arquivos_aleatorios(
    pasta_origem: Path,
    pasta_destino: Path,
    quantidade: int = 50,
    seed: int | None = None,
) -> list[Path]:
    """Seleciona arquivos JSON aleatórios de uma pasta de origem e os copia para uma pasta de destino."""
    if not pasta_origem.exists():
        raise FileNotFoundError(f"Pasta de origem não encontrada: {pasta_origem}")

    arquivos_json = sorted(
        arquivo for arquivo in pasta_origem.iterdir() if arquivo.is_file() and arquivo.suffix.lower() == ".json"
    )

    if not arquivos_json:
        raise FileNotFoundError(f"Nenhum arquivo .json encontrado em: {pasta_origem}")

    if seed is not None:
        random.seed(seed)

    quantidade = min(quantidade, len(arquivos_json))
    selecionados = random.sample(arquivos_json, quantidade)

    pasta_destino.mkdir(parents=True, exist_ok=True)
    for arquivo in selecionados:
        shutil.copy2(arquivo, pasta_destino / arquivo.name)

    return selecionados


def main() -> None:
    selecionados = selecionar_arquivos_aleatorios(
        pasta_origem=Path("json_parsed"),
        pasta_destino=Path("json_teste"),
        quantidade=50,
        seed=500,  # Semente fixa para garantir a mesma seleção em execuções futuras
    )

    # Imprime os arquivos selecionados para o usuário
    print(f"{len(selecionados)} arquivo(s) copiado(s) para '{Path("json_teste")}':")
    for arquivo in selecionados:
        print(f"- {arquivo.name}")

# Execute este script para selecionar aleatoriamente 50 arquivos JSON da pasta 'json_parsed' e copiá-los para 'json_teste'.
# A semente fixa garante que a mesma seleção seja feita em execuções futuras, facilitando testes consistentes.
if __name__ == "__main__":
    main()
