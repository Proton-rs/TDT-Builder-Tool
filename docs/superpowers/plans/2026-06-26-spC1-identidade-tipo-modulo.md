# C1 — Identidade e Tipo do Módulo (núcleo, sem slot) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolver o nome real do módulo a partir do nome da sheet (ex.: `AL FWB15` → `AL15`, `GTD_11` → `AL11`) e classificá-lo num dos 9 tipos conhecidos, gravando `Modulo.nome`/`Modulo.tipo` antes do scoring; módulo não resolvível com confiança vai pra revisão (`modulo_indefinido`).

**Architecture:** Novo módulo puro `src/tdt/identidade_modulo.py` com funções determinísticas (regex + tabelas em `config.py`). O `pipeline.executar` chama um helper que aplica nome/tipo aos `SignalRecord` de cada sheet, no caminho não-homogêneo, antes do `forcar_polaridade_equipamento`. Sem slot (módulo por linha) — fica em plano de follow-up.

**Tech Stack:** Python 3.14, pytest 9, dataclasses (frozen, `dataclasses.replace`), regex (`re`).

## Global Constraints

- **Sem falsos positivos:** caso ambíguo vai pra revisão, nunca decide errado. Módulo não resolvível ⇒ fallback ao nome cru **e** revisão (`modulo_indefinido`), nunca módulo inventado.
- **Determinístico:** sem LLM (SP2 em espera). Só regras + tabelas.
- **Knobs só em `config.py`**; tipos compartilhados só em `contracts.py`; `pipeline.py` é o único orquestrador que conhece o novo módulo (SRP).
- **Imutabilidade:** `SignalRecord`/`Modulo` são `@dataclass(frozen=True)` — enriquecer com `dataclasses.replace`, nunca mutação in-place.
- **TDD obrigatório:** teste primeiro (RED→GREEN→refactor); 1 `test_*.py` por módulo.
- **Benchmark como gate:** `PYTHONPATH=src python bench/benchmark.py` não pode regredir decisão/FP.
- **DOX:** ao final, atualizar `src/tdt/AGENTS.md` (pipeline ganha passo de identidade) e o índice em `src/tdt/dados/AGENTS.md` se aplicável.

**Fora de escopo (follow-up):** sheets *slot* (módulo por linha) — exige caracterizar `docs/input_nao_homogeneo_3.xlsx` primeiro. `resolver_modulo` já devolve o campo `por_linha` (sempre `None` aqui) para o follow-up preencher sem mudar a assinatura.

---

## File Structure

- **Create** `src/tdt/identidade_modulo.py` — resolução de nome (`resolver_modulo`), classificação de tipo (`classificar_tipo`), aplicação aos registros (`aplicar_identidade`), particionamento por confiança (`particionar_por_confianca`). Conhece só `contracts` + `config`.
- **Modify** `src/tdt/contracts.py` — `Modulo` ganha `tipo`; nova constante `TIPOS_MODULO`.
- **Modify** `src/tdt/config.py` — tabelas `mapa_prefixo_modulo`, `tipo_por_prefixo`, `palavras_chave_tipo`.
- **Modify** `src/tdt/pipeline.py` — chamar `aplicar_identidade` + `particionar_por_confianca` no laço de sheets (caminho não-homogêneo).
- **Create** `tests/test_identidade_modulo.py` — todos os testes unitários deste plano.

---

### Task 1: Contrato — `Modulo.tipo` + `TIPOS_MODULO`

**Files:**
- Modify: `src/tdt/contracts.py:12-15` (dataclass `Modulo`)
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Produces: `Modulo(nome, origem_contexto, tipo=None)`; `contracts.TIPOS_MODULO: tuple[str, ...]` (9 itens).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_identidade_modulo.py
from tdt.contracts import Modulo, TIPOS_MODULO


def test_modulo_tem_campo_tipo_default_none():
    m = Modulo("AL15", "sheet_name")
    assert m.tipo is None
    m2 = Modulo("AL15", "sheet_name", tipo="Alimentador")
    assert m2.tipo == "Alimentador"


def test_tipos_modulo_tem_nove_categorias():
    assert "Alimentador" in TIPOS_MODULO
    assert "Outros" in TIPOS_MODULO
    assert len(TIPOS_MODULO) == 9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -v`
Expected: FAIL — `ImportError: cannot import name 'TIPOS_MODULO'` (e/ou `Modulo` sem `tipo`).

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/contracts.py`, alterar a dataclass `Modulo` e adicionar a constante logo abaixo dela:

```python
@dataclass(frozen=True)
class Modulo:
    nome: str | None
    origem_contexto: str  # "sheet_name" | "linha" | "coluna:<x>"
    tipo: str | None = None  # um de TIPOS_MODULO, ou None até classificar


TIPOS_MODULO: tuple[str, ...] = (
    "Alimentador",
    "Linha de Transmissão",
    "Banco de Capacitores",
    "Alta do Transformador",
    "Baixa do Transformador",
    "Transformador",
    "Barra",
    "Transferência",
    "Outros",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/contracts.py tests/test_identidade_modulo.py
git commit -m "feat(contracts): Modulo.tipo + TIPOS_MODULO (C1)"
```

---

### Task 2: Config — tabelas de prefixo e tipo

**Files:**
- Modify: `src/tdt/config.py:74-76` (final da dataclass `Config`)
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Produces: `Config.mapa_prefixo_modulo: dict[str,str]`, `Config.tipo_por_prefixo: dict[str,str]`, `Config.palavras_chave_tipo: dict[str, tuple[str, ...]]`.

> Valores são **sementes** — confirmar contra os inputs reais (`docs/input_*.xlsx`) durante a Task 6; ajustar as tabelas, não o código.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_identidade_modulo.py (append)
from tdt.config import Config


def test_config_tem_tabelas_de_modulo():
    cfg = Config()
    assert cfg.mapa_prefixo_modulo["GTD"] == "AL"
    assert cfg.mapa_prefixo_modulo["FWB"] == "AL"
    assert cfg.tipo_por_prefixo["AL"] == "Alimentador"
    assert "CAPACITOR" in cfg.palavras_chave_tipo["Banco de Capacitores"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py::test_config_tem_tabelas_de_modulo -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'mapa_prefixo_modulo'`.

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/config.py`, dentro da dataclass `Config` (após `gaps_por_confianca`):

```python
    # Identidade do módulo (C1) — sementes calibráveis; confirmar nos inputs.
    mapa_prefixo_modulo: dict[str, str] = field(
        default_factory=lambda: {
            "AL": "AL", "GTD": "AL", "FWB": "AL",
            "LT": "LT", "BC": "BC", "TR": "TR",
        }
    )
    tipo_por_prefixo: dict[str, str] = field(
        default_factory=lambda: {
            "AL": "Alimentador",
            "LT": "Linha de Transmissão",
            "BC": "Banco de Capacitores",
            "TR": "Transformador",
        }
    )
    palavras_chave_tipo: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "Banco de Capacitores": ("CAPACITOR", "BANCO"),
            "Linha de Transmissão": ("LINHA",),
            "Transformador": ("TRANSFORMADOR", "TRAFO"),
            "Barra": ("BARRA",),
            "Transferência": ("TRANSFERENCIA",),
        }
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py::test_config_tem_tabelas_de_modulo -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/config.py tests/test_identidade_modulo.py
git commit -m "feat(config): tabelas de prefixo/tipo de módulo (C1)"
```

---

### Task 3: `resolver_modulo` — nome real (não-slot)

**Files:**
- Create: `src/tdt/identidade_modulo.py`
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Consumes: `Config.mapa_prefixo_modulo` (Task 2).
- Produces: `ResolucaoModulo(nome: str, confianca: str, por_linha: dict[int,str] | None = None)`; `resolver_modulo(sheet_name: str, rows: list[tuple], config: Config) -> ResolucaoModulo`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_identidade_modulo.py (append)
from tdt.identidade_modulo import resolver_modulo


def test_resolver_modulo_prefixo_e_numero():
    cfg = Config()
    assert resolver_modulo("AL FWB15", [], cfg).nome == "AL15"
    assert resolver_modulo("GTD_11", [], cfg).nome == "AL11"
    assert resolver_modulo("AL FWB15", [], cfg).confianca == "alta"


def test_resolver_modulo_sem_numero_cai_em_baixa_confianca():
    cfg = Config()
    r = resolver_modulo("SLOT GERAL", [], cfg)
    assert r.confianca == "baixa"
    assert r.nome == "SLOT GERAL"  # fallback ao nome cru
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k resolver -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tdt.identidade_modulo'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/tdt/identidade_modulo.py
"""Identidade e tipo do módulo (determinístico).

Resolve o nome real do módulo a partir do nome da sheet (prefixo canônico +
número) e classifica num de TIPOS_MODULO. Funções puras; tabelas vêm de
config. Sheets slot (módulo por linha) ficam para o follow-up — `por_linha`
já existe na assinatura, sempre None aqui.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from tdt.config import Config
from tdt.contracts import ItemRevisao, SignalRecord

_TOKENS = re.compile(r"[A-Za-z]+|\d+")


def _tokens(s: str) -> list[str]:
    return _TOKENS.findall(s.upper())


@dataclass(frozen=True)
class ResolucaoModulo:
    nome: str
    confianca: str  # "alta" | "baixa"
    por_linha: dict[int, str] | None = None  # slot (follow-up); None aqui


def resolver_modulo(sheet_name: str, rows: list[tuple], config: Config) -> ResolucaoModulo:
    toks = _tokens(sheet_name)
    numeros = [t for t in toks if t.isdigit()]
    alphas = [t for t in toks if t.isalpha()]
    prefixo = next(
        (config.mapa_prefixo_modulo[a] for a in alphas if a in config.mapa_prefixo_modulo),
        None,
    )
    if prefixo and numeros:
        return ResolucaoModulo(nome=f"{prefixo}{numeros[0]}", confianca="alta")
    return ResolucaoModulo(nome=sheet_name, confianca="baixa")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k resolver -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/identidade_modulo.py tests/test_identidade_modulo.py
git commit -m "feat(identidade_modulo): resolver_modulo nome real (C1)"
```

---

### Task 4: `classificar_tipo` — cascata prefixo→conteúdo→Outros

**Files:**
- Modify: `src/tdt/identidade_modulo.py`
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Consumes: `Config.tipo_por_prefixo`, `Config.palavras_chave_tipo` (Task 2); `SignalRecord.descricoes.normalizada`.
- Produces: `classificar_tipo(modulo_nome: str, registros: list[SignalRecord], config: Config) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_identidade_modulo.py (append)
from tdt.identidade_modulo import classificar_tipo
from tdt.contracts import Modulo, TipoSinal, Enderecamento, Descricoes, SignalRecord


def _rec(norm: str) -> SignalRecord:
    return SignalRecord(
        id="t:1",
        modulo=Modulo("X", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", ()),
        descricoes=Descricoes(norm, norm),
    )


def test_classificar_por_prefixo():
    assert classificar_tipo("AL15", [], Config()) == "Alimentador"


def test_classificar_por_conteudo_quando_prefixo_desconhecido():
    recs = [_rec("BANCO CAPACITOR FASE A")]
    assert classificar_tipo("XYZ9", recs, Config()) == "Banco de Capacitores"


def test_classificar_fallback_outros():
    assert classificar_tipo("ZZZ1", [_rec("SINAL GENERICO")], Config()) == "Outros"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k classificar -v`
Expected: FAIL — `ImportError: cannot import name 'classificar_tipo'`.

- [ ] **Step 3: Write minimal implementation**

Adicionar em `src/tdt/identidade_modulo.py`:

```python
def classificar_tipo(modulo_nome: str, registros: list[SignalRecord], config: Config) -> str:
    # 1. por prefixo do nome do módulo
    for tok in _tokens(modulo_nome):
        if tok in config.tipo_por_prefixo:
            return config.tipo_por_prefixo[tok]
    # 2. por conteúdo (palavras-chave nas descrições normalizadas)
    texto = " ".join(r.descricoes.normalizada for r in registros).upper()
    for tipo, palavras in config.palavras_chave_tipo.items():
        if any(p in texto for p in palavras):
            return tipo
    # 3. fallback
    return "Outros"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k classificar -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/identidade_modulo.py tests/test_identidade_modulo.py
git commit -m "feat(identidade_modulo): classificar_tipo cascata (C1)"
```

---

### Task 5: `aplicar_identidade` — grava nome/tipo nos registros

**Files:**
- Modify: `src/tdt/identidade_modulo.py`
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Consumes: `resolver_modulo` (Task 3), `classificar_tipo` (Task 4).
- Produces: `aplicar_identidade(sinais: list[SignalRecord], sheet_name: str, rows: list[tuple], config: Config) -> tuple[list[SignalRecord], str]` — devolve `(registros_atualizados, confianca)`. Só sobrescreve `nome` quando `origem_contexto == "sheet_name"` (preserva módulo vindo de coluna no caminho homogêneo); sempre preenche `tipo`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_identidade_modulo.py (append)
from tdt.identidade_modulo import aplicar_identidade


def test_aplicar_identidade_sobrescreve_nome_de_sheet_e_classifica():
    sinais = [_rec("DISJUNTOR LIGADO")]  # _rec usa Modulo("X","sheet_name")
    novos, conf = aplicar_identidade(sinais, "AL FWB15", [], Config())
    assert novos[0].modulo.nome == "AL15"
    assert novos[0].modulo.tipo == "Alimentador"
    assert conf == "alta"


def test_aplicar_identidade_preserva_nome_de_coluna():
    base = _rec("DISJUNTOR")
    base = base.__class__(**{**base.__dict__, "modulo": Modulo("AL11", "coluna:MODULO")})
    novos, _ = aplicar_identidade([base], "GTD_11", [], Config())
    assert novos[0].modulo.nome == "AL11"  # não sobrescreve módulo de coluna
    assert novos[0].modulo.tipo == "Alimentador"  # mas classifica o tipo
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k aplicar -v`
Expected: FAIL — `ImportError: cannot import name 'aplicar_identidade'`.

- [ ] **Step 3: Write minimal implementation**

Adicionar em `src/tdt/identidade_modulo.py`:

```python
def aplicar_identidade(
    sinais: list[SignalRecord], sheet_name: str, rows: list[tuple], config: Config
) -> tuple[list[SignalRecord], str]:
    res = resolver_modulo(sheet_name, rows, config)
    # nome: resolve só onde veio do nome da sheet; preserva módulo de coluna.
    com_nome = [
        replace(s, modulo=replace(s.modulo, nome=res.nome))
        if s.modulo.origem_contexto == "sheet_name"
        else s
        for s in sinais
    ]
    nome_ref = com_nome[0].modulo.nome if com_nome else res.nome
    tipo = classificar_tipo(nome_ref or "", com_nome, config)
    com_tipo = [replace(s, modulo=replace(s.modulo, tipo=tipo)) for s in com_nome]
    # confiança só importa quando o nome veio da sheet (caminho não-homogêneo).
    veio_de_sheet = any(s.modulo.origem_contexto == "sheet_name" for s in sinais)
    return com_tipo, (res.confianca if veio_de_sheet else "alta")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k aplicar -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/identidade_modulo.py tests/test_identidade_modulo.py
git commit -m "feat(identidade_modulo): aplicar_identidade grava nome/tipo (C1)"
```

---

### Task 6: `particionar_por_confianca` + integração no pipeline

**Files:**
- Modify: `src/tdt/identidade_modulo.py`
- Modify: `src/tdt/pipeline.py:300-305` (após montar `sinais`, antes de `forcar_polaridade_equipamento`)
- Modify: `src/tdt/AGENTS.md` (documentar o novo passo de identidade)
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Consumes: `aplicar_identidade` (Task 5); `contracts.ItemRevisao`.
- Produces: `particionar_por_confianca(sinais: list[SignalRecord], confianca: str) -> tuple[list[SignalRecord], list[ItemRevisao]]` — confiança `"baixa"` ⇒ todos viram `ItemRevisao(motivo="modulo_indefinido")` (não seguem para classificação); `"alta"` ⇒ passam adiante.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_identidade_modulo.py (append)
from tdt.identidade_modulo import particionar_por_confianca


def test_particionar_baixa_vai_tudo_pra_revisao():
    sinais = [_rec("SINAL A"), _rec("SINAL B")]
    segue, revisao = particionar_por_confianca(sinais, "baixa")
    assert segue == []
    assert [it.motivo for it in revisao] == ["modulo_indefinido", "modulo_indefinido"]


def test_particionar_alta_segue_adiante():
    sinais = [_rec("SINAL A")]
    segue, revisao = particionar_por_confianca(sinais, "alta")
    assert segue == sinais
    assert revisao == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k particionar -v`
Expected: FAIL — `ImportError: cannot import name 'particionar_por_confianca'`.

- [ ] **Step 3: Write minimal implementation (helper)**

Adicionar em `src/tdt/identidade_modulo.py`:

```python
def particionar_por_confianca(
    sinais: list[SignalRecord], confianca: str
) -> tuple[list[SignalRecord], list[ItemRevisao]]:
    if confianca == "baixa":
        return [], [ItemRevisao(s, motivo="modulo_indefinido") for s in sinais]
    return sinais, []
```

- [ ] **Step 4: Run helper test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k particionar -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Wire into the pipeline**

Em `src/tdt/pipeline.py`, adicionar o import no topo (junto dos demais `from tdt import ...`):

```python
from tdt.identidade_modulo import aplicar_identidade, particionar_por_confianca
```

No laço `for sn in rota.sheets_dados:`, logo após o bloco `if header_homog ... else ...` que monta `sinais` e **antes** de `sinais = forcar_polaridade_equipamento(sinais, config)`, inserir:

```python
        rows_atuais = rows  # rows já foi lido acima por ler_rows(wb_in[sn])
        sinais, conf_mod = aplicar_identidade(sinais, sn, rows_atuais, config)
        sinais, rev_modulo = particionar_por_confianca(sinais, conf_mod)
        if rev_modulo:
            aud.evento("identidade_modulo",
                       f"Sheet {sn}: módulo indefinido — {len(rev_modulo)} sinais p/ revisão", "AVISO")
            revisao.extend(rev_modulo)
```

(`sinais` segue para `forcar_polaridade_equipamento` e o laço de classificação como antes; quando `conf_mod=="baixa"`, `sinais` fica vazio e o laço não processa nada daquela sheet.)

- [ ] **Step 6: Run the full suite + benchmark gate**

Run: `PYTHONPATH=src python -m pytest -q`
Expected: PASS (incluindo os testes existentes do pipeline).

Run: `PYTHONPATH=src python bench/benchmark.py`
Expected: taxa de decisão e FP **iguais ou melhores** que o baseline (módulos resolvidos ajudam as regras de equipamento/contexto). Se piorar, revisar as tabelas-semente da Task 2 contra os inputs reais (`docs/input_nao_homogeneo_1.xlsx`, `_3.xlsx`).

- [ ] **Step 7: DOX — atualizar o contrato do pipeline**

Em `src/tdt/AGENTS.md`, no parágrafo do fluxo do pipeline (`Fluxo pipeline:`), inserir o passo de identidade após a montagem dos sinais e antes de `pareamento_polaridade`. Exemplo de texto a acrescentar:

> `… → estruturador/estruturador_homogeneo → identidade_modulo (resolve nome real do módulo p/ sheets não-homogêneas via prefixo+número de config; classifica Modulo.tipo; confiança baixa ⇒ revisão modulo_indefinido) → pareamento_polaridade → …`

E no parágrafo `Módulos:` listar `identidade_modulo.py` (resolução/classificação de módulo, determinístico).

- [ ] **Step 8: Commit**

```bash
git add src/tdt/identidade_modulo.py src/tdt/pipeline.py src/tdt/AGENTS.md tests/test_identidade_modulo.py
git commit -m "feat(pipeline): integra identidade/tipo de módulo (C1)"
```

---

## Self-Review (preenchido)

- **Cobertura do spec C1 (núcleo):** C1.1 nome real (Tasks 3) ✓; C1.2 classificar tipo (Task 4) ✓; C1.3 integração no pipeline (Task 6) ✓; contrato `Modulo.tipo`/`TIPOS_MODULO` (Task 1) ✓; `modulo_indefinido` → revisão (Task 6) ✓. **Gap deliberado:** C1.1 *slot* (módulo por linha) → follow-up (assinatura `por_linha` já preparada).
- **Placeholders:** nenhum — todo passo traz código real e comando com saída esperada.
- **Consistência de tipos:** `resolver_modulo`→`ResolucaoModulo`; `aplicar_identidade`→`(list, str)`; `particionar_por_confianca`→`(list, list[ItemRevisao])`; nomes batem entre tasks.
- **Motivo de revisão:** `"modulo_indefinido"` é novo; é só um rótulo livre em `ItemRevisao.motivo` (string), não precisa registro — mas convém adicionar ao `_MOTIVO_LABEL` da UI (`ui/modelo_tabela.py`) num passo futuro da spec A para exibir bonito (fora do escopo deste plano; a UI já mostra `—` para motivos desconhecidos sem quebrar).
