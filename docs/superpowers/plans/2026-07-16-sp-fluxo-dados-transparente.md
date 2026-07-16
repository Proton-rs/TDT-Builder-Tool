# SP-FLUXO-DADOS-TRANSPARENTE — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Garantir que nenhuma informação de identidade (sigla, módulo, equipamento, endereço) adquirida no pipeline seja perdida ou sobrescrita silenciosamente — com diff auditável entre estágios, testes de conservação/independência e relatório para listas reais.

**Architecture:** Função pura `diff_identidade(antes, depois)` em `auditoria.py` compara dois estágios por `SignalRecord.id` e classifica mudanças em `sobrescrita` (valor→valor, INFO) e `perda` (valor→vazio, AVISO). O `pipeline` chama `Auditoria.sobrescritas()` em volta das etapas que mutam identidade — nenhuma assinatura de `dc_pairer`/`normalizador_estrutural` muda. Testes usam a mesma função pura direto.

**Tech Stack:** Python 3.14, pytest, dataclasses frozen (`contracts.SignalRecord`). Spec: `docs/superpowers/specs/2026-07-16-sp-fluxo-dados-transparente-design.md`.

## Global Constraints

- Regra universal do `CLAUDE.md` ("Não-regressão e fluxo de dados"): nada do que funciona pode quebrar; rodar a suíte completa antes de cada commit.
- Só ADIÇÕES a contratos públicos — nunca remover campo ou mudar assinatura existente (`dc_pairer.parear`, `corrigir`, `fundir_pares_posicao` ficam intactos).
- Pré-processamento/normalização (N0–N5, tokenizer) estão FORA de escopo (exceção reconhecida da spec).
- Testes rodam com `PYTHONPATH=src python -m pytest ...` (Git Bash) a partir da raiz do repo.
- Commits em português, Conventional Commits, terminando com `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Fusões que ABSORVEM um id (dc_pairer D+C, fundir_pares_posicao) não são "perda" — são cobertas pelos testes de conservação por contagem já existentes (`tests/test_conservacao_comandos.py`); `diff_identidade` só compara ids presentes nos dois lados.

---

### Task 1: Mapa de fluxo de dados (`docs/fluxo_dados.md`)

**Files:**
- Create: `docs/fluxo_dados.md`

**Interfaces:**
- Consumes: nada (documento).
- Produces: tabela de referência usada pelas Tasks 3 (onde wirar) e por specs futuras (regra 2 do CLAUDE.md).

- [x] **Step 1: Criar o documento com a tabela abaixo**

```markdown
# Fluxo de dados do pipeline — quem lê, escreve e sobrescreve identidade

Identidade = `sigla_sinal`, `modulo.nome`, `eletrico.nome_equipamento`,
`enderecamento.indices`. Invariantes I1–I4 na spec
`docs/superpowers/specs/2026-07-16-sp-fluxo-dados-transparente-design.md`.

| Etapa | Lê | Escreve | Sobrescreve/descarta | Como é auditado |
|---|---|---|---|---|
| normalização N0–N5 (`normalizador.canonizar`) | descrição bruta | `descricoes.normalizada`, `eletrico.*` (N0) | descarta ruído do texto (EXCEÇÃO da regra) | `descricoes.bruta` sempre preservada |
| `analise_colunas.analisar` | rows | `MapaColunas` | — | — |
| `estruturador.estruturar` | rows + mapa | `SignalRecord` completo (sigla, módulo, equipamento, endereços, tipo) | — | I2: módulo/sigla/equipamento em ramos INDEPENDENTES (regressão LVA AL21) |
| `identidade_modulo.aplicar_identidade` | sinais + rows | `modulo.nome`, confiança | saneia módulo fora do padrão p/ dominante da sheet | aviso `identidade_modulo` + `aud.sobrescritas()` (Task 3) |
| `inferencia_topologia.subdividir_transformador_at_bt` | sinais | `modulo.nome` (+sufixo AT/BT) | renomeia módulo | `aud.sobrescritas()` (Task 3) |
| `inferencia_topologia.inferir_equipamento` | sinais | `eletrico.equipamento_alvo` | — | flag `equipamento_inferido` |
| `inferencia_topologia.atribuir_id_por_registro` | sinais | `eletrico.nome_equipamento` (só None→valor) | nunca sobrescreve | aviso `registro_equipamentos` p/ ambíguo |
| scoring/roteador (`_classificar_roteado`) | descrições | `sigla_sinal`, `candidatos`, `status` | — | `diagnostico`/candidatos |
| `normalizador_estrutural.fundir_pares_posicao` | decididos | `indices` (a+b), datatype MultiCoord | absorve o id do segundo registro | `aud.sobrescritas()` (Task 3) + conservação por contagem |
| `dc_pairer.parear` | decididos | `indices_saida`; re-chaveia sigla de posição divergente | absorve o id do comando na fusão (upgrade path na docstring de `dc_pairer.separar`) | `aud.sobrescritas()` (Task 3) + conservação por contagem |
| `normalizador_estrutural.corrigir` | pareados | — | particiona duplicata/sem-endereço p/ revisão | `ItemRevisao` |
| `criador_lista_homogenea.montar` + `engine_tdt.particionar_*` | lista | nomes de saída | move grupos p/ revisão | eventos `engine` |
| UI (`AppState`) | registros | edições do usuário | NUNCA reverte edição sem comando explícito (bug aprovar 16/07, 16645f4) | `_snapshot()`/desfazer |

## Lacunas conhecidas (follow-ups, fora deste plano)

- Coluna EQUIPAMENTO dedicada (LVA) não é detectada por `analise_colunas` —
  hoje só a varredura de linha inteira pega IDs da whitelist nela.
- Id do comando é perdido na fusão D+C (rastreável só por endereço) —
  upgrade path documentado em `dc_pairer.separar`.
```

- [x] **Step 2: Commit**

```bash
git add docs/fluxo_dados.md
git commit -m "docs(fluxo): mapa etapa x le/escreve/sobrescreve identidade (SP-FLUXO-DADOS Task 1)"
```

---

### Task 2: `diff_identidade` + `Auditoria.sobrescritas` (I3)

**Files:**
- Modify: `src/tdt/auditoria.py` (append após a classe `Auditoria`; método novo dentro dela)
- Test: `tests/test_auditoria.py` (append)

**Interfaces:**
- Consumes: `SignalRecord` por duck-typing (`rec.id`, `rec.sigla_sinal`, `rec.modulo.nome`, `rec.eletrico.nome_equipamento`, `rec.enderecamento.indices`) — sem import de `contracts` em `auditoria.py`.
- Produces: `diff_identidade(antes, depois) -> list[Sobrescrita]` com `Sobrescrita(signal_id: str, campo: str, antes, depois, tipo: str)` onde `tipo ∈ {"sobrescrita", "perda"}`; `Auditoria.sobrescritas(etapa: str, antes, depois) -> int` (eventos emitidos). Tasks 3, 4 e 6 dependem EXATAMENTE desses nomes.

- [x] **Step 1: Escrever os testes que falham** (append em `tests/test_auditoria.py`)

```python
# --- diff_identidade / sobrescritas (SP-FLUXO-DADOS Task 2) -----------------

from dataclasses import replace

from tdt.auditoria import diff_identidade
from tdt.contracts import (
    Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)


def _rec_id(id_, sigla="DJF1", modulo="BC1", equip="52-1", indices=(10,)):
    return SignalRecord(
        id=id_, modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes("d", "D"),
        eletrico=Eletrico(nome_equipamento=equip),
        sigla_sinal=sigla, status="decidido",
    )


def test_diff_identidade_detecta_sobrescrita_e_perda():
    antes = [_rec_id("a:1"), _rec_id("a:2")]
    depois = [
        replace(antes[0], sigla_sinal="DJA1"),
        replace(antes[1], sigla_sinal=None),
    ]
    diffs = diff_identidade(antes, depois)
    assert [(d.signal_id, d.campo, d.tipo) for d in diffs] == [
        ("a:1", "sigla_sinal", "sobrescrita"),
        ("a:2", "sigla_sinal", "perda"),
    ]


def test_diff_identidade_ignora_preenchimento_e_ids_novos():
    # None -> valor é ENRIQUECIMENTO (permitido); id só de um lado é fusão/
    # particionamento (coberto pelos testes de conservação por contagem)
    antes = [_rec_id("a:1", sigla=None)]
    depois = [replace(antes[0], sigla_sinal="DJF1"), _rec_id("a:9")]
    assert diff_identidade(antes, depois) == []


def test_sobrescritas_emite_eventos_com_nivel_por_tipo():
    aud = Auditoria()
    antes = [_rec_id("a:1"), _rec_id("a:2")]
    depois = [
        replace(antes[0], modulo=Modulo("BC1AT", "sheet_name")),
        replace(antes[1], eletrico=Eletrico(nome_equipamento=None)),
    ]
    n = aud.sobrescritas("subdividir_at_bt", antes, depois)
    assert n == 2
    ev_info, ev_aviso = aud.eventos
    assert ev_info.nivel == "INFO"
    assert ev_info.signal_id == "a:1"
    assert ev_info.dados == {
        "etapa": "subdividir_at_bt", "campo": "modulo",
        "antes": "BC1", "depois": "BC1AT", "tipo": "sobrescrita",
    }
    assert ev_aviso.nivel == "AVISO"
    assert ev_aviso.signal_id == "a:2"
    assert ev_aviso.dados["tipo"] == "perda"
    assert ev_aviso.dados["campo"] == "equipamento"
```

Nota: `tests/test_auditoria.py` já importa `Auditoria`; adicione só os imports que faltarem.

- [x] **Step 2: Rodar e ver falhar**

Run: `PYTHONPATH=src python -m pytest tests/test_auditoria.py -q`
Expected: FAIL — `ImportError: cannot import name 'diff_identidade'`

- [x] **Step 3: Implementar em `src/tdt/auditoria.py`**

Método novo DENTRO da classe `Auditoria` (após `contagem`):

```python
    def sobrescritas(self, etapa: str, antes, depois) -> int:
        """I3 (spec fluxo-dados): emite 1 evento por mudança de identidade
        entre dois estágios do pipeline. "sobrescrita" (valor -> outro
        valor) é INFO — legítima, mas visível; "perda" (valor -> vazio) é
        AVISO — nunca deve acontecer silenciosamente. Devolve o total."""
        diffs = diff_identidade(antes, depois)
        for d in diffs:
            self.evento(
                "fluxo_dados",
                f"{etapa}: {d.campo} {d.antes!r} -> {d.depois!r}",
                "AVISO" if d.tipo == "perda" else "INFO",
                signal_id=d.signal_id,
                dados={"etapa": etapa, "campo": d.campo, "antes": d.antes,
                       "depois": d.depois, "tipo": d.tipo},
            )
        return len(diffs)
```

Funções module-level no FINAL do arquivo (duck-typing, sem import de contracts):

```python
@dataclass(frozen=True)
class Sobrescrita:
    signal_id: str
    campo: str
    antes: object
    depois: object
    tipo: str  # "sobrescrita" (valor -> outro valor) | "perda" (valor -> vazio)


def _identidade(rec) -> dict:
    return {
        "sigla_sinal": rec.sigla_sinal,
        "modulo": rec.modulo.nome,
        "equipamento": rec.eletrico.nome_equipamento,
        "indices": rec.enderecamento.indices,
    }


def diff_identidade(antes, depois) -> "list[Sobrescrita]":
    """Mudanças de campos de identidade entre dois estágios, por id.

    Ids presentes só num dos lados ficam de fora (fusão/particionamento —
    cobertos pelos testes de conservação por contagem); vazio -> valor é
    enriquecimento, não mudança. Vazio = None ou tupla ().
    """
    por_id = {r.id: r for r in antes}
    out: list[Sobrescrita] = []
    for rec in depois:
        r_antes = por_id.get(rec.id)
        if r_antes is None:
            continue
        ia, id_ = _identidade(r_antes), _identidade(rec)
        for campo, v_antes in ia.items():
            v_depois = id_[campo]
            if v_antes in (None, ()) or v_depois == v_antes:
                continue
            tipo = "perda" if v_depois in (None, ()) else "sobrescrita"
            out.append(Sobrescrita(rec.id, campo, v_antes, v_depois, tipo))
    return out
```

Atenção: `sobrescritas` (método) referencia `diff_identidade` definida depois no arquivo — ok em Python (resolução em runtime).

- [x] **Step 4: Rodar e ver passar**

Run: `PYTHONPATH=src python -m pytest tests/test_auditoria.py tests/test_auditoria_callback.py -q`
Expected: PASS (todos)

- [x] **Step 5: Commit**

```bash
git add src/tdt/auditoria.py tests/test_auditoria.py
git commit -m "feat(auditoria): diff_identidade + Auditoria.sobrescritas (SP-FLUXO-DADOS Task 2)"
```

---

### Task 3: Wiring no pipeline (`gerar_tdt` + `executar`)

**Files:**
- Modify: `src/tdt/pipeline.py:526-547` (`gerar_tdt`), `src/tdt/pipeline.py:617` (`aplicar_identidade`), `src/tdt/pipeline.py:646-647` (`subdividir_transformador_at_bt`), `src/tdt/pipeline.py:735-745` (cadeia final de `executar`)
- Test: `tests/test_fluxo_dados.py` (create)

**Interfaces:**
- Consumes: `Auditoria.sobrescritas(etapa, antes, depois)` da Task 2.
- Produces: eventos `modulo="fluxo_dados"` na auditoria de qualquer execução — consumidos pela Task 6 (relatório). Nenhuma assinatura pública muda.

- [x] **Step 1: Escrever o teste que falha** (`tests/test_fluxo_dados.py`)

```python
"""SP-FLUXO-DADOS Task 3: o pipeline emite eventos fluxo_dados quando uma
etapa muda identidade — aqui, a fusão MultiCoord do par de posição muda
`indices` do registro sobrevivente (320,) -> (320, 321)."""

from dataclasses import replace

from tdt import pipeline
from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.contracts import (
    Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS

LISTA_PADRAO = "docs/Pontos Padrao ADMS_v8.xlsx"
TEMPLATE = "docs/dnp3_template.xlsx"


def _rec(rid, sigla, indices, desc):
    return SignalRecord(
        id=rid, modulo=Modulo("BC2", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        eletrico=Eletrico(nome_equipamento="52-6"),
        sigla_sinal=sigla, status="decidido",
    )


def test_gerar_tdt_audita_sobrescrita_de_indices_na_fusao():
    lp = ListaPadraoADMS.carregar(LISTA_PADRAO)
    aud = Auditoria()
    cfg = replace(Config(), siglas_fundiveis_extra=frozenset({"DJF1"}))
    regs = [
        _rec("BC2:21", "DJF1", (320,), "52 06 ABERTO"),
        _rec("BC2:22", "DJF1", (321,), "52 06 FECHADO"),
    ]
    pipeline.gerar_tdt(regs, TEMPLATE, lp, subestacao="SE1",
                       config=cfg, auditoria=aud)
    evs = [e for e in aud.eventos if e.modulo == "fluxo_dados"]
    assert any(
        e.dados["campo"] == "indices"
        and e.dados["etapa"] == "fundir_pares_posicao"
        and e.signal_id == "BC2:21"
        for e in evs
    ), f"nenhum evento de fusão: {evs}"
```

Nota: se `Config` não aceitar `siglas_fundiveis_extra` via `replace` (campo inexistente), o teste quebra com erro claro — nesse caso use `frozenset({"DJF1"})` que já É a whitelist SwitchStatus da lista padrão v8 (DJF1 é SwitchStatus) e remova o `cfg`/`config=cfg`. O campo existe hoje (`pipeline._whitelist_posicao` lê `config.siglas_fundiveis_extra`).

- [x] **Step 2: Rodar e ver falhar**

Run: `PYTHONPATH=src python -m pytest tests/test_fluxo_dados.py -q`
Expected: FAIL — `assert any(...)` (nenhum evento `fluxo_dados` ainda)

- [x] **Step 3: Wirar `gerar_tdt`** (linhas 529-535 atuais)

De:

```python
    aud = auditoria or Auditoria()
    lst = _aplicar_aliases(list(registros), aliases)
    wl_pos = _whitelist_posicao(lp, config)
    lst = fundir_pares_posicao(lst, wl_pos)
    pareados, _rev = dc_pairer.parear(lst, config)
    corrigidos, _rev2 = corrigir(list(pareados), wl_pos)
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
```

Para:

```python
    aud = auditoria or Auditoria()
    lst = _aplicar_aliases(list(registros), aliases)
    wl_pos = _whitelist_posicao(lp, config)
    fundidos = fundir_pares_posicao(lst, wl_pos)
    aud.sobrescritas("fundir_pares_posicao", lst, fundidos)
    pareados, _rev = dc_pairer.parear(fundidos, config)
    aud.sobrescritas("dc_pairer", fundidos, pareados)
    corrigidos, _rev2 = corrigir(list(pareados), wl_pos)
    aud.sobrescritas("corrigir", pareados, corrigidos)
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
    aud.sobrescritas("montar", corrigidos, lista.registros)
```

- [x] **Step 4: Wirar `executar` — cadeia final** (linhas 735-745 atuais)

De:

```python
        decididos = fundir_pares_posicao(decididos, wl_pos)
        pareados, rev_pair = dc_pairer.parear(decididos, config)
        corrigidos, rev_estrut = corrigir(list(pareados), wl_pos)
```

Para:

```python
        decididos_pre = decididos
        decididos = fundir_pares_posicao(decididos, wl_pos)
        aud.sobrescritas("fundir_pares_posicao", decididos_pre, decididos)
        pareados, rev_pair = dc_pairer.parear(decididos, config)
        aud.sobrescritas("dc_pairer", decididos, pareados)
        corrigidos, rev_estrut = corrigir(list(pareados), wl_pos)
        aud.sobrescritas("corrigir", pareados, corrigidos)
```

- [x] **Step 5: Wirar `executar` — mutações por sheet**

Em volta de `aplicar_identidade` (linha 617 atual):

```python
        sinais_pre = sinais
        sinais, conf_mod, avisos_mod = aplicar_identidade(sinais, sn, rows, config)
        aud.sobrescritas("aplicar_identidade", sinais_pre, sinais)
```

Em volta de `subdividir_transformador_at_bt` (linha 647 atual):

```python
        secao_por_linha = derivar_secao_por_linha(rows, sn)
        sinais_pre = sinais
        sinais = subdividir_transformador_at_bt(sinais, config, secao_por_linha)
        aud.sobrescritas("subdividir_at_bt", sinais_pre, sinais)
```

- [x] **Step 6: Rodar o teste novo e a suíte completa**

Run: `PYTHONPATH=src python -m pytest tests/test_fluxo_dados.py -q`
Expected: PASS

Run: `PYTHONPATH=src python -m pytest tests/ -q`
Expected: tudo PASS (hoje: 1018 passed, 2 xfailed) — nenhuma regressão; os eventos são só aditivos.

- [x] **Step 7: Commit**

```bash
git add src/tdt/pipeline.py tests/test_fluxo_dados.py
git commit -m "feat(pipeline): audita sobrescritas de identidade entre etapas (SP-FLUXO-DADOS Task 3)"
```

---

### Task 4: Teste de conservação de identidade (zero perdas na cadeia)

**Files:**
- Test: `tests/test_conservacao_identidade.py` (create)

**Interfaces:**
- Consumes: `diff_identidade` (Task 2); cadeia parcial igual à de `tests/test_conservacao_comandos.py`.
- Produces: trava de regressão — qualquer etapa futura que zere identidade quebra este teste.

- [x] **Step 1: Escrever o teste** (deve passar de primeira — é trava, não bug conhecido; se falhar, achou violação real: investigar antes de prosseguir)

```python
"""SP-FLUXO-DADOS Task 4: nenhum campo de identidade preenchido na entrada
(sigla, módulo, equipamento, endereço) é PERDIDO (valor -> vazio) até o fim
da cadeia parcial de geração. Sobrescrita (valor -> outro valor) é permitida
— e auditada em produção via Auditoria.sobrescritas (Task 3). Fixture espelha
tests/test_conservacao_comandos.py (conservação por CONTAGEM); aqui é
conservação por CONTEÚDO."""

from tdt import criador_lista_homogenea, dc_pairer, engine_tdt
from tdt.auditoria import diff_identidade
from tdt.config import Config
from tdt.contracts import (
    Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.normalizador_estrutural import corrigir, fundir_pares_posicao


def _rec(rid, sigla, direcao, modulo, indices, desc, equip="52-1"):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        eletrico=Eletrico(nome_equipamento=equip),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_nenhuma_perda_de_identidade_na_cadeia_de_geracao():
    entrada = [
        # par de posição fundível (vira MultiCoord no id BC2:21)
        _rec("BC2:21", "DJF1", "Input", "BC2", [320], "52 06 ABERTO"),
        _rec("BC2:22", "DJF1", "Input", "BC2", [321], "52 06 FECHADO"),
        # comando toggle do mesmo grupo (funde no dc_pairer)
        _rec("BC2:14", "DJF1", "Output", "BC2", [90], "52 06 ABRIR FECHAR"),
        # input comum com equipamento
        _rec("BC2:32", "MOLA", "Input", "BC2", [326], "MOLA DESCARREGADA"),
        # comando órfão -> revisão comando_sem_discreto
        _rec("BC9:1", "DJF1", "Output", "BC9", [200], "DISJ DESLIGAR LIGAR"),
        # duplicata de endereço no mesmo grupo -> revisão endereco_duplicado
        _rec("BC3:5", "VAB", "Input", "BC3", [50], "TENSAO BARRA AB"),
        _rec("BC3:6", "VAB", "Input", "BC3", [50], "TENSAO BARRA AB"),
    ]
    wl = frozenset({"DJF1"})
    fundidos = fundir_pares_posicao(entrada, wl)
    pareados, rev1 = dc_pairer.parear(fundidos, Config())
    corrigidos, rev2 = corrigir(list(pareados), wl)
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao="SE1")
    lista, rev3 = engine_tdt.particionar_custom_id_duplicado(lista)
    lista, rev4 = engine_tdt.particionar_endereco_duplicado(lista)

    finais = list(lista.registros) + [
        ir.registro for ir in (*rev1, *rev2, *rev3, *rev4)
    ]
    perdas = [d for d in diff_identidade(entrada, finais) if d.tipo == "perda"]
    assert perdas == [], f"identidade perdida no caminho: {perdas}"
```

- [x] **Step 2: Rodar**

Run: `PYTHONPATH=src python -m pytest tests/test_conservacao_identidade.py tests/test_conservacao_comandos.py -q`
Expected: PASS. Se FALHAR: é violação real de I3 — reportar ao usuário com o diff antes de qualquer "ajuste no teste".

- [x] **Step 3: Commit**

```bash
git add tests/test_conservacao_identidade.py
git commit -m "test(conservacao): identidade por conteudo, zero perdas na cadeia (SP-FLUXO-DADOS Task 4)"
```

---

### Task 5: Testes de independência de identidades (guarda anti-`elif`)

**Files:**
- Test: `tests/test_estruturador.py` (append, seção nova antes de `# --- marcador tolerante a numeracao`)

**Interfaces:**
- Consumes: `estruturar`, `MapaColunas`, `Config` (imports já existem no arquivo).
- Produces: guardas — módulo×sigla já coberto por `test_modulo_por_linha_nao_engole_coluna_sigla`; aqui entram sigla×equipamento e módulo×equipamento.

- [x] **Step 1: Escrever os testes**

```python
# --- independência de identidades (SP-FLUXO-DADOS Task 5, invariante I2) ---
# Cada fonte de identidade presente na linha resolve a SUA identidade;
# nenhuma desliga a outra (módulo×sigla coberto em
# test_modulo_por_linha_nao_engole_coluna_sigla).


def test_sigla_coluna_e_equipamento_na_linha_resolvem_juntos():
    rows = [
        ("DESCRIÇÃO", "TIPO", "EQUIPAMENTO", "SIGLA", "IDX"),
        ("Mola carregada", "D", "52-11", "MOLA", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "descricao": 0, "tipo": 1, "sigla": 3, "indice": 4})
    recs = estruturar(rows, mapa, sheet_name="AL11", config=Config(),
                      siglas_set=frozenset({"MOLA"}))
    assert recs[0].sigla_sinal == "MOLA"           # coluna SIGLA
    assert recs[0].eletrico.nome_equipamento == "52-11"  # varredura da linha


def test_modulo_coluna_e_equipamento_na_linha_resolvem_juntos():
    rows = [
        ("MODULO", "DESCRIÇÃO", "TIPO", "EQUIPAMENTO", "IDX"),
        ("AL21", "Disj. aberto", "D", "52-11", "10"),
        ("AL22", "Disj. fechado", "D", "52-12", "11"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "modulo": 0, "descricao": 1, "tipo": 2, "indice": 4})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert [r.modulo.nome for r in recs] == ["AL21", "AL22"]
    assert [r.eletrico.nome_equipamento for r in recs] == ["52-11", "52-12"]


def test_modulo_sigla_e_equipamento_simultaneos_resolvem_os_tres():
    """Critério de sucesso da spec: as TRÊS identidades na mesma linha
    (layout LVA AL11/AL21 completo) resolvem juntas."""
    rows = [
        ("MODULO", "DESCRIÇÃO", "TIPO", "EQUIPAMENTO", "SIGLA", "IDX"),
        ("AL21", "Mola carregada", "D", "52-11", "MOLA", "10"),
        ("AL22", "Mola carregada", "D", "52-12", "MOLA", "11"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "modulo": 0, "descricao": 1, "tipo": 2, "sigla": 4, "indice": 5})
    recs = estruturar(rows, mapa, sheet_name="AL21", config=Config(),
                      siglas_set=frozenset({"MOLA"}))
    assert [r.modulo.nome for r in recs] == ["AL21", "AL22"]
    assert [r.sigla_sinal for r in recs] == ["MOLA", "MOLA"]
    assert [r.eletrico.nome_equipamento for r in recs] == ["52-11", "52-12"]
```

- [x] **Step 2: Rodar**

Run: `PYTHONPATH=src python -m pytest tests/test_estruturador.py -q`
Expected: PASS (a varredura de linha inteira de 14a886b já cobre; se falhar, achou violação real de I2 — reportar, não contornar).

- [x] **Step 3: Commit**

```bash
git add tests/test_estruturador.py
git commit -m "test(estruturador): independencia sigla/modulo x equipamento na linha (SP-FLUXO-DADOS Task 5)"
```

---

### Task 6: Relatório de fluxo para listas reais (gate de closeout)

**Files:**
- Create: `scripts/relatorio_fluxo_real.py`

**Interfaces:**
- Consumes: `pipeline.executar` (assinatura em `src/tdt/pipeline.py:550`), eventos `fluxo_dados` da Task 3, `criar_encoder` de `tdt.dados.encoder`.
- Produces: relatório de terminal usado na verificação de closeout (regra 4 do CLAUDE.md). Inputs reais vivem FORA do repo (ex. `C:\Users\vinic\Documents\docs importantes\RGE\...`) — path é argumento.

- [x] **Step 1: Criar o script**

```python
"""Relatório de fluxo/conservação para listas reais (gate de closeout).

Roda o pipeline completo numa lista e imprime: TDT × revisão (por motivo) e
eventos de identidade (sobrescritas INFO / perdas AVISO do módulo
fluxo_dados). Perda > 0 = bug de fluxo (regra 2 do CLAUDE.md).

Uso (listas reais ficam fora do repo — passe o path):
    PYTHONPATH=src python scripts/relatorio_fluxo_real.py \
        "C:/Users/vinic/Documents/docs importantes/RGE/LVA/Lista de pontos LVA.xlsx" \
        --subestacao LVA
"""

import argparse
import sys
from collections import Counter

from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.pipeline import executar


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="planilha de entrada (.xlsx)")
    p.add_argument("--lista-padrao", default="docs/Pontos Padrao ADMS_v8.xlsx")
    p.add_argument("--template", default="docs/dnp3_template.xlsx")
    p.add_argument("--subestacao", default=None)
    args = p.parse_args()

    cfg = Config()
    aud = Auditoria()
    res, _wb = executar(
        args.input, args.template, args.lista_padrao,
        config=cfg, encoder=criar_encoder(cfg.modelo_embedding),
        subestacao=args.subestacao, auditoria=aud,
    )

    print(f"\nTDT: {len(res.lista.registros)} | revisão: {len(res.revisao)}")
    print("revisão por motivo:")
    for motivo, n in Counter(ir.motivo for ir in res.revisao).most_common():
        print(f"  {motivo}: {n}")

    fluxo = [e for e in aud.eventos if e.modulo == "fluxo_dados"]
    perdas = [e for e in fluxo if e.dados and e.dados.get("tipo") == "perda"]
    print(f"\neventos de identidade: {len(fluxo)} ({len(perdas)} PERDAS)")
    for e in perdas:
        print(f"  PERDA {e.signal_id}: {e.msg}")
    return 1 if perdas else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 2: Verificar com a lista do repo (SAN2)**

Run: `PYTHONPATH=src python scripts/relatorio_fluxo_real.py docs/SAN2_LISTA_PADRONIZADA_PARA_TESTE.xlsx --subestacao SND`
Expected: relatório imprime contagens, `0 PERDAS`, exit code 0. (Demora: carrega o encoder real — é ferramenta de verificação manual, não teste de CI.)

- [x] **Step 3: Commit**

```bash
git add scripts/relatorio_fluxo_real.py
git commit -m "feat(scripts): relatorio de fluxo/conservacao p/ listas reais (SP-FLUXO-DADOS Task 6)"
```

---

## Closeout (após as 6 tasks)

- [x] Suíte completa: `PYTHONPATH=src python -m pytest tests/ -q` — tudo verde.
- [x] Rodar `scripts/relatorio_fluxo_real.py` nas listas reais disponíveis (LVA, CVA — paths em `C:\Users\vinic\Documents\docs importantes\RGE\`) e anexar resumo na conversa de closeout; qualquer PERDA é bug de fluxo (regra 2).
- [x] Ledger `docs/AGENTS.md`: linha da spec muda de "proposta" para "implementada" com hashes.
- [x] DOX pass: `src/tdt/AGENTS.md` (nova função pública `diff_identidade`/`sobrescritas` em auditoria) — 1 linha.
