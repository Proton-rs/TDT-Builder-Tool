# SP Metadados na Decisão + ALIAS da v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Usar as colunas `DIRECTION` e `TYPE SEVERIDADE` da lista padrão como desempate no matching, ampliar o vocabulário de estados do MM, e fazer `Signal Alias` da TDT gerada vir da lista padrão **v1**.

**Architecture:** Duas regras novas no motor de regras (funções puras, pesos calibráveis em `config.pesos_regras`), uma classe nova de estado (`MODO`) no léxico compartilhado de `semantica_estados`, `type_severidade` no loader e no corpus vetorial (só embeddings), e um mapa sigla→descrição carregado da v1 threadeado até `engine_tdt`. Cada passo de matching é medido isolado no gate (`bench/gate_tdt_real`); regressão = peso 0 / revert do passo, sem derrubar o resto.

**Tech Stack:** Python 3.14, openpyxl, pytest. Sem dependência nova.

**Spec:** `docs/superpowers/specs/2026-07-08-sp-metadados-decisao-alias-v1-design.md`

## Global Constraints

- Ordem de medição do gate (spec §6): baseline → §4 MODO → §3 r8 → §3 r9 → §5 corpus. Um gate por task, comparado ao baseline.
- Gate: `output/LISTA 1 - GTD/TDT.xlsx` (gerado por `bench/reprocessar_lista1.py`) vs `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. Critério: `pct >= baseline`. Regrediu → desligar o passo (peso 0 / revert) e registrar em `bench/resultados/`.
- `SinalPadrao` é construído **posicionalmente** em testes existentes — campo novo entra no FIM, keyword com default `None`.
- Pesos novos: `"direcao": 0.10`, `"type_severidade": 0.05` (fraco, abaixo de `numero_protecao` 0.10).
- Regras que dependem de `ctx.lista_padrao` são no-op quando ela é `None` (contrato da r7; `bench/benchmark.py` não a threadeia).
- ALIAS: fonte fixa `docs/Pontos Padrao ADMS_v1.xlsx` (`defaults.DEFAULT_LISTA_ALIAS`); arquivo ausente → mapa vazio → fallback descrição bruta do cliente, **nunca** quebra a geração.
- Comandos bash; no PowerShell trocar prefixo `PYTHONPATH=src python ...` por `$env:PYTHONPATH='src'; python ...`. pytest não precisa de PYTHONPATH (pyproject já tem `pythonpath = ["src"]`).
- Commits em PT, formato do repo: `feat(...)`, `test(...)`, `docs(...)`.

---

### Task 0: Branch + baseline do gate

**Files:**
- Create: `bench/resultados/spMET_baseline_gate.txt`

**Interfaces:**
- Produces: número baseline `pct` usado como critério de aceite pelas Tasks 1, 3, 4 e 5.

- [ ] **Step 1: Criar branch**

```bash
git checkout -b feature/sp-metadados-alias
```

- [ ] **Step 2: Reprocessar LISTA 1 do zero**

Run: `PYTHONPATH=src python bench/reprocessar_lista1.py`
Expected: `decididos=<N> revisao=<M>` e `salvo em: output/LISTA 1 - GTD/TDT.xlsx`. Demora minutos (embeddings).

- [ ] **Step 3: Medir e salvar baseline**

```bash
PYTHONPATH=src python -c "
from bench.gate_tdt_real import comparar
r = comparar('output/LISTA 1 - GTD/TDT.xlsx', 'docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx')
linha = f'baseline spMET: comum={r.comum} iguais={r.iguais} pct={r.pct:.2f}'
print(linha)
open('bench/resultados/spMET_baseline_gate.txt', 'w', encoding='utf-8').write(linha + chr(10))
"
```

Expected: imprime `baseline spMET: comum=... iguais=... pct=...`. Anotar o `pct` — é o baseline das tasks seguintes.

- [ ] **Step 4: Commit**

```bash
git add bench/resultados/spMET_baseline_gate.txt
git commit -m "bench: baseline gate_tdt_real pre SP-METADADOS"
```

---

### Task 1: Classe MODO no léxico de estados (§4)

**Files:**
- Modify: `src/tdt/semantica_estados.py` (constantes ~linha 17-22, `_LEXICO` ~linha 35)
- Test: `tests/test_semantica_estados.py`

**Interfaces:**
- Produces: constante `MODO = "modo"` exportada por `tdt.semantica_estados`; `classe_do_mm` passa a classificar MMs `MANUAL@AUTOMATICO`; `detectar_estado` reconhece tokens `MANUAL`/`AUTOMATICO`/`AUTOMATICA`. Nenhuma outra task consome `MODO` diretamente — o benefício é r7/filtro D2 cobrirem esses sinais sem mudança de código.

- [ ] **Step 1: Auditar os MMs sem classe (estado atual)**

```bash
PYTHONPATH=src python -c "
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.semantica_estados import classe_do_mm
lp = ListaPadraoADMS.carregar('docs/Pontos Padrao ADMS_v2.xlsx')
sem = [(s.sigla, s.mm) for s in lp.discretos if s.mm and classe_do_mm(s.mm) is None]
print(f'sem classe: {len(sem)}')
for sig, mm in sem: print(' ', sig, '|', mm[:70])
"
```

Expected: `sem classe: 35`, incluindo `25AM`/`43AM` com estados `MANUAL@AUTOMATICO`. Anotar quais entradas têm par de estados real (não `null@null` nem estados custom sem semântica) — essas são o alvo.

- [ ] **Step 2: Escrever os testes que falham**

Adicionar em `tests/test_semantica_estados.py` (seguir os imports existentes do arquivo):

```python
from tdt.semantica_estados import MODO  # junto aos imports existentes


def test_classe_do_mm_manual_automatico_e_modo():
    assert classe_do_mm("null@null___MANUAL@AUTOMATICO___Custom_S_TS_SS") == MODO


def test_detectar_estado_manual_e_modo():
    est = detectar_estado("SELETORA MANUAL")
    assert est is not None and est.classe == MODO


def test_detectar_estado_automatismo_nao_e_modo():
    # AUTOMATISMO (função de proteção) não pode colidir com AUTOMATICO (modo)
    est = detectar_estado("AUTOMATISMO ATUADO")
    assert est is not None and est.classe == "evento"


def test_compativel_modo_com_modo():
    assert compativel(EstadoDetectado(MODO), MODO)
    assert not compativel(EstadoDetectado(MODO), "evento")
```

Se `EstadoDetectado`/`compativel`/`detectar_estado`/`classe_do_mm` não estiverem nos imports do arquivo de teste, adicioná-los.

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_semantica_estados.py -v -k modo`
Expected: FAIL — `ImportError: cannot import name 'MODO'`.

- [ ] **Step 4: Implementar**

Em `src/tdt/semantica_estados.py`, adicionar a constante junto às demais (após `LOCAL_REMOTO`):

```python
MODO = "modo"                # manual/automático (seleção de modo de operação)
```

E no `_LEXICO`, adicionar as duas entradas (antes da linha do `INDEFINID`):

```python
    # MODO: prefixo "AUTOMATIC" cobre AUTOMATICO/AUTOMATICA sem colidir com
    # AUTOMATISMO ("AUTOMATIS..." difere no 9º char); "MANUAL" não colide com
    # MANUTENCAO ("MANUT...").
    ("MANUAL", MODO, None), ("AUTOMATIC", MODO, None),
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_semantica_estados.py -v`
Expected: PASS em todos (novos e existentes).

- [ ] **Step 6: Re-auditar cobertura**

Rodar o mesmo comando do Step 1.
Expected: contagem cai (35 → ~33 ou menos); os restantes são só comandos puros (`null@null` nos estados) ou pares custom sem semântica (`CMD_CEEE@CMD_RGE`, `RGE@CPFLT`). Se sobrar par de estado real legível (ex. outro par tipo `X@Y` com palavras de estado), adicionar prefixos ao `_LEXICO` no mesmo padrão do Step 4 e re-rodar Step 5.

- [ ] **Step 7: Gate (§4 é o primeiro passo medido)**

```bash
PYTHONPATH=src python bench/reprocessar_lista1.py
PYTHONPATH=src python -c "
from bench.gate_tdt_real import comparar
r = comparar('output/LISTA 1 - GTD/TDT.xlsx', 'docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx')
print(f'pos-MODO: comum={r.comum} iguais={r.iguais} pct={r.pct:.2f}')
"
```

Expected: `pct >= baseline` (Task 0). Se regredir: reverter as entradas do `_LEXICO` (manter a constante e os testes de `classe_do_mm` — a regressão só pode vir do lado texto/filtro D2), registrar o achado em `bench/resultados/spMET_baseline_gate.txt` e seguir.

- [ ] **Step 8: Rodar suíte de contato e commitar**

Run: `python -m pytest tests/test_semantica_estados.py tests/test_motor_regras.py tests/test_pipeline_semantica.py -v`
Expected: PASS.

```bash
git add src/tdt/semantica_estados.py tests/test_semantica_estados.py
git commit -m "feat(semantica): classe MODO (manual/automatico) no lexico de estados"
```

---

### Task 2: Loader lê TYPE SEVERIDADE (§2)

**Files:**
- Modify: `src/tdt/dados/lista_padrao.py` (dataclass ~linha 19-29, mapas ~linha 102-127)
- Test: `tests/test_lista_padrao.py`

**Interfaces:**
- Produces: `SinalPadrao.type_severidade: str | None` (último campo, default `None`). Consumido pelas Tasks 4 (r9) e 5 (corpus vetorial). Valores reais (v2): `"PROT"`, `"FALHAS FCOM/VCA/VCC"`, `"ALARMES PREDIAIS/VF/GRUPO"`, `"FUNÇÕES/43/PARALELISMO"` (com acento), `"DEFEITOS"`, `"DJ"`, `"DJ BC/SEC"`. Analógicos: sempre `None`.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar em `tests/test_lista_padrao.py`:

```python
def test_le_type_severidade_dos_discretos(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    assert lp.por_sigla("TEA").type_severidade == "PROT"
    assert lp.por_sigla("DJF1").type_severidade == "DJ"
    assert lp.por_sigla("CMDE").type_severidade == "ALARMES PREDIAIS/VF/GRUPO"


def test_analogico_sem_type_severidade(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    assert lp.por_sigla("IN61").type_severidade is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_lista_padrao.py -v -k type_severidade`
Expected: FAIL — `AttributeError: 'SinalPadrao' object has no attribute 'type_severidade'`.

- [ ] **Step 3: Implementar**

Em `src/tdt/dados/lista_padrao.py`:

1. No dataclass `SinalPadrao`, adicionar como ÚLTIMO campo (preserva construção posicional dos testes existentes):

```python
    type_severidade: str | None = None  # "PROT", "FALHAS FCOM/VCA/VCC", ... (só discretos)
```

2. No `sinais.append(SinalPadrao(...))` de `_ler_sheet`, adicionar:

```python
                type_severidade=get("type_severidade"),
```

3. No mapa dos **discretos** (dentro de `carregar`), adicionar a chave:

```python
                    "type_severidade": "TYPE SEVERIDADE",
```

4. No mapa dos **analógicos**, adicionar:

```python
                    "type_severidade": None,
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_lista_padrao.py -v`
Expected: PASS em todos.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/dados/lista_padrao.py tests/test_lista_padrao.py
git commit -m "feat(dados): loader le TYPE SEVERIDADE da lista padrao"
```

---

### Task 3: Regra r8_direcao (§3)

**Files:**
- Modify: `src/tdt/motor_regras.py` (nova função antes do registro `_REGRAS` ~linha 371; registrar em `_REGRAS`)
- Modify: `src/tdt/config.py` (`pesos_regras` ~linha 70-81)
- Test: `tests/test_motor_regras.py`

**Interfaces:**
- Consumes: `SinalPadrao.direction` (já existente: "Read" 623, "ReadWrite" 62, "Write" 7), `rec.tipo_sinal.direcao` ("Input" | "Output" | "InputOutput"), `ctx.lista_padrao`.
- Produces: `r8_direcao(rec, cand, ctx, cfg) -> AjusteRegra`, peso `pesos_regras["direcao"] = 0.10`.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar em `tests/test_motor_regras.py`. O helper `_rec` do arquivo fixa `direcao="Input"` — criar variante com direção parametrizada. NÃO reusar o `_lp()` do arquivo: seus candidatos têm MM com par de estados, e a r7 já os diferenciaria — o teste não isolaria a r8. Usar candidatos com `mm=None` e texto neutro ("REARME AUTOMATISMO" não aciona r1–r7; AUTOMATISMO não colide com o prefixo AUTOMATIC da classe MODO):

```python
def _rec_dir(desc_norm, direcao):
    return SignalRecord(
        id="LT3:9",
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", (17,)),
        descricoes=Descricoes(desc_norm, desc_norm),
    )


def _lp_dir():
    return ListaPadraoADMS(
        discretos=(
            SinalPadrao("AUTC", "REARME AUTOMATISMO", "Custom", "ReadWrite",
                        None, "Discrete"),
            SinalPadrao("AUTA", "REARME AUTOMATISMO ALARME", "Custom", "Read",
                        None, "Discrete"),
        ),
        analogicos=(),
    )


# --- R8: direção -------------------------------------------------------------


def test_r8_comando_favorece_candidato_de_escrita():
    rec = _rec_dir("REARME AUTOMATISMO", "Output")
    cands = [Candidato("AUTA", 0.70, "mesclado"), Candidato("AUTC", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG, lista_padrao=_lp_dir())
    assert out[0].sigla == "AUTC"  # ReadWrite boost; AUTA (Read) penalizado


def test_r8_input_puro_e_noop():
    rec = _rec_dir("REARME AUTOMATISMO", "Input")
    cands = [Candidato("AUTA", 0.70, "mesclado"), Candidato("AUTC", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG, lista_padrao=_lp_dir())
    # sem comando no input, r8 não mexe — ordem original preservada
    assert out[0].sigla == "AUTA"


def test_r8_sem_lista_padrao_e_noop():
    rec = _rec_dir("REARME AUTOMATISMO", "Output")
    cands = [Candidato("AUTA", 0.70, "mesclado"), Candidato("AUTC", 0.69, "mesclado")]
    out = aplicar(rec, cands, _CFG)  # sem lista_padrao
    assert out[0].sigla == "AUTA"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_motor_regras.py -v -k r8`
Expected: `test_r8_comando_favorece_candidato_de_escrita` FAIL (empate mantém ordem, AUTA primeiro); os dois no-op passam desde já — o que confirma o ciclo TDD é a falha do teste de boost.

- [ ] **Step 3: Implementar a regra**

Em `src/tdt/motor_regras.py`, antes do registro `_REGRAS`:

```python
# --- R8: direção (comando exige escrita) --------------------------------------


def r8_direcao(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Input com comando (Output/InputOutput) favorece candidato ReadWrite/Write
    e penaliza Read puro. ASSIMÉTRICA de propósito: input só-leitura é no-op —
    status de equipamento manobrável (DJ) casa sigla ReadWrite legitimamente
    (par comando+status resolvido pelo dc_pairer); penalizar quebraria esse
    caminho. Requer ctx.lista_padrao (ausente = no-op, contrato da r7)."""
    if ctx.lista_padrao is None:
        return _ZERO
    if rec.tipo_sinal.direcao not in ("Output", "InputOutput"):
        return _ZERO
    sp = ctx.lista_padrao.por_sigla(cand.sigla)
    if sp is None or not sp.direction:
        return _ZERO
    peso = cfg.pesos_regras["direcao"]
    if sp.direction in ("ReadWrite", "Write"):
        return AjusteRegra(peso, f"direcao: comando casa candidato {sp.direction}")
    return AjusteRegra(-peso, "direcao: comando mas candidato so-leitura (Read)")
```

Registrar em `_REGRAS` (após `r7_estado_compativel`):

```python
    r8_direcao,
```

Em `src/tdt/config.py`, no dict de `pesos_regras`, adicionar:

```python
            "direcao": 0.10,
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_motor_regras.py tests/test_config.py -v`
Expected: PASS em todos.

- [ ] **Step 5: Gate**

```bash
PYTHONPATH=src python bench/reprocessar_lista1.py
PYTHONPATH=src python -c "
from bench.gate_tdt_real import comparar
r = comparar('output/LISTA 1 - GTD/TDT.xlsx', 'docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx')
print(f'pos-r8: comum={r.comum} iguais={r.iguais} pct={r.pct:.2f}')
"
```

Expected: `pct >= baseline`. Se regredir: `"direcao": 0.0` no config (regra fica no código, desligada), anotar em `bench/resultados/spMET_baseline_gate.txt`, commitar mesmo assim (histórico do porquê).

- [ ] **Step 6: Commit**

```bash
git add src/tdt/motor_regras.py src/tdt/config.py tests/test_motor_regras.py
git commit -m "feat(regras): r8_direcao - comando exige candidato de escrita"
```

---

### Task 4: Regra r9_type_severidade (§3)

**Files:**
- Create: `bench/diag_type_severidade.py`
- Modify: `src/tdt/motor_regras.py`, `src/tdt/config.py`
- Test: `tests/test_motor_regras.py`

**Interfaces:**
- Consumes: `SinalPadrao.type_severidade` (Task 2), `ctx.tokens`, `_numeros_no_texto` (já existe em motor_regras), `ctx.lista_padrao`.
- Produces: `r9_type_severidade(rec, cand, ctx, cfg) -> AjusteRegra`, peso `pesos_regras["type_severidade"] = 0.05`, tabela `_PISTAS_TS`.

- [ ] **Step 1: Escrever o diagnóstico de pureza do léxico**

Criar `bench/diag_type_severidade.py`:

```python
"""Pureza das pistas lexicais → classe TYPE SEVERIDADE, medida na própria
lista padrão (descrição de cada sinal discreto vs sua classe real).

Uso: PYTHONPATH=src python bench/diag_type_severidade.py
Critério (spec SP-METADADOS §3): manter pista com pureza >= 90% e >= 5 hits.
"""
from __future__ import annotations

import unicodedata
from collections import Counter

from tdt.dados.lista_padrao import ListaPadraoADMS


def _ascii_upper(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


# Mesmas pistas candidatas da r9 (manter em sincronia com motor_regras._PISTAS_TS)
PISTAS = {
    "PROT": {"TRIP"},
    "FALHAS FCOM/VCA/VCC": {"FCOM", "VCA", "VCC"},
    "FUNCOES/43/PARALELISMO": {"43", "PARALELISMO", "TRANSFERENCIA"},
    "DEFEITOS": {"DEFEITO", "DEFEITOS"},
}


def main() -> None:
    lp = ListaPadraoADMS.carregar("docs/Pontos Padrao ADMS_v2.xlsx")
    for classe_alvo, pistas in PISTAS.items():
        for pista in sorted(pistas):
            contagem: Counter[str] = Counter()
            for s in lp.discretos:
                if not s.descricao or not s.type_severidade:
                    continue
                tokens = set(_ascii_upper(s.descricao).split())
                if pista in tokens:
                    contagem[_ascii_upper(s.type_severidade)] += 1
            total = sum(contagem.values())
            acertos = contagem.get(classe_alvo, 0)
            pureza = 100.0 * acertos / total if total else 0.0
            veredito = "MANTER" if pureza >= 90.0 and total >= 5 else "REMOVER"
            print(f"{classe_alvo:28s} {pista:14s} hits={total:3d} pureza={pureza:5.1f}% {veredito}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar o diagnóstico e podar o léxico**

Run: `PYTHONPATH=src python bench/diag_type_severidade.py`
Expected: uma linha por pista com `MANTER`/`REMOVER`. As pistas marcadas `REMOVER` saem do dict `PISTAS` deste script E da tabela `_PISTAS_TS` do Step 4. Se TODAS as pistas de uma classe caírem, a classe sai da tabela (a regra continua funcionando para as demais).

- [ ] **Step 3: Escrever os testes que falham**

Adicionar em `tests/test_motor_regras.py`. Precisa de candidatos com `type_severidade` — criar uma lista padrão própria do teste (SinalPadrao aceita o campo por keyword):

```python
def _lp_ts():
    return ListaPadraoADMS(
        discretos=(
            SinalPadrao("50F1", "50 - TRIP SOBRECORRENTE", "RelayTrip", "Read",
                        "null@null___NORMAL@ATUADO___RelayTrip_S_TS_SA", "Discrete",
                        type_severidade="PROT"),
            SinalPadrao("FVCC", "FALHA VCC", "Custom", "Read",
                        "null@null___NORMAL@FALHA___Custom_S_TS_SA", "Discrete",
                        type_severidade="FALHAS FCOM/VCA/VCC"),
        ),
        analogicos=(),
    )


# --- R9: type severidade ------------------------------------------------------


def test_r9_trip_favorece_classe_prot():
    rec = _rec("TRIP SOBRECORRENTE INSTANTANEO")
    cands = [Candidato("FVCC", 0.70, "mesclado"), Candidato("50F1", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG, lista_padrao=_lp_ts())
    assert out[0].sigla == "50F1"  # PROT casa; FALHAS diverge


def test_r9_vcc_favorece_classe_falhas():
    rec = _rec("FALHA VCC PAINEL")
    cands = [Candidato("50F1", 0.70, "mesclado"), Candidato("FVCC", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG, lista_padrao=_lp_ts())
    assert out[0].sigla == "FVCC"


def test_r9_pista_ambigua_e_noop():
    # TRIP (PROT) + VCC (FALHAS) no mesmo texto -> duas classes -> não decide
    rec = _rec("TRIP FALHA VCC")
    cands = [Candidato("FVCC", 0.70, "mesclado"), Candidato("50F1", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG, lista_padrao=_lp_ts())
    assert out[0].sigla == "FVCC"  # empate preservado (nenhum ajuste r9)


def test_r9_sem_lista_padrao_e_noop():
    rec = _rec("TRIP SOBRECORRENTE")
    cands = [Candidato("FVCC", 0.72, "mesclado"), Candidato("50F1", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "FVCC"
```

Atenção: `test_r9_trip_favorece_classe_prot` e `test_r9_sem_lista_padrao_e_noop` têm textos que também acionam r1 (número 50 na sigla `50F1`) — como as duas siglas do teste divergem em r1 na mesma direção OU o texto não contém número, verificar na prática; se r1 interferir, trocar `50F1` por sigla sem número líder (ex. criar `SGFT` com `type_severidade="PROT"` no `_lp_ts`). O invariante: **r9 sozinha desempata pela classe**.

- [ ] **Step 4: Rodar e ver falhar**

Run: `python -m pytest tests/test_motor_regras.py -v -k r9`
Expected: FAIL nos testes de boost (empate mantém primeira posição).

- [ ] **Step 5: Implementar a regra**

Em `src/tdt/motor_regras.py`. Import no topo (junto aos existentes):

```python
import unicodedata
```

Antes do registro `_REGRAS`:

```python
# --- R9: TYPE SEVERIDADE (desempate fraco) ------------------------------------

_TS_PROT = "PROT"

# classe (ASCII upper) -> tokens-pista no texto canônico. Tabela É dado
# (padrão _PARES_OPOSTOS): podada por bench/diag_type_severidade.py
# (pureza >= 90%, hits >= 5 na lista padrão). PROT também aceita número ANSI
# no texto (_numeros_no_texto), tratado em _classe_ts_do_texto.
_PISTAS_TS: tuple[tuple[str, frozenset[str]], ...] = (
    (_TS_PROT, frozenset({"TRIP"})),
    ("FALHAS FCOM/VCA/VCC", frozenset({"FCOM", "VCA", "VCC"})),
    ("FUNCOES/43/PARALELISMO", frozenset({"43", "PARALELISMO", "TRANSFERENCIA"})),
    ("DEFEITOS", frozenset({"DEFEITO", "DEFEITOS"})),
)


def _ascii_upper(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


def _classe_ts_do_texto(tokens: frozenset[str]) -> str | None:
    """Classe TYPE SEVERIDADE sugerida pelo texto; None sem pista ou ambíguo."""
    achadas = {classe for classe, pistas in _PISTAS_TS if tokens & pistas}
    if _numeros_no_texto(tokens):
        achadas.add(_TS_PROT)
    return achadas.pop() if len(achadas) == 1 else None


def r9_type_severidade(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Pista lexical do texto × classe TYPE SEVERIDADE do candidato. Peso
    fraco: desempata descrições parecidas, nunca decide sozinha. Comparação
    em ASCII upper (a coluna real tem acento: "FUNÇÕES/43/PARALELISMO")."""
    if ctx.lista_padrao is None:
        return _ZERO
    classe_texto = _classe_ts_do_texto(ctx.tokens)
    if classe_texto is None:
        return _ZERO
    sp = ctx.lista_padrao.por_sigla(cand.sigla)
    ts = _ascii_upper(sp.type_severidade) if sp and sp.type_severidade else ""
    if not ts:
        return _ZERO
    peso = cfg.pesos_regras["type_severidade"]
    if ts == classe_texto:
        return AjusteRegra(peso, f"type_severidade: candidato e texto em {classe_texto}")
    return AjusteRegra(
        -peso, f"type_severidade: candidato em {ts} diverge de {classe_texto}"
    )
```

Registrar em `_REGRAS` (após `r8_direcao`):

```python
    r9_type_severidade,
```

Em `src/tdt/config.py`, no dict `pesos_regras`:

```python
            "type_severidade": 0.05,
```

Aplicar aqui a poda do Step 2: remover de `_PISTAS_TS` as pistas `REMOVER` (e refletir no dict `PISTAS` do diag, mantendo os dois em sincronia).

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests/test_motor_regras.py tests/test_config.py -v`
Expected: PASS em todos.

- [ ] **Step 7: Gate**

```bash
PYTHONPATH=src python bench/reprocessar_lista1.py
PYTHONPATH=src python -c "
from bench.gate_tdt_real import comparar
r = comparar('output/LISTA 1 - GTD/TDT.xlsx', 'docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx')
print(f'pos-r9: comum={r.comum} iguais={r.iguais} pct={r.pct:.2f}')
"
```

Expected: `pct >= baseline`. Se regredir: `"type_severidade": 0.0`, anotar em `bench/resultados/spMET_baseline_gate.txt`, commitar com a regra desligada.

- [ ] **Step 8: Commit**

```bash
git add src/tdt/motor_regras.py src/tdt/config.py tests/test_motor_regras.py bench/diag_type_severidade.py
git commit -m "feat(regras): r9_type_severidade - desempate por classe da lista padrao"
```

---

### Task 5: TYPE SEVERIDADE no corpus vetorial (§5)

**Files:**
- Modify: `src/tdt/pipeline.py` (`_corpus_enriquecido`, ~linha 79-98)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `SinalPadrao.type_severidade` (Task 2).
- Produces: corpus de embeddings com a classe anexada. BM25/fuzzy (`_corpus`) intocados. Cache de scorers invalida sozinho (chave = corpus enriquecido).

- [ ] **Step 1: Escrever o teste que falha**

Adicionar em `tests/test_pipeline.py` (usar os imports existentes do arquivo; `_corpus_enriquecido` é função de módulo):

```python
def test_corpus_enriquecido_inclui_type_severidade():
    from tdt.config import Config
    from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
    from tdt.pipeline import _corpus_enriquecido

    lp = ListaPadraoADMS(
        discretos=(
            SinalPadrao("SGFT", "TRIP SGF", "RelayTrip", "Read", None, "Discrete",
                        type_severidade="PROT"),
        ),
        analogicos=(),
    )
    corpus = _corpus_enriquecido(lp, Config(), "Discrete")
    assert len(corpus) == 1
    sigla, texto = corpus[0]
    assert sigla == "SGFT"
    assert "PROT" in texto  # canonizar expande PROT->PROTECAO; aceitar ambos
```

Nota: `canonizar` expande a abreviação `PROT` → `PROTECAO` (config.ABREVIACOES_PADRAO); a asserção `"PROT" in texto` cobre os dois casos por ser prefixo.

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_pipeline.py -v -k corpus_enriquecido`
Expected: FAIL — `"PROT" in texto` é False (campo não entra no corpus).

- [ ] **Step 3: Implementar**

Em `src/tdt/pipeline.py`, dentro de `_corpus_enriquecido`, após o bloco do `s.direction`:

```python
        if s.type_severidade:
            partes.append(s.type_severidade)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_pipeline.py tests/test_cache_scorers.py -v`
Expected: PASS em todos.

- [ ] **Step 5: Gate**

```bash
PYTHONPATH=src python bench/reprocessar_lista1.py
PYTHONPATH=src python -c "
from bench.gate_tdt_real import comparar
r = comparar('output/LISTA 1 - GTD/TDT.xlsx', 'docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx')
print(f'pos-corpus: comum={r.comum} iguais={r.iguais} pct={r.pct:.2f}')
"
```

Expected: `pct >= baseline`. Se regredir (lição N6: enriquecer corpus pode poluir): reverter o Step 3 (remover as 2 linhas), manter o teste ajustado para o comportamento revertido OU remover o teste, anotar em `bench/resultados/spMET_baseline_gate.txt`.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): type_severidade no corpus vetorial (embeddings)"
```

---

### Task 6: Signal Alias da lista padrão v1 (§1)

**Files:**
- Modify: `src/tdt/defaults.py`
- Modify: `src/tdt/dados/lista_padrao.py` (helper novo no fim do arquivo)
- Modify: `src/tdt/engine_tdt.py` (`gerar` ~linha 244, `_valores` ~linha 145/172, `_valores_analog` ~linha 211/225, `_escrever_sheet` — sem mudança, threading via lambda)
- Modify: `src/tdt/pipeline.py` (`gerar_tdt` ~linha 498, `executar` ~linha 682)
- Test: `tests/test_lista_padrao.py`, `tests/test_engine_tdt.py`, `tests/test_pipeline_gerar_tdt.py`

**Interfaces:**
- Consumes: `ListaPadraoADMS.carregar` (existente), `rec.sigla_sinal`, `rec.descricoes.bruta`.
- Produces:
  - `defaults.DEFAULT_LISTA_ALIAS: str` — path da v1.
  - `lista_padrao.descricoes_por_sigla(path: str) -> dict[str, str]` — sigla UPPER → descrição; `{}` se arquivo ausente/ilegível; `lru_cache`.
  - `engine_tdt.gerar(lista, template_path, lista_padrao, alias_v1: dict[str, str] | None = None)` — default `None` = comportamento atual (testes existentes intactos).

- [ ] **Step 1: Escrever os testes que falham (helper)**

Adicionar em `tests/test_lista_padrao.py`:

```python
from tdt.dados.lista_padrao import descricoes_por_sigla  # junto aos imports


def test_descricoes_por_sigla_le_v1(docs):
    m = descricoes_por_sigla(str(docs / "Pontos Padrao ADMS_v1.xlsx"))
    assert m["TEA"] == "49 - ALARME TEMPERATURA ENROLAMENTO"
    assert "IN61" in m  # analógicos também entram


def test_descricoes_por_sigla_arquivo_ausente_devolve_vazio(tmp_path):
    assert descricoes_por_sigla(str(tmp_path / "nao_existe.xlsx")) == {}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_lista_padrao.py -v -k descricoes_por_sigla`
Expected: FAIL — `ImportError: cannot import name 'descricoes_por_sigla'`.

- [ ] **Step 3: Implementar defaults + helper**

Em `src/tdt/defaults.py`, após `DEFAULT_LISTA`:

```python
# Fonte FIXA do Signal Alias na TDT gerada (spec SP-METADADOS §1): descrições
# originais da v1, independente da lista padrão carregada (v6+ tem descrições
# enriquecidas p/ matching que não devem vazar pro ALIAS).
DEFAULT_LISTA_ALIAS = str(_DOCS / "Pontos Padrao ADMS_v1.xlsx")
```

Em `src/tdt/dados/lista_padrao.py`, import no topo:

```python
from functools import lru_cache
```

E no fim do arquivo:

```python
@lru_cache(maxsize=4)
def descricoes_por_sigla(path: str) -> dict[str, str]:
    """Mapa sigla UPPER -> descrição de uma lista padrão (Signal Alias da v1).

    Arquivo ausente/ilegível -> {} : a geração de TDT nunca quebra por causa
    do alias (fallback = descrição bruta do cliente, comportamento antigo).
    """
    try:
        lp = ListaPadraoADMS.carregar(path)
    except Exception:
        return {}
    return {
        s.sigla.upper(): s.descricao
        for s in (*lp.discretos, *lp.analogicos)
        if s.descricao
    }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_lista_padrao.py tests/test_ui_defaults.py -v`
Expected: PASS.

- [ ] **Step 5: Escrever os testes que falham (engine)**

Adicionar em `tests/test_engine_tdt.py` (reusa `_lista()` do arquivo — registros `DJ` e `SECC` com bruta `"DJ BRUTO"`/`"SECC BRUTO"`):

```python
def test_signal_alias_usa_descricao_do_mapa_v1(template_dnp3_path, lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp,
               alias_v1={"DJ": "DISJUNTOR DE LINHA"})
    ws = wb["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    assert ws.cell(5, col["Signal Alias"]).value == "DISJUNTOR DE LINHA"
    # SECC fora do mapa -> mantém descrição bruta do cliente
    assert ws.cell(6, col["Signal Alias"]).value == "SECC BRUTO"


def test_signal_alias_sem_mapa_mantem_bruta(template_dnp3_path, lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)  # alias_v1 default None
    ws = wb["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    assert ws.cell(5, col["Signal Alias"]).value == "DJ BRUTO"
```

- [ ] **Step 6: Rodar e ver falhar**

Run: `python -m pytest tests/test_engine_tdt.py -v -k signal_alias`
Expected: FAIL — `gerar() got an unexpected keyword argument 'alias_v1'`.

- [ ] **Step 7: Implementar no engine**

Em `src/tdt/engine_tdt.py`:

1. Helper (perto de `_alias_hoje`):

```python
def _signal_alias(rec: SignalRecord, alias_v1: "dict[str, str] | None") -> str:
    """Descrição da lista padrão v1 quando a sigla está no mapa; senão a
    descrição bruta do cliente (Custom/sem sigla/mapa ausente)."""
    if alias_v1 and rec.sigla_sinal:
        desc = alias_v1.get(rec.sigla_sinal.upper())
        if desc:
            return desc
    return rec.descricoes.bruta
```

2. Em `_valores`, assinatura e campo:

```python
def _valores(rec: SignalRecord, subestacao: str | None, padrao: ListaPadraoADMS,
             alias_v1: "dict[str, str] | None" = None) -> dict:
```

e trocar `"Signal Alias": rec.descricoes.bruta,` por:

```python
        "Signal Alias": _signal_alias(rec, alias_v1),
```

3. Mesma mudança em `_valores_analog` (assinatura + campo `"Signal Alias"`).

4. Em `gerar`, assinatura e threading via lambda (a assinatura de `_escrever_sheet` não muda):

```python
def gerar(
    lista: ListaHomogenea,
    template_path: str | Path,
    lista_padrao: ListaPadraoADMS,
    alias_v1: "dict[str, str] | None" = None,
) -> openpyxl.Workbook:
    wb = openpyxl.load_workbook(template_path)  # mantém fórmulas/estilos
    _escrever_sheet(
        wb[SHEET_DISCRETOS], SHEET_DISCRETOS, COLUNAS_ESPERADAS,
        [r for r in lista.registros if r.tipo_sinal.categoria == "Discrete"],
        lambda rec, sub, padrao: _valores(rec, sub, padrao, alias_v1),
        lista.subestacao, lista_padrao,
    )
    _escrever_sheet(
        wb[SHEET_ANALOGICOS], SHEET_ANALOGICOS, COLUNAS_ESPERADAS_ANALOG,
        [r for r in lista.registros if r.tipo_sinal.categoria == "Analog"],
        lambda rec, sub, padrao: _valores_analog(rec, sub, padrao, alias_v1),
        lista.subestacao, lista_padrao,
    )
    return wb
```

- [ ] **Step 8: Rodar e ver passar**

Run: `python -m pytest tests/test_engine_tdt.py -v`
Expected: PASS em todos (os existentes não passam `alias_v1` → default `None` → comportamento antigo).

- [ ] **Step 9: Escrever o teste que falha (pipeline threading)**

Adicionar em `tests/test_pipeline_gerar_tdt.py`:

```python
from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal


@pytest.mark.skipif(
    not (DOCS / "dnp3_template.xlsx").exists(), reason="template ausente"
)
def test_gerar_tdt_signal_alias_vem_da_v1():
    lp = ListaPadraoADMS.carregar(DOCS / "Pontos Padrao ADMS_v2.xlsx")
    rec = SignalRecord(
        id="LT3:1",
        modulo=Modulo("3", "sheet"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (17,)),
        descricoes=Descricoes("ALARME TEMP ENROLAMENTO DO CLIENTE", "ALARME TEMP"),
        sigla_sinal="TEA",
        status="decidido",
    )
    wb = pipeline.gerar_tdt([rec], DOCS / "dnp3_template.xlsx", lp, subestacao="IMA")
    ws = wb["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    # descrição original da v1, não a do cliente
    assert ws.cell(5, col["Signal Alias"]).value == "49 - ALARME TEMPERATURA ENROLAMENTO"
```

- [ ] **Step 10: Rodar e ver falhar**

Run: `python -m pytest tests/test_pipeline_gerar_tdt.py -v`
Expected: o teste novo FAIL (`Signal Alias` = "ALARME TEMP ENROLAMENTO DO CLIENTE").

- [ ] **Step 11: Threadear no pipeline**

Em `src/tdt/pipeline.py`:

1. Imports: trocar a linha 35 `from tdt.dados.lista_padrao import ListaPadraoADMS` por:

```python
from tdt.dados.lista_padrao import ListaPadraoADMS, descricoes_por_sigla
from tdt.defaults import DEFAULT_LISTA_ALIAS
```

2. `gerar_tdt` (linha ~498):

```python
def gerar_tdt(registros, template_path, lp, subestacao=None, aliases=None, config=None):
    """Gera o workbook TDT a partir de uma lista (já decidida/editada) de registros."""
    lst = _aplicar_aliases(list(registros), aliases)
    pareados, _rev = dc_pairer.parear(lst, config)
    corrigidos, _rev2 = corrigir(list(pareados), _whitelist_posicao(lp, config))
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
    return engine_tdt.gerar(
        lista, template_path, lp, alias_v1=descricoes_por_sigla(DEFAULT_LISTA_ALIAS)
    )
```

3. Em `executar` (linha ~682), trocar `wb_out = engine_tdt.gerar(lista, template_path, lp)` por:

```python
        alias_v1 = descricoes_por_sigla(DEFAULT_LISTA_ALIAS)
        if not alias_v1:
            aud.evento(
                "pipeline",
                f"lista v1 ausente ({DEFAULT_LISTA_ALIAS}): Signal Alias usa descrição do cliente",
                "WARN",
            )
        wb_out = engine_tdt.gerar(lista, template_path, lp, alias_v1=alias_v1)
```

- [ ] **Step 12: Rodar e ver passar**

Run: `python -m pytest tests/test_pipeline_gerar_tdt.py tests/test_pipeline.py tests/test_engine_tdt.py tests/test_integracao_san2.py -v`
Expected: PASS. Atenção: se algum teste de integração existente assertar `Signal Alias` com a descrição do cliente para sinal com sigla da lista padrão, ele agora recebe a descrição v1 — atualizar a asserção do teste para o valor v1 (é o comportamento novo especificado), não reverter o código.

- [ ] **Step 13: Commit**

```bash
git add src/tdt/defaults.py src/tdt/dados/lista_padrao.py src/tdt/engine_tdt.py src/tdt/pipeline.py tests/test_lista_padrao.py tests/test_engine_tdt.py tests/test_pipeline_gerar_tdt.py
git commit -m "feat(engine): Signal Alias vem da descricao original da lista padrao v1"
```

---

### Task 7: Closeout — suíte completa, gate final, DOX

**Files:**
- Create: `bench/resultados/spMET_final_gate.txt`
- Modify: `docs/superpowers/specs/2026-07-08-sp-metadados-decisao-alias-v1-design.md` (Status)
- Modify (se contrato mudou): `src/tdt/AGENTS.md`, `src/tdt/dados/AGENTS.md`, `bench/AGENTS.md`

**Interfaces:**
- Consumes: tudo das tasks anteriores.

- [ ] **Step 1: Suíte completa**

Run: `python -m pytest tests/ -x -q`
Expected: PASS (0 failed). Falhou → corrigir antes de seguir (raiz, não sintoma).

- [ ] **Step 2: Benchmark de matching (não deve regredir)**

Run: `PYTHONPATH=src python bench/benchmark.py`
Expected: acc@1/precisão ≥ valores do `bench/resultados/benchmark.log` anterior (r8/r9 são no-op aqui — benchmark não threadeia lista_padrao — mudança viria só do §5 corpus).

- [ ] **Step 3: Gate final consolidado**

```bash
PYTHONPATH=src python bench/reprocessar_lista1.py
PYTHONPATH=src python -c "
from bench.gate_tdt_real import comparar
r = comparar('output/LISTA 1 - GTD/TDT.xlsx', 'docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx')
linha = f'final spMET: comum={r.comum} iguais={r.iguais} pct={r.pct:.2f}'
print(linha)
open('bench/resultados/spMET_final_gate.txt', 'w', encoding='utf-8').write(linha + chr(10))
"
```

Expected: `pct >= baseline` da Task 0.

- [ ] **Step 4: Verificação de ponta a ponta do ALIAS**

```bash
PYTHONPATH=src python -c "
import openpyxl
wb = openpyxl.load_workbook('output/LISTA 1 - GTD/TDT.xlsx', read_only=True)
ws = wb['DNP3_DiscreteSignals']
col_alias = next(c for c in range(1, ws.max_column + 1) if ws.cell(4, c).value == 'Signal Alias')
exemplos = [ws.cell(r, col_alias).value for r in range(5, 15)]
print(*exemplos, sep='\n')
wb.close()
"
```

Expected: aliases legíveis = descrições da lista padrão v1 (ex. "49 - ALARME TEMPERATURA ENROLAMENTO"), não códigos/descrições cruas do cliente, para sinais com sigla decidida.

- [ ] **Step 5: DOX pass**

Reler `src/tdt/AGENTS.md`, `src/tdt/dados/AGENTS.md` e `bench/AGENTS.md`; atualizar só o que mudou de contrato:
- `src/tdt/dados/AGENTS.md`: `SinalPadrao` ganhou `type_severidade`; helper `descricoes_por_sigla` (alias v1).
- `src/tdt/AGENTS.md`: registro de regras agora vai até r9; `engine_tdt.gerar` aceita `alias_v1`.
- `bench/AGENTS.md`: `diag_type_severidade.py` na lista de contratos locais.

- [ ] **Step 6: Atualizar status da spec e commitar**

Na spec, trocar `**Status:** Proposto` por `**Status:** Implementado (2026-07-08)`.

```bash
git add -A
git commit -m "docs: closeout SP-METADADOS - gate final, DOX e status da spec"
```

- [ ] **Step 7: Finalizar branch**

Invocar a skill `superpowers:finishing-a-development-branch` para decidir merge/PR com o usuário.
