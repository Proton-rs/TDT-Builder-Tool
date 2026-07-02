# SP-G — Correções de classificação — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans. TDD obrigatório: RED → GREEN → commit. Steps com checkbox (`- [ ]`).

**Goal:** corrigir os 5 erros de classificação da spec `2026-07-02-spG-correcoes-classificacao-design.md` (79 qualificador, DJA1 forçado, "Secc." com ponto, fase A, SGF→SGFT).

**Architecture:** correções pontuais nas superfícies já existentes — N0/N1 (`normalizador.py`), motor de regras, e um guard pós-decisão novo. Diagnóstico instrumentado ANTES dos fixes cujos caminhos de decisão são desconhecidos (boost >1.0 do 79; DJA1 a 0.858).

**Tech Stack:** Python 3.14, pytest, openpyxl. Gates: `bench/benchmark.py` e `bench/gate_tdt_real.py`.

## Global Constraints

- `python -m pytest -q` verde ao fim de cada task.
- `PYTHONPATH=src python bench/benchmark.py` sem queda de acc/precisão nas tasks que tocam normalização/scoring.
- Corretude vs GTD real (`bench/gate_tdt_real.py`) não pode cair abaixo do baseline da Task 0.
- Commits pequenos, um por task (`feat(spG): ...` / `fix(spG): ...`).

---

### Task 0: Baseline de corretude vs TDT real

**Files:**
- Create: `bench/resultados/spG_baseline_gate.txt` (gerado, commitado)

**Interfaces:**
- Consumes: `bench.gate_tdt_real.comparar(nosso, real)` — existe.
- Produces: nº baseline `pct` que as tasks seguintes não podem reduzir.

- [ ] Step 1: rodar o gate contra o output atual

```powershell
$env:PYTHONPATH="src;bench"; python -c "from gate_tdt_real import comparar; r = comparar(r'output\LISTA 1 - GTD\TDT.xlsx', r'docs\TDT\exportTDT_UTR_GTD_1_20260626.xlsx'); print(f'comum={r.comum} iguais={r.iguais} pct={r.pct:.1f}'); [print(d) for d in r.divergencias[:50]]" | Tee-Object bench/resultados/spG_baseline_gate.txt
```

Expected: imprime `comum=... iguais=... pct=...` + lista de divergências (deve conter os casos 79/DJA1 da spec).

- [ ] Step 2: conferir que as divergências incluem os casos da spec (79→79OK etc.); anotar no fim do txt quais casos da spec aparecem.
- [ ] Step 3: commit — `git add bench/resultados/spG_baseline_gate.txt && git commit -m "test(spG): baseline gate TDT real pre-correcoes"`

---

### Task 1: Caso 1a — sinônimo SUCEDIDO→SUCESSO (N1)

**Files:**
- Modify: `src/tdt/normalizacao/normalizador.py` (dict `ABREVIACOES_EXTRA`)
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Produces: `canonizar("Religamento (79) - Bem Sucedido", cfg)` contém token `SUCESSO`.

- [ ] Step 1: teste RED

```python
def test_sinonimo_sucedido_vira_sucesso(config):
    # "BEM SUCEDIDO" (input) precisa casar com "COM SUCESSO" (descrição-padrão 79OK)
    canonico = canonizar("Religamento (79) - Bem Sucedido", config)
    assert "SUCESSO" in canonico.split()
    assert "SUCEDIDO" not in canonico.split()
```

(adaptar à fixture de Config já usada em `tests/test_normalizador.py`.)

- [ ] Step 2: `python -m pytest -q tests/test_normalizador.py -k sucedido` → FAIL
- [ ] Step 3: implementar — em `ABREVIACOES_EXTRA` adicionar `"SUCEDIDO": "SUCESSO",` (whole-token; "BEM" é removido como stopword ou fica inócuo)
- [ ] Step 4: `python -m pytest -q tests/test_normalizador.py` → PASS
- [ ] Step 5: commit `fix(spG): sinonimo SUCEDIDO->SUCESSO no N1 (caso 79OK)`

---

### Task 2: Caso 3 — pontuação periférica nos lookups do N0

**Files:**
- Modify: `src/tdt/normalizacao/normalizador.py` (`extrair_contexto_estrutural`)
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Produces: `extrair_contexto_estrutural("Secc. Barra Aberta")[1].equipamento_alvo == "Seccionadora"`.

- [ ] Step 1: testes RED

```python
def test_n0_equipamento_com_ponto_final():
    _, ctx = extrair_contexto_estrutural("Secc. Barra Aberta")
    assert ctx.equipamento_alvo == "Seccionadora"

def test_n0_equipamento_com_ponto_disj():
    _, ctx = extrair_contexto_estrutural("Disj. Intertravamento Manual Bloqueado")
    assert ctx.equipamento_alvo == "Disjuntor"
```

- [ ] Step 2: rodar → FAIL (token `SECC.`/`DISJ.` não casa whole-token)
- [ ] Step 3: implementar — helper de strip periférico e usar nos lookups por palavra:

```python
_PONTUACAO_BORDA = ".,;:()"

def _tok_limpo(tok: str) -> str:
    return tok.strip(_PONTUACAO_BORDA)
```

Em `extrair_contexto_estrutural`, no loop `for tok in base.split(): if tok in _EQUIPAMENTO_PALAVRA` → usar `_tok_limpo(tok)`. Aplicar também no match de `_FASE_TOKENS`/`FASES` em `_fase_no_texto` (tokens vêm do mesmo `base`).

- [ ] Step 4: rodar testes → PASS; `python -m pytest -q` inteiro verde
- [ ] Step 5: commit `fix(spG): N0 ignora pontuacao periferica nos lookups (Secc. com ponto)`

---

### Task 3: Caso 4 — fase vira anotação, token permanece no texto

**Files:**
- Modify: `src/tdt/normalizacao/normalizador.py` (`extrair_contexto_estrutural`, `_fase_no_texto`)
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Produces: contrato novo — N0 anota `ctx.fase` SEM remover o token do texto remanescente.

- [ ] Step 1: testes RED

```python
def test_n0_fase_anotada_e_token_mantido():
    texto, ctx = extrair_contexto_estrutural("Corrente Fase A")
    assert ctx.fase == "A"
    assert "A" in texto.split()          # discriminador continua p/ os scorers

def test_n0_fase_nao_remove_artigo_errado():
    # regressão: "A" artigo antes de "FASE A" não pode ser confundido
    texto, ctx = extrair_contexto_estrutural("CHAVE A FASE A")
    assert ctx.fase == "A"
    assert texto.split().count("A") == 2  # nada removido
```

- [ ] Step 2: rodar → FAIL
- [ ] Step 3: implementar — em `extrair_contexto_estrutural`, trocar o bloco de fase:

```python
    fase, _tok = _fase_no_texto(tokens)
    # anota apenas; o token fica no texto (discriminador para os scorers,
    # D2.1 já protege a letra do filtro de stopwords adiante)
```

`_fase_no_texto` deixa de devolver `token_a_remover` para remoção — pode manter a assinatura e o chamador ignora o 2º item (menor diff), ou simplificar para devolver só a fase. Escolher o menor diff que passe os testes existentes; atualizar testes antigos que assertavam a remoção.

- [ ] Step 4: `python -m pytest -q` → PASS
- [ ] Step 5: gate — `PYTHONPATH=src python bench/benchmark.py`: acc/precisão sem queda. Se cair, fallback da spec: reinjetar token canônico `FASE_<X>` em vez de manter cru — implementar e re-medir antes de prosseguir.
- [ ] Step 6: commit `fix(spG): fase anotada sem remover token do matching (caso fase A)`

---

### Task 4: Diagnóstico — caminho de decisão dos casos 1b (79 a 1.007) e 2 (DJA1 a 0.858)

**Files:**
- Create: `bench/diag_spg_decisor.py`
- Create: `bench/resultados/spG_diag_decisor.txt` (gerado, commitado)

**Interfaces:**
- Consumes: `tdt.pipeline.executar(input, template, lp, config=..., encoder=..., auditoria=...)`; `Auditoria` (`salvar_json`).
- Produces: causa raiz anotada (qual etapa gera score fixo 0.858 p/ DJA1 e boost >1.0 p/ 79) — insumo das Tasks 5 e 6.

- [ ] Step 1: escrever o script

```python
"""Diagnóstico SP-G: de onde vêm as decisões 79 (score>1) e DJA1 (0.858).
Uso: PYTHONPATH=src python bench/diag_spg_decisor.py <input_lista1.xlsx>
"""
import sys, json
from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.pipeline import executar

ALVOS = ("BEM SUCEDIDO", "INTERTRAVAMENTO", "RELIGAMENTO (79)", "DESLIGADO")

def main(input_path: str) -> None:
    cfg = Config(); aud = Auditoria()
    resultado, _wb = executar(
        input_path, "docs/dnp3_template.xlsx", "docs/Pontos Padrao ADMS_v2.xlsx",
        config=cfg, encoder=criar_encoder(cfg.modelo_embedding), auditoria=aud,
    )
    aud.salvar_json("bench/resultados/spG_diag_decisor_aud.json")
    for r in resultado.lista.registros:
        d = r.descricoes.bruta.upper()
        if any(a in d for a in ALVOS):
            print(f"{r.descricoes.bruta!r} -> {r.sigla_sinal} | just={r.justificativa}"
                  f" | cands={[(c.sigla, round(c.score,3), c.fonte) for c in (r.candidatos or [])[:4]]}")

if __name__ == "__main__":
    main(sys.argv[1])
```

(ajustar atributos conforme `contracts.py` se divergirem — o campo `fonte` do `Candidato` e `justificativa` do record existem; conferir nomes exatos antes de rodar.)

- [ ] Step 2: rodar com o MESMO input usado para gerar `output/LISTA 1 - GTD` (perguntar/confirmar o caminho; salvar saída com `| Tee-Object bench/resultados/spG_diag_decisor.txt`)
- [ ] Step 3: analisar: a `justificativa` identifica o decisor (fuzzy/e5/consenso/quadrante/polaridade); `fonte` identifica a origem do candidato (ancora_sigla/whitelist/expansão). Anotar no fim do txt: **decisor + origem do boost para cada caso**.
- [ ] Step 4: commit `test(spG): diagnostico decisor 79/DJA1`

---

### Task 5: Caso 1b — regra de especificidade de qualificador

**Files:**
- Create: `src/tdt/especificidade_qualificador.py`
- Modify: `src/tdt/pipeline.py` (após a decisão, no ponto que a Task 4 confirmar — região do skip `status=="decidido"`, ~linha 497)
- Test: `tests/test_especificidade_qualificador.py`

**Interfaces:**
- Consumes: `ListaPadraoADMS` (siglas + descrições), `SignalRecord` decidido.
- Produces: `preferir_irmao_qualificado(rec, lp, config) -> SignalRecord` — troca a sigla base pelo irmão qualificado quando exatamente 1 irmão casa; múltiplos irmãos casando → `status="revisao"`, motivo `qualificador_ambiguo`.

- [ ] Step 1: testes RED

```python
def test_bem_sucedido_prefere_79ok(lp, config):
    rec = _rec_decidido("Religamento (79) - Bem Sucedido", sigla="79")
    out = preferir_irmao_qualificado(rec, lp, config)
    assert out.sigla_sinal == "79OK"

def test_sem_qualificador_mantem_base(lp, config):
    rec = _rec_decidido("Religamento (79)", sigla="79")
    assert preferir_irmao_qualificado(rec, lp, config).sigla_sinal == "79"

def test_dois_irmaos_casando_vai_revisao(lp, config):
    # texto com dois qualificadores de irmãos distintos -> ambíguo
    rec = _rec_decidido("Religamento (79) Bloqueado Pronto", sigla="79")
    assert preferir_irmao_qualificado(rec, lp, config).status == "revisao"
```

(`_rec_decidido` = helper local do teste construindo SignalRecord com descrição canônica via `canonizar`.)

- [ ] Step 2: rodar → FAIL (módulo não existe)
- [ ] Step 3: implementar

```python
"""Pós-decisão: sigla base de família não engole qualificador presente no texto.

Se o decidido é prefixo de irmãos na LP (79 -> 79OK/79LO/79RE/79TF/79_1) e a
descrição-padrão de exatamente UM irmão tem token distintivo presente no texto
canônico do sinal, o irmão vence. Vários irmãos casando -> revisão.
"""
from __future__ import annotations
from dataclasses import replace

def _tokens(s: str) -> set[str]:
    return set(s.upper().split())

def preferir_irmao_qualificado(rec, lp, config):
    if rec.status != "decidido" or not rec.sigla_sinal:
        return rec
    base = rec.sigla_sinal.upper()
    texto = _tokens(rec.descricoes.normalizada)
    desc_base = next((s.descricao for s in lp.discretos if s.sigla.upper() == base), "")
    casando = []
    for s in lp.discretos:
        sig = s.sigla.upper()
        if sig == base or not sig.startswith(base.rstrip("_")):
            continue
        distintivos = _tokens(s.descricao) - _tokens(desc_base)
        if distintivos & texto:
            casando.append(s.sigla)
    if len(casando) == 1:
        return replace(rec, sigla_sinal=casando[0],
                       justificativa=f"{casando[0]} por qualificador (base {rec.sigla_sinal})")
    if len(casando) > 1:
        return replace(rec, status="revisao",
                       justificativa=f"qualificador ambíguo: {casando}")
    return rec
```

Comparar descrições via `canonizar` (mesma forma dos dois lados) — ajustar `_tokens` para receber texto já canônico. Registrar motivo `qualificador_ambiguo` em `contracts.py` (docstring `ItemRevisao`) e rótulo em `ui/modelo_tabela.py::_MOTIVO_LABEL`.

- [ ] Step 4: rodar testes → PASS
- [ ] Step 5: integrar no pipeline (ponto da Task 4) e reprocessar LISTA 1: `Religamento (79) - Bem Sucedido` sai `79OK`; contagem de decididos não cai (trocas, não perdas).
- [ ] Step 6: gate TDT real ≥ baseline Task 0; benchmark sem queda.
- [ ] Step 7: commit `feat(spG): regra de especificidade de qualificador (79OK nao perde p/ 79)`

---

### Task 6: Caso 2 — gate de posição para DJ*/SEC* de posição

**Files:**
- Modify: ponto decisor identificado na Task 4 (candidato provável: whitelist/boost de equipamento ou `expansao_candidatos`)
- Create (helper): função `eh_texto_de_posicao` em `src/tdt/pareamento_polaridade.py` (reusa os prefixos existentes)
- Test: `tests/test_pareamento_polaridade.py` (ou o teste do módulo decisor)

**Interfaces:**
- Produces: `eh_texto_de_posicao(texto_normalizado: str) -> bool` — True se contém prefixo `LIGAD|FECHAD|DESLIGAD|ABERT` ou token `NA`.

- [ ] Step 1: testes RED

```python
def test_texto_posicao():
    assert eh_texto_de_posicao("DISJUNTOR DESLIGADO")
    assert eh_texto_de_posicao("SECCIONADORA ABERTA")
    assert not eh_texto_de_posicao("DISJUNTOR INTERTRAVAMENTO")
    assert not eh_texto_de_posicao("MOLA DESCARREGADA")
```

- [ ] Step 2: rodar → FAIL
- [ ] Step 3: implementar em `pareamento_polaridade.py` (reusa `_LIGADO_PREFIXOS`/`_DESLIGADO_PREFIXOS`):

```python
_SIGLAS_POSICAO = frozenset({"DJF1", "DJA1", "SECC", "SECB", "SECT", "SECG", "SECF", "SECI", "SECL"})

def eh_texto_de_posicao(texto_normalizado: str) -> bool:
    tokens = texto_normalizado.upper().split()
    return ("NA" in tokens
            or _tem_prefixo(tokens, _LIGADO_PREFIXOS)
            or _tem_prefixo(tokens, _DESLIGADO_PREFIXOS))
```

- [ ] Step 4: aplicar o gate no decisor da Task 4: candidato cuja sigla ∈ `_SIGLAS_POSICAO` só pode DECIDIR se `eh_texto_de_posicao(rec.descricoes.normalizada)`; caso contrário o candidato de posição é rebaixado/removido daquele sinal (vai a revisão se nada mais decidir).
- [ ] Step 5: teste de integração RED→GREEN: `'Disj. 52-1 (01Q0) - Intertravamento'` NÃO decide DJA1; `'Disj. 24-3 (05Q0) - Desligado'` CONTINUA DJA1 (é posição legítima).
- [ ] Step 6: reprocessar LISTA 1 + gate TDT real ≥ baseline; separar no relatório as 96 linhas DJA1 em mantidas × re-roteadas.
- [ ] Step 7: commit `fix(spG): sigla de posicao exige palavra de posicao no texto`

---

### Task 7: Caso 5 — estado compatível pontua (SGF-Atuado → SGFT)

**Files:**
- Modify: `src/tdt/motor_regras.py` (regra nova, padrão de R3/fase), `src/tdt/config.py` (`pesos_regras["estado"]`)
- Read first: `src/tdt/semantica_estados.py` (API de extração/compatibilidade de estados — SP-E)
- Test: `tests/test_motor_regras.py`

**Interfaces:**
- Produces: regra R-estado — candidato cujos estados da LP são compatíveis com o estado extraído do texto ganha `+pesos_regras["estado"]`; incompatível: `-peso`.

- [ ] Step 1: ler `semantica_estados.py` e mapear: função que extrai estado do texto (ex. ATUADO) e estados da sigla na LP (ex. `NORMAL@ATUADO`). A regra usa essas funções — NÃO reimplementar parsing de estados.
- [ ] Step 2: teste RED (adaptar helpers existentes de `tests/test_motor_regras.py`):

```python
def test_regra_estado_compativel_pontua(config, lp):
    # 'PROTECAO SGF ATUADO': estado ATUADO casa com NORMAL@ATUADO de SGFT
    rec = _rec("Proteção SGF - Atuado")
    ajuste = regra_estado(rec, _candidato("SGFT"), lp, config)
    assert ajuste.delta > 0

def test_regra_estado_incompativel_penaliza(config, lp):
    # sigla só-comando (Write) não casa com texto de estado
    rec = _rec("Proteção SGF - Atuado")
    ajuste = regra_estado(rec, _candidato("79_EXC"), lp, config)
    assert ajuste.delta < 0
```

- [ ] Step 3: rodar → FAIL; implementar a regra no padrão das existentes (assinatura igual à R3), registrar em `aplicar_rastreado`, peso default `0.15` em `config.pesos_regras`.
- [ ] Step 4: teste de integração: `'Proteção SGF - Atuado'` com candidatos reais → SGFT vence e decide (se ainda ficar abaixo do threshold, registrar o score alcançado — o resgate da SP-H completa o caso; critério mínimo aqui: SGFT topo com gap > 0 sobre SGT2).
- [ ] Step 5: benchmark sem queda; commit `feat(spG): regra estado-compativel no motor (SGF-Atuado -> SGFT)`

---

### Task 8: Validação final SP-G

- [ ] Step 1: `python -m pytest -q` verde
- [ ] Step 2: `PYTHONPATH=src python bench/benchmark.py` sem queda vs pré-SP-G
- [ ] Step 3: reprocessar LISTA 1 e rodar gate: pct ≥ baseline Task 0 E casos da spec conferidos 1 a 1 (79OK, DJA1/intertravamento, Secc., fase, SGFT)
- [ ] Step 4: atualizar `bench/resultados/spG_baseline_gate.txt` → `spG_final_gate.txt`; anotar novos erros observados (prática: erros achados aqui alimentam o próximo lote)
- [ ] Step 5: commit final `docs(spG): resultado do gate pos-correcoes`
