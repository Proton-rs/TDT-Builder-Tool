# SP-Pendencias-09jul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar as 9 pendências de uso real: alias YYYYMMDD, KMDF→Unitless, nome de arquivo com SUB+data+seq, número do módulo no path homogêneo, diagnóstico de pendentes, aba DiscreteAnalog/TAP na lista padrão + pipeline, startup lento, auto-tuning de pesos.

**Architecture:** Fixes cirúrgicos em `engine_tdt.py`/`tela_geracao.py`/`relatorio_revisao.py` (Fase 1); parser do bloco NÚMERO OPERATIVO em `estruturador_homogeneo.py` (Fase 2); lista padrão v7 com aba nova + leitura em `lista_padrao.py` + sheet nova no `engine_tdt.py` + gate (Fase 3); diagnóstico de boot em `ui_main.py` (Fase 4); `bench/tune_pesos.py` estendendo a montagem de `bench/exp_pesos.py` (Fase 5).

**Tech Stack:** Python 3.14, openpyxl, PySide6, pytest, sklearn/faiss/rapidfuzz (já instalados).

**Spec:** `docs/superpowers/specs/2026-07-09-sp-pendencias-09jul-design.md`

## Global Constraints

- Formato de data em TODO lugar novo: `YYYYMMDD` (`%Y%m%d`).
- Nome dos arquivos: `TDT_<SUB>_<YYYYMMDD>.xlsx` / `Auditoria_<SUB>_<YYYYMMDD>.xlsx`; colisão → sufixo `_v2`, `_v3`...; sem subestação → omite o segmento, nunca quebra.
- Nunca escrever valor fora do domínio ADMS (`DMSMatchingTemplateInfo`) — sem equivalente confirmado, deixar vazio.
- Regressão: `bench/regressao.py` (gate + casos travados) precisa passar ao fim de cada fase.
- Rodar testes com `PYTHONPATH=src` a partir da raiz do repo (padrão do projeto: `python -m pytest`).
- Mensagens de commit em PT, formato conventional commits, com `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

## Fase 1 — Fixes rápidos

### Task 1: Remote Point Alias em YYYYMMDD

**Files:**
- Modify: `src/tdt/engine_tdt.py:110-111` (`_alias_hoje`)
- Test: `tests/test_engine_tdt.py` (arquivo existente; adicionar teste — se o nome real do arquivo de testes do engine for outro, `grep -l "_alias_hoje\|engine_tdt" tests/` e usar esse)

**Interfaces:**
- Produces: `_alias_hoje() -> str` retornando `date.today().strftime("%Y%m%d")` (ex. `"20260709"`).

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
from tdt.engine_tdt import _alias_hoje

def test_alias_hoje_formato_yyyymmdd():
    # TDT real (GTD DNP3_DiscreteAnalog) usa 20260204 — YYYYMMDD
    assert _alias_hoje() == date.today().strftime("%Y%m%d")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_engine_tdt.py::test_alias_hoje_formato_yyyymmdd -v`
Expected: FAIL (retorna `%m%d%Y`, ex. `07092026`)

- [ ] **Step 3: Fix**

Em `src/tdt/engine_tdt.py`:

```python
def _alias_hoje() -> str:
    return date.today().strftime("%Y%m%d")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_engine_tdt.py -v`
Expected: PASS (suite inteira do arquivo, não só o teste novo — alias aparece em `_valores` e `_valores_analog`)

- [ ] **Step 5: Commit**

```bash
git add -A tests src/tdt/engine_tdt.py
git commit -m "fix(engine): Remote Point Alias em YYYYMMDD (padrao do TDT real)"
```

### Task 2: KMDF → Unitless + auditoria dos tipos de medição sem tradução

**Files:**
- Modify: `src/tdt/engine_tdt.py:198-204` (`_MEASUREMENT_TYPE_PT_EN`)
- Test: mesmo arquivo de testes da Task 1

**Interfaces:**
- Consumes: `_measurement_type(sp)` (existente, não muda assinatura).
- Produces: tabela `_MEASUREMENT_TYPE_PT_EN` ampliada; chave `"COMPRIMENTO"` → `"Unitless"`.

- [ ] **Step 1: Levantar o domínio MeasurementType do template**

Run:
```bash
python - <<'EOF'
import openpyxl
wb = openpyxl.load_workbook('docs/dnp3_template.xlsx', read_only=True, data_only=True)
ws = wb['DMSMatchingTemplateInfo']
# dump das colunas de dominio; procurar a lista de MeasurementType validos
for row in ws.iter_rows(values_only=True):
    vals = [v for v in row if v is not None]
    if vals: print(vals)
wb.close()
EOF
```
Anotar os valores válidos do domínio MeasurementType (esperados: Current, Voltage, ActivePower, ReactivePower, Temperature, Unitless, Frequency, PowerFactor, ApparentPower, ...).

- [ ] **Step 2: Write the failing test**

```python
from tdt.engine_tdt import _measurement_type
from tdt.dados.lista_padrao import SinalPadrao

def _sp(tipo):
    return SinalPadrao(sigla="X", descricao="d", signal_type="MeasuredValue",
                       direction=None, mm=None, categoria="Analog", tipo_medicao=tipo)

def test_kmdf_comprimento_vira_unitless():
    assert _measurement_type(_sp("Comprimento")) == "Unitless"

def test_todos_tipos_da_lista_padrao_v6_tem_traducao():
    # tipos reais da lista padrao v6 (auditoria 09jul)
    tipos = ["Corrente", "Tensão", "Potência Ativa", "Potência Reativa",
             "Temperatura", "Comprimento", "Frequência", "Fator de Potência",
             "Potência Aparente"]
    sem = [t for t in tipos if _measurement_type(_sp(t)) is None]
    assert sem == [], f"tipos sem traducao: {sem}"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_engine_tdt.py -k "kmdf or traducao" -v`
Expected: FAIL (Comprimento/Frequência/etc. não estão na tabela)

- [ ] **Step 4: Ampliar a tabela**

```python
_MEASUREMENT_TYPE_PT_EN: dict[str, str] = {
    "CORRENTE": "Current",
    "TENSÃO": "Voltage",
    "POTÊNCIA ATIVA": "ActivePower",
    "POTÊNCIA REATIVA": "ReactivePower",
    "TEMPERATURA": "Temperature",
    # auditoria 09jul (lista padrao v6) — valores confirmados no domínio
    # MeasurementType do DMSMatchingTemplateInfo:
    "COMPRIMENTO": "Unitless",  # KMDF: distância de defeito é unitless no ADMS
    "FREQUÊNCIA": "Frequency",
    "FATOR DE POTÊNCIA": "PowerFactor",
    "POTÊNCIA APARENTE": "ApparentPower",
}
```

⚠️ Os 3 últimos valores EN acima são hipótese: **confirmar no dump do Step 1** e usar o
nome exato do domínio. `Ângulo de Tensão`, `Umidade` e `Discreto`: incluir **somente** se
o domínio tiver equivalente inequívoco; senão deixar fora (Measurement Type vazio) e
remover esses tipos do teste `test_todos_tipos...` com comentário do porquê.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_engine_tdt.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add -A tests src/tdt/engine_tdt.py
git commit -m "fix(engine): KMDF->Unitless e traducoes de measurement type faltantes"
```

### Task 3: Nome dos arquivos com subestação + data + sequência

**Files:**
- Create: `src/tdt/nomes_saida.py`
- Modify: `src/tdt/ui/tela_geracao.py:186-205` (`_gerar`)
- Modify: `src/tdt/relatorio_revisao.py:97-135` (`gerar_relatorio_revisao`)
- Test: `tests/test_nomes_saida.py`

**Interfaces:**
- Produces: `nome_saida(prefixo: str, subestacao: str | None, pasta: str | Path, ext: str = ".xlsx") -> Path` — caminho livre de colisão (`_v2`, `_v3`...).
- `gerar_relatorio_revisao(...)` ganha kwarg `subestacao: str | None = None`; retorno continua `Path` (agora com nome novo).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_nomes_saida.py
from datetime import date
from tdt.nomes_saida import nome_saida

HOJE = date.today().strftime("%Y%m%d")

def test_nome_com_subestacao(tmp_path):
    assert nome_saida("TDT", "GAU", tmp_path).name == f"TDT_GAU_{HOJE}.xlsx"

def test_nome_sem_subestacao(tmp_path):
    assert nome_saida("TDT", None, tmp_path).name == f"TDT_{HOJE}.xlsx"

def test_sequencia_quando_existe(tmp_path):
    (tmp_path / f"TDT_GAU_{HOJE}.xlsx").touch()
    assert nome_saida("TDT", "GAU", tmp_path).name == f"TDT_GAU_{HOJE}_v2.xlsx"
    (tmp_path / f"TDT_GAU_{HOJE}_v2.xlsx").touch()
    assert nome_saida("TDT", "GAU", tmp_path).name == f"TDT_GAU_{HOJE}_v3.xlsx"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_nomes_saida.py -v`
Expected: FAIL (`ModuleNotFoundError: tdt.nomes_saida`)

- [ ] **Step 3: Implement `src/tdt/nomes_saida.py`**

```python
"""Nomeação dos arquivos gerados: <prefixo>_<SUB>_<YYYYMMDD>[_vN].ext.

Sem subestação o segmento é omitido — a geração nunca quebra por falta de sigla.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path


def nome_saida(prefixo: str, subestacao: str | None,
               pasta: str | Path, ext: str = ".xlsx") -> Path:
    base = "_".join(p for p in (prefixo, subestacao, date.today().strftime("%Y%m%d")) if p)
    caminho = Path(pasta) / f"{base}{ext}"
    v = 2
    while caminho.exists():
        caminho = Path(pasta) / f"{base}_v{v}{ext}"
        v += 1
    return caminho
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_nomes_saida.py -v`
Expected: PASS

- [ ] **Step 5: Usar o helper na geração e no relatório**

Em `src/tdt/relatorio_revisao.py` (import no topo: `from tdt.nomes_saida import nome_saida`), adicionar kwarg e trocar a linha 133:

```python
def gerar_relatorio_revisao(
    registros: list[SignalRecord],
    revisao: tuple[ItemRevisao, ...],
    destino: str | Path,
    diagnostico: "dict[str, dict] | None" = None,
    subestacao: str | None = None,
) -> Path:
    ...
    saida = nome_saida("Auditoria", subestacao, destino)
    wb.save(str(saida))
    return saida
```

Em `src/tdt/ui/tela_geracao.py::_gerar` (import no topo: `from tdt.nomes_saida import nome_saida`):

```python
        out_path = nome_saida("TDT", self._estado.subestacao, output)
        # nome com sequência não colide; manter o confirm só por corrida
        if out_path.exists() and not self._confirmar(
                "Sobrescrever", f"{out_path} já existe. Sobrescrever?"):
            return
        ...
            aud_path = gerar_relatorio_revisao(
                self._estado.registros, revisao, output, diagnostico=diag,
                subestacao=self._estado.subestacao)
            self.lbl_resultado.setText(
                f"TDT gerado:\n{out_path}\n{aud_path}")
```

(Nota: `gerar_relatorio_revisao` é chamado ANTES do `setText`; reordenar o bloco atual
para capturar `aud_path` — hoje o caminho da auditoria é hardcoded no label, linha 205.)

- [ ] **Step 6: Atualizar chamadores existentes**

Run: `grep -rn "gerar_relatorio_revisao\|/ \"TDT.xlsx\"\|Auditoria_Revisao" src tests bench scripts`
Ajustar todo chamador/asserção que espera `TDT.xlsx`/`Auditoria_Revisao.xlsx` fixos
(kwarg nova é opcional — chamador sem sigla continua funcionando, só muda o nome do
arquivo pra `Auditoria_<data>.xlsx`; testes que asserem o nome antigo mudam pra usar o
`Path` retornado). `bench/reprocessar_lista1.py` salva `TDT.xlsx` direto (linha 42) e o
gate lê esse caminho — **não mudar o bench** (nome fixo é feature lá).

- [ ] **Step 7: Run full test suite**

Run: `python -m pytest tests/ -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add -A src tests
git commit -m "feat(saida): nomes TDT/Auditoria com subestacao+data+sequencia"
```

---

## Fase 2 — Path homogêneo

### Task 4: Número do módulo vem do bloco NÚMERO OPERATIVO

**Files:**
- Modify: `src/tdt/normalizacao/estruturador_homogeneo.py`
- Test: `tests/test_estruturador_homogeneo.py`

**Interfaces:**
- Produces: `extrair_numeros_operativos(rows: list[tuple], header_idx: int) -> dict[str, str]` — mapeia rótulo normalizado (`"MODULO"`, `"DJ"`, `"SECC"`, ...) → número operativo (`"23"`, `"52-23"`, ...), lido de `rows[:header_idx]`.
- `estruturar_homogeneo(...)`: assinatura inalterada; `modulo_nome` composto quando a coluna não traz dígito.

- [ ] **Step 1: Write the failing tests**

Formato real (input homogêneo IMA — bloco acima do cabeçalho):

```python
def _rows_com_bloco(modulo_col="AL", numero="23"):
    return [
        ("MÓDULO - ALIMENTADOR", None, None, None, None, None, None, None, None),
        ("EQUIPAMENTO", "NÚMERO OPERATIVO / MNEMNICO", None, None, None, None, None, None, None),
        ("MÓDULO  ", numero, None, None, None, None, None, None, None),
        ("DJ", "52-23", None, None, None, None, None, None, None),
        ("SECC", "29-62", None, None, None, None, None, None, None),
        ("Utilizado?", "SUBESTAÇÃO", "MÓDULO", "EQUIPAMENTO", "TIPO",
         "DESCRIÇÃO DO PONTO", "SIGLA SINAL", "NOME", "INDEX DNP3"),
        ("SIM", "IMA", modulo_col, "DJ", "S", "DISJUNTOR NF", "DJF1",
         "IMA_AL23_52-23_DJF1", "1"),
    ]

def test_extrai_numeros_operativos_do_bloco():
    from tdt.normalizacao.estruturador_homogeneo import extrair_numeros_operativos
    nums = extrair_numeros_operativos(_rows_com_bloco(), header_idx=5)
    assert nums["MODULO"] == "23"
    assert nums["DJ"] == "52-23"

def test_modulo_compoe_tipo_da_coluna_com_numero_do_bloco(lp, config):
    rows = _rows_com_bloco(modulo_col="AL", numero="23")
    decididos, pendentes = estruturar_homogeneo(rows, 5, "AL23", lp, config)
    rec = (decididos + pendentes)[0]
    assert rec.modulo.nome == "AL23"
    assert "header:NUMERO_OPERATIVO" in rec.modulo.origem_contexto

def test_modulo_coluna_ja_numerada_mantem_comportamento(lp, config):
    rows = _rows_com_bloco(modulo_col="LT 1", numero="99")
    decididos, pendentes = estruturar_homogeneo(rows, 5, "LT1", lp, config)
    rec = (decididos + pendentes)[0]
    assert rec.modulo.nome == "LT 1"          # engine normaliza espaço depois
    assert rec.modulo.origem_contexto == "coluna:MODULO"

def test_bloco_ausente_mantem_comportamento(lp, config):
    rows = _rows_com_bloco()[5:]              # só header + dados
    decididos, pendentes = estruturar_homogeneo(rows, 0, "AL", lp, config)
    rec = (decididos + pendentes)[0]
    assert rec.modulo.nome == "AL"            # não inventa número
    assert rec.modulo.origem_contexto == "coluna:MODULO"
```

(Usar as fixtures `lp`/`config` já existentes em `tests/test_estruturador_homogeneo.py` /
`conftest.py`; se os testes existentes constroem `lp` inline, seguir o padrão local.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_estruturador_homogeneo.py -v`
Expected: FAIL (função não existe; módulo sai `"AL"`)

- [ ] **Step 3: Implement**

Em `estruturador_homogeneo.py`:

```python
_ROTULO_BLOCO = "EQUIPAMENTO"          # 1a celula da linha-titulo do bloco
_COLUNA_NUMERO_BLOCO = 1               # "NÚMERO OPERATIVO / MNEMNICO"


def extrair_numeros_operativos(rows: list[tuple], header_idx: int) -> dict[str, str]:
    """Bloco acima do cabeçalho: EQUIPAMENTO | NÚMERO OPERATIVO / MNEMNICO.

    Devolve rótulo normalizado -> número ("MODULO" -> "23", "DJ" -> "52-23").
    Bloco ausente/ilegível -> {} (chamador não inventa número).
    """
    nums: dict[str, str] = {}
    dentro = False
    for row in rows[:header_idx]:
        rotulo = _normaliza_celula(row[0] if row else None)
        if rotulo == _ROTULO_BLOCO and "OPERATIVO" in _normaliza_celula(
                row[_COLUNA_NUMERO_BLOCO] if len(row) > _COLUNA_NUMERO_BLOCO else None):
            dentro = True
            continue
        if not dentro:
            continue
        if not rotulo:
            dentro = False
            continue
        valor = row[_COLUNA_NUMERO_BLOCO] if len(row) > _COLUNA_NUMERO_BLOCO else None
        if valor is not None and str(valor).strip():
            nums[rotulo] = str(valor).strip()
    return nums
```

Em `estruturar_homogeneo`, antes do loop:

```python
    numeros = extrair_numeros_operativos(rows, header_idx)
    numero_modulo = numeros.get("MODULO")
```

E no lugar da atribuição atual de `modulo_nome` (linha 87) / `Modulo` (linha 99):

```python
        modulo_nome = str(row[idx["modulo"]]) if idx["modulo"] is not None and row[idx["modulo"]] else None
        origem_modulo = "coluna:MODULO"
        if (modulo_nome and numero_modulo
                and not any(ch.isdigit() for ch in modulo_nome)):
            modulo_nome = f"{modulo_nome.strip()}{numero_modulo}"
            origem_modulo = "coluna:MODULO+header:NUMERO_OPERATIVO"
        ...
            modulo=Modulo(modulo_nome, origem_modulo),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_estruturador_homogeneo.py tests/test_pipeline.py -v`
Expected: PASS (incl. testes pré-existentes — coluna já numerada não muda)

- [ ] **Step 5: Commit**

```bash
git add -A src tests
git commit -m "feat(homogeneo): compoe modulo com numero operativo do bloco de header"
```

### Task 5: Diagnóstico dos pendentes no homogêneo (fix condicional)

**Files:**
- Create: `bench/diag_pendentes_homogeneo.py`
- Modify (condicional): `src/tdt/dados/lista_padrao.py` (`por_sigla`) e/ou anotação pra lista v7 (Task 6)

**Interfaces:**
- Consumes: `estruturar_homogeneo` (Task 4), `ListaPadraoADMS.carregar`.
- Produces: relatório `bench/resultados/diag_pendentes_homogeneo.txt` com sigla, contagem, descrição e classificação (a/b/c da spec).

- [ ] **Step 1: Escrever o script de diagnóstico**

```python
"""Lista as siglas do input homogêneo real que caem em pendentes (lp.por_sigla == None).

Uso: PYTHONPATH=src python bench/diag_pendentes_homogeneo.py <input.xlsx> [lista_padrao.xlsx]
"""
import sys
from collections import Counter

import openpyxl

from tdt.config import Config
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.normalizacao.estruturador_homogeneo import detectar_header, estruturar_homogeneo

inp = sys.argv[1]
lp_path = sys.argv[2] if len(sys.argv) > 2 else "docs/Pontos Padrao ADMS_v6.xlsx"
lp = ListaPadraoADMS.carregar(lp_path)
cfg = Config()

wb = openpyxl.load_workbook(inp, read_only=True, data_only=True)
pend = Counter()
exemplos: dict[str, str] = {}
for sn in wb.sheetnames:
    rows = [tuple(r) for r in wb[sn].iter_rows(values_only=True)]
    h = detectar_header(rows)
    if h is None:
        continue
    _, pendentes = estruturar_homogeneo(rows, h, sn, lp, cfg)
    for rec in pendentes:
        sigla = rec.id  # sem sigla decidida; agrupar pela sigla bruta da coluna
        # a sigla bruta esta na descricao? nao: reprocessar a linha
    # simplificação: estruturar_homogeneo não guarda a sigla bruta no rec pendente —
    # ler a coluna SIGLA SINAL direto:
    from tdt.normalizacao.estruturador_homogeneo import _col, _normaliza_celula
    i_sig = _col(rows[h], "SIGLA SINAL")
    i_uso = _col(rows[h], "UTILIZADO?")
    for row in rows[h + 1:]:
        if i_uso is None or i_uso >= len(row) or _normaliza_celula(row[i_uso]) != "SIM":
            continue
        s = str(row[i_sig] or "").strip() if i_sig is not None else ""
        if s and lp.por_sigla(s) is None:
            pend[s] += 1
wb.close()

print(f"{'sigla':<12} n")
for s, n in pend.most_common():
    print(f"{s:<12} {n}")
```

(Se o input homogêneo real não estiver no repo, pedir o caminho ao usuário — o
convertido `graphify-out/converted/input_homogeneo_a72b185b.md` prova que existe um
`input_homogeneo.xlsx`; localizar com `Glob **/input_homogeneo*.xlsx` primeiro.)

- [ ] **Step 2: Rodar e classificar**

Run: `PYTHONPATH=src python bench/diag_pendentes_homogeneo.py <input_homogeneo.xlsx>`
Para cada sigla da saída, classificar:
- (a) sigla legítima ausente da lista padrão → anotar pra entrar na v7 (Task 6);
- (b) variação de grafia (acento/espaço/sufixo) que `por_sigla` deveria casar → fix no
  lookup + teste unitário reproduzindo o caso real;
- (c) desconhecida/ambígua → fica em revisão; documentar no relatório.

Salvar a saída + classificação em `bench/resultados/diag_pendentes_homogeneo.txt`.

- [ ] **Step 3: Aplicar fixes (b), se houver**

Cada fix (b) segue TDD: teste com a sigla real que falhava → fix em `por_sigla`/normalização → suite verde.

- [ ] **Step 4: Commit**

```bash
git add -A bench src tests
git commit -m "diag(homogeneo): siglas pendentes classificadas (+fixes de lookup se houver)"
```

---

## Fase 3 — DiscreteAnalog / TAP

### Task 6: Lista padrão v7 com aba DiscreteAnalog

**Files:**
- Create: `scripts/gerar_lista_v7.py`
- Create (gerado): `docs/Pontos Padrao ADMS_v7.xlsx`
- Modify: `src/tdt/defaults.py` (`DEFAULT_LISTA` → v7)

**Interfaces:**
- Produces: aba `DiscreteAnalog` com header `("SINAL", "DESCRIÇÃO NOVA", "SIGNAL TYPE", "MEASUREMENT TYPE", "FASES", "DIRECTION", "NORMAL VALUE", "REMOTE POINT TYPE", "OUTPUT DATA TYPE", "DEVICE MAPPING REF", "APLICABILIDADE")` e 1 linha TAP.

- [ ] **Step 1: Confirmar a descrição padrão do TAP**

Run: `grep -i "TAP" "docs/conhecimento_sinais.md"` e inspecionar a aba `DE->PARA` da v6:
```bash
python - <<'EOF'
import openpyxl
wb = openpyxl.load_workbook('docs/Pontos Padrao ADMS_v6.xlsx', read_only=True, data_only=True)
for r in wb['DE->PARA'].iter_rows(values_only=True):
    if r[0] and 'TAP' in str(r[0]).upper(): print(r)
wb.close()
EOF
```
Usar a descrição encontrada; se não houver, usar `"Posição do TAP"`.

- [ ] **Step 2: Escrever `scripts/gerar_lista_v7.py`**

```python
"""Gera docs/Pontos Padrao ADMS_v7.xlsx = v6 + aba DiscreteAnalog (TAP).

Valores da linha TAP vêm do TDT real (exportTDT_UTR_GTD_1_20260626.xlsx,
aba DNP3_DiscreteAnalog): SignalType=TapPosition, MeasType=Discrete,
Phases=ABC, Direction=Read, NormalValue=9, RemotePointType=Analog,
deadband Float, DeviceMapping -> <nome>_COMTAP. Só em transformadores.
"""
import shutil

import openpyxl

ORIGEM = "docs/Pontos Padrao ADMS_v6.xlsx"
DESTINO = "docs/Pontos Padrao ADMS_v7.xlsx"

HEADER = ("SINAL", "DESCRIÇÃO NOVA", "SIGNAL TYPE", "MEASUREMENT TYPE", "FASES",
          "DIRECTION", "NORMAL VALUE", "REMOTE POINT TYPE", "OUTPUT DATA TYPE",
          "DEVICE MAPPING REF", "APLICABILIDADE")
TAP = ("TAP", "Posição do TAP", "TapPosition", "Discrete", "ABC",
       "Read", 9, "Analog", "Float", "COMTAP", "TRANSFORMADOR")

shutil.copyfile(ORIGEM, DESTINO)
wb = openpyxl.load_workbook(DESTINO)
ws = wb.create_sheet("DiscreteAnalog", index=2)  # ao lado de Discrete/Analog
ws.append(HEADER)
ws.append(TAP)
wb.save(DESTINO)
print(f"gerado: {DESTINO}")
```

(Ajustar `"Posição do TAP"` pro valor do Step 1.)

- [ ] **Step 3: Rodar e conferir**

Run: `python scripts/gerar_lista_v7.py`
Depois: reabrir o arquivo com openpyxl e assert manual de que as 9 abas antigas + a nova existem e que `DiscreteSignals`/`AnalogSignals` estão intactas (mesmo nº de linhas da v6).

- [ ] **Step 4: Apontar o default pra v7**

Em `src/tdt/defaults.py`, trocar o path de `DEFAULT_LISTA` pra `docs/Pontos Padrao ADMS_v7.xlsx` (conferir o valor atual com `grep -n "DEFAULT_LISTA" src/tdt/defaults.py` — manter o mesmo estilo de path).

- [ ] **Step 5: Commit**

```bash
git add scripts/gerar_lista_v7.py "docs/Pontos Padrao ADMS_v7.xlsx" src/tdt/defaults.py
git commit -m "feat(lista-padrao): v7 com aba DiscreteAnalog (TAP)"
```

### Task 7: `lista_padrao.py` lê a aba DiscreteAnalog

**Files:**
- Modify: `src/tdt/dados/lista_padrao.py`
- Test: `tests/test_lista_padrao.py` (existente; se não existir, criar)

**Interfaces:**
- Produces: `ListaPadraoADMS.discrete_analog: tuple[SinalPadrao, ...]` (novo campo, default `()`); sinais com `categoria="DiscreteAnalog"`; `por_sigla`/`siglas` passam a incluir a categoria nova. `SinalPadrao` ganha campos `normal_value: int | None = None`, `remote_point_type: str | None = None`, `output_data_type: str | None = None`, `device_mapping_ref: str | None = None`, `aplicabilidade: str | None = None` (defaults None — retrocompatível).

- [ ] **Step 1: Write the failing tests**

```python
def test_carrega_aba_discrete_analog():
    lp = ListaPadraoADMS.carregar("docs/Pontos Padrao ADMS_v7.xlsx")
    tap = lp.por_sigla("TAP")
    assert tap is not None
    assert tap.categoria == "DiscreteAnalog"
    assert tap.signal_type == "TapPosition"
    assert tap.normal_value == 9
    assert tap.remote_point_type == "Analog"
    assert tap.device_mapping_ref == "COMTAP"
    assert "TAP" in lp.siglas

def test_lista_v6_sem_aba_nova_carrega_vazio():
    lp = ListaPadraoADMS.carregar("docs/Pontos Padrao ADMS_v6.xlsx")
    assert lp.discrete_analog == ()
    assert lp.por_sigla("TAP") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lista_padrao.py -v`
Expected: FAIL (`discrete_analog` não existe)

- [ ] **Step 3: Implement**

Em `SinalPadrao`, acrescentar os 5 campos novos com default. Em `ListaPadraoADMS`:

```python
@dataclass(frozen=True)
class ListaPadraoADMS:
    discretos: tuple[SinalPadrao, ...]
    analogicos: tuple[SinalPadrao, ...]
    discrete_analog: tuple[SinalPadrao, ...] = ()
```

Em `carregar`, após ler `ana`:

```python
            da: list[SinalPadrao] = []
            if "DiscreteAnalog" in wb.sheetnames:
                da = _ler_sheet_discrete_analog(wb["DiscreteAnalog"])
        finally:
            wb.close()
        return cls(tuple(disc), tuple(ana), tuple(da))
```

Leitor dedicado (colunas fora do shape de `_ler_sheet` — mais simples que
generalizar o mapa):

```python
def _ler_sheet_discrete_analog(ws) -> list[SinalPadrao]:
    linhas = ws.iter_rows(values_only=True)
    header = next(linhas)
    def i(nome): return _coluna(header, nome)
    idx = {n: i(n) for n in ("SINAL", "DESCRIÇÃO NOVA", "SIGNAL TYPE", "FASES",
                             "DIRECTION", "NORMAL VALUE", "REMOTE POINT TYPE",
                             "OUTPUT DATA TYPE", "DEVICE MAPPING REF",
                             "APLICABILIDADE")}
    out: list[SinalPadrao] = []
    for row in linhas:
        def get(nome):
            j = idx[nome]
            return _val(row[j]) if j is not None and j < len(row) else None
        sigla = get("SINAL")
        if sigla is None:
            continue
        nv = get("NORMAL VALUE")
        out.append(SinalPadrao(
            sigla=sigla, descricao=get("DESCRIÇÃO NOVA") or "",
            signal_type=get("SIGNAL TYPE") or "", direction=get("DIRECTION"),
            mm=None, categoria="DiscreteAnalog",
            normal_value=int(nv) if nv is not None else None,
            remote_point_type=get("REMOTE POINT TYPE"),
            output_data_type=get("OUTPUT DATA TYPE"),
            device_mapping_ref=get("DEVICE MAPPING REF"),
            aplicabilidade=get("APLICABILIDADE"),
        ))
    return out
```

E incluir a categoria nova em `por_sigla` e `siglas`:

```python
    def _todos(self):
        return (*self.discretos, *self.analogicos, *self.discrete_analog)
```
(usar `_todos()` nos dois lugares que hoje fazem `(*self.discretos, *self.analogicos)`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lista_padrao.py tests/ -q`
Expected: PASS (suite inteira — `siglas` mudou de conteúdo, atenção a testes que contam siglas)

- [ ] **Step 5: Commit**

```bash
git add -A src tests
git commit -m "feat(lista-padrao): leitura da aba DiscreteAnalog (categoria nova)"
```

### Task 8: Engine gera DNP3_DiscreteAnalog + gate cobre a sheet

**Files:**
- Modify: `src/tdt/engine_tdt.py` (`gerar`, constantes, `_valores_discrete_analog` novo)
- Modify: `bench/gate_tdt_real.py:14` (`_SHEETS`)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `SinalPadrao.categoria == "DiscreteAnalog"`, `device_mapping_ref`, `normal_value`, `remote_point_type` (Task 7).
- Produces: registros cuja sigla decidida é de categoria DiscreteAnalog saem na sheet `DNP3_DiscreteAnalog` do template; demais comportamentos inalterados.

- [ ] **Step 1: Medir o template**

Run:
```bash
python - <<'EOF'
import openpyxl
wb = openpyxl.load_workbook('docs/dnp3_template.xlsx', read_only=True)
ws = wb['DNP3_DiscreteAnalog']
print('max_col:', ws.max_column)
print('row4:', [ws.cell(4, c).value for c in range(1, ws.max_column + 1)])
wb.close()
EOF
```
Anotar `max_column` → vira `COLUNAS_ESPERADAS_DISCRETE_ANALOG`; anotar os display names da row 4 (são as chaves do dict de valores).

- [ ] **Step 2: Write the failing test**

```python
def test_tap_sai_na_sheet_discrete_analog(lista_homogenea_com_tap, lp_v7):
    # fixture: ListaHomogenea com 1 registro sigla=TAP categoria DiscreteAnalog
    # (montar seguindo o padrão das fixtures existentes de gerar())
    wb = gerar(lista_homogenea_com_tap, "docs/dnp3_template.xlsx", lp_v7)
    ws = wb["DNP3_DiscreteAnalog"]
    nomes = [ws.cell(r, 1).value for r in range(5, 7)]
    assert any(n and n.endswith("_TAP") for n in nomes)
    # e NÃO saiu nas outras sheets
    for sn in ("DNP3_DiscreteSignals", "DNP3_AnalogSignals"):
        vals = [wb[sn].cell(5, 1).value]
        assert not any(v and str(v).endswith("_TAP") for v in vals)
```

A categoria do registro: o roteamento em `gerar()` é por `rec.tipo_sinal.categoria`;
para TAP decidir a categoria pelo `SinalPadrao` (não pelo input): rotear primeiro por
sigla → `lista_padrao.por_sigla(sigla).categoria == "DiscreteAnalog"`, senão pela
categoria do registro (comportamento atual).

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_engine_tdt.py -k discrete_analog -v`
Expected: FAIL

- [ ] **Step 4: Implement**

Em `engine_tdt.py`:

```python
SHEET_DISCRETE_ANALOG = "DNP3_DiscreteAnalog"
COLUNAS_ESPERADAS_DISCRETE_ANALOG = <valor medido no Step 1>


def _eh_discrete_analog(rec, padrao) -> bool:
    sp = padrao.por_sigla(rec.sigla_sinal) if rec.sigla_sinal else None
    return bool(sp and sp.categoria == "DiscreteAnalog")


def _valores_discrete_analog(rec, subestacao, padrao, alias_v1=None) -> dict:
    """TAP real (GTD): MeasType=Discrete, SignalType=TapPosition, RP Type=Analog,
    NormalValue=9, DeviceMapping -> comando COMTAP no mesmo módulo."""
    sp = padrao.por_sigla(rec.sigla_sinal)
    nome = _nome_hierarquico(subestacao, rec.modulo.nome,
                             rec.eletrico.nome_equipamento, rec.eletrico.barra,
                             rec.sigla_sinal or "?")
    remote_unit = _remote_unit(subestacao)
    indices = rec.enderecamento.indices
    coords = indices[0] if len(indices) == 1 else ";".join(str(i) for i in indices)
    device = nome
    if sp.device_mapping_ref and nome.endswith(rec.sigla_sinal or ""):
        device = nome[: len(nome) - len(rec.sigla_sinal)] + sp.device_mapping_ref
    return {
        "Signal Name": nome,
        "Signal Alias": _signal_alias(rec, alias_v1),
        "Measurement Type": "Discrete",
        "Signal Type": sp.signal_type or "Custom",
        "Phases": _fase_saida(rec.eletrico.fase),
        "Side": "None",
        "Direction": "Read",
        "Normal Value": sp.normal_value,
        "Device Mapping": device,
        "Signal AOR Group": _aor_group(subestacao, _eh_alimentador(rec.modulo.nome)),
        "Input Coordinates": coords,
        "Remote Point Type": sp.remote_point_type or "Analog",
        "Remote Point Name": nome,
        "Remote Unit": remote_unit,
        "Remote Point Custom ID": f"{nome}_{remote_unit}" if remote_unit else None,
        "Remote Point Alias": _alias_hoje(),
    }
```

(Conferir cada display name contra a row 4 medida no Step 1 — chave que não existe na
sheet é silenciosamente ignorada por `_escrever_sheet`; cobrir com assert no teste.)

Em `gerar()`, trocar os dois filtros por roteamento de 3 vias:

```python
    regs_da = [r for r in lista.registros if _eh_discrete_analog(r, lista_padrao)]
    ids_da = {id(r) for r in regs_da}
    regs_disc = [r for r in lista.registros
                 if r.tipo_sinal.categoria == "Discrete" and id(r) not in ids_da]
    regs_ana = [r for r in lista.registros
                if r.tipo_sinal.categoria == "Analog" and id(r) not in ids_da]
    ...
    if regs_da:
        _escrever_sheet(
            wb[SHEET_DISCRETE_ANALOG], SHEET_DISCRETE_ANALOG,
            COLUNAS_ESPERADAS_DISCRETE_ANALOG, regs_da,
            lambda rec, sub, padrao: _valores_discrete_analog(rec, sub, padrao, alias_v1),
            lista.subestacao, lista_padrao,
        )
```

Em `bench/gate_tdt_real.py`:

```python
_SHEETS = ("DNP3_DiscreteSignals", "DNP3_AnalogSignals", "DNP3_DiscreteAnalog")
```

- [ ] **Step 5: Run tests + regressão**

Run: `python -m pytest tests/ -q && PYTHONPATH=src python bench/regressao.py`
Expected: tudo PASS; gate não regride (DiscreteAnalog agora conta — anotar o pct novo como baseline).

- [ ] **Step 6: Commit**

```bash
git add -A src bench tests
git commit -m "feat(engine): sheet DNP3_DiscreteAnalog (TAP) + gate cobre a categoria"
```

---

## Fase 4 — Startup

### Task 9: Diagnóstico do boot + fixes condicionais

**Files:**
- Modify: `src/tdt/ui_main.py`
- Modify (condicional): módulos com import pesado no caminho do boot

**Interfaces:**
- Produces: boot com janela visível em <2s (medido); import morto removido.

- [ ] **Step 1: Medir os imports**

Run: `python -X importtime -c "import tdt.ui_main" 2> import_boot.log; sort -t'|' -k2 -n import_boot.log | tail -30`
Anotar os 5 módulos mais caros e QUEM os importa (cadeia).

- [ ] **Step 2: Remover o import morto**

`src/tdt/ui_main.py:12` importa `criar_encoder` e não usa (confirmar com `grep -n criar_encoder src/tdt/ui_main.py` — 1 hit = só o import). Remover a linha. Se `tdt.dados.encoder` importa sentence-transformers/torch no topo do módulo, este único fix já corta o grosso.

- [ ] **Step 3: Verificar quem mais puxa encoder/faiss no boot**

Run: `grep -rn "from tdt.dados.encoder\|import faiss\|sentence_transformers" src/tdt/ui/ src/tdt/ui_main.py`
Qualquer hit na cadeia de módulos importados pela UI ANTES de `win.show()` → mover pra import local (dentro da função que usa). Padrão:

```python
def _analisar(self):
    from tdt.dados.encoder import criar_encoder  # lazy: só quando o usuário analisa
    ...
```

- [ ] **Step 4: Medir o resultado**

Run: `python -X importtime -c "import tdt.ui_main" 2> import_boot2.log; sort -t'|' -k2 -n import_boot2.log | tail -5`
E boot real: `Measure-Command { python -c "import tdt.ui_main" }` (PowerShell).
Critério: import de `tdt.ui_main` sem encoder/torch na cadeia; tempo total de import < 2s.
Se `ListaPadraoADMS.carregar` (síncrono em `main()`) custar > 0.5s: mover pra depois de `win.show()` via `QTimer.singleShot(0, ...)`; senão deixar como está e corrigir só o comentário mentiroso ("Carrega ... em background" → "Carrega a lista padrão (síncrono, barato)").

- [ ] **Step 5: Smoke test da UI**

Run: `python -m tdt.ui_main` (manual): janela abre, análise de um input funciona (encoder lazy carrega sob demanda).

- [ ] **Step 6: Run test suite + commit**

Run: `python -m pytest tests/ -q`

```bash
git add -A src
git commit -m "perf(ui): remove import morto do encoder e lazy-load no boot"
```

**Follow-up registrado (não bloqueia a task):** `docs/RGE GAU 2026 - Lista de Pontos v09.xlsx` quebra o openpyxl (py3.14, `PatternFill ... extLst`). Se a UI precisar abrir esse arquivo, tratar num SP próprio (shim de compat ou upgrade do openpyxl).

---

## Fase 5 — Auto-tuning dos pesos

### Task 10: `bench/tune_pesos.py` (grid simplex + validação no gate)

**Files:**
- Create: `bench/tune_pesos.py`
- Modify (condicional, só se o gate melhorar): `src/tdt/config.py:38-40`
- Modify: `bench/reprocessar_lista1.py` (aceitar pesos por env var, 3 linhas)

**Interfaces:**
- Consumes: montagem de scorers idêntica a `bench/exp_pesos.py` (copiar o bloco de setup — os scripts de bench são standalone por convenção do diretório); `gate_tdt_real.comparar`.
- Produces: `bench/resultados/tune_pesos.txt` (tabela completa + top-10 + validação gate).

- [ ] **Step 1: Parametrizar `reprocessar_lista1.py` por env var**

```python
import os
...
    pesos = os.environ.get("TDT_PESOS")  # "0.70,0.25,0.05"
    if pesos:
        t, v, f = (float(x) for x in pesos.split(","))
        cfg = Config(peso_tfidf=t, peso_vetorial=v, peso_fuzzy=f,
                     peso_tfidf_analog=t, peso_vetorial_analog=v, peso_fuzzy_analog=f)
    else:
        cfg = Config()
```

- [ ] **Step 2: Escrever `bench/tune_pesos.py`**

```python
"""Tuning dos pesos de mescla em 2 estágios.

Estágio 1 (barato): grid simplex passo 0.05 (231 combos) sobre candidatos
cacheados por método, métrica prec@decididos + acc@1 no ROTULOS.
Estágio 2 (caro): top-3 do estágio 1 rodam o pipeline real
(bench/reprocessar_lista1.py via TDT_PESOS) e comparam no gate_tdt_real.

Só recomenda atualizar a Config se o melhor combo superar o atual NO GATE.

Uso: PYTHONPATH=src python bench/tune_pesos.py
"""
import itertools
import os
import subprocess
import sys

sys.path.insert(0, "bench")
# --- setup identico a bench/exp_pesos.py (corpus, tfidf, vetorial, fuzzy,
#     combinar_calib, rec, ROTULOS, cfg) — copiar o bloco das linhas 13-76 ---
...

# Estagio 1: cache dos candidatos (pesos nao afetam os scores por metodo)
cache = [(tfidf.pontuar(rec(d), 5), vetorial(rec(d), 5), fuzzy.pontuar(rec(d), 5), esp)
         for d, esp in ROTULOS]

def simplex(passo=0.05):
    n = round(1 / passo)
    for i in range(n + 1):
        for j in range(n + 1 - i):
            yield (i * passo, j * passo, round(1 - (i + j) * passo, 2))

PCT, GAP = cfg.threshold_pct, cfg.threshold_gap
resultados = []
for pesos in simplex():
    acc1 = decid = corr = 0
    for t_c, v_c, f_c, esp in cache:
        cands = combinar_calib([t_c, v_c, f_c], pesos, "minmax")
        if not cands:
            continue
        top = cands[0]
        if top.sigla == esp: acc1 += 1
        gap = top.score - (cands[1].score if len(cands) > 1 else 0)
        if top.score >= PCT and gap >= GAP:
            decid += 1
            if top.sigla == esp: corr += 1
    prec = corr / decid if decid else 0.0
    resultados.append((prec, acc1 / len(ROTULOS), decid / len(ROTULOS), pesos))

resultados.sort(reverse=True)
for r in resultados[:10]:
    print(f"prec@dec={r[0]:.2%} acc@1={r[1]:.2%} decid={r[2]:.2%} pesos={r[3]}")

# Estagio 2: top-3 + atual no gate real
from gate_tdt_real import comparar
REAL = "docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx"
candidatos = [r[3] for r in resultados[:3]]
atual = (cfg.peso_tfidf, cfg.peso_vetorial, cfg.peso_fuzzy)
if atual not in candidatos:
    candidatos.append(atual)
for pesos in candidatos:
    env = dict(os.environ, TDT_PESOS=",".join(str(p) for p in pesos),
               PYTHONPATH="src")
    subprocess.run([sys.executable, "bench/reprocessar_lista1.py"],
                   env=env, check=True)
    res = comparar("output/LISTA 1 - GTD/TDT.xlsx", REAL)
    tag = " (ATUAL)" if pesos == atual else ""
    print(f"GATE pesos={pesos}{tag}: {res.iguais}/{res.comum} = {res.pct:.1f}%")
```

(Completar o bloco `...` com o setup real copiado de `exp_pesos.py`; gravar a saída
completa em `bench/resultados/tune_pesos.txt` no padrão `LOG`/`log()` dos outros scripts.)

- [ ] **Step 3: Rodar**

Run: `PYTHONPATH=src python bench/tune_pesos.py | tee bench/resultados/tune_pesos.txt`
Expected: tabela do estágio 1 + 3-4 linhas de GATE. Duração: estágio 1 minutos (231 × mescla barata), estágio 2 ~4 execuções do pipeline.

- [ ] **Step 4: Decidir e (condicional) atualizar a Config**

- Melhor combo supera o atual NO GATE → atualizar `peso_tfidf/vetorial/fuzzy` (e as
  variantes `_analog`) em `src/tdt/config.py`, com comentário `(tune_pesos 09jul:
  gate X%→Y%)`; rodar `python -m pytest tests/ -q` + `PYTHONPATH=src python
  bench/regressao.py` (precisa passar).
- Não supera → manter 0.70/0.25/0.05 e registrar no relatório que o atual é ótimo.
- Em ambos os casos: corrigir o baseline enganoso `[0.34, 0.33, 0.33]` das entradas
  combo de `bench/benchmark.py:87-90` para usar `(cfg.peso_tfidf, cfg.peso_vetorial,
  cfg.peso_fuzzy)` (mesma correção já feita em `exp_pesos.py:78-83`).

- [ ] **Step 5: Commit**

```bash
git add -A bench src
git commit -m "feat(bench): tune_pesos 2 estagios (grid simplex + validacao gate)"
```

---

## Fechamento

- [ ] `python -m pytest tests/ -q` verde
- [ ] `PYTHONPATH=src python bench/regressao.py` verde
- [ ] Ledger (`docs/AGENTS.md`) atualizado com o fechamento do SP e o antes/depois do gate
- [ ] DOX pass: conferir cadeia AGENTS.md dos diretórios tocados (`src/tdt/`, `bench/`, `docs/`)
