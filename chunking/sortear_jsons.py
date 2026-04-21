from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path


def selecionar_arquivos_aleatorios(
    pasta_origem: Path,
    pasta_destino: Path,
    quantidade: int = 50,
    seed: int | None = None,
) -> list[Path]:
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
    parser = argparse.ArgumentParser(
        description="Seleciona arquivos JSON aleatórios de json_parsed e copia para json_teste."
    )
    parser.add_argument(
        "--origem",
        type=Path,
        default=Path("json_parsed"),
        help="Pasta com os arquivos JSON de origem.",
    )
    parser.add_argument(
        "--destino",
        type=Path,
        default=Path("json_teste"),
        help="Pasta onde as cópias serão salvas.",
    )
    parser.add_argument(
        "--quantidade",
        type=int,
        default=50,
        help="Quantidade de arquivos a copiar.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Semente opcional para tornar a seleção reproduzível.",
    )
    args = parser.parse_args()

    selecionados = selecionar_arquivos_aleatorios(
        pasta_origem=args.origem,
        pasta_destino=args.destino,
        quantidade=args.quantidade,
        seed=500,  # Semente fixa para garantir a mesma seleção em execuções futuras
    )

    print(f"{len(selecionados)} arquivo(s) copiado(s) para '{args.destino}':")
    for arquivo in selecionados:
        print(f"- {arquivo.name}")


if __name__ == "__main__":
    main()
