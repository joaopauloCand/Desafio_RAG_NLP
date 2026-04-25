import json
import os
import sys
import time
import logging
import hashlib
import argparse
import csv
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import cloudscraper
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ─── Configuração ────────────────────────────────────────────────────────────

DEFAULT_OUTPUT_DIR = "D:/aneel_pdfs"
DEFAULT_LOG_DIR = "./logs"
DEFAULT_MAX_WORKERS = 2      
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 60          
DELAY_BETWEEN_REQUESTS = 1.5 
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


# ─── Data Classes ────────────────────────────────────────────────────────────

class DownloadResult:
    """Resultado de uma tentativa de download."""
    def __init__(self, url, arquivo, data_registro, titulo, tipo_pdf, sucesso,
                 caminho_salvo=None, tamanho_bytes=None, tentativas=0,
                 erro_tipo=None, erro_mensagem=None, status_code=None,
                 response_headers=None, response_body_preview=None, tempo_total_seg=0.0):
        self.url = url
        self.arquivo = arquivo
        self.data_registro = data_registro
        self.titulo = titulo
        self.tipo_pdf = tipo_pdf
        self.sucesso = sucesso
        self.caminho_salvo = caminho_salvo
        self.tamanho_bytes = tamanho_bytes
        self.tentativas = tentativas
        self.erro_tipo = erro_tipo
        self.erro_mensagem = erro_mensagem
        self.status_code = status_code
        self.response_headers = response_headers
        self.response_body_preview = response_body_preview
        self.tempo_total_seg = tempo_total_seg


class DownloadStats:
    """Estatísticas gerais da execução."""
    def __init__(self, total_registros=0, total_pdfs_encontrados=0,
                 total_pdfs_ja_marcados_nao_baixados=0, downloads_sucesso=0,
                 downloads_falha=0, downloads_pulados=0, bytes_total=0,
                 inicio=None, fim=None):
        self.total_registros = total_registros
        self.total_pdfs_encontrados = total_pdfs_encontrados
        self.total_pdfs_ja_marcados_nao_baixados = total_pdfs_ja_marcados_nao_baixados
        self.downloads_sucesso = downloads_sucesso
        self.downloads_falha = downloads_falha
        self.downloads_pulados = downloads_pulados
        self.bytes_total = bytes_total
        self.inicio = inicio
        self.fim = fim


# ─── Logger Setup ────────────────────────────────────────────────────────────

def setup_logging(log_dir):
    """Configura logging com output para console e arquivo."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"download_{timestamp}.log")

    logger = logging.getLogger("aneel_downloader")
    logger.setLevel(logging.DEBUG)

    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)

   
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter("%(levelname)-8s | %(message)s")
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Log sendo salvo em: {log_file}")
    return logger


# ─── HTTP Session Factory ───────────────────────────────────────────────────

def create_session(use_cloudscraper=True):
    """
    Cria uma sessão HTTP.
    - Tenta cloudscraper primeiro (bypass Cloudflare).
    - Fallback para requests.Session com retry adapter.
    """
    if use_cloudscraper:
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    "browser": "chrome",
                    "platform": "windows",
                    "desktop": True,
                },
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


# ─── Parser de JSON ──────────────────────────────────────────────────────────

def parse_json_files(file_paths, logger):
    """
    Lê os arquivos JSON e extrai todos os PDFs para download.
    Retorna lista de dicts com metadados de cada PDF.
    """
    pdf_items = []

    for fpath in file_paths:
        logger.info(f"Lendo arquivo: {fpath}")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON {fpath}: {e}")
            continue
        except FileNotFoundError:
            logger.error(f"Arquivo não encontrado: {fpath}")
            continue

        if isinstance(data, dict):
            entries = data.items()
        elif isinstance(data, list):
            entries = [(str(i), item) for i, item in enumerate(data)]
        else:
            logger.warning(f"Formato inesperado em {fpath}, pulando.")
            continue

        for date_key, day_data in entries:
            registros = []
            if isinstance(day_data, dict):
                registros = day_data.get("registros", [])
            elif isinstance(day_data, list):
                registros = day_data

            for reg in registros:
                pdfs = reg.get("pdfs", []) or []
                titulo = reg.get("titulo", "SEM_TITULO")
                for pdf_info in pdfs:
                    url = pdf_info.get("url", "")
                    arquivo = pdf_info.get("arquivo", "")
                    tipo = pdf_info.get("tipo", "")
                    baixado = pdf_info.get("baixado", False)

                    if not url:
                        logger.debug(f"PDF sem URL em {date_key}/{titulo}, pulando.")
                        continue

                    pdf_items.append({
                        "url": url,
                        "arquivo": arquivo or url.split("/")[-1],
                        "tipo": tipo,
                        "baixado_flag": baixado,
                        "data_registro": str(date_key),
                        "titulo": titulo,
                        "source_file": fpath,
                    })

        logger.info(f"  -> {len(pdf_items)} PDFs acumulados após {fpath}")

    return pdf_items


# ─── Download de PDF Individual ──────────────────────────────────────────────

def download_pdf(item, session, output_dir, max_retries, timeout, logger):
    """Faz download de um PDF com retries e logging detalhado."""

    url = item["url"]
    arquivo = item["arquivo"]
    data_registro = item["data_registro"]
    titulo = item["titulo"]
    tipo = item["tipo"]

    result = DownloadResult(
        url=url,
        arquivo=arquivo,
        data_registro=data_registro,
        titulo=titulo,
        tipo_pdf=tipo,
        sucesso=False,
    )

    safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in arquivo)
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"

    date_dir = os.path.join(output_dir, data_registro.replace("/", "-"))
    Path(date_dir).mkdir(parents=True, exist_ok=True)
    dest_path = os.path.join(date_dir, safe_name)

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        result.sucesso = True
        result.caminho_salvo = dest_path
        result.tamanho_bytes = os.path.getsize(dest_path)
        result.erro_tipo = "PULADO_JA_EXISTE"
        logger.debug(f"Já existe, pulando: {safe_name}")
        return result

    start_time = time.time()

    for attempt in range(1, max_retries + 1):
        result.tentativas = attempt
        try:
            logger.debug(f"Tentativa {attempt}/{max_retries}: {url}")

            response = session.get(url, timeout=timeout, stream=True)
            result.status_code = response.status_code


            resp_headers_str = "\n".join(
                f"  {k}: {v}" for k, v in response.headers.items()
            )
            result.response_headers = resp_headers_str

            if response.status_code != 200:
                body_preview = response.text[:500] if response.text else "(vazio)"
                result.response_body_preview = body_preview
                result.erro_tipo = f"HTTP_{response.status_code}"
                result.erro_mensagem = (
                    f"Status {response.status_code} na tentativa {attempt}. "
                    f"Body: {body_preview[:200]}"
                )
                logger.warning(
                    f"HTTP {response.status_code} para {arquivo} "
                    f"(tentativa {attempt}/{max_retries})"
                )

                if response.status_code in (403, 503):
                    wait = DELAY_BETWEEN_RETRIES * attempt
                    logger.info(f"  Possível Cloudflare, aguardando {wait}s...")
                    time.sleep(wait)
                    continue
                elif response.status_code == 404:
                    result.erro_mensagem = f"PDF não encontrado (404): {url}"
                    logger.error(f"404 - PDF não existe: {arquivo}")
                    break 
                elif response.status_code == 429:
                    wait = DELAY_BETWEEN_RETRIES * attempt * 2
                    logger.warning(f"  Rate limited (429), aguardando {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    time.sleep(DELAY_BETWEEN_RETRIES)
                    continue

            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
                body_preview = response.text[:500]
                if "cloudflare" in body_preview.lower() or "challenge" in body_preview.lower():
                    result.erro_tipo = "CLOUDFLARE_CHALLENGE"
                    result.erro_mensagem = (
                        f"Cloudflare challenge detectado. Content-Type: {content_type}"
                    )
                    result.response_body_preview = body_preview
                    logger.warning(f"Cloudflare challenge em {arquivo}, retry...")
                    time.sleep(DELAY_BETWEEN_RETRIES * attempt)
                    continue
                else:
                    logger.warning(
                        f"Content-Type inesperado ({content_type}) para {arquivo}, "
                        f"mas tentando salvar mesmo assim."
                    )

            total_size = 0
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            with open(dest_path, "rb") as f:
                magic = f.read(5)

            if magic != b"%PDF-":
                with open(dest_path, "r", errors="replace") as f:
                    content_preview = f.read(500)
                os.remove(dest_path)
                result.erro_tipo = "NAO_E_PDF"
                result.erro_mensagem = (
                    f"Arquivo baixado não é PDF (magic bytes: {magic!r}). "
                    f"Preview: {content_preview[:200]}"
                )
                result.response_body_preview = content_preview
                logger.warning(f"Conteúdo baixado não é PDF: {arquivo}")
                time.sleep(DELAY_BETWEEN_RETRIES)
                continue

            result.sucesso = True
            result.caminho_salvo = dest_path
            result.tamanho_bytes = total_size
            result.tempo_total_seg = time.time() - start_time
            logger.info(
                f"Baixado: {safe_name} ({total_size / 1024:.1f} KB) "
                f"[tentativa {attempt}]"
            )
            return result

        except requests.exceptions.Timeout:
            result.erro_tipo = "TIMEOUT"
            result.erro_mensagem = f"Timeout ({timeout}s) na tentativa {attempt}"
            logger.warning(f"Timeout para {arquivo} (tentativa {attempt})")
            time.sleep(DELAY_BETWEEN_RETRIES)

        except requests.exceptions.ConnectionError as e:
            result.erro_tipo = "CONNECTION_ERROR"
            result.erro_mensagem = f"Erro de conexão: {str(e)[:300]}"
            logger.warning(f"Erro de conexão para {arquivo}: {str(e)[:100]}")
            time.sleep(DELAY_BETWEEN_RETRIES * 2)

        except requests.exceptions.SSLError as e:
            result.erro_tipo = "SSL_ERROR"
            result.erro_mensagem = f"Erro SSL: {str(e)[:300]}"
            logger.error(f"Erro SSL para {arquivo}: {str(e)[:100]}")
            time.sleep(DELAY_BETWEEN_RETRIES)

        except Exception as e:
            result.erro_tipo = type(e).__name__
            result.erro_mensagem = f"Erro inesperado: {str(e)[:500]}"
            logger.error(f"Erro inesperado para {arquivo}: {e}")
            time.sleep(DELAY_BETWEEN_RETRIES)

  
    result.tempo_total_seg = time.time() - start_time
    if not result.erro_mensagem:
        result.erro_mensagem = f"Falhou após {max_retries} tentativas"
    logger.error(f"Falha definitiva: {arquivo} | {result.erro_tipo}: {result.erro_mensagem[:150]}")
    return result


# ─── Relatório de Erros ─────────────────────────────────────────────────────

def generate_error_report(results, stats, log_dir, logger):
    """Gera relatórios CSV e JSON detalhados dos erros e resumo da execução."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    errors = [r for r in results if not r.sucesso or r.erro_tipo == "PULADO_JA_EXISTE"]
    real_errors = [r for r in results if not r.sucesso]

    if real_errors:
        csv_path = os.path.join(log_dir, f"erros_{timestamp}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "url", "arquivo", "data_registro", "titulo", "tipo_pdf",
                "erro_tipo", "erro_mensagem", "status_code", "tentativas",
                "response_headers", "response_body_preview", "tempo_total_seg",
            ])
            for r in real_errors:
                writer.writerow([
                    r.url, r.arquivo, r.data_registro, r.titulo, r.tipo_pdf,
                    r.erro_tipo, r.erro_mensagem, r.status_code, r.tentativas,
                    r.response_headers, r.response_body_preview, r.tempo_total_seg,
                ])
        logger.info(f"Relatório de erros CSV: {csv_path}")

    report = {
        "execucao": {
            "inicio": stats.inicio.isoformat() if stats.inicio else None,
            "fim": stats.fim.isoformat() if stats.fim else None,
            "duracao_segundos": (
                (stats.fim - stats.inicio).total_seconds()
                if stats.inicio and stats.fim else 0
            ),
        },
        "estatisticas": {
            "total_registros_processados": stats.total_registros,
            "total_pdfs_encontrados": stats.total_pdfs_encontrados,
            "downloads_sucesso": stats.downloads_sucesso,
            "downloads_falha": stats.downloads_falha,
            "downloads_pulados_ja_existiam": stats.downloads_pulados,
            "bytes_baixados": stats.bytes_total,
            "megabytes_baixados": round(stats.bytes_total / (1024 * 1024), 2),
        },
        "erros": [
            {
                "url": r.url,
                "arquivo": r.arquivo,
                "data_registro": r.data_registro,
                "titulo": r.titulo,
                "tipo_pdf": r.tipo_pdf,
                "erro_tipo": r.erro_tipo,
                "erro_mensagem": r.erro_mensagem,
                "status_code": r.status_code,
                "tentativas": r.tentativas,
                "response_headers": r.response_headers,
                "response_body_preview": r.response_body_preview,
                "tempo_total_seg": r.tempo_total_seg,
            }
            for r in real_errors
        ],
    }

    json_path = os.path.join(log_dir, f"relatorio_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Relatório completo JSON: {json_path}")

    print("\n" + "=" * 60)
    print("  RESUMO DA EXECUÇÃO")
    print("=" * 60)
    print(f"  PDFs encontrados:       {stats.total_pdfs_encontrados}")
    print(f"  Downloads com sucesso:  {stats.downloads_sucesso}")
    print(f"  Downloads com falha:    {stats.downloads_falha}")
    print(f"  Pulados (já existiam):  {stats.downloads_pulados}")
    print(f"  Total baixado:          {stats.bytes_total / (1024*1024):.2f} MB")
    if stats.inicio and stats.fim:
        dur = (stats.fim - stats.inicio).total_seconds()
        print(f"  Tempo total:            {dur:.1f}s")
    print("=" * 60)

    if real_errors:
        print(f"\n  AVISO: {len(real_errors)} ERROS - veja detalhes em:")
        print(f"    CSV: {csv_path}")
        print(f"    JSON: {json_path}")
    else:
        print("\n  Nenhum erro!")
    print()




def main():
    parser = argparse.ArgumentParser(
        description="ANEEL PDF Downloader - Baixa PDFs de registros JSON da ANEEL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python3 aneel_pdf_downloader.py dados1.json dados2.json dados3.json
  python3 aneel_pdf_downloader.py --input-dir ./jsons/
  python3 aneel_pdf_downloader.py dados.json --output-dir ./pdfs/ --max-workers 1
        """,
    )
    parser.add_argument(
        "files", nargs="*", help="Arquivos JSON de entrada"
    )
    parser.add_argument(
        "--input-dir", "-i",
        help="Diretório contendo os arquivos JSON (alternativa a listar arquivos)"
    )
    parser.add_argument(
        "--output-dir", "-o", default=DEFAULT_OUTPUT_DIR,
        help=f"Diretório para salvar PDFs (padrão: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--log-dir", "-l", default=DEFAULT_LOG_DIR,
        help=f"Diretório para logs (padrão: {DEFAULT_LOG_DIR})"
    )
    parser.add_argument(
        "--max-workers", "-w", type=int, default=DEFAULT_MAX_WORKERS,
        help=f"Downloads paralelos (padrão: {DEFAULT_MAX_WORKERS})"
    )
    parser.add_argument(
        "--max-retries", "-r", type=int, default=DEFAULT_MAX_RETRIES,
        help=f"Máximo de tentativas por PDF (padrão: {DEFAULT_MAX_RETRIES})"
    )
    parser.add_argument(
        "--timeout", "-t", type=int, default=DEFAULT_TIMEOUT,
        help=f"Timeout por request em segundos (padrão: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--no-cloudscraper", action="store_true",
        help="Desabilita cloudscraper (usa requests puro)"
    )
    parser.add_argument(
        "--delay", "-d", type=float, default=DELAY_BETWEEN_REQUESTS,
        help=f"Delay entre downloads em segundos (padrão: {DELAY_BETWEEN_REQUESTS})"
    )

    args = parser.parse_args()


    json_files = list(args.files) if args.files else []
    if args.input_dir:
        input_path = Path(args.input_dir)
        if input_path.is_dir():
            json_files.extend(
                str(p) for p in sorted(input_path.glob("*.json"))
            )

    if not json_files:
        parser.error(
            "Nenhum arquivo JSON fornecido. "
            "Use: script.py arquivo1.json ou --input-dir ./pasta/"
        )

    logger = setup_logging(args.log_dir)
    logger.info("=" * 60)
    logger.info("ANEEL PDF Downloader - Iniciando")
    logger.info("=" * 60)
    logger.info(f"Arquivos JSON: {json_files}")
    logger.info(f"Output dir: {args.output_dir}")
    logger.info(f"Workers: {args.max_workers} | Retries: {args.max_retries} | "
                f"Timeout: {args.timeout}s | Delay: {args.delay}s")
    logger.info(f"Cloudscraper: {'Desabilitado' if args.no_cloudscraper else 'Ativo'}")

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    stats = DownloadStats(inicio=datetime.now())


    pdf_items = parse_json_files(json_files, logger)
    stats.total_pdfs_encontrados = len(pdf_items)

    if not pdf_items:
        logger.warning("Nenhum PDF encontrado nos arquivos JSON.")
        return

    logger.info(f"Total de PDFs para processar: {len(pdf_items)}")

   
    session = create_session(use_cloudscraper=not args.no_cloudscraper)

    logger.info("Aquecendo sessão (visitando aneel.gov.br)...")
    try:
        warmup = session.get("https://www.aneel.gov.br/", timeout=15)
        logger.info(f"Warmup: status {warmup.status_code}")
    except Exception as e:
        logger.warning(f"Warmup falhou (não crítico): {e}")


    results = []

    if args.max_workers <= 1:
        for i, item in enumerate(pdf_items, 1):
            logger.info(f"[{i}/{len(pdf_items)}] {item['arquivo']}")
            result = download_pdf(
                item, session, args.output_dir,
                args.max_retries, args.timeout, logger,
            )
            results.append(result)
            if i < len(pdf_items):
                time.sleep(args.delay)
    else:
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_to_item = {}
            for i, item in enumerate(pdf_items):
                if i > 0:
                    time.sleep(args.delay / args.max_workers)
                future = executor.submit(
                    download_pdf, item, session, args.output_dir,
                    args.max_retries, args.timeout, logger,
                )
                future_to_item[future] = item

            for j, future in enumerate(as_completed(future_to_item), 1):
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"[{j}/{len(pdf_items)}] Concluído: {result.arquivo}")
                except Exception as e:
                    item = future_to_item[future]
                    logger.error(f"Erro thread para {item['arquivo']}: {e}")
                    results.append(DownloadResult(
                        url=item["url"],
                        arquivo=item["arquivo"],
                        data_registro=item["data_registro"],
                        titulo=item["titulo"],
                        tipo_pdf=item["tipo"],
                        sucesso=False,
                        erro_tipo="THREAD_ERROR",
                        erro_mensagem=str(e),
                    ))

    
    stats.fim = datetime.now()
    for r in results:
        if r.sucesso:
            if r.erro_tipo == "PULADO_JA_EXISTE":
                stats.downloads_pulados += 1
            else:
                stats.downloads_sucesso += 1
                stats.bytes_total += r.tamanho_bytes or 0
        else:
            stats.downloads_falha += 1

    
    generate_error_report(results, stats, args.log_dir, logger)

    logger.info("Execução finalizada.")

    
    if stats.downloads_falha > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()