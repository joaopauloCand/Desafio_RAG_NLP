import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse


def is_html_url(url: str) -> bool:
    path = urlparse(url.strip()).path.lower()
    return path.endswith(".htm") or path.endswith(".html")


def main():
    parser = argparse.ArgumentParser(
        description="Filtra URLs .htm/.html de um TSV e exporta CSV com url e data_registro."
    )
    parser.add_argument("-i", "--input", required=True, help="Arquivo de entrada (TSV)")
    parser.add_argument("-o", "--output", required=True, help="Arquivo de saída (CSV)")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    resultados = []

    with input_path.open("r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue

            partes = linha.split("\t")

            if len(partes) < 3:
                continue

            url = partes[0].strip()
            data = partes[2].strip()

            if is_html_url(url):
                resultados.append((url, data))

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "data_registro"])  # cabeçalho
        writer.writerows(resultados)

    print(f"Total de registros filtrados: {len(resultados)}")
    print(f"CSV gerado em: {output_path.resolve()}")


if __name__ == "__main__":
    main()