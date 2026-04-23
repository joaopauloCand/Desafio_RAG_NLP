import json
import re
import argparse
from pathlib import Path


# variações de "Texto Integral" 
_TEXTO_INTEGRAL_TYPOS = {
    "texto integral",
    "texto integeral",
    "texto integraal",
    "texto integra",
    "texto interal",
    "texto iintegral",
    "texto integral",
    "texto lintegral",
    "texxto integral",
    "integral",
    "pdf",
}



def normalizar_tipo_pdf(tipo_raw):
    if not tipo_raw:
        return ""
  
    limpo = tipo_raw.strip().rstrip(":").strip()
    limpo = re.sub(r"\s+", " ", limpo)

    lower = limpo.lower()

    if lower in _TEXTO_INTEGRAL_TYPOS:
        return "Texto Integral"

    if lower == "texto original":
        return "Texto Original"

    if lower == "texto":
        return "Texto"

    if lower == "voto" or lower.startswith("voto ") or lower.startswith("voto_") or lower.startswith("voto-"):
        return "Voto"

    if lower == "decisão judicial":
        return "Decisão Judicial"

    if lower == "decisão":
        return "Decisão"

    if lower.startswith("nota técnica") or lower.startswith("nota tecnica"):
        return "Nota Técnica"

    if lower.startswith("nt ") or lower.startswith("nt.") or lower.startswith("nt-"):
        return "Nota Técnica"

    if lower.startswith("exposição de motivos"):
        return "Exposição de Motivos"

    if lower.startswith("memória de cálculo") or lower.startswith("memória de calculo"):
        return "Memória de Cálculo"

    if lower.startswith("pleito"):
        return "Pleito"

    if lower.startswith("glossário"):
        return "Glossário"

    if lower.startswith("simulador"):
        return "Simulador"

    if lower.startswith("programa nodal"):
        return "Programa Nodal"

    if lower.startswith("planilha"):
        return "Planilha"

    if lower.startswith("base de da"):
        return "Base de Dados"

    if lower.startswith("submódulo") or lower.startswith("submodulo"):
        return "Submódulo"

    if lower.startswith("região"):
        return "Região"

    if lower.startswith("anexo"):
        return "Anexo"
    
    if lower.startswith("plano anual"):
        return "Plano"

    if lower.startswith("site"):
        return "Site"

    if lower.startswith("rag"):
        return "Resultado Leilão"

    return limpo


def remover_prefixo(valor, prefixo):
    if not valor:
        return None
    limpo = valor.strip()
    if limpo.lower().startswith(prefixo.lower()):
        limpo = limpo[len(prefixo):].strip()
    if not limpo:
        return None
    limpo = re.sub(r"\s+", " ", limpo)
    return limpo


def converter_data(valor):
    if not valor:
        return None
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", valor)
    if match:
        dia, mes, ano = match.groups()
        return f"{ano}-{mes}-{dia}"
    return None


def limpar_ementa(ementa):
    if not ementa:
        return None
    limpo = ementa.strip()
    if limpo.endswith("Imprimir"):
        limpo = limpo[:-len("Imprimir")].strip()
    if not limpo:
        return None
    return limpo


def gerar_id(data, titulo):
    if not titulo:
        titulo = "sem_titulo"
    slug = titulo.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return f"{data}_{slug}"


def normalizar_espacos(valor):
    if not valor:
        return None
    limpo = re.sub(r"\s+", " ", valor.strip())
    if not limpo:
        return None
    return limpo


def processar_registro(data_key, registro):

    titulo_raw = registro.get("titulo")
    titulo = titulo_raw.strip() if titulo_raw else None

    autor_raw = registro.get("autor")
    autor = normalizar_espacos(autor_raw)

    material_raw = registro.get("material")
    material = normalizar_espacos(material_raw)

    esfera = remover_prefixo(registro.get("esfera"), "Esfera:")
    situacao = remover_prefixo(registro.get("situacao"), "Situação:")
    assinatura_str = registro.get("assinatura")
    assinatura = converter_data(assinatura_str)
    publicacao_str = registro.get("publicacao")
    publicacao = converter_data(publicacao_str)
    assunto = remover_prefixo(registro.get("assunto"), "Assunto:")

    ementa_raw = registro.get("ementa")
    ementa = limpar_ementa(ementa_raw)

    documentos = []
    pdfs = registro.get("pdfs", []) or []
    for pdf in pdfs:
        tipo_raw = pdf.get("tipo", "") or ""
        tipo_limpo = tipo_raw.strip().rstrip(":").strip()
        tipo_limpo = re.sub(r"\s+", " ", tipo_limpo)

        tipo_normalizado = normalizar_tipo_pdf(tipo_raw)

        doc = {
            "tipo": tipo_normalizado,
            "tipo_original": tipo_limpo if tipo_limpo else None,
            "url": pdf.get("url", ""),
            "arquivo_origem": pdf.get("arquivo", ""),
            "texto_extraido": None,
        }
        documentos.append(doc)

    resultado = {
        "id": gerar_id(data_key, titulo),
        "data_publicacao": data_key,
        "titulo": titulo,
        "autor": autor,
        "material": material,
        "esfera": esfera,
        "situacao": situacao,
        "assinatura": assinatura,
        "publicacao": publicacao,
        "assunto": assunto,
        "ementa": ementa,
        "documentos": documentos,
    }

    return resultado


def processar_json(json_path, output_dir):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    subpasta = Path(output_dir) / Path(json_path).stem
    subpasta.mkdir(parents=True, exist_ok=True)

    total = 0
    for data_key, day_data in data.items():
        if not isinstance(day_data, dict):
            continue

        registros = day_data.get("registros", [])
        for registro in registros:
            resultado = processar_registro(data_key, registro)

            filename = f"{resultado['id']}.json"
            filepath = subpasta / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)

            total += 1

    return {"arquivo": json_path, "registros_processados": total}


def main():
    parser = argparse.ArgumentParser(
        description="Normaliza metadados ANEEL para modelo da fase 2"
    )
    parser.add_argument("--input-dir", "-i", required=True,
                        help="Diretório com JSONs de metadados brutos")
    parser.add_argument("--output-dir", "-o", default="D:/clean_metadata",
                        help="Diretório de saída (padrão: D:/clean_metadata)")
    args = parser.parse_args()

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_files = sorted(Path(args.input_dir).glob("*.json"))
    if not json_files:
        print(f"Nenhum JSON encontrado em {args.input_dir}")
        return

    total_geral = 0
    for jf in json_files:
        print(f"  Processando: {jf.name}...", end=" ")
        stats = processar_json(str(jf), args.output_dir)
        print(f"{stats['registros_processados']} registros")
        total_geral += stats["registros_processados"]

    print(f"\nTotal: {total_geral} JSONs gerados em {args.output_dir}")


if __name__ == "__main__":
    main()