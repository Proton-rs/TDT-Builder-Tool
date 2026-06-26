# Gerador de Mockup (corruptor determinístico) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recomendado) ou executing-plans. Steps usam `- [ ]`.

**Goal:** Gerar pares rotulados `(descrição_corrompida → sigla)` a partir da Lista Padrão V2, em 5 níveis cumulativos de dificuldade, determinístico — dados de treino p/ a spec E.

**Architecture:** Tooling offline em `scripts/treino/` (fora de `src/`): assets de corrupção + transforms puros (um por classe) + `gerar_dataset` compondo os níveis. RNG semeado por `(sigla, nível, variante, seed)`.

**Tech Stack:** Python 3.14, `random` (stdlib), pytest, openpyxl (ler V2). Reusa `config.ABREVIACOES_PADRAO` e `scripts/enriquecer_v5/ansi_ref.py`.

## Global Constraints

- **Determinístico:** mesmo `seed` ⇒ saída idêntica. Sem `random` global — sempre `random.Random(semente_local)`.
- **Rótulo preservado:** toda variante mantém a sigla verdadeira.
- **Puro/offline:** sem escrita em disco nas funções de geração (dump é passo separado opcional). Tooling em `scripts/treino/`, não tocar `src/`.
- **Fonte = V2** (`docs/Pontos Padrao ADMS_v2.xlsx`). Reusar assets, não reinventar abreviações/ANSI.
- **TDD.** Testes rodam: `PYTHONPATH=scripts/treino:src python -m pytest scripts/treino -v`.

---

### Task 1: Assets + transforms puros

**Files:**
- Create: `scripts/treino/conftest.py`, `scripts/treino/corrupt.py`
- Test: `scripts/treino/test_corrupt.py`

**Interfaces:**
- Produces: `SINONIMOS: dict[str,str]`, `IDS_EQUIP: tuple[str,...]`, `SUFIXOS_ESTADO: tuple[str,...]`; transforms puros `_abreviar`, `_sinonimo`, `_reordenar`, `_ruido_equip`, `_sufixo_estado`, `_remover_tokens`, `_ansi_parens`, `_typo` — cada um `(texto: str, rng: random.Random) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/treino/test_corrupt.py
import random
from corrupt import (_abreviar, _sinonimo, _reordenar, _ruido_equip,
                     _sufixo_estado, _remover_tokens, _ansi_parens, _typo)


def _rng(): return random.Random(42)


def test_abreviar_encurta_token_conhecido():
    out = _abreviar("DISJUNTOR FASE A", _rng())
    assert "DISJ" in out.upper() and "FASE" in out.upper()  # encurtou DISJUNTOR


def test_reordenar_preserva_tokens():
    out = _reordenar("CORRENTE FASE A", _rng())
    assert sorted(out.split()) == sorted("CORRENTE FASE A".split())


def test_ruido_equip_insere_id():
    out = _ruido_equip("CORRENTE FASE A", _rng())
    assert len(out) > len("CORRENTE FASE A")


def test_ansi_parens_substitui_funcao_por_codigo():
    out = _ansi_parens("87 - PROTECAO DIFERENCIAL", _rng())
    assert "(87)" in out


def test_typo_muda_um_caractere():
    base = "CORRENTE"
    out = _typo(base, _rng())
    assert out != base and abs(len(out) - len(base)) <= 1


def test_determinismo_transform():
    assert _ruido_equip("X", random.Random(1)) == _ruido_equip("X", random.Random(1))
```

- [ ] **Step 2: Run → FAIL** (`ModuleNotFoundError: corrupt`).
Run: `PYTHONPATH=scripts/treino:src python -m pytest scripts/treino/test_corrupt.py -v`

- [ ] **Step 3: Implement**

```python
# scripts/treino/conftest.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
```

```python
# scripts/treino/corrupt.py
"""Transforms determinísticos de corrupção de descrição (build-time)."""
from __future__ import annotations
import random
from tdt.config import ABREVIACOES_PADRAO
from ansi_ref import ANSI_C37_2  # scripts/enriquecer_v5 no PYTHONPATH em runtime de teste? ver nota

# reverso: palavra inteira -> abreviação (1ª que expande p/ ela)
_REV_ABREV: dict[str, str] = {}
for ab, full in ABREVIACOES_PADRAO.items():
    _REV_ABREV.setdefault(full, ab)

SINONIMOS: dict[str, str] = {
    "DESEQUILIBRIO": "DESBALANCO", "CORRENTE": "CORR", "TENSAO": "TENS",
    "TEMPERATURA": "TEMP", "RELIGAMENTO": "RELIGA", "BLOQUEIO": "BLOQ",
}
IDS_EQUIP: tuple[str, ...] = ("52-1", "01Q0", "01F1", "43TC", "52-2", "IED 01F1")
SUFIXOS_ESTADO: tuple[str, ...] = ("BLOQUEIO", "ABERTO", "FECHADO", "POS. REMOTO", "TRIP")


def _toks(s): return s.split()


def _abreviar(texto: str, rng: random.Random) -> str:
    out = []
    for t in _toks(texto):
        u = t.upper()
        if u in _REV_ABREV and rng.random() < 0.7:
            out.append(_REV_ABREV[u])
        elif u in SINONIMOS and rng.random() < 0.5:
            out.append(SINONIMOS[u])
        else:
            out.append(t)
    return " ".join(out)


def _sinonimo(texto: str, rng: random.Random) -> str:
    return " ".join(SINONIMOS.get(t.upper(), t) if rng.random() < 0.6 else t for t in _toks(texto))


def _reordenar(texto: str, rng: random.Random) -> str:
    ts = _toks(texto); rng.shuffle(ts); return " ".join(ts)


def _ruido_equip(texto: str, rng: random.Random) -> str:
    return f"{texto} {rng.choice(IDS_EQUIP)}"


def _sufixo_estado(texto: str, rng: random.Random) -> str:
    return f"{texto} - {rng.choice(SUFIXOS_ESTADO)}"


def _remover_tokens(texto: str, rng: random.Random) -> str:
    ts = _toks(texto)
    if len(ts) <= 2:
        return texto
    n = rng.randint(1, max(1, len(ts) // 3))
    idx = set(rng.sample(range(len(ts)), min(n, len(ts) - 1)))
    return " ".join(t for i, t in enumerate(ts) if i not in idx)


def _ansi_parens(texto: str, rng: random.Random) -> str:
    ts = _toks(texto)
    if ts and ts[0].isdigit() and int(ts[0]) in ANSI_C37_2:
        # "87 - PROTECAO DIFERENCIAL" -> "PROTECAO DIFERENCIAL (87)" sem a função-frase
        cod = ts[0]
        resto = [t for t in ts[1:] if t != "-"]
        return (" ".join(resto) + f" ({cod})").strip()
    return texto


def _typo(texto: str, rng: random.Random) -> str:
    if not texto:
        return texto
    i = rng.randrange(len(texto))
    c = texto[i]
    op = rng.choice(("drop", "dup", "swap"))
    if op == "drop" and len(texto) > 1:
        return texto[:i] + texto[i + 1:]
    if op == "dup":
        return texto[:i] + c + texto[i:]
    j = min(i + 1, len(texto) - 1)
    return texto[:i] + texto[j] + texto[i + 1:j] + c + texto[j + 1:]
```

> NOTA imports: `ansi_ref` vive em `scripts/enriquecer_v5/`. O teste roda com `PYTHONPATH=scripts/treino:src`. Acrescentar `scripts/enriquecer_v5` ao PYTHONPATH do comando (`PYTHONPATH=scripts/treino:scripts/enriquecer_v5:src`) OU copiar a constante mínima. **Decisão:** usar o PYTHONPATH composto no comando de teste; documentar no plano. Se o subagente achar frágil, copiar `ANSI_C37_2` p/ um dado local é aceitável (reportar).

- [ ] **Step 4: Run → PASS** (`PYTHONPATH=scripts/treino:scripts/enriquecer_v5:src python -m pytest scripts/treino/test_corrupt.py -v`).

- [ ] **Step 5: Commit**
```bash
git add scripts/treino/conftest.py scripts/treino/corrupt.py scripts/treino/test_corrupt.py
git commit -m "feat(treino): assets + transforms de corrupção (mockup)"
```

---

### Task 2: `gerar_dataset` — níveis cumulativos

**Files:**
- Create: `scripts/treino/mockup.py`
- Test: `scripts/treino/test_mockup.py`

**Interfaces:**
- Consumes: transforms de Task 1.
- Produces: `corromper(texto: str, nivel: int, rng) -> str` (aplica as classes cumulativas até `nivel`); `gerar_dataset(pares: list[tuple[str,str]], niveis=(1,2,3,4,5), n_variantes=3, seed=0) -> list[tuple[str,str,int]]` → `(texto, sigla, nivel)`. `pares` = `(descricao_padrao, sigla)` da V2.

- [ ] **Step 1: Write the failing test**

```python
# scripts/treino/test_mockup.py
from mockup import corromper, gerar_dataset

PARES = [("CORRENTE FASE A", "IA"), ("87 - PROTECAO DIFERENCIAL", "87"),
         ("DISJUNTOR FASE A", "DJF1"), ("TENSAO FASE B", "VB")]


def test_determinismo_dataset():
    a = gerar_dataset(PARES, seed=7)
    b = gerar_dataset(PARES, seed=7)
    assert a == b
    assert gerar_dataset(PARES, seed=8) != a


def test_rotulo_preservado_e_cobertura():
    ds = gerar_dataset(PARES, n_variantes=2)
    siglas = {sig for _, sig, _ in ds}
    assert siglas == {"IA", "87", "DJF1", "VB"}  # toda sigla aparece
    for _, sig, nivel in ds:
        assert sig in siglas and 1 <= nivel <= 5


def test_monotonicidade_sobreposicao():
    # sobreposição média de tokens c/ o padrão decresce do nível 1 ao 5
    def overlap(nivel):
        tot = 0
        for desc, _ in PARES:
            base = set(desc.upper().split())
            c = set(corromper(desc, nivel, __import__("random").Random(1)).upper().split())
            tot += len(base & c) / max(1, len(base))
        return tot / len(PARES)
    assert overlap(1) >= overlap(5)
    assert overlap(5) < overlap(1)  # nível 5 perde mais


def test_nivel4_tem_ansi_parens_quando_aplicavel():
    out = corromper("87 - PROTECAO DIFERENCIAL", 4, __import__("random").Random(0))
    assert "(87)" in out or len(out.split()) < 3  # virou código ou perdeu tokens
```

- [ ] **Step 2: Run → FAIL** (`ModuleNotFoundError: mockup`).

- [ ] **Step 3: Implement**

```python
# scripts/treino/mockup.py
"""Gera dataset rotulado de descrições corrompidas em 5 níveis cumulativos."""
from __future__ import annotations
import random
from corrupt import (_abreviar, _sinonimo, _reordenar, _ruido_equip,
                     _sufixo_estado, _remover_tokens, _ansi_parens, _typo)

# classe nova introduzida em cada nível (cumulativo)
_CLASSES = {
    2: [_abreviar, _sinonimo],
    3: [_reordenar, _ruido_equip, _sufixo_estado],
    4: [_remover_tokens, _ansi_parens, _typo],
    5: [_remover_tokens, _ruido_equip, _typo, _reordenar],  # agressivo
}


def _norm_trivial(texto: str) -> str:
    return " ".join(texto.split()).strip()


def corromper(texto: str, nivel: int, rng: random.Random) -> str:
    out = _norm_trivial(texto)
    for n in range(2, nivel + 1):
        for fn in _CLASSES.get(n, ()):
            out = fn(out, rng)
    return _norm_trivial(out)


def gerar_dataset(pares, niveis=(1, 2, 3, 4, 5), n_variantes=3, seed=0):
    ds: list[tuple[str, str, int]] = []
    for desc, sigla in pares:
        for nivel in niveis:
            for v in range(n_variantes):
                rng = random.Random(hash((sigla, nivel, v, seed)) & 0xFFFFFFFF)
                ds.append((corromper(desc, nivel, rng), sigla, nivel))
    return ds
```

- [ ] **Step 4: Run → PASS** (`PYTHONPATH=scripts/treino:scripts/enriquecer_v5:src python -m pytest scripts/treino/test_mockup.py -v`).

- [ ] **Step 5: Commit**
```bash
git add scripts/treino/mockup.py scripts/treino/test_mockup.py
git commit -m "feat(treino): gerar_dataset níveis cumulativos (mockup)"
```

---

### Task 3: Dump de inspeção a partir da V2 + amostra revisada

**Files:**
- Create: `scripts/treino/dump_mockup.py`
- Test: (manual) — gera CSV e revisa amostra

**Interfaces:**
- Consumes: `gerar_dataset` (Task 2); `tdt.dados.lista_padrao.ListaPadraoADMS`.

- [ ] **Step 1: Implement o dump**

```python
# scripts/treino/dump_mockup.py
"""Lê a V2, gera o mockup e grava CSV de inspeção (não usado em runtime)."""
from __future__ import annotations
import csv
from tdt.dados.lista_padrao import ListaPadraoADMS
from mockup import gerar_dataset

V2 = "docs/Pontos Padrao ADMS_v2.xlsx"
OUT = "docs/mockup_treino_amostra.csv"


def main():
    lp = ListaPadraoADMS.carregar(V2)
    pares = [(s.descricao, s.sigla) for s in (*lp.discretos, *lp.analogicos) if s.descricao]
    ds = gerar_dataset(pares, n_variantes=2, seed=0)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["texto", "sigla", "nivel"]); w.writerows(ds)
    print(f"{len(ds)} pares de {len(pares)} sinais -> {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar e inspecionar**
Run: `PYTHONPATH=scripts/treino:scripts/enriquecer_v5:src python scripts/treino/dump_mockup.py`
Expected: imprime contagem e cria `docs/mockup_treino_amostra.csv`. Abrir uma amostra: confirmar que níveis 1-2 ainda casam visualmente com a sigla e nível 5 é claramente degradado, sem rótulo errado.

- [ ] **Step 3: Commit**
```bash
git add scripts/treino/dump_mockup.py docs/mockup_treino_amostra.csv
git commit -m "feat(treino): dump de inspeção do mockup a partir da V2"
```

---

## Self-Review (preenchido)

- **Cobertura:** 5 níveis cumulativos (Task 2 `_CLASSES`) ✓; determinismo (seed → idêntico, testado) ✓; rótulo preservado + cobertura de todos os sinais (Task 2 teste) ✓; monotonicidade testada ✓; reuso de `ABREVIACOES_PADRAO`/`ANSI_C37_2` (Task 1) ✓; fonte V2 (Task 3) ✓; offline/puro ✓; consumo pela spec E = `gerar_dataset` em memória (combinar c/ `bench/rotulos`).
- **Placeholders:** nenhum; código real em cada passo. Único ponto aberto: PYTHONPATH composto p/ importar `ansi_ref` de outro dir de tooling — resolvido no comando (`scripts/treino:scripts/enriquecer_v5:src`), com fallback documentado (copiar a constante).
- **Tipos:** `corromper(str,int,Random)->str`; `gerar_dataset(list,...)->list[(str,str,int)]`; transforms `(str,Random)->str`. Consistentes entre tasks.
- **Risco:** `_typo`/`_remover_tokens` raramente podem zerar discriminação numa variante — aceitável (é nível adversarial; rótulo preservado); o gate real da spec E é o benchmark, e o mockup sempre entra combinado com `bench/rotulos` real.
