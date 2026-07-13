# SP-GAU — Correções pós-revisão das TDTs GAU/CVA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar as 14 observações das TDTs GAU/CVA (13 do `docs/anot.txt` + tensão CA×AC): diagnóstico reproduzível dos comandos perdidos e do tipo VAB, 3 correções de classificação com gate, aviso de módulo suspeito, e o pacote de UI de revisão (motivos visíveis, lote, endereço editável, par de posição, colunas e contadores).

**Architecture:** Faseado, na receita do SP-Unificado 08jul: diagnóstico primeiro (E3 e o fix do VAB são bloqueados por dado), correções determinísticas de UI/motivos sem gate, correções de scoring/pareamento **uma por task com gate individual** (`bench/gate_tdt_real.py`, `pct >= baseline`, nunca agrupar). Lógica nova de UI vai em `estado`/`modelo_tabela` (testável headless); `tela_revisao` só wira.

**Tech Stack:** Python 3.12, openpyxl, pytest, PySide6 (Fases 6-7). Sem dependências novas.

**Spec:** `docs/superpowers/specs/2026-07-13-sp-correcoes-tdt-gau-design.md`

## Global Constraints

- **Gate obrigatório e individual** em toda task que altera matching/roteamento/pareamento (Tasks 4, 4b, 5, 8, 9): `PYTHONPATH=src python bench/gate_tdt_real.py`; `pct` não pode cair vs. a task anterior. Regrediu → reverter a task, registrar em `bench/resultados/spGAU_<task>.txt`, seguir.
- **Lista padrão de matching:** `Pontos Padrao ADMS_v8.xlsx` (default atual; nunca v5/v6).
- **Tasks bloqueadas por dado (8 e 9):** instanciar SÓ depois do diagnóstico (Task 1); uma causa = uma task = um gate; parar e reportar ao usuário antes de implementar.
- Estilo: nomes descritivos, funções puras, teste por função pública (CLAUDE.md). TDD sempre. Commits pequenos `fix(...)|feat(ui)|test(...)`.
- Closeout: atualizar Ledger (`docs/AGENTS.md`), `src/tdt/ui/AGENTS.md` e o status da spec A (26jun) — Task 17.
- Contratos imutáveis: enriquecer `SignalRecord` com `dataclasses.replace`, nunca mutar.

---

## Fase 0 — Baseline

### Task 0: Congelar o baseline do gate

**Files:**
- Create: `bench/resultados/spGAU_baseline.txt`

- [ ] **Step 1: Rodar o gate**

Run: `PYTHONPATH=src python bench/gate_tdt_real.py`
Expected: imprime `pct`.

- [ ] **Step 2: Registrar**

```
baseline spGAU — 2026-07-13
pct=<valor impresso>
commit=<git rev-parse --short HEAD>
```

- [ ] **Step 3: Commit**

```bash
git add bench/resultados/spGAU_baseline.txt
git commit -m "test(gate): congela baseline spGAU"
```

---

## Fase 1 — Diagnóstico GAU (E1) — sem mudança de produção

### Task 1: `bench/diag_gau.py` — rastrear comandos, VAB e colisões de módulo

**Files:**
- Create: `bench/diag_gau.py`
- Create: `docs/superpowers/specs/2026-07-13-diag-gau-achados.md`

**Interfaces:**
- Consumes: `pipeline.executar` (ou os estágios individuais, como `bench/diag_direcao_comando.py` já faz), `docs/RGE GAU 2026 - Lista de Pontos v09.xlsx`.
- Produces: doc de achados que instancia as Tasks 8 e 9.

- [ ] **Step 1: Ler o padrão dos diag existentes**

Run: `ls bench/diag_*.py` e ler o mais próximo (`diag_direcao_comando.py`) — reusar o carregamento de xlsx e o cruzamento por endereço.

- [ ] **Step 2: Instrumentar a cadeia de comandos**

Para cada sheet (BC1, BC2, BC5_6, CVA11): rodar o pipeline e, para cada registro com direção Output (comando) detectado na entrada, imprimir onde terminou:

```python
# pseudo-estrutura do relatório por comando:
# sheet | linha | texto bruto | endereço lido | destino final:
#   "TDT ReadWrite (fundido com <id status>)" |
#   "TDT Write órfão" |
#   "revisão: <motivo>" |
#   "AUSENTE (perda silenciosa)"  <- se ocorrer, é bug confirmado
```

Instrumentação: comparar os ids presentes em `decididos` (pré `dc_pairer.parear`) contra a união (saída de `particionar_custom_id_duplicado` ∪ todos os `ItemRevisao`). Casos-alvo do anot.txt: BC1 "endereço 80", BC2 DJF1, BC5_6 DJF1.

- [ ] **Step 3: Instrumentar o CVA11 (VAB)**

Imprimir: índice/nome da coluna que `analise_colunas._col_tipo` escolheu, e para cada sinal analógico (VAB, VBC, ...) a categoria/direção atribuída pelo `estruturador` e de onde veio (célula TIPO × marcador de seção). Confirmar a hipótese "tipo na linha numa sheet, na coluna em outra".

- [ ] **Step 3b: Instrumentar as tensões entre fases (item 14 — CA×AC)**

Para cada tensão entre fases do input (VAB/VBC/VCA, "tensão fase CA" etc.): imprimir o texto bruto, a fase que `extrair_contexto_estrutural` devolveu, o valor final da coluna Phases e o texto do Signal Alias no TDT gerado. Objetivo: localizar exatamente onde o "AC" invertido aparece — extração N0 (texto do input traz "AC"), descrição da lista padrão (Signal Alias), ou outro campo. Se vier da lista padrão, a correção é de dado (proposta à parte), não a Task 4b.

- [ ] **Step 4: Instrumentar BC1/BC2 (módulo)**

Listar os grupos que `particionar_custom_id_duplicado` removeu: Custom ID, ids dos registros e **sheet de origem de cada um** (prefixo do `SignalRecord.id`, formato `sheet:linha`).

- [ ] **Step 5: Escrever os achados**

`docs/superpowers/specs/2026-07-13-diag-gau-achados.md`: por caso do anot.txt (1b, 3, 5, 8, 10, 11), a causa confirmada com evidência (linha da planilha + ponto do código). Terminar com a instanciação proposta das Tasks 8 e 9 (uma causa = uma task).

- [ ] **Step 6: Parar e reportar ao usuário** — as correções de pareamento/análise (Tasks 8-9) só se implementam com o achado validado.

- [ ] **Step 7: Commit**

```bash
git add bench/diag_gau.py docs/superpowers/specs/2026-07-13-diag-gau-achados.md
git commit -m "docs(diag): rastreio de comandos, tipo VAB e colisoes de modulo na lista GAU"
```

---

## Fase 2 — Motivos e relatório (E6) — determinístico, sem gate

### Task 2: `_MOTIVO_LABEL` completo + fim do "—" + "Sem endereço"

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py:22-32` (dict), `:143-145` (fallback)
- Test: `tests/test_modelo_tabela.py`

**Interfaces:**
- Produces: `_MOTIVO_LABEL` cobrindo os 14 motivos emitidos; fallback exibe o motivo cru (nunca "—" quando há motivo). Tooltip via `Qt.ToolTipRole` na coluna Motivo.

- [ ] **Step 1: Teste que falha**

```python
def test_motivo_sem_label_exibe_motivo_cru():
    # motivo emitido pelo pipeline mas fora do dict não pode virar "—"
    assert _MOTIVO_LABEL.get("motivo_futuro_desconhecido", "motivo_futuro_desconhecido") != "—"

def test_todos_motivos_emitidos_tem_label():
    emitidos = {
        "sem_endereco", "score_baixo", "categoria_ambigua", "endereco_duplicado",
        "sem_fix", "modulo_indefinido", "nome_sigla_inconsistente",
        "qualificador_ambiguo", "pareamento_ambiguo", "comando_sem_discreto",
        "custom_id_duplicado", "posicao_ambigua", "comando_tap_nao_modelado",
        "decisao_por_projeto", "descartado_indefinido", "descartado_redundante",
    }
    assert emitidos <= set(_MOTIVO_LABEL)

def test_sem_endereco_nao_diz_futuro():
    assert "futuro" not in _MOTIVO_LABEL["sem_endereco"].lower()
```

- [ ] **Step 2: Rodar — falha.** `python -m pytest tests/test_modelo_tabela.py -k motivo -v` → FAIL.

- [ ] **Step 3: Implementar**

Completar o dict (labels curtos; descrição longa num segundo dict p/ tooltip):

```python
_MOTIVO_LABEL = {
    "sem_endereco": "Sem endereço",
    "score_baixo": "Score baixo",
    "categoria_ambigua": "Categoria ambígua",
    "endereco_duplicado": "Endereço duplicado",
    "sem_fix": "Sem correção automática",
    "modulo_indefinido": "Módulo indefinido",
    "equipamento_ambiguo": "Equipamento ambíguo",
    "nome_sigla_inconsistente": "Sigla ≠ NOME",
    "qualificador_ambiguo": "Qualificador ambíguo",
    "pareamento_ambiguo": "Comando sem par claro",
    "comando_sem_discreto": "Comando sem status",
    "custom_id_duplicado": "Custom ID duplicado",
    "posicao_ambigua": "Posição sem palavra-chave",
    "comando_tap_nao_modelado": "Comando de TAP (não vira ponto)",
    "decisao_por_projeto": "Decisão por projeto",
    "descartado_indefinido": "Descartado (indefinido)",
    "descartado_redundante": "Descartado (redundante)",
}
_MOTIVO_TOOLTIP = {
    # o que aconteceu + o que o operador pode fazer, uma frase cada; ex.:
    "pareamento_ambiguo": "O comando não encontrou um status compatível para fundir. "
                          "Selecione o status e o comando e use Parear.",
    "custom_id_duplicado": "Dois ou mais sinais gerariam o mesmo Custom ID no ADMS "
                           "(módulo+equipamento+sigla). Verifique módulo/equipamento.",
    # ... uma entrada por motivo
}
```

Fallback em `_texto()` (linha ~145): `_MOTIVO_LABEL.get(motivo, motivo) if motivo else "—"`. Adicionar `ToolTipRole` na coluna Motivo devolvendo `_MOTIVO_TOOLTIP.get(motivo, "")`.

- [ ] **Step 4: Rodar — passa.** PASS (suíte inteira: `python -m pytest tests/test_modelo_tabela.py -v`).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py tests/test_modelo_tabela.py
git commit -m "fix(ui): todos os motivos de revisao visiveis + tooltip; 'Sem endereco' substitui 'Futuro'"
```

### Task 3: Sheet de origem destacada no relatório

**Files:**
- Modify: `src/tdt/relatorio_revisao.py` (`_sheet_origem` já existe em `:65`; garantir coluna própria e presença na seção de duplicados)
- Test: `tests/test_relatorio_revisao.py`

- [ ] **Step 1: Teste que falha** — relatório de um grupo `custom_id_duplicado` com registros de sheets distintas deve listar as sheets:

```python
def test_relatorio_duplicado_lista_sheets_de_origem():
    recs = [_rec(id="BC1:10"), _rec(id="BC2:12")]  # mesmo custom id
    texto = gerar_relatorio(..., revisao=_revisao_dup(recs))
    assert "BC1" in texto and "BC2" in texto
```

- [ ] **Step 2: Rodar — falha.** FAIL.
- [ ] **Step 3: Implementar** — na linha do item de revisão, incluir `_sheet_origem(rec)` (já usada na `:83`; conferir que a seção de duplicados também a usa).
- [ ] **Step 4: Rodar — passa.** PASS.
- [ ] **Step 5: Commit** `git commit -am "feat(relatorio): sheet de origem destacada nos itens de revisao"`

---

## Fase 3 — Classificação (E2) — gate individual por task

### Task 4: `f_r4` — fallback quando a família não tem a variante do estágio (50N E2)

**Files:**
- Modify: `src/tdt/filtro_preciso.py:96-107` (`f_r4`)
- Test: `tests/test_filtro_preciso.py`

**Interfaces:**
- Consumes: assinatura atual `f_r4(cand, ctx) -> bool` (padrão dos filtros registrados em `_FILTROS`).
- Produces: comportamento novo — remove só candidato que termina em dígito **diferente**; sem candidato terminando no dígito do texto → mantém os sem-estágio.

- [ ] **Step 1: Teste que falha**

```python
def test_estagio_sem_variante_na_familia_mantem_sigla_base():
    # texto "50N E2": se nenhum candidato termina em 2, 50N sobrevive
    rec = _rec_texto("sobrecorrente neutro 50n e2")
    out = filtrar(rec, [_cand("50N"), _cand("51N")], Config())
    assert "50N" in _siglas(out)

def test_estagio_com_variante_remove_digito_divergente():
    # comportamento atual preservado: 81E1 vs 81E2 com texto E2 -> fica 81E2
    rec = _rec_texto("subfrequencia estagio 2")
    out = filtrar(rec, [_cand("81E1"), _cand("81E2")], Config())
    assert _siglas(out) == ["81E2"]
```

- [ ] **Step 2: Rodar — falha.** `PYTHONPATH=src python -m pytest tests/test_filtro_preciso.py -k estagio -v` → primeiro teste FAIL.

- [ ] **Step 3: Implementar** — em `f_r4`, trocar "remove quem não termina no dígito" por:

```python
def f_r4(cand: Candidato, ctx: Contexto) -> bool:
    digito = _digito_estagio(ctx)          # já existe (E1..E4 -> "1".."4")
    if digito is None:
        return True
    final = cand.sigla[-1]
    if final.isdigit():
        return final == digito             # variante de estágio errado: remove
    # sigla sem estágio: só remove se ALGUM candidato da família tem a variante certa
    return not ctx.familia_tem_final(digito)
```

Se `Contexto` não expõe a família, computar o conjunto de finais uma vez em `filtrar` e passar via ctx (seguir o padrão que `filtrar_especificidade` já usa para olhar o grupo).

- [ ] **Step 4: Rodar — passa.** Suíte inteira de `test_filtro_preciso.py` PASS.

- [ ] **Step 5: Gate individual.** `PYTHONPATH=src python bench/gate_tdt_real.py` → `pct >= baseline` (Task 0). Regrediu → revert + `bench/resultados/spGAU_task4.txt`.

- [ ] **Step 6: Commit** `git commit -am "fix(regras): f_r4 mantem sigla base quando familia nao tem variante do estagio (50N E2)"`

### Task 4b: Canonização de par de fases invertido (AC→CA, BA→AB, CB→BC)

**Files:**
- Modify: `src/tdt/normalizacao/normalizador.py:90-120` (`_fase_no_texto` + tupla multi-letra do D2.2)
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Consumes: `extrair_contexto_estrutural(texto) -> (texto_remanescente, ContextoEstrutural)` (assinatura atual, `normalizador.py:132`).
- Produces: `ContextoEstrutural.fase` sempre em ordem canônica (`AB`/`BC`/`CA`); domínio `FASES` inalterado. Beneficia `f_r3` (filtro duro de fase) e a coluna Phases (`engine_tdt._fase_saida`).

- [ ] **Step 1: Teste que falha**

```python
def test_par_de_fase_invertido_canoniza():
    _, ctx = extrair_contexto_estrutural("TENSAO FASE AC")
    assert ctx.fase == "CA"
    _, ctx = extrair_contexto_estrutural("TENSAO FASE BA")
    assert ctx.fase == "AB"
    _, ctx = extrair_contexto_estrutural("TENSAO FASE CB")
    assert ctx.fase == "BC"

def test_par_de_fase_canonico_inalterado():
    _, ctx = extrair_contexto_estrutural("TENSAO FASE CA")
    assert ctx.fase == "CA"
```

- [ ] **Step 2: Rodar — falha.** `PYTHONPATH=src python -m pytest tests/test_normalizador.py -k fase_invertido -v` → FAIL (fase=None hoje: "AC" não está em `FASES`).

- [ ] **Step 3: Implementar**

```python
_PAR_FASE_INVERTIDO = {"AC": "CA", "BA": "AB", "CB": "BC"}
```

Em `_fase_no_texto`: antes de cada lookup em `FASES` (e na tupla multi-letra do D2.2, `normalizador.py:117`), canonizar o token: `t = _PAR_FASE_INVERTIDO.get(t, t)`. Devolver a fase canonizada — o token original permanece no texto (contrato atual da função).

- [ ] **Step 4: Rodar — passa.** Suíte inteira de `test_normalizador.py` PASS.

- [ ] **Step 5: Gate individual.** `PYTHONPATH=src python bench/gate_tdt_real.py` → `pct >= baseline`. Regrediu → revert + `bench/resultados/spGAU_task4b.txt`.

- [ ] **Step 6: Commit** `git commit -am "fix(normalizacao): canoniza par de fases invertido (AC->CA, BA->AB, CB->BC)"`

### Task 5: Piso absoluto de decisão (51F → FC87)

**Files:**
- Modify: `src/tdt/config.py` (novo knob `piso_decisao`)
- Modify: `src/tdt/roteador.py:131-173` (`_quadrante`)
- Test: `tests/test_roteador.py`

**Interfaces:**
- Produces: `Config.piso_decisao: float = 0.20`; `_quadrante` manda para revisão (`motivo="score_baixo"`) quando a confiança calibrada do top-1 fica abaixo do piso, mesmo com pct/gap ok.

- [ ] **Step 1: Localizar a confiança calibrada** — grep `aplicar_calibrador_confianca` em `src/tdt/pipeline.py` e conferir onde o valor P(correto) do top-1 fica acessível ao roteador (campo do candidato ou parâmetro). O piso compara contra **essa** escala [0,1], não contra o score cru pós-motor (que é unbounded — ledger spB-B2).

- [ ] **Step 2: Teste que falha**

```python
def test_top1_abaixo_do_piso_vai_para_revisao():
    # gap enorme mas similaridade absoluta ridícula -> revisão, não decisão
    cands = [_cand("FC87", conf=0.12), _cand("51F", conf=0.02)]
    destino = rotear(_rec(), cands, Config(piso_decisao=0.20))
    assert destino.revisao and destino.motivo == "score_baixo"

def test_piso_zero_preserva_comportamento_atual():
    cands = [_cand("FC87", conf=0.12), _cand("51F", conf=0.02)]
    destino = rotear(_rec(), cands, Config(piso_decisao=0.0))
    assert not destino.revisao
```

- [ ] **Step 3: Rodar — falha.** FAIL.

- [ ] **Step 4: Implementar** — `config.py`: `piso_decisao: float = 0.20` (comentário: piso de confiança calibrada; 0.0 desliga). Em `_quadrante`, antes do retorno "decidido":

```python
if cfg.piso_decisao and confianca_top1 < cfg.piso_decisao:
    return _para_revisao(motivo="score_baixo")
```

- [ ] **Step 5: Rodar — passa.** PASS.

- [ ] **Step 6: Gate individual + calibração.** Rodar o gate; se `pct` cair, reduzir o piso (0.15, 0.10) até `pct >= baseline` e registrar o valor final + trade-off em `bench/resultados/spGAU_task5.txt`. Se nem 0.10 segurar, reverter e registrar.

- [ ] **Step 7: Commit** `git commit -am "feat(roteador): piso absoluto de confianca calibrada (config.piso_decisao)"`

---

## Fase 4 — Aviso de módulo suspeito (E4)

### Task 6: Motivo `modulo_duplicado_entre_sheets`

**Files:**
- Modify: `src/tdt/engine_tdt.py:321-344` (`particionar_custom_id_duplicado`)
- Modify: `src/tdt/ui/modelo_tabela.py` (label/tooltip do motivo novo — dict da Task 2)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `SignalRecord.id` no formato `sheet:linha` (mesma derivação de `modelo_tabela.sheet_origem`).
- Produces: grupos colididos cujos registros vêm de 2+ sheets ganham `motivo="modulo_duplicado_entre_sheets"`; grupos de sheet única mantêm `custom_id_duplicado`.

- [ ] **Step 1: Teste que falha**

```python
def test_colisao_entre_sheets_ganha_motivo_especifico():
    recs = [_rec(id="BC1:10", modulo="BC1"), _rec(id="BC2:12", modulo="BC1")]  # mesmo custom id
    _, revisao = particionar_custom_id_duplicado(_lista(recs))
    assert {ir.motivo for ir in revisao} == {"modulo_duplicado_entre_sheets"}

def test_colisao_mesma_sheet_mantem_motivo_atual():
    recs = [_rec(id="BC1:10"), _rec(id="BC1:11")]
    _, revisao = particionar_custom_id_duplicado(_lista(recs))
    assert {ir.motivo for ir in revisao} == {"custom_id_duplicado"}
```

- [ ] **Step 2: Rodar — falha.** FAIL.

- [ ] **Step 3: Implementar** — no ramo que emite os itens de revisão do grupo: derivar `sheets = {r.id.split(":")[0] for r in grupo}`; `motivo = "modulo_duplicado_entre_sheets" if len(sheets) > 1 else "custom_id_duplicado"`. Reusar a derivação existente se `sheet_origem` for importável sem ciclo (senão, duplicar o split de 1 linha com comentário apontando a fonte).

- [ ] **Step 4: Rodar — passa.** PASS (incluindo teste da Task 2 atualizado com o motivo novo no dict).

- [ ] **Step 5: Gate** (muda composição do TDT? Não — só o motivo; mas rodar por segurança). `pct >= baseline`.

- [ ] **Step 6: Commit** `git commit -am "feat(engine): motivo modulo_duplicado_entre_sheets para colisao vinda de sheets distintas"`

---

## Fase 5 — Pareamento (E3) — invariante + correções pós-diagnóstico

### Task 7: Invariante de conservação de comandos

**Files:**
- Create: `tests/test_conservacao_comandos.py`

**Interfaces:**
- Consumes: `dc_pairer.parear`, `normalizador_estrutural.corrigir`, `criador_lista_homogenea.montar`, `engine_tdt.particionar_custom_id_duplicado` (mesma composição de `pipeline.gerar_tdt:525-533`); helpers `_rec` de `tests/test_dc_pairer.py`.

- [ ] **Step 1: Escrever o teste (deve passar já hoje — é trava de regressão)**

```python
def test_nenhum_comando_some_silenciosamente():
    # status+comando pareáveis, comando órfão, e par que colide custom id
    entrada = [_status("DJF1", mod="BC1"), _comando("LIGAR", mod="BC1"),
               _comando("DESLIGAR", mod="BC9"),                # órfão
               _status("DJF1", mod="BC2"), _comando("LIGAR", mod="BC2")]
    ids_comando = {r.id for r in entrada if _e_output(r)}
    pareados, rev1 = dc_pairer.parear(entrada, Config())
    corrigidos, rev2 = corrigir(list(pareados), whitelist)
    lista = montar(list(corrigidos))
    lista, rev3 = particionar_custom_id_duplicado(lista)
    sobreviventes = _ids_no_tdt(lista) | _ids_fundidos(lista) | {
        ir.registro.id for ir in rev1 + rev2 + rev3}
    assert ids_comando <= sobreviventes, "comando sumiu sem TDT nem revisão"
```

`_ids_fundidos`: par fundido carrega o id do status — o teste considera o comando "vivo" se o registro fundido tem `indices_saida` preenchido (a evidência de que o Output foi incorporado). Ajustar os helpers ao contrato real de `tests/test_dc_pairer.py`.

- [ ] **Step 2: Rodar.** Se PASS: commit como trava. Se FAIL: **bug confirmado de perda silenciosa** — reportar ao usuário com o caso mínimo antes de corrigir (a correção vira uma Task 8 instanciada).

- [ ] **Step 3: Commit** `git commit -am "test(pareamento): invariante de conservacao de comandos (TDT ou revisao, nunca some)"`

### Task 8: Correções do pareamento GAU (instanciar pós-Task 1)

**BLOQUEADA POR DADO.** Uma sub-task por causa confirmada no diagnóstico, cada uma com teste-que-falha reproduzindo o caso GAU + gate individual. Hipóteses mapeadas (sites verificados 13jul):

| Hipótese | Site | Correção candidata |
|---|---|---|
| H1: limiar greedy 60.0 alto p/ textos GAU | `dc_pairer.py:139-165` | ajustar/knob `config` |
| H2: `compatibilidade_texto` (gate D5) bloqueia par legítimo | `dc_pairer.py:107-110` | afrouxar predicado p/ o padrão GAU |
| H3: endereço de output do comando não capturado na análise | `analise_colunas.py` / `estruturador.py` | captura da coluna/bloco de endereço de comando ("endereço 80") |
| H4: par fundido removido por colisão de Custom ID (item 11) | `engine_tdt.py:321-344` | já mitigada por Task 6 (visibilidade); avaliar se o par deve sair inteiro mesmo |

- [ ] **Step 1:** Ler `docs/superpowers/specs/2026-07-13-diag-gau-achados.md` e escrever uma sub-task TDD por causa confirmada (formato das Tasks 4-5).
- [ ] **Step 2:** Aprovação do usuário sobre as sub-tasks propostas.
- [ ] **Step 3:** Implementar cada sub-task com gate individual (`spGAU_task8_<n>.txt` se regredir).

### Task 9: Tipo do sinal na linha × na coluna (CVA11 VAB) (instanciar pós-Task 1)

**BLOQUEADA POR DADO.** Sites já mapeados: `analise_colunas.py:217-236` (`_col_tipo`) e `estruturador.py:86-89` (célula TIPO × marcador de seção precedente).

- [ ] **Step 1:** Do diagnóstico (Task 1 Step 3), escrever teste-que-falha com bloco de rows sintético reproduzindo o layout do CVA11 (tipo em linha de seção) onde VAB deve sair `Analog`/`Input` — nunca input digital.
- [ ] **Step 2:** Corrigir no site apontado (detecção da coluna errada → endurecer `_col_tipo`; seção não detectada → estender o marcador de seção). Correção mínima, sem módulo novo.
- [ ] **Step 3:** Suíte + gate individual (`pct >= baseline`; registrar `spGAU_task9.txt` se regredir).
- [ ] **Step 4:** Commit `fix(analise): tipo de sinal por linha de secao no layout CVA11`.

---

## Fase 6 — UI de revisão: dados e edição (E5, sem gate)

Lógica nova em `estado.py`/`modelo_tabela.py` (headless, testável com pytest puro); `tela_revisao.py` só conecta botão/menu → método. Padrão de teste: os testes existentes de `tests/test_modelo_tabela.py`/`tests/test_estado*.py`.

### Task 10: Aprovar seleção (lote)

**Files:**
- Modify: `src/tdt/ui/estado.py` (novo `aprovar_ids`)
- Modify: `src/tdt/ui/tela_revisao.py:637-663` (wiring: aprovar age sobre todas as linhas selecionadas)
- Test: `tests/test_estado_lote.py`

**Interfaces:**
- Produces: `AppState.aprovar_ids(ids: list[str]) -> int` — um `_snapshot()` único (um Ctrl+Z desfaz o lote inteiro), aprova cada id com a mesma transição usada por `_aprovar_e_proximo`, retorna quantos aprovou.

- [ ] **Step 1: Teste que falha**

```python
def test_aprovar_ids_aprova_todos_com_um_snapshot():
    estado = _estado_com(3)
    n = estado.aprovar_ids([r.id for r in estado.registros])
    assert n == 3 and all(_aprovado(r) for r in estado.registros)
    estado.desfazer()
    assert not any(_aprovado(r) for r in estado.registros)  # 1 undo desfaz o lote
```

- [ ] **Step 2: Rodar — falha.** FAIL (`aprovar_ids` não existe).
- [ ] **Step 3: Implementar** `aprovar_ids` extraindo a transição de aprovação hoje embutida no fluxo linha-a-linha (reusar, não duplicar). Wiring: `_aprovar_e_proximo` passa a chamar `aprovar_ids(_linhas_selecionadas())` quando a seleção tem 2+ linhas; com 1 linha, comportamento atual (aprova e pula pra próxima).
- [ ] **Step 4: Rodar — passa.** PASS.
- [ ] **Step 5: Commit** `feat(ui): aprovar em lote as linhas selecionadas (um undo por lote)`

### Task 11: "Aplicar à seleção" (propagar edição)

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py` (novo `aplicar_valor_em_lote`)
- Modify: `src/tdt/ui/tela_revisao.py` (ação de menu de contexto da tabela)
- Test: `tests/test_estado_lote.py`

**Interfaces:**
- Produces: `ModeloSinais.aplicar_valor_em_lote(ids: list[str], coluna: str, valor) -> int` — só colunas em `_EDITAVEIS`; um snapshot; usa o mesmo `setData`/validação da edição individual; retorna aplicados.

- [ ] **Step 1: Teste que falha**

```python
def test_aplicar_valor_em_lote_propaga_coluna_editavel():
    modelo = _modelo_com(3)
    n = modelo.aplicar_valor_em_lote(_ids(modelo), "Módulo", "BC2")
    assert n == 3 and all(r.modulo.nome == "BC2" for r in _regs(modelo))

def test_aplicar_valor_em_lote_recusa_coluna_nao_editavel():
    modelo = _modelo_com(2)
    assert modelo.aplicar_valor_em_lote(_ids(modelo), "Confiança", 1.0) == 0
```

- [ ] **Step 2: Rodar — falha.** FAIL.
- [ ] **Step 3: Implementar** o método no modelo (loop de `setData` com snapshot único) + menu de contexto "Aplicar '<valor>' às N selecionadas" que aparece após edição com seleção múltipla (explícito por decisão de spec §7.3 — nunca propaga automático).
- [ ] **Step 4: Rodar — passa.** PASS.
- [ ] **Step 5: Commit** `feat(ui): acao 'Aplicar a selecao' propaga edicao a linhas selecionadas`

### Task 12: Endereço editável com validação

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py` (`_EDITAVEIS` + `setData` das colunas de endereço)
- Test: `tests/test_modelo_tabela.py`

**Interfaces:**
- Produces: colunas "Endereço" e "Endereço Output" editáveis; parser aceita `900` e `900;901`; valida int 0..65535; inválido → recusa (setData retorna False), sem mutação.

- [ ] **Step 1: Teste que falha**

```python
def test_endereco_editavel_grava_indices():
    modelo = _modelo_com(1)
    assert modelo.setData(_idx(modelo, 0, "Endereço"), "900;901", Qt.EditRole)
    assert _regs(modelo)[0].enderecamento.indices == (900, 901)

def test_endereco_invalido_recusado():
    modelo = _modelo_com(1)
    antes = _regs(modelo)[0].enderecamento.indices
    assert not modelo.setData(_idx(modelo, 0, "Endereço"), "abc", Qt.EditRole)
    assert not modelo.setData(_idx(modelo, 0, "Endereço"), "70000", Qt.EditRole)
    assert _regs(modelo)[0].enderecamento.indices == antes
```

- [ ] **Step 2: Rodar — falha.** FAIL.
- [ ] **Step 3: Implementar** — adicionar as 2 colunas a `_EDITAVEIS`; no `setData`, ramo de endereço: `tuple(int(p) for p in valor.split(";"))`, validar `all(0 <= v <= 65535)`, gravar com `dataclasses.replace` no `enderecamento` (`indices` / `indices_saida`), snapshot p/ undo.
- [ ] **Step 4: Rodar — passa.** PASS.
- [ ] **Step 5: Commit** `feat(ui): enderecos input/output editaveis com validacao DNP3`

### Task 13: Colunas "Pareado" e "Sheet origem" + nome hierárquico no painel

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py` (2 colunas novas em `COLUNAS` + `_texto`)
- Modify: `src/tdt/ui/tela_revisao.py:29-32` (entram no default) e `:211-244` (nome hierárquico no painel lateral)
- Modify: `src/tdt/engine_tdt.py` (expor `nome_hierarquico(rec, subestacao)` público se hoje for `_nome_hierarquico` privado — rename com re-export, sem duplicar a lógica)
- Test: `tests/test_modelo_tabela.py`

**Interfaces:**
- Produces: coluna "Pareado" → `"Sim"` (`direcao=="InputOutput"`), `"Órfão"` (Output sem `indices`), `"—"` (Input puro); coluna "Sheet origem" → `sheet_origem(rec)` (função existente `modelo_tabela.py:60`); painel lateral mostra `nome_hierarquico(rec, subestacao)` — mesmo texto do Custom ID do TDT.

- [ ] **Step 1: Teste que falha**

```python
def test_coluna_pareado():
    assert _texto_col(_rec_fundido(), "Pareado") == "Sim"
    assert _texto_col(_rec_input(), "Pareado") == "—"

def test_coluna_sheet_origem():
    assert _texto_col(_rec(id="BC2:12"), "Sheet origem") == "BC2"
```

- [ ] **Step 2: Rodar — falha.** FAIL.
- [ ] **Step 3: Implementar** (colunas + painel). Conferir que `proxy_revisao` e as larguras salvas não quebram com colunas novas (índices por nome, não por posição).
- [ ] **Step 4: Rodar — passa.** PASS (suíte UI inteira).
- [ ] **Step 5: Commit** `feat(ui): colunas Pareado e Sheet origem + nome hierarquico no painel`

### Task 14: Contadores pendentes/total por sheet

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py:269-280` (`pendentes_por_sheet` → também totais)
- Modify: `src/tdt/ui/tela_revisao.py:304-317` (`_rotulo_aba`)
- Test: `tests/test_modelo_tabela.py`

**Interfaces:**
- Produces: `ModeloSinais.contagem_por_sheet() -> dict[str, tuple[int, int]]` (pendentes, total); rótulo da aba vira `"BC1 (3/57)"`; aba "Tudo" mostra o global.

- [ ] **Step 1: Teste que falha**

```python
def test_contagem_por_sheet_pendentes_e_total():
    modelo = _modelo_com_sheets({"BC1": (3, 57), "BC2": (1, 40)})
    assert modelo.contagem_por_sheet()["BC1"] == (3, 57)
```

- [ ] **Step 2: Rodar — falha.** FAIL.
- [ ] **Step 3: Implementar** (estender a função existente; `pendentes_por_sheet` pode virar wrapper de compatibilidade ou ser substituída nos 2 call-sites).
- [ ] **Step 4: Rodar — passa.** PASS.
- [ ] **Step 5: Commit** `feat(ui): abas mostram pendentes/total por sheet`

---

## Fase 7 — UI de revisão: par de posição + double-click (E5 restante)

### Task 15: Formar par de posição (MultiCoord) + swap DJA1↔DJF1

**Files:**
- Modify: `src/tdt/ui/estado.py` (novos `formar_par_posicao`, `trocar_sigla_par`)
- Modify: `src/tdt/ui/tela_revisao.py` (botão/menu "Formar par de posição" com 2 linhas selecionadas; diálogo de sigla DJF1/DJA1/SEC\*)
- Test: `tests/test_estado_par_posicao.py`

**Interfaces:**
- Consumes: catálogo de siglas de posição de `pareamento_polaridade` (DJF1/DJA1 + 7 SEC\*) e o formato de fusão de `normalizador_estrutural.corrigir` (datatype `MultiCoord`, `indices=(a, b)`).
- Produces: `AppState.formar_par_posicao(id_a, id_b, sigla) -> str | None` — valida mesmo módulo + mesmo equipamento + 1 endereço cada; devolve mensagem de erro ou None (sucesso: registro fundido MultiCoord com a sigla escolhida, segundo registro removido, snapshot único). `AppState.trocar_sigla_par(id_, nova_sigla)` — troca DJA1↔DJF1 (ou SEC\*) mantendo endereços/par.

- [ ] **Step 1: Teste que falha**

```python
def test_formar_par_posicao_funde_multicoord():
    estado = _estado_com_regs([_rec(id="s:1", ind=(900,)), _rec(id="s:2", ind=(901,))])
    erro = estado.formar_par_posicao("s:1", "s:2", "DJF1")
    assert erro is None
    (r,) = estado.registros
    assert r.tipo.datatype == "MultiCoord" and r.enderecamento.indices == (900, 901)
    assert _sigla(r) == "DJF1"

def test_formar_par_recusa_modulos_diferentes():
    estado = _estado_com_regs([_rec(id="s:1", mod="BC1"), _rec(id="s:2", mod="BC2")])
    assert estado.formar_par_posicao("s:1", "s:2", "DJF1") is not None

def test_trocar_sigla_par_preserva_enderecos():
    estado = _estado_com_regs([_rec_multicoord("DJA1", ind=(900, 901))])
    estado.trocar_sigla_par("s:1", "DJF1")
    (r,) = estado.registros
    assert _sigla(r) == "DJF1" and r.enderecamento.indices == (900, 901)
```

- [ ] **Step 2: Rodar — falha.** FAIL.
- [ ] **Step 3: Implementar** — fusão espelha o formato que `normalizador_estrutural.corrigir` produz (mesmos campos; conferir num registro fundido real antes de codar); sigla escolhida limita-se ao catálogo de posição (validação); tudo via `dataclasses.replace`. Diálogo simples (`QInputDialog`/combo) na tela.
- [ ] **Step 4: Rodar — passa.** PASS.
- [ ] **Step 5: Commit** `feat(ui): formar par de posicao MultiCoord e trocar DJA1<->DJF1 na revisao`

### Task 16: Double-click × formatação — reproduzir e corrigir

**Files:**
- Modify: (condicional ao achado) `src/tdt/ui/delegate_sinal.py:72-102` / `modelo_tabela.py`
- Test: `tests/test_modelo_tabela.py`

- [ ] **Step 1: Reproduzir** — `PYTHONPATH=src python -m tdt.ui_main`, carregar um resultado, double-click em cada coluna editável e cancelar/confirmar sem alterar. Suspeito principal: delegate lendo `DisplayRole` (texto formatado, ex. confiança `"0.85 (regra)"` ou módulo com sufixo) e gravando de volta via `EditRole` — round-trip suja o dado.
- [ ] **Step 2:** Se reproduzir: teste headless que faz o round-trip `data(EditRole) -> setData` e asserta valor idêntico ao original para toda coluna editável:

```python
def test_roundtrip_edicao_nao_altera_valor():
    modelo = _modelo_com(1)
    for col in _EDITAVEIS:
        idx = _idx(modelo, 0, col)
        antes = modelo.data(idx, Qt.EditRole)
        modelo.setData(idx, antes, Qt.EditRole)
        assert modelo.data(idx, Qt.EditRole) == antes
```

- [ ] **Step 3:** Corrigir (delegates `setEditorData` devem ler `EditRole` cru, nunca `DisplayRole` formatado). Se NÃO reproduzir: registrar no doc de achados e pedir ao usuário o passo-a-passo (coluna, valor, o que "quebrou").
- [ ] **Step 4: Commit** `fix(ui): edicao por double-click preserva o valor cru (roundtrip EditRole)`

---

## Fase 8 — Closeout

### Task 17: Ledger + DOX + status da spec A

**Files:**
- Modify: `docs/AGENTS.md` (Ledger: uma linha por decisão nova — piso_decisao, motivo modulo_duplicado_entre_sheets, f_r4 fallback, par de posição na UI, status das Tasks 8/9)
- Modify: `src/tdt/ui/AGENTS.md` (colunas novas, lote, par de posição)
- Modify: `docs/superpowers/specs/2026-06-26-spA-revisao-ui-lote-enderecamento-modulo-design.md` (nota de status: itens A1/A3 cobertos por este SP; A2-redo/A5 seguem pendentes)

- [ ] **Step 1:** Rodar a suíte inteira + gate final; registrar `pct` em `bench/resultados/spGAU_final.txt`.
- [ ] **Step 2:** Atualizar os três documentos.
- [ ] **Step 3:** Commit `docs: closeout SP-GAU (ledger, DOX, status spec A)`.

---

## Self-Review (cobertura spec → plano)

- E1 diagnóstico (itens 1b/3/5/8/10/11) → Task 1 ✓
- E2 f_r4 estágio (item 2) → Task 4 ✓ | piso absoluto (item 4) → Task 5 ✓ | par de fases invertido (item 14) → Task 4b ✓ (+ rastreio no diag, Task 1 Step 3b)
- E3 invariante → Task 7 ✓ | correções GAU → Task 8 (bloqueada por dado, hipóteses H1-H4) ✓
- E1→fix VAB (item 8) → Task 9 (bloqueada por dado) ✓
- E4 aviso módulo (item 11) → Task 6 ✓
- E5: aprovar lote (item 7) → Task 10 ✓ | propagar edição (item 7) → Task 11 ✓ | endereço editável (item 9) → Task 12 ✓ | Pareado + Sheet origem (itens 3/12) + nome hierárquico (item 9) → Task 13 ✓ | contadores (item 9) → Task 14 ✓ | par de posição / DJA1↔DJF1 (itens 1a/6) → Task 15 ✓ | double-click (item 7) → Task 16 ✓
- E6 motivos (item 13) → Task 2 ✓ | relatório origem → Task 3 ✓
- Painel lateral (item 9): já existe (`tela_revisao.py:211-244`) — só ganha o nome hierárquico (Task 13) ✓

**Ordem de risco:** Fases 0-2 (zero risco) → Fase 3 (gate individual) → Fase 4 (gate por segurança) → Fase 5 (invariante já; correções após diag+aprovação) → Fases 6-7 (UI, sem gate) → Fase 8 (closeout). Nenhuma rodada de gate agrupa duas mudanças.

**Assinaturas assumidas a conferir na execução** (padrão "localizar antes de codar", Steps já incluídos): campo da confiança calibrada no roteador (Task 5 Step 1), contrato dos helpers de `tests/test_dc_pairer.py` (Task 7), formato do registro fundido de `corrigir` (Task 15 Step 3).
