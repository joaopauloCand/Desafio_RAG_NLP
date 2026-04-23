import csv
import os
import sys
import time
import logging
import argparse
import shutil
from datetime import datetime
from pathlib import Path

import cloudscraper
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ─── Configuração ─────────────────────────────────────────────────────────────

DEFAULT_OUTPUT_DIR = "D:/aneel_pdfs"
DEFAULT_LOG_DIR = "./logs"
DEFAULT_MAX_WORKERS = 1
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 60
DELAY_BETWEEN_REQUESTS = 2.0
DELAY_BETWEEN_RETRIES = 5

HEADERS_TEMPLATE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "Referer": "https://www.aneel.gov.br/",
}


# ─── Logger ───────────────────────────────────────────────────────────────────

def setup_logging(log_dir):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"html_download_{timestamp}.log")

    logger = logging.getLogger("html_downloader")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s",
                                       datefmt="%Y-%m-%d %H:%M:%S"))

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s | %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info(f"Log sendo salvo em: {log_file}")
    return logger


# ─── Sessão HTTP (idêntica ao scraper) ────────────────────────────────────────

def create_session():
    try:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True},
            delay=3,
        )
        scraper.headers.update(HEADERS_TEMPLATE)
        return scraper
    except Exception:
        pass

    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS_TEMPLATE)
    return session


# ─── Download individual ──────────────────────────────────────────────────────

def download_html(url, data_registro, output_dir, session, max_retries, timeout, logger):

    url_lower = url.lower().split("?")[0]
    ext = ".htm" if url_lower.endswith(".htm") else ".html"

    nome_base = url.rstrip("/").split("/")[-1].split("?")[0]
    safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in nome_base)
    if not safe_name.lower().endswith((".html", ".htm")):
        safe_name += ext

    date_dir = os.path.join(output_dir, str(data_registro).replace("/", "-"))
    Path(date_dir).mkdir(parents=True, exist_ok=True)
    dest_path = os.path.join(date_dir, safe_name)


    testes_dir = os.path.join(output_dir, "htm_html_testes")
    Path(testes_dir).mkdir(parents=True, exist_ok=True)
    testes_path = os.path.join(testes_dir, safe_name)

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        if not os.path.exists(testes_path):
            shutil.copy2(dest_path, testes_path)
        logger.debug(f"Já existe, pulando: {safe_name}")
        return {"url": url, "sucesso": True, "motivo": "JA_EXISTE", "caminho": dest_path}

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Tentativa {attempt}/{max_retries}: {url}")
            response = session.get(url, timeout=timeout, stream=True)

            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} para {safe_name} (tentativa {attempt})")
                if response.status_code == 404:
                    return {"url": url, "sucesso": False, "motivo": "HTTP_404"}
                if response.status_code in (403, 503):
                    time.sleep(DELAY_BETWEEN_RETRIES * attempt)
                    continue
                if response.status_code == 429:
                    time.sleep(DELAY_BETWEEN_RETRIES * attempt * 2)
                    continue
                time.sleep(DELAY_BETWEEN_RETRIES)
                continue

            content_type = response.headers.get("Content-Type", "").lower()

            if "text/html" in content_type or not content_type:
                preview = response.text[:600]
                if "cloudflare" in preview.lower() and "challenge" in preview.lower():
                    logger.warning(f"Cloudflare challenge detectado em {safe_name}, aguardando...")
                    time.sleep(DELAY_BETWEEN_RETRIES * attempt)
                    continue

            total_size = 0
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)

            shutil.copy2(dest_path, testes_path)
            logger.info(f"✓ Baixado: {safe_name} ({total_size / 1024:.1f} KB) [tentativa {attempt}]")
            return {"url": url, "sucesso": True, "motivo": None, "caminho": dest_path, "bytes": total_size}

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout para {safe_name} (tentativa {attempt})")
            time.sleep(DELAY_BETWEEN_RETRIES)
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Erro de conexão para {safe_name}: {str(e)[:100]}")
            time.sleep(DELAY_BETWEEN_RETRIES * 2)
        except Exception as e:
            logger.error(f"Erro inesperado para {safe_name}: {e}")
            time.sleep(DELAY_BETWEEN_RETRIES)

    logger.error(f"✗ Falha definitiva: {safe_name}")
    return {"url": url, "sucesso": False, "motivo": f"FALHOU_APOS_{max_retries}_TENTATIVAS"}


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Downloader de HTML/HTM da ANEEL")
    parser.add_argument("--csv", "-c", required=True,
                        help="Arquivo CSV com colunas 'url' e 'data_registro'")
    parser.add_argument("--output-dir", "-o", default=DEFAULT_OUTPUT_DIR,
                        help=f"Diretório de saída (padrão: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--log-dir", "-l", default=DEFAULT_LOG_DIR)
    parser.add_argument("--max-retries", "-r", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--delay", "-d", type=float, default=DELAY_BETWEEN_REQUESTS)
    args = parser.parse_args()

    logger = setup_logging(args.log_dir)
    logger.info("=" * 60)
    logger.info("ANEEL HTML Downloader - Iniciando")
    logger.info(f"CSV: {args.csv} | Output: {args.output_dir}")
    logger.info("=" * 60)

    items = []
    with open(args.csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url", "").strip()
            data_registro = row.get("data_registro", "").strip()
            if url:
                items.append({"url": url, "data_registro": data_registro})

    if not items:
        logger.error("Nenhuma URL encontrada no CSV.")
        sys.exit(1)

    logger.info(f"Total de URLs para processar: {len(items)}")

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    session = create_session()

    try:
        warmup = session.get("https://www.aneel.gov.br/", timeout=15)
        logger.info(f"Warmup: status {warmup.status_code}")
    except Exception as e:
        logger.warning(f"Warmup falhou (não crítico): {e}")

    sucesso = falha = pulados = bytes_total = 0

    for i, item in enumerate(items, 1):
        logger.info(f"[{i}/{len(items)}] {item['url']}")
        result = download_html(
            url=item["url"],
            data_registro=item["data_registro"],
            output_dir=args.output_dir,
            session=session,
            max_retries=args.max_retries,
            timeout=args.timeout,
            logger=logger,
        )

        if result["sucesso"]:
            if result.get("motivo") == "JA_EXISTE":
                pulados += 1
            else:
                sucesso += 1
                bytes_total += result.get("bytes", 0)
        else:
            falha += 1

        if i < len(items):
            time.sleep(args.delay)

    print("\n" + "=" * 60)
    print("  RESUMO")
    print("=" * 60)
    print(f"  Downloads com sucesso:  {sucesso}")
    print(f"  Pulados (já existiam):  {pulados}")
    print(f"  Falhas:                 {falha}")
    print(f"  Total baixado:          {bytes_total / (1024*1024):.2f} MB")
    print("=" * 60 + "\n")

    if falha > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
