import json
import sys
import time
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime

from unstructured.partition.auto import partition

EXTENSOES_SUPORTADAS = {".pdf", ".html", ".htm"}


# ─── Logger ──────────────────────────────────────────────────────────────────

def setup_logging(log_dir: str) -> logging.Logger:
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


# ─── SQLite - Controle de Progresso ──────────────────────────────────────────

def init_db(db_path: str) -> sqlite3.Connection:
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


def ja_processado(conn: sqlite3.Connection, json_id: str) -> bool:
    row = conn.execute(
        "SELECT status FROM progresso WHERE json_id = ?", (json_id,)
    ).fetchone()
    return row is not None and row[0] == "OK"


def registrar_progresso(conn: sqlite3.Connection, json_id: str,
                        status: str, docs_total: int, docs_extraidos: int,
                        docs_sem_arquivo: int, docs_erro: int,
                        tempo_seg: float, erro_msg: str = None):
    conn.execute("""
        INSERT OR REPLACE INTO progresso
        (json_id, status, docs_total, docs_extraidos, docs_sem_arquivo,
         docs_erro, tempo_seg, erro_msg, processado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (json_id, status, docs_total, docs_extraidos, docs_sem_arquivo,
          docs_erro, round(tempo_seg, 2), erro_msg,
          datetime.now().isoformat()))
    conn.commit()


# ─── Extração de Texto ──────────────────────────────────────────────────────

def extrair_texto_arquivo(filepath: str) -> str:
    """Extrai texto de um PDF, HTML ou HTM usando Unstructured."""
    ext = Path(filepath).suffix.lower()

    kwargs = {"filename": filepath, "languages": ["por"]}
    if ext == ".pdf":
        kwargs["strategy"] = "fast"

    elements = partition(**kwargs)
    texto = "\n\n".join(str(el) for el in elements)
    tem_tabela = any(el.category == "Table" for el in elements)
    return {"texto": texto, "tem_tabela": tem_tabela}

# ─── Processamento ──────────────────────────────────────────────────────────

def processar_json(json_path: str, files_dir: str, output_dir: str,
                   conn: sqlite3.Connection, logger: logging.Logger) -> dict:
    """Processa um JSON normalizado: localiza arquivos, extrai texto, salva."""

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

    for doc in docs:
        arquivo = doc.get("arquivo_origem", "")
        if not arquivo:
            stats["sem_arquivo"] += 1
            continue

        # Tenta localizar o arquivo
        caminho = Path(files_dir) / data_pub / arquivo
        if not caminho.exists():
            # Tenta sem sanitização (nome original)
            stats["sem_arquivo"] += 1
            logger.debug(f"Arquivo não encontrado: {caminho}")
            continue

        # Verifica extensão suportada
        ext = caminho.suffix.lower()
        if ext not in EXTENSOES_SUPORTADAS:
            logger.debug(f"Extensão não suportada: {caminho.name} ({ext})")
            stats["sem_arquivo"] += 1
            continue

        # Extrai texto
        try:
            resultado = extrair_texto_arquivo(str(caminho))
            texto = resultado["texto"]
            doc["texto_extraido"] = texto if texto.strip() else None
            doc["tem_tabela"] = resultado["tem_tabela"]
            if texto.strip():
                stats["extraidos"] += 1
            else:
                logger.debug(f"Texto vazio: {caminho.name}")
        except Exception as e:
            logger.warning(f"Erro ao extrair {caminho.name}: {type(e).__name__}: {e}")
            doc["texto_extraido"] = None
            stats["erro"] += 1

    # Salva JSON atualizado
    output_path = Path(output_dir) / Path(json_path).name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Extrai texto dos arquivos e popula os JSONs normalizados"
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
    args = parser.parse_args()

    logger = setup_logging(args.log_dir)
    logger.info("=" * 60)
    logger.info("Pipeline de Parsing - Extração de Texto")
    logger.info("=" * 60)
    logger.info(f"Metadados: {args.metadata_dir}")
    logger.info(f"Arquivos:  {args.files_dir}")
    logger.info(f"Saída:     {args.output_dir}")
    logger.info(f"DB:        {args.db}")

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    conn = init_db(args.db)

    # Coleta JSONs
    jsons = sorted(Path(args.metadata_dir).glob("*.json"))
    if not jsons:
        logger.error(f"Nenhum JSON encontrado em {args.metadata_dir}")
        return

    # Filtra já processados
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

    # Estatísticas globais
    total_extraidos = 0
    total_sem_arquivo = 0
    total_erros = 0
    total_docs = 0
    inicio_geral = time.time()

    for i, json_path in enumerate(pendentes, 1):
        json_id = json_path.stem
        logger.info(f"[{i}/{len(pendentes)}] {json_id}")

        inicio = time.time()
        try:
            stats = processar_json(
                str(json_path), args.files_dir, args.output_dir, conn, logger
            )
            tempo = time.time() - inicio

            registrar_progresso(
                conn, json_id, "OK",
                stats["total"], stats["extraidos"],
                stats["sem_arquivo"], stats["erro"],
                tempo
            )

            total_docs += stats["total"]
            total_extraidos += stats["extraidos"]
            total_sem_arquivo += stats["sem_arquivo"]
            total_erros += stats["erro"]

            logger.info(
                f"  -> {stats['extraidos']}/{stats['total']} extraídos, "
                f"{stats['sem_arquivo']} sem arquivo, "
                f"{stats['erro']} erros, {tempo:.1f}s"
            )

        except Exception as e:
            tempo = time.time() - inicio
            registrar_progresso(conn, json_id, "ERRO", 0, 0, 0, 0, tempo, str(e))
            logger.error(f"  -> ERRO GERAL: {e}")
            total_erros += 1

    tempo_total = time.time() - inicio_geral
    conn.close()

    # Resumo
    print(f"\n{'='*60}")
    print(f"  RESUMO DA EXTRAÇÃO")
    print(f"{'='*60}")
    print(f"  JSONs processados:      {len(pendentes)}")
    print(f"  Documentos encontrados: {total_docs}")
    print(f"  Textos extraídos:       {total_extraidos}")
    print(f"  Sem arquivo no disco:   {total_sem_arquivo}")
    print(f"  Erros de extração:      {total_erros}")
    print(f"  Tempo total:            {tempo_total:.1f}s")
    if len(pendentes) > 0:
        print(f"  Tempo médio por JSON:   {tempo_total/len(pendentes):.2f}s")
    print(f"{'='*60}")
    print(f"  Saída em: {args.output_dir}")
    print(f"  Progresso em: {args.db}")


if __name__ == "__main__":
    main()