"""Valida a estrutura dos projetos Power BI (PBIP) antes do deploy.

Uso: python scripts/validar_pbip.py [pasta]   (padrão: relatorios)

Verifica:
  - pastas <Nome>.Report possuem definition.pbir e o modelo referenciado existe;
  - pastas <Nome>.SemanticModel possuem definition.pbism e a definição (TMDL ou model.bim);
  - todos os arquivos JSON (.json, .pbir, .pbism, .platform, .pbip) são válidos;
  - arquivos proibidos (cache.abf, localSettings.json, .pbix) não foram versionados.

Retorna código 1 se houver erros; avisos não falham o pipeline.
"""

import json
import subprocess
import sys
from pathlib import Path

EXTENSOES_JSON = {".json", ".pbir", ".pbism", ".platform", ".pbip"}
PROIBIDOS = {"cache.abf", "localSettings.json"}

erros: list[str] = []
avisos: list[str] = []


def validar_json(arquivo: Path) -> dict | None:
    try:
        return json.loads(arquivo.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        erros.append(f"JSON inválido: {arquivo} (linha {e.lineno}: {e.msg})")
    except UnicodeDecodeError:
        erros.append(f"Arquivo não está em UTF-8: {arquivo}")
    return None


def ignorados_pelo_git(arquivos: list[Path]) -> set[Path]:
    """Arquivos cobertos pelo .gitignore (existem só na máquina local, não vão para o GitLab)."""
    try:
        r = subprocess.run(["git", "check-ignore", "-z", "--stdin"],
                           input="\0".join(a.as_posix() for a in arquivos),
                           capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        return set()
    return {Path(p) for p in r.stdout.split("\0") if p}


def validar_report(pasta: Path) -> None:
    pbir = pasta / "definition.pbir"
    if not pbir.exists():
        erros.append(f"{pasta.name}: falta definition.pbir")
        return
    dados = validar_json(pbir)
    caminho = (dados or {}).get("datasetReference", {}).get("byPath", {}).get("path")
    if caminho and not (pasta / caminho).resolve().exists():
        erros.append(f"{pasta.name}: modelo referenciado não encontrado ({caminho})")
    if not (pasta / ".platform").exists():
        avisos.append(f"{pasta.name}: sem arquivo .platform (necessário para o deploy via API)")


def validar_modelo(pasta: Path) -> None:
    if not (pasta / "definition.pbism").exists():
        erros.append(f"{pasta.name}: falta definition.pbism")
    if not (pasta / "definition").is_dir() and not (pasta / "model.bim").exists():
        erros.append(f"{pasta.name}: falta a definição do modelo (pasta definition/ ou model.bim)")
    if not (pasta / ".platform").exists():
        avisos.append(f"{pasta.name}: sem arquivo .platform (necessário para o deploy via API)")


def main() -> int:
    raiz = Path(sys.argv[1] if len(sys.argv) > 1 else "relatorios")
    if not raiz.is_dir():
        print(f"Pasta '{raiz}' não encontrada.")
        return 1

    reports = sorted(p for p in raiz.rglob("*.Report") if p.is_dir())
    modelos = sorted(p for p in raiz.rglob("*.SemanticModel") if p.is_dir())

    arquivos = [a for a in raiz.rglob("*") if a.is_file()]
    ignorados = ignorados_pelo_git(arquivos)
    for arquivo in arquivos:
        if arquivo in ignorados:
            continue
        if arquivo.name in PROIBIDOS or arquivo.suffix.lower() == ".pbix":
            erros.append(f"Arquivo não deve ser versionado: {arquivo}")
        elif arquivo.suffix.lower() in EXTENSOES_JSON:
            validar_json(arquivo)

    for pasta in reports:
        validar_report(pasta)
    for pasta in modelos:
        validar_modelo(pasta)

    print(f"Relatórios encontrados: {len(reports)}")
    for p in reports:
        print(f"  - {p.relative_to(raiz)}")
    print(f"Modelos semânticos encontrados: {len(modelos)}")
    for p in modelos:
        print(f"  - {p.relative_to(raiz)}")

    if not reports and not modelos:
        avisos.append(f"Nenhum projeto PBIP em '{raiz}' — nada para validar.")

    for a in avisos:
        print(f"AVISO: {a}")
    for e in erros:
        print(f"ERRO:  {e}")

    print("Resultado: " + ("FALHOU" if erros else "OK"))
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
