

import json
import sys
import time
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool, cpu_count

import fitz 
import pdfplumber
from bs4 import BeautifulSoup

EXTENSOES_SUPORTADAS = {".pdf", ".html", ".htm"}


# ─── Logger: Implementado com ajuda da LLM Claude ──────────────────────────────────────────────────────────────────

def setup_logging(log_dir):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = str(Path(log_dir) / f"parsing_{timestamp}.log")

    logger = logging.getLogger("parsing")
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
    logger.info(f"Log: {log_file}")
    return logger


# ─── SQLite - Controle de Progresso: Implementado com ajuda da LLM Claude ──────────────────────────────────────────

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS progresso (
            json_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            docs_total INTEGER DEFAULT 0,
            docs_extraidos INTEGER DEFAULT 0,
            docs_sem_arquivo INTEGER DEFAULT 0,
            docs_erro INTEGER DEFAULT 0,
            tempo_seg REAL DEFAULT 0,
            erro_msg TEXT,
            processado_em TEXT
        )
    """)
    conn.commit()
    return conn


def ja_processado(conn, json_id):
    row = conn.execute(
        "SELECT status FROM progresso WHERE json_id = ?", (json_id,)
    ).fetchone()
    return row is not None and row[0] == "OK"


def registrar_progresso(conn, json_id, status, docs_total, docs_extraidos,
                        docs_sem_arquivo, docs_erro, tempo_seg, erro_msg=None):
    conn.execute("""
        INSERT OR REPLACE INTO progresso
        (json_id, status, docs_total, docs_extraidos, docs_sem_arquivo,
         docs_erro, tempo_seg, erro_msg, processado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (json_id, status, docs_total, docs_extraidos, docs_sem_arquivo,
          docs_erro, round(tempo_seg, 2), erro_msg,
          datetime.now().isoformat()))
    conn.commit()



def tabela_para_markdown(tabela):
    if not tabela or len(tabela) < 1:
        return ""

    linhas = []
    for row in tabela:
        linhas.append([str(cell).strip() if cell else "" for cell in row])

    num_cols = max(len(row) for row in linhas)

    for row in linhas:
        while len(row) < num_cols:
            row.append("")

    header = "| " + " | ".join(linhas[0]) + " |"
    separador = "| " + " | ".join(["---"] * num_cols) + " |"

    rows_md = []
    for row in linhas[1:]:
        rows_md.append("| " + " | ".join(row) + " |")

    return "\n".join([header, separador] + rows_md)


def detectar_tabelas_pagina(doc_fitz, page_num):
    page = doc_fitz[page_num]
    tables = page.find_tables()
    return len(tables.tables) > 0


def extrair_pdf(filepath):
    doc = fitz.open(filepath)

    paginas_com_tabela = set()
    for i in range(len(doc)):
        if detectar_tabelas_pagina(doc, i):
            paginas_com_tabela.add(i)

    tem_tabela = len(paginas_com_tabela) > 0

    blocos_texto = []    
    blocos_md = []       

    plumber = None
    if tem_tabela:
        plumber = pdfplumber.open(filepath)

    for i in range(len(doc)):
        page_fitz = doc[i]

        if i in paginas_com_tabela and plumber:
            page_plumber = plumber.pages[i]

            tabelas = page_plumber.extract_tables()

            texto_pagina = page_fitz.get_text("text").strip()

            partes_texto = [texto_pagina] if texto_pagina else []
            for tab in tabelas:
                for row in tab:
                    celulas = [str(c).strip() if c else "" for c in row]
                    partes_texto.append("  ".join(celulas))
            blocos_texto.append("\n".join(partes_texto))

            partes_md = [texto_pagina] if texto_pagina else []
            for tab in tabelas:
                md_tabela = tabela_para_markdown(tab)
                if md_tabela:
                    partes_md.append("\n" + md_tabela + "\n")
            blocos_md.append("\n".join(partes_md))

        else:
            texto_pagina = page_fitz.get_text("text").strip()
            if texto_pagina:
                blocos_texto.append(texto_pagina)
                blocos_md.append(texto_pagina)

    doc.close()
    if plumber:
        plumber.close()

    texto_final = "\n\n".join(blocos_texto)
    md_final = "\n\n".join(blocos_md)

    return {
        "texto": texto_final,
        "texto_md": md_final,
        "tem_tabela": tem_tabela,
    }


def extrair_html(filepath):
    conteudo = None
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                conteudo = f.read()
            if "�" not in conteudo:
                break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if conteudo is None:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            conteudo = f.read()

    soup = BeautifulSoup(conteudo, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    tabelas_html = soup.find_all("table")
    tem_tabela = len(tabelas_html) > 0

    texto = soup.get_text(separator="\n", strip=True)

    partes_md = []
    container = soup.body if soup.body else soup

    for element in container.children:
        if hasattr(element, 'name') and element.name == "table":
            rows = []
            for tr in element.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                rows.append(cells)
            md_tab = tabela_para_markdown(rows)
            if md_tab:
                partes_md.append("\n" + md_tab + "\n")
        elif hasattr(element, 'get_text'):
            t = element.get_text(strip=True)
            if t:
                partes_md.append(t)

    texto_md = "\n\n".join(partes_md) if partes_md else texto

    return {
        "texto": texto,
        "texto_md": texto_md,
        "tem_tabela": tem_tabela,
    }


def extrair_texto_arquivo(filepath):
    ext = Path(filepath).suffix.lower()

    if ext == ".pdf":
        return extrair_pdf(filepath)
    elif ext in (".html", ".htm"):
        return extrair_html(filepath)

    return {"texto": "", "texto_md": "", "tem_tabela": False}


def processar_json_worker(args_tuple):
    json_path, files_dir, output_dir = args_tuple

    inicio = time.time()

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            registro = json.load(f)

        json_id = registro["id"]
        data_pub = registro["data_publicacao"]
        docs = registro.get("documentos", [])

        stats = {
            "total": len(docs),
            "extraidos": 0,
            "sem_arquivo": 0,
            "erro": 0,
        }

        erros_detalhe = []

        for doc in docs:
            arquivo = doc.get("arquivo_origem", "")
            if not arquivo:
                stats["sem_arquivo"] += 1
                continue

            caminho = Path(files_dir) / data_pub / arquivo
            if not caminho.exists():
                stats["sem_arquivo"] += 1
                continue

            ext = caminho.suffix.lower()
            if ext not in EXTENSOES_SUPORTADAS:
                stats["sem_arquivo"] += 1
                continue

            try:
                resultado = extrair_texto_arquivo(str(caminho))
                texto = resultado["texto"]
                texto_md = resultado["texto_md"]

                doc["texto_extraido"] = texto if texto.strip() else None
                doc["texto_extraido_md"] = texto_md if texto_md.strip() else None
                doc["tem_tabela"] = resultado["tem_tabela"]

                if texto.strip():
                    stats["extraidos"] += 1
            except Exception as e:
                doc["texto_extraido"] = None
                doc["texto_extraido_md"] = None
                doc["tem_tabela"] = False
                stats["erro"] += 1
                erros_detalhe.append(f"{caminho.name}: {type(e).__name__}: {e}")

        output_path = Path(output_dir) / Path(json_path).name
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(registro, f, ensure_ascii=False, indent=2)

        tempo = time.time() - inicio

        return {
            "json_id": json_id,
            "json_path": json_path,
            "status": "OK",
            "stats": stats,
            "tempo": tempo,
            "erro_msg": None,
            "erros_detalhe": erros_detalhe,
        }

    except Exception as e:
        tempo = time.time() - inicio
        json_id = Path(json_path).stem
        return {
            "json_id": json_id,
            "json_path": json_path,
            "status": "ERRO",
            "stats": {"total": 0, "extraidos": 0, "sem_arquivo": 0, "erro": 0},
            "tempo": tempo,
            "erro_msg": f"{type(e).__name__}: {e}",
            "erros_detalhe": [],
        }


def main():
    parser = argparse.ArgumentParser(
        description="Extrai texto com abordagem híbrida + multiprocessing"
    )
    parser.add_argument("--metadata-dir", "-m", required=True,
                        help="Pasta com JSONs normalizados (clean_metadata)")
    parser.add_argument("--files-dir", "-f", required=True,
                        help="Pasta com arquivos baixados (aneel_pdfs)")
    parser.add_argument("--output-dir", "-o", default="./parsed",
                        help="Pasta de saída com JSONs completos (padrão: ./parsed)")
    parser.add_argument("--log-dir", "-l", default="./logs",
                        help="Pasta de logs (padrão: ./logs)")
    parser.add_argument("--db", default="./parsing_progresso.db",
                        help="Arquivo SQLite de progresso (padrão: ./parsing_progresso.db)")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help=f"Número de workers (padrão: 4, máximo detectado: {cpu_count()})")
    args = parser.parse_args()

    logger = setup_logging(args.log_dir)
    logger.info("=" * 60)
    logger.info("Pipeline de Parsing - Abordagem Híbrida + Multiprocessing")
    logger.info("=" * 60)
    logger.info(f"Metadados: {args.metadata_dir}")
    logger.info(f"Arquivos:  {args.files_dir}")
    logger.info(f"Saída:     {args.output_dir}")
    logger.info(f"DB:        {args.db}")
    logger.info(f"Workers:   {args.workers}")

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    conn = init_db(args.db)

    jsons = sorted(Path(args.metadata_dir).glob("*.json"))
    if not jsons:
        logger.error(f"Nenhum JSON encontrado em {args.metadata_dir}")
        return
    
    pendentes = []
    pulados = 0
    for j in jsons:
        json_id = j.stem
        if ja_processado(conn, json_id):
            pulados += 1
        else:
            pendentes.append(j)

    logger.info(f"JSONs encontrados: {len(jsons)}")
    logger.info(f"Já processados:    {pulados}")
    logger.info(f"Pendentes:         {len(pendentes)}")

    if not pendentes:
        logger.info("Nada a processar.")
        return

    tarefas = [
        (str(j), args.files_dir, args.output_dir)
        for j in pendentes
    ]

    total_extraidos = 0
    total_sem_arquivo = 0
    total_erros = 0
    total_docs = 0
    concluidos = 0
    inicio_geral = time.time()

    # Processa com Pool - processo principal recebe resultados e registra no SQLite
    with Pool(processes=args.workers) as pool:
        for resultado in pool.imap_unordered(processar_json_worker, tarefas):
            concluidos += 1
            json_id = resultado["json_id"]
            stats = resultado["stats"]
            tempo = resultado["tempo"]

            # Registra no SQLite (só o processo principal toca no banco)
            registrar_progresso(
                conn, json_id, resultado["status"],
                stats["total"], stats["extraidos"],
                stats["sem_arquivo"], stats["erro"],
                tempo, resultado["erro_msg"]
            )

            total_docs += stats["total"]
            total_extraidos += stats["extraidos"]
            total_sem_arquivo += stats["sem_arquivo"]
            total_erros += stats["erro"]

            if resultado["status"] == "OK":
                logger.info(
                    f"[{concluidos}/{len(pendentes)}] {json_id} -> "
                    f"{stats['extraidos']}/{stats['total']} extraídos, "
                    f"{stats['sem_arquivo']} sem arquivo, "
                    f"{stats['erro']} erros, {tempo:.1f}s"
                )
                for err in resultado["erros_detalhe"]:
                    logger.warning(f"  {err}")
            else:
                logger.error(
                    f"[{concluidos}/{len(pendentes)}] {json_id} -> "
                    f"ERRO: {resultado['erro_msg']}"
                )

    tempo_total = time.time() - inicio_geral
    conn.close()

    print(f"\n{'='*60}")
    print(f"  RESUMO DA EXTRAÇÃO (MULTIPROCESSING)")
    print(f"{'='*60}")
    print(f"  Workers:                {args.workers}")
    print(f"  JSONs processados:      {concluidos}")
    print(f"  Documentos encontrados: {total_docs}")
    print(f"  Textos extraídos:       {total_extraidos}")
    print(f"  Sem arquivo no disco:   {total_sem_arquivo}")
    print(f"  Erros de extração:      {total_erros}")
    print(f"  Tempo total:            {tempo_total:.1f}s")
    if concluidos > 0:
        print(f"  Tempo médio por JSON:   {tempo_total/concluidos:.2f}s")
    print(f"{'='*60}")
    print(f"  Saída em: {args.output_dir}")
    print(f"  Progresso em: {args.db}")


if __name__ == "__main__":
    main()