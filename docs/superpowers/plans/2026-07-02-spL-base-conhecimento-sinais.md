# SP-L — Base de conhecimento de sinais + skills — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development ou superpowers:executing-plans. Tarefa de pesquisa/documentação — sem TDD, mas com critério verificável por task. Steps com checkbox.

**Goal:** `docs/conhecimento_sinais.md` cobrindo 100% das famílias da LP + skills `especialista-ADMS`/`especialista-ADMS-TDT` atualizadas (spec `2026-07-02-spL-base-conhecimento-sinais-design.md`).

**Architecture:** mineração determinística da LP primeiro (autoridade máxima), TDT reais depois, web por último (complementa, nunca sobrepõe arquivo real). Compilado por família ANSI.

## Global Constraints

- Conflito web × arquivo real → arquivo real vence, exceção anotada.
- Toda afirmação tem fonte (LP / TDT real / spec do projeto / URL).
- Skills não duplicam o compilado — referenciam.

---

### Task 1: Mineração da LP (esqueleto do compilado)

**Files:**
- Create: `bench/minerar_lp_conhecimento.py`
- Create: `docs/conhecimento_sinais.md` (esqueleto gerado + curadoria manual)

- [ ] Step 1: script que lê `docs/Pontos Padrao ADMS_v2.xlsx` (sheets DiscreteSignals/AnalogSignals/Message Mapping/DE->PARA) e emite, por família (prefixo ANSI 2-3 dígitos ou sigla alfabética):

```python
"""Gera o esqueleto de docs/conhecimento_sinais.md a partir da LP.
Por família: siglas, descrição-padrão, tipo ADMS, direção (Read/Write/RW),
estados (message mapping ...@...___...@...), grupo/categoria, DE->PARA.
Uso: python bench/minerar_lp_conhecimento.py > docs/conhecimento_sinais.md
"""
```

(corpo do script: openpyxl read_only, agrupamento por `_numero_lider`-like — reusar `tdt.motor_regras._numero_lider`; saída markdown com uma seção `## Família NN` por grupo e tabela de siglas.)

- [ ] Step 2: rodar e conferir: todas as siglas da LP aparecem em alguma família (contagem no fim do doc = nº de siglas da LP).
- [ ] Step 3: commit `docs(spL): esqueleto do compilado minerado da LP`

---

### Task 2: Enriquecimento com TDT reais + descobertas do projeto

**Files:**
- Modify: `docs/conhecimento_sinais.md`

- [ ] Step 1: cruzar com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`: nomenclaturas brutas reais por sigla (as descrições de input que a GTD usa), pares comando↔estado observados, cardinalidades reais por equipamento.
- [ ] Step 2: incorporar regras já provadas nas specs do projeto (fusão D+C, sigla persistente=LP, sem comando analógico, DJF1/DJA1, semântica de estados SP-E, whitelist por equipamento de `config.py`) — com link para a spec de origem.
- [ ] Step 3: commit `docs(spL): nomenclaturas reais + regras do projeto no compilado`

---

### Task 3: Pesquisa web (nomenclaturas e funcionamento)

**Files:**
- Modify: `docs/conhecimento_sinais.md`

- [ ] Step 1: pesquisar por família: ANSI/IEEE C37.2 (números de função), práticas de concessionárias BR (religamento 79, check de sincronismo 25, bloqueios 86/94, SGF/sobrecorrente de terra, seccionadoras motorizadas 43LR, mola do disjuntor, SF6, CDC/OLTC, GOOSE IEC 61850). Para cada: função real na subestação (1-3 frases), sinônimos de campo, exceções conhecidas.
- [ ] Step 2: anotar fontes (URLs); conflitos com a LP marcados `> **Conflito:** ...` com a LP vencendo.
- [ ] Step 3: seção final `## Candidatos a regra` — ≥ 5 itens acionáveis para o motor de regras (formato: SE texto contém X e candidato é Y ENTÃO ajuste, com evidência).
- [ ] Step 4: commit `docs(spL): pesquisa web por familia + candidatos a regra`

---

### Task 4: Atualização das skills

**Files:**
- Modify: `.claude/skills/especialista-ADMS/SKILL.md` (e arquivos auxiliares)
- Modify: `.claude/skills/especialista-ADMS-TDT/SKILL.md` (nome exato: conferir diretório)

- [ ] Step 1: ler as duas skills inteiras; listar afirmações que o projeto PROVOU erradas/obsoletas (cruzar com o compilado e as specs).
- [ ] Step 2: remover/corrigir cada uma; adicionar referência: "fonte canônica de conhecimento de sinais: `docs/conhecimento_sinais.md`". Não duplicar conteúdo do compilado.
- [ ] Step 3: revisão de consistência: nenhuma frase da skill contradiz o compilado.
- [ ] Step 4: commit `docs(spL): skills especialista atualizadas e apontando pro compilado`
