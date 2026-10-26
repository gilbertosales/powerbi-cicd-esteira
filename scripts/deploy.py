"""Publica os projetos PBIP no workspace do Power BI de um ambiente.

Uso: python scripts/deploy.py --ambiente <desenvolvimento|homologacao|producao> [--modo dry-run|real]

Modos:
  dry-run  mostra o que seria publicado, sem chamar a API (padrão enquanto não há Service Principal);
  real     publica com fabric-cicd usando o Service Principal das variáveis
           AZURE_TENANT_ID, AZURE_CLIENT_ID e AZURE_CLIENT_SECRET.

O ID do workspace vem da variável PBI_WORKSPACE_ID (definida por environment no GitLab)
ou, na falta dela, de config/ambientes.json.
"""

import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RELATORIOS = RAIZ / "relatorios"
TIPOS = {".SemanticModel": "SemanticModel", ".Report": "Report"}


def listar_itens() -> list[tuple[str, str]]:
    itens = []
    for sufixo, tipo in TIPOS.items():
        for pasta in sorted(PASTA_RELATORIOS.rglob(f"*{sufixo}")):
            if pasta.is_dir():
                itens.append((tipo, pasta.name[: -len(sufixo)]))
    return itens


def publicar_real(workspace_id: str, ambiente: str) -> None:
    faltando = [v for v in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET") if not os.getenv(v)]
    if faltando:
        sys.exit(f"ERRO: variáveis do Service Principal ausentes: {', '.join(faltando)}")

    try:
        from azure.identity import ClientSecretCredential
        from fabric_cicd import FabricWorkspace, publish_all_items
    except ImportError:
        sys.exit("ERRO: instale as dependências: pip install fabric-cicd azure-identity")

    credencial = ClientSecretCredential(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )
    workspace = FabricWorkspace(
        workspace_id=workspace_id,
        environment=ambiente,
        repository_directory=str(PASTA_RELATORIOS),
        item_type_in_scope=list(TIPOS.values()),
        token_credential=credencial,
    )
    publish_all_items(workspace)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ambiente", required=True, choices=["desenvolvimento", "homologacao", "producao"])
    parser.add_argument("--modo", default="dry-run", choices=["dry-run", "real"])
    args = parser.parse_args()

    config = json.loads((RAIZ / "config" / "ambientes.json").read_text(encoding="utf-8"))[args.ambiente]
    workspace_id = os.getenv("PBI_WORKSPACE_ID") or config["workspace_id"]

    print(f"Ambiente:  {args.ambiente}")
    print(f"Workspace: {config['nome']} ({workspace_id})")
    print(f"Modo:      {args.modo}")
    print(f"Commit:    {os.getenv('CI_COMMIT_SHORT_SHA', 'local')}")

    itens = listar_itens()
    print(f"\nItens a publicar ({len(itens)}):")
    for tipo, nome in itens:
        print(f"  - [{tipo}] {nome}")

    if not itens:
        print("\nNenhum item encontrado em relatorios/ — nada a publicar.")
        return 0

    if args.modo == "dry-run":
        print("\nSIMULAÇÃO: nenhuma alteração foi feita no Power BI.")
        return 0

    publicar_real(workspace_id, args.ambiente)
    print("\nPublicação concluída.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
