## Promoção de ambiente

**Origem → Destino:** <!-- ex.: develop → homologacao | homologacao → main -->

### Itens alterados
<!-- Liste relatórios / modelos semânticos alterados -->
- 

### Descrição da mudança
<!-- O que mudou e por quê. Link para issue/demanda, se houver. -->

### Checklist do solicitante
- [ ] Pipeline do MR passou (validação PBIP)
- [ ] Relatório testado no ambiente anterior
- [ ] Não há `.pbix`, `cache.abf` ou credenciais nos arquivos
- [ ] Parâmetros de conexão revisados para o ambiente de destino

### Aprovação (preenchido pelo aprovador)
- [ ] Mudança revisada e validada pelo negócio
- [ ] Autorizado o deploy manual no ambiente de destino

/label ~"promoção"
