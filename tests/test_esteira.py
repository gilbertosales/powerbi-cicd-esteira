"""Testes da validação PBIP e do deploy em modo simulação."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLO = RAIZ / "relatorios"


def rodar(*args, cwd=RAIZ):
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )


@pytest.fixture
def copia(tmp_path):
    destino = tmp_path / "relatorios"
    shutil.copytree(EXEMPLO, destino)
    return destino


def test_exemplo_valido():
    r = rodar("scripts/validar_pbip.py", "relatorios")
    assert r.returncode == 0, r.stdout
    assert "Relatórios encontrados: 1" in r.stdout
    assert "Resultado: OK" in r.stdout


def test_json_invalido_reprova(copia):
    (copia / "Vendas_Exemplo.Report" / "definition.pbir").write_text("{ quebrado", encoding="utf-8")
    r = rodar(str(RAIZ / "scripts/validar_pbip.py"), str(copia), cwd=copia.parent)
    assert r.returncode == 1
    assert "JSON inválido" in r.stdout


def test_modelo_referenciado_inexistente_reprova(copia):
    shutil.rmtree(copia / "Vendas_Exemplo.SemanticModel")
    r = rodar(str(RAIZ / "scripts/validar_pbip.py"), str(copia), cwd=copia.parent)
    assert r.returncode == 1
    assert "modelo referenciado não encontrado" in r.stdout


def test_pbix_versionado_reprova(copia):
    (copia / "Relatorio.pbix").write_bytes(b"PK")
    r = rodar(str(RAIZ / "scripts/validar_pbip.py"), str(copia), cwd=copia.parent)
    assert r.returncode == 1
    assert "não deve ser versionado" in r.stdout


def test_sem_platform_so_avisa(copia):
    (copia / "Vendas_Exemplo.Report" / ".platform").unlink()
    r = rodar(str(RAIZ / "scripts/validar_pbip.py"), str(copia), cwd=copia.parent)
    assert r.returncode == 0
    assert "AVISO" in r.stdout


@pytest.mark.parametrize("ambiente", ["desenvolvimento", "homologacao", "producao"])
def test_deploy_dry_run_lista_itens(ambiente):
    r = rodar("scripts/deploy.py", "--ambiente", ambiente, "--modo", "dry-run")
    assert r.returncode == 0, r.stderr
    assert "[SemanticModel] Vendas_Exemplo" in r.stdout
    assert "[Report] Vendas_Exemplo" in r.stdout
    assert "SIMULAÇÃO" in r.stdout


def test_deploy_real_exige_service_principal(monkeypatch):
    for v in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"):
        monkeypatch.delenv(v, raising=False)
    r = rodar("scripts/deploy.py", "--ambiente", "desenvolvimento", "--modo", "real")
    assert r.returncode != 0
    assert "Service Principal ausentes" in r.stderr


def test_ambientes_sem_ids_reais():
    ambientes = json.loads((RAIZ / "config" / "ambientes.json").read_text(encoding="utf-8"))
    assert all(a["workspace_id"].startswith("00000000-") for a in ambientes.values())
