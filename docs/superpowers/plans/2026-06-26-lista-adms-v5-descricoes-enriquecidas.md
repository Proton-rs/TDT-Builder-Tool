# Lista Padrão ADMS v5 — descrições enriquecidas para matching — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar `docs/Pontos Padrao ADMS_v5.xlsx` com as descrições (`DESCRIÇÃO NOVA`) enriquecidas **append-only** sobre o texto da v1 (preservado verbatim), para melhorar o matching sem os erros da v3; validar no benchmark e tornar a v5 o novo default.

**Architecture:** Pacote de tooling build-time em `scripts/enriquecer_v5/` (fora de `src/`, não é runtime): uma tabela ANSI C37.2 **verificada** + um compositor puro (append-only, dispatch por grupo) + um gerador que copia a v2 e reescreve só a coluna de descrição via openpyxl, emitindo um sidecar de conflitos e um diff CSV. Validação pelo `bench/benchmark.py` apontando para a v5. Só então o switch de default.

**Tech Stack:** Python 3.14, openpyxl (preserva o resto do .xlsx), pytest, `bench/benchmark.py` (matching tfidf+vetorial+fuzzy).

## Global Constraints

- **Append-only:** o texto exato da v1 fica no INÍCIO de cada `DESCRIÇÃO NOVA`; só se acrescenta depois. Invariante testável: `v5_desc.startswith(v1_desc)` para TODA linha. Nunca reescrever/sobrescrever a v1.
- **Profundidade moderada:** v1 verbatim + função ANSI expandida + 2–4 termos de alto valor. Termos compartilhados da família curtos; a discriminação (neutro/fase) vem do texto v1 preservado.
- **Precisão é o objetivo nº1 (a v3 falhou nisso):** funções ANSI vêm de uma tabela C37.2 verificada; onde o padrão contradiz a convenção da v1, **NÃO** se acrescenta o texto contraditório — flaga-se no sidecar. Conflitos conhecidos são data-driven (set explícito), não heurística.
- **Só a coluna `DESCRIÇÃO NOVA`** de `DiscreteSignals` e `AnalogSignals`. Nenhuma outra coluna/sheet/sigla/linha muda. Sem dedupe de linhas. Sem mexer em v1/v2/v3/v4 (histórico).
- **Tooling fora de `src/`:** tudo em `scripts/enriquecer_v5/`. Não poluir o runtime `src/tdt`.
- **Validação como gate:** benchmark v5 vs baseline v1 — precisão@decididos ≥ baseline e acc@1 não-regredido. Default só troca após passar.
- **TDD:** teste primeiro nos passos de código. Enriquecimento de conteúdo é validado por invariantes (append-only, cobertura) + revisão humana do diff, não por asserção string-a-string de 694 linhas.

## File Structure

- **Create** `scripts/enriquecer_v5/conftest.py` — adiciona o próprio dir ao `sys.path` (imports do pacote nos testes).
- **Create** `scripts/enriquecer_v5/ansi_ref.py` — tabela ANSI C37.2 verificada (`ANSI_C37_2`, `SINONIMOS_ANSI`, `CONFLITO_V1`) + glossário mínimo.
- **Create** `scripts/enriquecer_v5/composer.py` — funções puras de enriquecimento (dispatch ANSI / AJUSTE / composto / analógico / cauda) — append-only.
- **Create** `scripts/enriquecer_v5/mapa_dominio.py` — mapa curado para siglas não-ANSI idiossincráticas (pesquisa de domínio).
- **Create** `scripts/enriquecer_v5/gerar_v5.py` — copia v2→v5, reescreve `DESCRIÇÃO NOVA` (append-only), emite `docs/v5_conflitos_ansi.md` e `docs/v5_diff_descricoes.csv`.
- **Create** `scripts/enriquecer_v5/test_ansi_ref.py`, `test_composer.py`, `test_gerar_v5.py`.
- **Modify** (Task 7, pós-validação) `src/tdt/defaults.py`, `src/tdt/cli.py`, `tests/test_ui_defaults.py`, `docs/AGENTS.md`.

Comando de teste do tooling: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5 -v`
(No Windows usar a Bash tool / git-bash; se `python` faltar, tentar `py`.)

---

### Task 1: Tabela ANSI C37.2 verificada + conftest

**Files:**
- Create: `scripts/enriquecer_v5/conftest.py`
- Create: `scripts/enriquecer_v5/ansi_ref.py`
- Test: `scripts/enriquecer_v5/test_ansi_ref.py`

**Interfaces:**
- Produces: `ANSI_C37_2: dict[int, str]` (device → função PT verificada); `SINONIMOS_ANSI: dict[int, tuple[str, ...]]`; `CONFLITO_V1: dict[int, str]` (código → nota de conflito v1×padrão); `CODIGOS_PRESENTES: frozenset[int]` (os 26 da lista).

- [ ] **Step 1: Write the failing test**

```python
# scripts/enriquecer_v5/test_ansi_ref.py
from ansi_ref import ANSI_C37_2, SINONIMOS_ANSI, CONFLITO_V1, CODIGOS_PRESENTES


def test_cobre_os_26_codigos_presentes():
    presentes = {20, 21, 24, 25, 26, 27, 32, 43, 46, 49, 50, 51, 59, 61,
                 62, 63, 67, 71, 78, 79, 81, 85, 86, 87, 90, 94}
    assert CODIGOS_PRESENTES == presentes
    # todo código presente tem função, exceto os explicitamente em conflito
    for c in presentes:
        assert c in ANSI_C37_2 or c in CONFLITO_V1


def test_ancoras_corretas_anti_v3():
    # os erros que a v3 cometeu — aqui têm que estar certos
    assert "VOLTS" in ANSI_C37_2[24].upper()        # 24 = Volts/Hz (v3 errou p/ sobrecorrente)
    assert "VÁLVULA" in ANSI_C37_2[20].upper() or "VALVULA" in ANSI_C37_2[20].upper()  # 20 = válvula (v3 errou p/ diferencial)
    assert "INSTANT" in ANSI_C37_2[50].upper()      # 50 instantânea
    assert "INVERSO" in ANSI_C37_2[51].upper() or "TEMPO" in ANSI_C37_2[51].upper()
    assert "SUBTENS" in ANSI_C37_2[27].upper()
    assert "SOBRETENS" in ANSI_C37_2[59].upper()
    assert "DIFERENCIAL" in ANSI_C37_2[87].upper()
    assert "FREQU" in ANSI_C37_2[81].upper()


def test_61_marcado_como_conflito_v1():
    # C37.2 define 61 como chave/sensor de densidade, mas a v1 usa "desequilíbrio".
    # Não inventar: 61 vai pro sidecar, não recebe função contraditória.
    assert 61 in CONFLITO_V1
    assert 61 not in ANSI_C37_2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_ansi_ref.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ansi_ref'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/enriquecer_v5/conftest.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
```

```python
# scripts/enriquecer_v5/ansi_ref.py
"""Tabela ANSI/IEEE C37.2 verificada (device number -> função em PT).

Fonte: ANSI/IEEE C37.2 (standard device function numbers). Os ambíguos/menos
comuns (26, 62, 71, 78, 85, 90, 94) foram web-verificados; 61 diverge da
convenção da v1 e é tratado como conflito (não recebe função, vai pro sidecar).
"""
from __future__ import annotations

ANSI_C37_2: dict[int, str] = {
    20: "VÁLVULA OPERADA ELETRICAMENTE (SOLENOIDE)",
    21: "RELÉ DE DISTÂNCIA (IMPEDÂNCIA)",
    24: "RELÉ VOLTS/HERTZ (PROTEÇÃO CONTRA SOBREEXCITAÇÃO / FLUXO MAGNÉTICO)",
    25: "RELÉ DE SINCRONISMO OU VERIFICAÇÃO DE SINCRONISMO",
    26: "DISPOSITIVO TÉRMICO DE EQUIPAMENTO",
    27: "RELÉ DE SUBTENSÃO",
    32: "RELÉ DIRECIONAL DE POTÊNCIA",
    43: "DISPOSITIVO DE TRANSFERÊNCIA OU SELETOR MANUAL",
    46: "RELÉ DE CORRENTE DE SEQUÊNCIA NEGATIVA / DESEQUILÍBRIO DE FASE",
    49: "RELÉ TÉRMICO (DE MÁQUINA OU TRANSFORMADOR)",
    50: "RELÉ DE SOBRECORRENTE INSTANTÂNEA",
    51: "RELÉ DE SOBRECORRENTE TEMPORIZADA (TEMPO INVERSO)",
    59: "RELÉ DE SOBRETENSÃO",
    62: "RELÉ DE TEMPORIZAÇÃO DE PARADA OU ABERTURA",
    63: "RELÉ/CHAVE DE PRESSÃO (BUCHHOLZ / SÚBITA PRESSÃO)",
    67: "RELÉ DIRECIONAL DE SOBRECORRENTE CA",
    71: "RELÉ/CHAVE DE NÍVEL DE LÍQUIDO OU GÁS",
    78: "RELÉ DE MEDIÇÃO DE ÂNGULO DE FASE / PERDA DE SINCRONISMO (OUT-OF-STEP)",
    79: "RELÉ DE RELIGAMENTO AUTOMÁTICO CA",
    81: "RELÉ DE FREQUÊNCIA (SUB/SOBREFREQUÊNCIA)",
    85: "RELÉ DE TELEPROTEÇÃO (CARRIER / FIO PILOTO)",
    86: "RELÉ DE BLOQUEIO (LOCKOUT, REARME MANUAL)",
    87: "RELÉ DE PROTEÇÃO DIFERENCIAL",
    90: "DISPOSITIVO REGULADOR (TENSÃO/POTÊNCIA/FREQUÊNCIA)",
    94: "RELÉ DE DISPARO OU DISPARO LIVRE (TRIP / TRIP-FREE)",
}

# Termos curtos de alto valor por código (acrescentados além da função).
SINONIMOS_ANSI: dict[int, tuple[str, ...]] = {
    50: ("PROTEÇÃO INSTANTÂNEA", "CURTO-CIRCUITO"),
    51: ("PROTEÇÃO TEMPORIZADA", "COORDENAÇÃO"),
    27: ("PERDA DE TENSÃO",),
    59: ("SOBRETENSÃO",),
    67: ("DIRECIONAL",),
    79: ("RELIGAMENTO", "RELIGA"),
    86: ("LOCKOUT", "BLOQUEIO"),
    87: ("PROTEÇÃO DIFERENCIAL",),
    81: ("FREQUÊNCIA",),
}

# Códigos onde a convenção da v1 diverge do padrão C37.2 -> sidecar, sem
# acrescentar função contraditória (preservar v1).
CONFLITO_V1: dict[int, str] = {
    61: ("v1 usa '(des)equilíbrio'; C37.2 define 61 como chave/sensor de densidade. "
         "Verificar convenção da concessionária antes de descrever."),
}

CODIGOS_PRESENTES: frozenset[int] = frozenset(
    {20, 21, 24, 25, 26, 27, 32, 43, 46, 49, 50, 51, 59, 61,
     62, 63, 67, 71, 78, 79, 81, 85, 86, 87, 90, 94}
)
```

> Antes de marcar a task pronta: web-verificar (busca rápida "ANSI device number NN") os menos comuns — 26, 62, 71, 78, 85, 90, 94 — e confirmar 61 (densidade vs desequilíbrio). Ajustar a TABELA (não o código). Documentar no relatório qual fonte confirmou cada um.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_ansi_ref.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add scripts/enriquecer_v5/conftest.py scripts/enriquecer_v5/ansi_ref.py scripts/enriquecer_v5/test_ansi_ref.py
git commit -m "feat(v5): tabela ANSI C37.2 verificada + glossário (lista v5)"
```

---

### Task 2: Compositor — caminho ANSI (append-only)

**Files:**
- Create: `scripts/enriquecer_v5/composer.py`
- Test: `scripts/enriquecer_v5/test_composer.py`

**Interfaces:**
- Consumes: `ansi_ref.ANSI_C37_2`, `SINONIMOS_ANSI`, `CONFLITO_V1` (Task 1).
- Produces: `base_ansi(desc: str) -> int | None` (extrai o código-base do início da descrição); `enriquecer_ansi(v1: str, code: int) -> tuple[str, int | None]` (devolve `(texto_v5, conflito_or_None)`); `enriquecer(v1: str, sheet: str) -> tuple[str, int | None]` (dispatch — nesta task só trata ANSI; resto devolve v1 inalterado).

- [ ] **Step 1: Write the failing test**

```python
# scripts/enriquecer_v5/test_composer.py
from composer import base_ansi, enriquecer_ansi, enriquecer


def test_base_ansi_extrai_codigo():
    assert base_ansi("50 - SOBRECORRENTE INSTANTANEA NEUTRO") == 50
    assert base_ansi("50F2 - ...") == 50
    assert base_ansi("CORRENTE NEUTRO") is None
    assert base_ansi("20C 20T 63T - ALARME VALVULA OU BUCHHOLZ") == 20  # 1º código embutido


def test_enriquecer_ansi_append_only_e_funcao():
    v1 = "50 - SOBRECORRENTE INSTANTANEA NEUTRO"
    out, conflito = enriquecer_ansi(v1, 50)
    assert out.startswith(v1)            # append-only
    assert "ANSI 50" in out
    assert "INSTANT" in out.upper()
    assert conflito is None
    assert len(out) > len(v1)            # acrescentou algo


def test_enriquecer_ansi_conflito_nao_acrescenta_funcao():
    v1 = "61 - DESEQUILIBRIO TEMPORIZADO"
    out, conflito = enriquecer_ansi(v1, 61)
    assert out.startswith(v1)
    assert conflito == 61                 # flagado
    # não acrescenta texto contraditório (densidade); no máximo a referência neutra
    assert "DENSIDADE" not in out.upper()


def test_dispatch_preserva_nao_ansi_nesta_task():
    v1 = "CORRENTE NEUTRO"
    out, conflito = enriquecer(v1, "AnalogSignals")
    assert out == v1                      # ainda não tratado (Task 3)
    assert conflito is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_composer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'composer'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/enriquecer_v5/composer.py
"""Enriquecimento append-only das descrições da lista padrão (build-time).

O texto da v1 é preservado verbatim no início; só se acrescenta depois. A
discriminação dentro da família (neutro/fase) vem do texto v1 preservado, então
o compositor NÃO precisa reparsear sufixos.
"""
from __future__ import annotations

import re

from ansi_ref import ANSI_C37_2, CONFLITO_V1, SINONIMOS_ANSI

_PREFIXO_ANSI = re.compile(r"^\s*(\d{2})")


def base_ansi(desc: str) -> int | None:
    m = _PREFIXO_ANSI.match(desc or "")
    return int(m.group(1)) if m else None


def enriquecer_ansi(v1: str, code: int) -> tuple[str, int | None]:
    if code in CONFLITO_V1:
        return f"{v1} — ANSI {code}", code  # referência neutra + flag, sem função
    func = ANSI_C37_2[code]
    extra = f" — ANSI {code} {func}"
    syn = SINONIMOS_ANSI.get(code, ())
    if syn:
        extra += ", " + ", ".join(syn)
    return v1 + extra, None


def enriquecer(v1: str, sheet: str) -> tuple[str, int | None]:
    """Dispatch. Nesta task só o caminho ANSI; o resto volta inalterado."""
    code = base_ansi(v1)
    if code is not None and (code in ANSI_C37_2 or code in CONFLITO_V1):
        return enriquecer_ansi(v1, code)
    return v1, None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_composer.py -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Commit**

```bash
git add scripts/enriquecer_v5/composer.py scripts/enriquecer_v5/test_composer.py
git commit -m "feat(v5): compositor caminho ANSI (append-only)"
```

---

### Task 3: Compositor — grupos não-ANSI por regra (AJUSTE, composto, analógico)

**Files:**
- Modify: `scripts/enriquecer_v5/composer.py`
- Test: `scripts/enriquecer_v5/test_composer.py`

**Interfaces:**
- Consumes: `base_ansi`, `enriquecer_ansi` (Task 2); `ansi_ref.ANSI_C37_2`.
- Produces: estende `enriquecer(v1, sheet)` para tratar: (a) família `AJUSTE PARA <alvo>`; (b) composto com códigos ANSI embutidos no texto (ex. `20C 20T 63T - ...`); (c) medições analógicas (`sheet == "AnalogSignals"`), acrescentando grandeza+unidade. Tudo append-only.

- [ ] **Step 1: Write the failing test**

```python
# scripts/enriquecer_v5/test_composer.py (append)
def test_ajuste_family_append():
    v1 = "AJUSTE PARA AL15"
    out, c = enriquecer(v1, "DiscreteSignals")
    assert out.startswith(v1)
    assert "PARAMETR" in out.upper() or "SETTING" in out.upper()
    assert "AL15" in out


def test_composto_expande_codigos_embutidos():
    v1 = "20C 20T 63T - ALARME VALVULA OU BUCHHOLZ"
    out, c = enriquecer(v1, "DiscreteSignals")
    assert out.startswith(v1)
    # acrescenta a expansão de pelo menos um código embutido
    assert "VÁLVULA" in out.upper() or "VALVULA" in out.upper() or "PRESS" in out.upper()


def test_analogico_grandeza_unidade():
    out, c = enriquecer("CORRENTE NEUTRO", "AnalogSignals")
    assert out.startswith("CORRENTE NEUTRO")
    assert "AMP" in out.upper() or "(A)" in out.upper() or "IN" in out.upper()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_composer.py -k "ajuste or composto or analogico" -v`
Expected: FAIL (assertions de termos acrescentados não satisfeitas — `enriquecer` ainda devolve o texto cru).

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/enriquecer_v5/composer.py (acrescentar)

_AJUSTE = re.compile(r"^\s*AJUSTE\s+PARA\s+(.+)$", re.IGNORECASE)
_CODIGOS_EMBUTIDOS = re.compile(r"\b(\d{2})[A-Z]?\b")

# grandeza (token inicial da descrição analógica) -> (sinônimos, unidade)
_GRANDEZA_ANALOG: dict[str, tuple[str, str]] = {
    "CORRENTE": ("AMPERAGEM",), "TENSAO": ("VOLTAGEM",), "TENSÃO": ("VOLTAGEM",),
    "POTENCIA": ("POTÊNCIA",), "POTÊNCIA": ("POTÊNCIA",),
    "TEMPERATURA": ("TÉRMICO",), "FREQUENCIA": ("HZ",), "FREQUÊNCIA": ("HZ",),
    "ANGULO": ("FASE",), "ÂNGULO": ("FASE",),
}


def _enriquecer_ajuste(v1: str, alvo: str) -> str:
    return f"{v1} — AJUSTE/PARAMETRIZAÇÃO (SETTING) DA FUNÇÃO/ALIMENTADOR {alvo.strip()}"


def _enriquecer_composto(v1: str) -> str | None:
    cods = [int(c) for c in _CODIGOS_EMBUTIDOS.findall(v1) if int(c) in ANSI_C37_2]
    if len(set(cods)) < 2:   # composto = 2+ códigos ANSI distintos no texto
        return None
    vistos: list[str] = []
    for c in dict.fromkeys(cods):  # únicos, ordem
        vistos.append(f"ANSI {c} {ANSI_C37_2[c]}")
    return f"{v1} — " + "; ".join(vistos)


def _enriquecer_analogico(v1: str) -> str | None:
    tok = v1.strip().split()[0].upper() if v1.strip() else ""
    syn = _GRANDEZA_ANALOG.get(tok)
    if not syn:
        return None
    return f"{v1} — MEDIÇÃO {', '.join(syn)}"
```

E reescrever `enriquecer` para o dispatch completo (substituir a versão da Task 2).
**Ordem importa:** composto (2+ códigos ANSI no texto) ANTES do ANSI-single — senão
"20C 20T 63T..." cairia no caminho ANSI-single (lê só "20") e perderia o 63 (buchholz).

```python
def enriquecer(v1: str, sheet: str) -> tuple[str, int | None]:
    comp = _enriquecer_composto(v1)        # 2+ códigos ANSI distintos -> composto
    if comp is not None:
        return comp, None
    code = base_ansi(v1)
    if code is not None and (code in ANSI_C37_2 or code in CONFLITO_V1):
        return enriquecer_ansi(v1, code)
    m = _AJUSTE.match(v1 or "")
    if m:
        return _enriquecer_ajuste(v1, m.group(1)), None
    if sheet == "AnalogSignals":
        ana = _enriquecer_analogico(v1)
        if ana is not None:
            return ana, None
    return v1, None  # cauda idiossincrática — Task 4
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_composer.py -v`
Expected: PASS (todos, incluindo os da Task 2 — `test_dispatch_preserva_nao_ansi_nesta_task` ainda passa porque "CORRENTE NEUTRO" agora é tratado? NÃO: aquele teste esperava inalterado. Ajustar: ver nota).

> NOTA p/ o implementador: o teste `test_dispatch_preserva_nao_ansi_nesta_task` da Task 2 usava "CORRENTE NEUTRO"/AnalogSignals, que agora é enriquecido. Atualize aquele teste para um caso que permaneça na cauda (ex.: `enriquecer("PROPRIEDADE DO COMANDO", "DiscreteSignals")` deve voltar inalterado nesta task) — é uma mudança de expectativa legítima pela nova cobertura, não um bug. Mantenha a asserção de append-only.

- [ ] **Step 5: Commit**

```bash
git add scripts/enriquecer_v5/composer.py scripts/enriquecer_v5/test_composer.py
git commit -m "feat(v5): compositor grupos não-ANSI (ajuste/composto/analógico)"
```

---

### Task 4: Mapa de domínio para a cauda idiossincrática + cobertura

**Files:**
- Create: `scripts/enriquecer_v5/mapa_dominio.py`
- Modify: `scripts/enriquecer_v5/composer.py` (consultar o mapa na cauda)
- Test: `scripts/enriquecer_v5/test_composer.py`

**Interfaces:**
- Consumes: as sheets internas `DMS Signal Explanation`/`Information` da v2 (fonte) + skill `especialista-ADMS`.
- Produces: `mapa_dominio.MAPA: dict[str, str]` (sigla → termos curtos a acrescentar) p/ as siglas funcionais sem regra (ex. `TAL`, `TPPM`, `ABBN`, `CMDE`, `CCIC`); `composer.enriquecer` consulta `MAPA` por sigla antes do fallback. Assinatura de `enriquecer` ganha `sigla`: `enriquecer(v1: str, sheet: str, sigla: str = "") -> tuple[str, int | None]`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/enriquecer_v5/test_composer.py (append)
from mapa_dominio import MAPA


def test_mapa_dominio_aplica_por_sigla():
    # TAL existe no mapa (transferência automática de linha)
    v1 = "TAL - FUNCAO TRANSFERENCIA AUTOMATICA DE LINHA"
    out, c = enriquecer(v1, "DiscreteSignals", sigla="TAL")
    assert out.startswith(v1)
    if "TAL" in MAPA:
        assert len(out) > len(v1)


def test_cauda_sem_mapa_preserva_v1():
    out, c = enriquecer("SINAL XPTO SEM REGRA", "DiscreteSignals", sigla="ZZZZ")
    assert out == "SINAL XPTO SEM REGRA"   # preservar v1 é sempre seguro
    assert c is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_composer.py -k "mapa or cauda" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mapa_dominio'` (e `enriquecer` sem param `sigla`).

- [ ] **Step 3: Write minimal implementation**

Pesquisar (sheets internas `DMS Signal Explanation`/`Information` + skill `especialista-ADMS`) e curar o mapa para as siglas funcionais de maior volume. Começar pelo conjunto conhecido; expandir conforme o diff da Task 5 revelar cauda relevante.

```python
# scripts/enriquecer_v5/mapa_dominio.py
"""Termos curados a acrescentar (append-only) para siglas não-ANSI sem regra.
Fonte: sheets internas da lista (DMS Signal Explanation/Information) + domínio ADMS.
Acrescentar só o que se sabe correto — na dúvida, deixar de fora (preservar v1)."""
from __future__ import annotations

MAPA: dict[str, str] = {
    "TAL": "TRANSFERÊNCIA AUTOMÁTICA DE LINHA, COMUTAÇÃO DE ALIMENTAÇÃO",
    "TPPM": "TRANSFERÊNCIA COM PARALELISMO MOMENTÂNEO",
    "ABBN": "ABERTURA PELA BOBINA DE NEUTRO, COMANDO DE TRIP POR NEUTRO",
    "CMDE": "PROPRIEDADE/POSSE DO COMANDO (CONTROLE SCADA)",
    "CCIC": "CHAVE DE COMANDO ICCP (TELECONTROLE)",
    # expandir conforme o diff da Task 5; na dúvida, não incluir.
}
```

E em `composer.py`, alterar a assinatura e consultar o mapa na cauda:

```python
from mapa_dominio import MAPA

def enriquecer(v1: str, sheet: str, sigla: str = "") -> tuple[str, int | None]:
    comp = _enriquecer_composto(v1)        # 2+ códigos ANSI distintos -> composto
    if comp is not None:
        return comp, None
    code = base_ansi(v1)
    if code is not None and (code in ANSI_C37_2 or code in CONFLITO_V1):
        return enriquecer_ansi(v1, code)
    m = _AJUSTE.match(v1 or "")
    if m:
        return _enriquecer_ajuste(v1, m.group(1)), None
    if sheet == "AnalogSignals":
        ana = _enriquecer_analogico(v1)
        if ana is not None:
            return ana, None
    termos = MAPA.get((sigla or "").strip().upper())
    if termos:
        return f"{v1} — {termos}", None
    return v1, None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_composer.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add scripts/enriquecer_v5/mapa_dominio.py scripts/enriquecer_v5/composer.py scripts/enriquecer_v5/test_composer.py
git commit -m "feat(v5): mapa de domínio p/ cauda não-ANSI + cobertura"
```

---

### Task 5: Gerador da v5 + sidecar de conflitos + diff CSV

**Files:**
- Create: `scripts/enriquecer_v5/gerar_v5.py`
- Test: `scripts/enriquecer_v5/test_gerar_v5.py`

**Interfaces:**
- Consumes: `composer.enriquecer` (Tasks 2-4).
- Produces: ao rodar, cria `docs/Pontos Padrao ADMS_v5.xlsx` (cópia da v2 com `DESCRIÇÃO NOVA` reescrita append-only nas duas sheets), `docs/v5_conflitos_ansi.md`, `docs/v5_diff_descricoes.csv`. Função testável `aplicar(ws, sheet_nome) -> tuple[int, list[tuple]]` (nº linhas tocadas, linhas de conflito) que pode rodar sobre um workbook em memória.

- [ ] **Step 1: Write the failing test** (invariante append-only num workbook sintético)

```python
# scripts/enriquecer_v5/test_gerar_v5.py
import openpyxl
from gerar_v5 import aplicar, COL_DESC, COL_SIGLA


def _ws():
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["SINAL", "DESCRIÇÃO NOVA"])  # header (col 0,1)
    ws.append(["50N", "50 - SOBRECORRENTE INSTANTANEA NEUTRO"])
    ws.append(["61T", "61 - DESEQUILIBRIO TEMPORIZADO"])
    ws.append(["CMDE", "PROPRIEDADE DO COMANDO"])
    return ws


def test_aplicar_append_only_em_todas_as_linhas():
    ws = _ws()
    originais = [ws.cell(r, COL_DESC + 1).value for r in range(2, ws.max_row + 1)]
    tocadas, conflitos = aplicar(ws, "DiscreteSignals")
    for i, r in enumerate(range(2, ws.max_row + 1)):
        novo = ws.cell(r, COL_DESC + 1).value
        assert novo.startswith(originais[i])   # INVARIANTE central: append-only
    # 50N foi enriquecido; 61T flagado como conflito
    assert any(sig == "61T" for sig, *_ in conflitos)


def test_50n_recebeu_funcao_ansi():
    ws = _ws()
    aplicar(ws, "DiscreteSignals")
    v = ws.cell(2, COL_DESC + 1).value
    assert "ANSI 50" in v and "INSTANT" in v.upper()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_gerar_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gerar_v5'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/enriquecer_v5/gerar_v5.py
"""Gera a v5: copia a v2, reescreve DESCRIÇÃO NOVA append-only nas duas sheets,
e emite sidecar de conflitos + diff CSV. Não toca em nenhuma outra coluna/sheet."""
from __future__ import annotations

import csv
import shutil
from pathlib import Path

import openpyxl

from composer import enriquecer

DOCS = Path("docs")
V2 = DOCS / "Pontos Padrao ADMS_v2.xlsx"
V5 = DOCS / "Pontos Padrao ADMS_v5.xlsx"
SHEETS = ("DiscreteSignals", "AnalogSignals")
COL_SIGLA = 0          # 0-based
COL_DESC = 1           # DESCRIÇÃO NOVA é a coluna 1 (B)


def _achar_col_desc(ws) -> int:
    header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    for i, h in enumerate(header):
        if h is not None and "DESCRI" in str(h).upper():
            return i
    return COL_DESC


def aplicar(ws, sheet_nome: str) -> tuple[int, list[tuple]]:
    col = _achar_col_desc(ws)
    tocadas = 0
    conflitos: list[tuple] = []
    diffs: list[tuple] = []
    for r in range(2, ws.max_row + 1):
        sigla = ws.cell(r, COL_SIGLA + 1).value
        v1 = ws.cell(r, col + 1).value
        if sigla in (None, "") or v1 in (None, ""):
            continue
        v1s = str(v1).strip()
        novo, conflito = enriquecer(v1s, sheet_nome, sigla=str(sigla).strip())
        if novo != v1s:
            ws.cell(r, col + 1).value = novo
            tocadas += 1
            diffs.append((str(sigla).strip(), sheet_nome, v1s, novo, novo[len(v1s):].lstrip(" —")))
        if conflito is not None:
            conflitos.append((str(sigla).strip(), sheet_nome, conflito, v1s))
    aplicar.ultimo_diff = diffs  # type: ignore[attr-defined]
    return tocadas, conflitos


def main() -> None:
    shutil.copyfile(V2, V5)
    wb = openpyxl.load_workbook(V5)
    todos_conf: list[tuple] = []
    todos_diff: list[tuple] = []
    for sh in SHEETS:
        toc, conf = aplicar(wb[sh], sh)
        todos_conf += conf
        todos_diff += getattr(aplicar, "ultimo_diff", [])
        print(f"[{sh}] linhas enriquecidas: {toc}; conflitos: {len(conf)}")
    wb.save(V5)
    # sidecar de conflitos
    from ansi_ref import CONFLITO_V1
    with open(DOCS / "v5_conflitos_ansi.md", "w", encoding="utf-8") as f:
        f.write("# Conflitos v1 × ANSI (revisar; v1 preservado)\n\n")
        for sig, sheet, code, v1 in todos_conf:
            nota = CONFLITO_V1.get(code, "")
            f.write(f"- **{sig}** ({sheet}) ANSI {code}: {v1!r} — {nota}\n")
    # diff CSV
    with open(DOCS / "v5_diff_descricoes.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sigla", "sheet", "v1", "v5", "acrescentado"])
        w.writerows(todos_diff)
    print(f"v5 salvo em {V5}; conflitos={len(todos_conf)}; diffs={len(todos_diff)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts/enriquecer_v5 python -m pytest scripts/enriquecer_v5/test_gerar_v5.py -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Gerar a v5 de verdade e inspecionar**

> Pré-condição: o Excel NÃO pode estar com a v5/v2 aberta (lock `~$`). Se houver, fechar antes.

Run: `PYTHONPATH=scripts/enriquecer_v5 python scripts/enriquecer_v5/gerar_v5.py`
Expected: imprime linhas enriquecidas por sheet + cria `docs/Pontos Padrao ADMS_v5.xlsx`, `docs/v5_conflitos_ansi.md`, `docs/v5_diff_descricoes.csv`.

Verificação de invariante global (append-only em TODAS as linhas reais, e nenhuma outra coluna mudou):

```bash
PYTHONPATH=scripts/enriquecer_v5 python - <<'PY'
import openpyxl
v2=openpyxl.load_workbook("docs/Pontos Padrao ADMS_v2.xlsx", data_only=True)
v5=openpyxl.load_workbook("docs/Pontos Padrao ADMS_v5.xlsx", data_only=True)
for sh in ("DiscreteSignals","AnalogSignals"):
    a=list(v2[sh].iter_rows(values_only=True)); b=list(v5[sh].iter_rows(values_only=True))
    assert len(a)==len(b), (sh,len(a),len(b))
    for ra,rb in zip(a,b):
        for i,(ca,cb) in enumerate(zip(ra,rb)):
            if i==1:  # DESCRIÇÃO NOVA: append-only
                if ca: assert (cb or "").startswith(str(ca)), (sh, ca, cb)
            else:     # demais colunas: idênticas
                assert ca==cb, (sh,i,ca,cb)
print("OK invariantes: append-only na col 1, resto idêntico à v2")
PY
```
Expected: `OK invariantes...`.

- [ ] **Step 6: Commit**

```bash
git add scripts/enriquecer_v5/gerar_v5.py scripts/enriquecer_v5/test_gerar_v5.py "docs/Pontos Padrao ADMS_v5.xlsx" docs/v5_conflitos_ansi.md docs/v5_diff_descricoes.csv
git commit -m "feat(v5): gerador da lista v5 (append-only) + sidecar + diff"
```

---

### Task 6: Validação — benchmark v5 vs baseline v1 + revisão humana

**Files:**
- Modify: `bench/benchmark.py:37` (parametrizar o caminho da lista por env var, sem mudar o default)
- Test: (manual / gate) — o próprio benchmark

**Interfaces:**
- Consumes: `docs/Pontos Padrao ADMS_v5.xlsx` (Task 5).
- Produces: comparação acc@1 / precisão@decididos entre v1 (baseline) e v5; veredito de não-regressão.

- [ ] **Step 1: Parametrizar a lista no benchmark (1 linha, retrocompatível)**

Em `bench/benchmark.py`, trocar:
```python
lp = ListaPadraoADMS.carregar("docs/Pontos Padrao ADMS_v1.xlsx")
```
por:
```python
import os
lp = ListaPadraoADMS.carregar(os.environ.get("LISTA_BENCH", "docs/Pontos Padrao ADMS_v1.xlsx"))
```
(Default inalterado ⇒ não quebra nada; permite apontar p/ a v5 via env.)

- [ ] **Step 2: Rodar baseline (v1) e capturar números**

Run: `PYTHONPATH=src python bench/benchmark.py`
Anotar a linha `tfidf+vet+fuzzy` (acc@1 / rec@3 / decid / prec@dec) e `combo+regras` — é o baseline.

- [ ] **Step 3: Rodar com a v5 e comparar**

Run: `LISTA_BENCH="docs/Pontos Padrao ADMS_v5.xlsx" PYTHONPATH=src python bench/benchmark.py`
Expected/gate: para `tfidf+vet+fuzzy` e `combo+regras`, **precisão@decididos ≥ baseline** e **acc@1 não menor** que o baseline. Se regredir, identificar a família culpada pelo diff CSV e **reduzir** os termos acrescentados daquele grupo no compositor (menos sinônimos), rerodar. Não desligar tudo.

- [ ] **Step 4: Revisão humana dos artefatos**

Abrir `docs/v5_diff_descricoes.csv` (amostra ampla) e `docs/v5_conflitos_ansi.md` — conferir que os acréscimos são corretos e que nenhum conflito foi descrito de forma inventada. Ajustar `ansi_ref.py`/`mapa_dominio.py` e regenerar (Task 5 Step 5) se necessário.

- [ ] **Step 5: Commit**

```bash
git add bench/benchmark.py
git commit -m "chore(bench): permite LISTA_BENCH p/ validar a v5 (default inalterado)"
```

> Gate de saída desta task: registrar no relatório os números baseline vs v5 e a conclusão (≥ baseline). Só seguir p/ a Task 7 se passar.

---

### Task 7: Switch de default para a v5 (pós-validação)

**Files:**
- Modify: `src/tdt/defaults.py:12`
- Modify: `src/tdt/cli.py:44`
- Modify: `tests/test_ui_defaults.py:6`
- Modify: `docs/AGENTS.md:32`

**Interfaces:**
- Consumes: v5 validada (Task 6).
- Produces: runtime default = v5.

- [ ] **Step 1: Atualizar o teste do default (RED)**

Em `tests/test_ui_defaults.py`, trocar a asserção:
```python
assert DEFAULT_LISTA.endswith("Pontos Padrao ADMS_v5.xlsx")
```
Run: `PYTHONPATH=src python -m pytest tests/test_ui_defaults.py -v` → FAIL (ainda aponta v4).

- [ ] **Step 2: Trocar o default no código**

`src/tdt/defaults.py:12`:
```python
DEFAULT_LISTA = str(_DOCS / "Pontos Padrao ADMS_v5.xlsx")
```
`src/tdt/cli.py:44`:
```python
    g.add_argument("--lista-padrao", default="docs/Pontos Padrao ADMS_v5.xlsx")
```

- [ ] **Step 3: Verde + suíte completa**

Run: `PYTHONPATH=src python -m pytest tests/test_ui_defaults.py -v` → PASS.
Run: `PYTHONPATH=src python -m pytest -q` → todos verdes (a v5 carrega com as mesmas colunas da v2/v1, então `lista_padrao.py` e os testes que exercitam o default continuam válidos).

- [ ] **Step 4: DOX — atualizar a fonte de verdade**

Em `docs/AGENTS.md:32`, trocar a descrição do default p/ a v5: `Pontos Padrao ADMS_v5.xlsx` (lista padrão, **default** — base v2 = descrições v1 + fixes + DJF1, com `DESCRIÇÃO NOVA` enriquecida append-only p/ matching; v1–v4 ficam como histórico, não editar).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/defaults.py src/tdt/cli.py tests/test_ui_defaults.py docs/AGENTS.md
git commit -m "feat(lista): v5 enriquecida vira o novo default (substitui v4)"
```

---

## Self-Review (preenchido)

- **Cobertura do spec:** base v2→v5 (Task 5) ✓; append-only moderado (Tasks 2-5, invariante testada) ✓; backbone ANSI verificado (Task 1) ✓; não-ANSI por regra + domínio (Tasks 3-4) ✓; sidecar de conflitos + diff (Task 5) ✓; validação benchmark v5 vs v1 (Task 6) ✓; switch de default (Task 7) ✓; preservar v1 + flagar (Tasks 2/5) ✓; só a coluna DESCRIÇÃO NOVA, resto idêntico (invariante Task 5 Step 5) ✓. **Não-objetivos respeitados:** sem mudança estrutural, sem editar v1-v4, sem mexer em scorers/config.
- **Placeholders:** nenhum — cada passo de código traz o código real e o comando com saída esperada. A tabela ANSI é fornecida verbatim (Task 1); a única pesquisa em-task é a web-verify dos 7 códigos menos comuns + a curadoria do `mapa_dominio` (Task 4), explicitamente delimitada e validada por invariantes + benchmark.
- **Consistência de tipos:** `base_ansi -> int|None`; `enriquecer_ansi -> (str, int|None)`; `enriquecer(v1, sheet, sigla="") -> (str, int|None)` (a assinatura ganha `sigla` na Task 4 — nota explícita); `aplicar(ws, sheet) -> (int, list[tuple])`. `COL_DESC`/`COL_SIGLA` consistentes. Nomes batem entre tasks.
- **Risco residual conhecido:** benchmark só tem 28 pares (guarda de regressão, não medidor de melhoria ampla) — assumido no spec; a revisão humana do diff (Task 6 Step 4) é o complemento.
```
