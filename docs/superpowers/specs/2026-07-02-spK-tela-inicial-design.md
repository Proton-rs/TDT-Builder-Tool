# SP-K — Tela inicial: seleção de sheets + validação de sigla SE — Design

**Data:** 2026-07-02
**Arquivos-alvo:** `src/tdt/ui/tela_inicial.py`, `src/tdt/pipeline.py` (consumo
da seleção), `src/tdt/ui/estado.py`.

## Problema

1. **Bug:** o sistema de selecionar sheets para análise na tela inicial não
   está funcionando (seleção não é respeitada pelo pipeline). Conferir também
   se RENOMEAR sheet na tela inicial funciona.
2. **Validação faltante:** é possível executar sem informar a sigla da SE.

## Design

### 1. Seleção/rename de sheets (bug fix)

Fase diagnóstica: reproduzir com input multi-sheet — marcar/desmarcar sheets,
renomear, executar, verificar o que o pipeline recebeu. Localizar onde a
seleção se perde (UI não emite? estado não persiste? pipeline ignora?).
Fix na causa raiz + teste que cobre o contrato UI→pipeline (sheets
desmarcadas não processam; sheet renomeada processa com o nome novo, que é o
nome de módulo usado pelo estruturador).

### 2. Sigla da SE obrigatória

Bloquear execução sem sigla da SE: botão Executar desabilitado enquanto o
campo estiver vazio + hint visual do motivo (tooltip/label). Validação no
handler também (defesa em profundidade — o estado pode ser carregado de
config antiga).

## Critérios de aceite

1. Sheets desmarcadas não aparecem no output; renomear sheet reflete no
   módulo dos sinais. Teste automatizado do contrato (sem UI manual).
2. Executar bloqueado sem sigla SE; habilita ao preencher. Teste do gate.
3. `python -m pytest -q` verde.

## Fora de escopo

- Redesenho visual da tela inicial.
- Filtros da tela de revisão (SP-J).
