"""Testa o acesso do Service Principal aos workspaces do Power BI (somente leitura).

Uso: python scripts/testar_conexao.py

Para cada ambiente de config/ambientes.json:
  1. obtém um token no Entra ID com AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET;
  2. consulta o workspace na API do Fabric;
  3. lista os itens do workspace.

Não publica nem altera nada. Retorna código 1 se algum ambiente falhar.
Usa apenas a biblioteca padrão do Python.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
API = "https://api.fabric.microsoft.com/v1"
ESCOPO = "https://api.fabric.microsoft.com/.default"

DICAS = {
    "AADSTS7000215": "segredo inválido — confira se cadastrou o VALOR (não o ID do segredo)",
    "AADSTS7000222": "segredo expirado — gere um novo no App Registration",
    "AADSTS700016": "AZURE_CLIENT_ID não encontrado nesse tenant",
    "AADSTS90002": "AZURE_TENANT_ID inválido",
    "PowerBINotAuthorizedException": "o tenant não permite Service Principal nas APIs do Fabric (configuração do administrador)",
    "Unauthorized": "o tenant não permite Service Principal nas APIs do Fabric (configuração do administrador)",
    "InsufficientPrivileges": "o Service Principal não tem papel suficiente no workspace (use Membro ou Administrador)",
    "WorkspaceNotFound": "o Service Principal não foi adicionado ao workspace (Gerenciar acesso)",
    "ItemNotFound": "o Service Principal não foi adicionado ao workspace (Gerenciar acesso)",
}


def dica(texto: str) -> str:
    for chave, mensagem in DICAS.items():
        if chave in texto:
            return f" → {mensagem}"
    return ""


def requisicao(url: str, token: str | None = None, dados: bytes | None = None) -> dict:
    cabecalhos = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(url, data=dados, headers=cabecalhos)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def erro_http(e: urllib.error.HTTPError) -> str:
    corpo = e.read().decode("utf-8", errors="replace")
    try:
        j = json.loads(corpo)
        codigo = j.get("errorCode") or j.get("error", "")
        msg = j.get("message") or j.get("error_description", "")
        texto = f"HTTP {e.code} {codigo}: {msg.splitlines()[0] if msg else ''}"
    except json.JSONDecodeError:
        texto = f"HTTP {e.code}: {corpo[:200]}"
    return texto + dica(corpo)


def obter_token() -> str:
    faltando = [v for v in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET") if not os.getenv(v)]
    if faltando:
        sys.exit(f"ERRO: variáveis ausentes: {', '.join(faltando)} "
                 "(variáveis Protected só existem em pipelines de branches protegidas)")
    url = f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}/oauth2/v2.0/token"
    dados = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": os.environ["AZURE_CLIENT_ID"],
        "client_secret": os.environ["AZURE_CLIENT_SECRET"],
        "scope": ESCOPO,
    }).encode()
    try:
        return requisicao(url, dados=dados)["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"ERRO ao obter token: {erro_http(e)}")


def main() -> int:
    ambientes = json.loads((RAIZ / "config" / "ambientes.json").read_text(encoding="utf-8"))

    print(f"Service Principal: {os.getenv('AZURE_CLIENT_ID', '?')}")
    token = obter_token()
    print("Token obtido no Entra ID: OK\n")

    falhas = 0
    for ambiente, cfg in ambientes.items():
        ws_id = cfg["workspace_id"]
        print(f"[{ambiente}] {cfg['nome']} ({ws_id})")
        try:
            ws = requisicao(f"{API}/workspaces/{ws_id}", token)
            print(f"  workspace: OK — '{ws.get('displayName')}' capacidade={ws.get('capacityId', 'nenhuma')}")
            itens = requisicao(f"{API}/workspaces/{ws_id}/items", token).get("value", [])
            print(f"  itens: {len(itens)}")
            for item in itens[:15]:
                print(f"    - [{item.get('type')}] {item.get('displayName')}")
            if len(itens) > 15:
                print(f"    ... e mais {len(itens) - 15}")
        except urllib.error.HTTPError as e:
            falhas += 1
            print(f"  FALHOU: {erro_http(e)}")
        except urllib.error.URLError as e:
            falhas += 1
            print(f"  FALHOU: sem conexão com a API do Fabric ({e.reason})")
        print()

    print("Resultado: " + (f"FALHOU em {falhas} ambiente(s)" if falhas else "OK — acesso confirmado nos 3 workspaces"))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
