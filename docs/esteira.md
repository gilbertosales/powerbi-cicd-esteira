# Guia de operação da esteira

## Ambientes

| Ambiente | Branch | Deploy | Quem dispara |
|---|---|---|---|
| Desenvolvimento | `develop` | automático após o merge | pipeline |
| Homologação | `homologacao` | manual (▶) | aprovador |
| Produção | `main` | manual (▶) | aprovador |

O ID de cada workspace vem da variável `PBI_WORKSPACE_ID`, com escopo por ambiente. Na falta dela, vem de `config/ambientes.json`.

## Fluxo do dia a dia

1. `git checkout -b feature/<descricao> develop`
2. Abra o `.pbip` no Power BI Desktop, faça a alteração e salve.
3. Confira o que mudou de verdade: `git diff --stat`. Em PBIP, cada visual, página e tabela é um arquivo de texto, então o diff mostra exatamente o que mudou.
4. `python scripts/validar_pbip.py relatorios`
5. Faça commit, push e abra o MR para `develop`. O pipeline do MR roda só a validação.
6. Depois do merge, o deploy em Desenvolvimento acontece sozinho.
7. Para promover, abra o MR `develop → homologacao` com o template **Promocao**. O aprovador faz o merge e clica em ▶ no job de deploy.
8. Repita com `homologacao → main` para Produção.

## Fases de implantação

| Fase | O que entrega | Pré-requisito |
|---|---|---|
| **1. Simulação** | Branches protegidas, MRs, validação e deploy em `dry-run` | Só o GitLab e um runner |
| **2. Deploy real** | `fabric-cicd` publicando nos workspaces | Service Principal, permissão no tenant e Python ≤ 3.12 no runner |

Fazer em duas fases permitiu colocar governança e validação em uso antes de resolver as permissões no tenant, que dependiam de outra equipe.

## Service Principal

1. **App Registration** no Entra ID e um **client secret**. Guarde o *valor*, não o ID do segredo.
2. Coloque o Service Principal num **grupo de segurança**.
3. No portal de administração do Fabric, habilite *Service principals can use Fabric APIs* para esse grupo.
4. Adicione o Service Principal como **Membro** em cada workspace.
5. Cadastre `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` e `AZURE_CLIENT_SECRET` como variáveis **Protected + Masked**.
6. Rode o job manual `testar-conexao` para confirmar o acesso aos três workspaces.

## Rollback

1. No MR que introduziu o problema, clique em **Revert**. Isso cria um MR de reversão para `develop`.
2. Faça o merge. O deploy em Desenvolvimento restaura a versão anterior.
3. Promova a reversão como qualquer mudança: `develop → homologacao → main`.

Esse procedimento foi executado de ponta a ponta nos três ambientes.

## Depois da primeira publicação

Um modelo semântico publicado pela API chega **sem dados** e sem vínculo com o gateway. Na primeira vez, associe o gateway e as credenciais da fonte no serviço e rode a atualização. Nas publicações seguintes, as configurações são mantidas.

## Solução de problemas

| Sintoma | Causa / solução |
|---|---|
| Pipeline fica *pending* | Nenhum runner com a tag `powerbi-win` está ativo |
| `detected dubious ownership` | A pasta de builds foi criada por outro usuário. Apague a pasta de builds do runner e rode de novo |
| `Filename too long` (Windows) | `git config --global core.longpaths true` e um `builds_dir` curto |
| Não consigo fazer push na `main` | É o esperado. Use Merge Request |
| Deploy mostra `dry-run` mesmo com `DEPLOY_MODE=real` | A variável não tem o escopo do ambiente certo, ou o job rodou antes dela existir. Ajuste e use **Retry** |
| `instale as dependências: pip install fabric-cicd` | O job não usou o Python 3.12. Confira `FABRIC_PYTHON` no runner |
| `variáveis do Service Principal ausentes` | Deploy fora de branch protegida, ou faltam as variáveis `AZURE_*` |
| `403 InsufficientPrivileges` | O Service Principal não é Membro do workspace. Rode `testar-conexao` |
| Relatório publicado abre sem dados | Primeira publicação: configure o gateway e atualize o modelo |

## Segurança

- Nenhuma credencial no repositório: apenas variáveis **Protected + Masked**.
- O token do runner fica no `config.toml` da máquina e nunca é versionado.
- Use só runners **conhecidos e protegidos** com a tag da esteira, porque os jobs de deploy recebem o segredo do Service Principal.
- Revise periodicamente quem é Maintainer: esses usuários são os aprovadores.
