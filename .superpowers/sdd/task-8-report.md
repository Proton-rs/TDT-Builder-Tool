# Task 8 report — 2A: aplicar DE->PARA nos 2 choke points de sigla + gate

## Mudanças

- `src/tdt/normalizacao/estruturador.py`: novo param `de_para: dict[str, str] | None = None`
  em `estruturar()`. No branch `tem_sigla` (linha ~181), `sv` é canonizado via
  `de_para.get(sv, sv)` **antes** do teste `sv in siglas_set` — mas só quando `sv`
  bruto ainda NÃO é válido em `siglas_set` (precedência do match direto).
- `src/tdt/normalizacao/estruturador_homogeneo.py`: leitura de `sigla` (linha ~101)
  vira `sigla_bruta`; `sigla` = `lp.de_para.get(sigla_bruta.upper(), sigla_bruta)`
  só quando `lp.por_sigla(sigla_bruta)` é `None` (mesma precedência). Quando
  `sigla != sigla_bruta`, aviso é anexado a `avisos` (4º elemento do retorno):
  `f"{sheet_name}:{i}: sigla '{sigla_bruta}' normalizada p/ '{sigla}' (DE->PARA)"`.
- `src/tdt/pipeline.py`: call site de `estruturar()` (heterogêneo) passa
  `de_para=lp.de_para`.
- `tests/test_estruturador.py`: 2 testes novos — sigla presente em `de_para`
  normaliza e decide; sigla ausente de `de_para` comportamento inalterado.
- `tests/test_estruturador_homogeneo.py`: `_ListaPadraoFake` ganha `de_para`;
  1 teste novo — sigla normalizada emite aviso com sigla antiga → nova.
- `docs/fluxo_dados.md`: linha `estruturador.estruturar` atualizada
  (canoniza via DE->PARA, aviso no homogêneo).

## Achado durante a task (correção de design, fora do brief literal)

Rodar a suíte completa após a implementação literal do brief (aplicar `de_para`
incondicionalmente antes do teste `siglas_set`) quebrou
`tests/test_integracao_san2.py::test_san2_cobertura_por_sheet_bate_com_a_lista_padrao`
(decididos 145 < 150 esperado). Causa: a sheet `DE->PARA` real (`docs/Pontos
Padrao ADMS_v2.xlsx`) contém entradas como `LDF -> MANUT` e `FUGA -> FGTE`.
`LDF` e `FUGA` já são siglas VÁLIDAS em `siglas_set` (dado real SAN2) — o
mapeamento incondicional as trocava por siglas fora da lista (`MANUT` não
existe em `siglas_set`), fazendo sinais que já decidiam corretamente caírem
de volta pro scoring. Confirmado bisectando com `git stash` (baseline sem
minhas mudanças: teste passa).

Fix (regra do CLAUDE.md — não quebrar o que já funciona, sem desligar a
feature nova): DE->PARA só se aplica quando a sigla bruta NÃO resolve direto
(`sv not in siglas_set` / `lp.por_sigla(sigla_bruta) is None`) — precedência
do match direto sobre o mapeamento legado. Sigla "90" (ausente de
`siglas_set`, presente em `de_para` → "R90") continua normalizando
corretamente; `LDF`/`FUGA` (já válidas) não são mais desfeitas.

## Testes

`PYTHONPATH=src python -m pytest tests/test_estruturador.py
tests/test_estruturador_homogeneo.py tests/test_integracao_san2.py -q`
→ 61 passed.

Suíte completa: `PYTHONPATH=src python -m pytest -q` → 1049 passed, 5 skipped,
2 xfailed (mesmo baseline pré-existente, nenhuma regressão).

## Gate

```
PYTHONPATH=src python -m bench.regressao
[GTD] comum=952 iguais=688 pct=72.3%
   FAIL addr=5 esperado=MOLA obtido=? (Mola descarregada vira MLCC...)
   FAIL addr=7 esperado=BBFC obtido=LIGAR (...)
   FAIL addr=16 esperado=DSEC obtido=43LR (...)
   FAIL addr=51 esperado=AJG2 obtido=G2 (...)
   FAIL addr=62 esperado=50F1 obtido=1 (...)
   FAIL addr=67 esperado=51N1 obtido=? (...)
GATE FALHOU: 6 caso(s)
```

pct=72.3 (baseline: 72.3, commit 46cd915). 6 fail casos, mesmos addrs do
baseline (5,7,16,51,62,67) — nenhum caso PASS virou FAIL, nenhum caso novo.
Sem regressão.

## Status

DONE.
