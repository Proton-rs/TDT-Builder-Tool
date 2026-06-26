# Lista Padrão ADMS v5 — descrições enriquecidas para matching — Design

**Data:** 2026-06-26
**Status:** aprovado (brainstorming) — pronto para virar plano de implementação

## Objetivo

Produzir `docs/Pontos Padrao ADMS_v5.xlsx`: a lista padrão com as descrições
(`DESCRIÇÃO NOVA`) **enriquecidas para melhorar o matching**, partindo das
descrições da **v1** (preservadas verbatim) e **só adicionando** informação —
sem o desvio/erros que a v3 introduziu. Após validar no benchmark, a v5 vira o
novo default (substitui a v4).

## Contexto e diagnóstico (o que foi confirmado nos arquivos)

- A lista é o gabarito que os scorers (tfidf/vetorial/fuzzy) comparam contra os
  sinais reais. `DESCRIÇÃO NOVA` (coluna 1 de `DiscreteSignals`/`AnalogSignals`)
  é o **corpus de matching** — `lista_padrao.py` lê essa coluna; `bench/benchmark.py`
  pontua contra ela.
- **v1 e v2 têm descrições byte-idênticas** (0 diffs em 639 disc + 55 anal únicos).
  Os "fixes" da v2 estão em **outras colunas** (SIGNAL TYPE, DIRECTION, MM, FUNÇÃO,
  flags LINHA/BARRA/TRAFO/ALIMENTADOR/TRANSFERÊNCIA) + descrição do DJF1 enriquecida.
  ⇒ **partir da v2 já entrega as descrições da v1**; os dois objetivos não conflitam.
- **v3 reescreveu 250/639 descrições discretas** e introduziu **erros factuais**.
  Gerada pelo script `update_ansi_descriptions.py`, cujos 3 defeitos guiam este design:
  1. **Sobrescreveu** `DESCRIÇÃO NOVA` (`ws.cell(row,2).value = desc_b`) — destruiu o texto v1.
  2. **Genérico por código-base**: `50N`, `50F2`, `50CA` viraram todos "50 - Sobrecorrente
     Instantânea", perdendo neutro/fase (a distinção que mais importa pro matching).
  3. **Mapeamentos ANSI errados**: `24` → "sobrecorrente com reset de sobrecarga"
     (ANSI 24 é Volts/Hz sobreexcitação — a v1 estava certa); `61` → "potência reversa"
     (isso é ANSI 32).
- **Default atual = v4** (`defaults.py`, `cli.py`, `test_ui_defaults.py`), que é
  "v3 + DJF1". Ou seja, **o default em produção já carrega as descrições falhas da v3.**
  Logo este trabalho efetivamente substitui a v4.
- **Não editar v1/v2/v3/v4** (são histórico, conforme `docs/AGENTS.md`). A v5 é cópia
  fresca da v2.

## Decisões travadas (do brainstorming)

- **Objetivo:** melhorar o matching (não só documentação). Validar no benchmark.
- **Escopo:** todas as descrições — `DiscreteSignals` (692 linhas) + `AnalogSignals` (62 linhas com sigla).
- **Recipe:** **append-only, profundidade "moderada"** (texto v1 verbatim + função ANSI
  expandida + 2–4 sinônimos/termos de alto valor).
- **Conflito v1 × ANSI:** **preservar v1 verbatim + flagar** num sidecar para o usuário
  decidir caso a caso. Nada é sobrescrito sem aprovação.
- **Default:** v5 vira default **após** o benchmark confirmar precisão ≥ baseline.

## Superfície do trabalho (medida nos dados)

`DiscreteSignals` (692 linhas, 639 siglas únicas):
- **287 linhas ANSI-numeradas**, 26 códigos-base distintos:
  `20 21 24 25 26 27 32 43 46 49 50 51 59 61 62 63 67 71 78 79 81 85 86 87 90 94`.
- **405 linhas não-ANSI** (370 siglas únicas): compostas (`263A` = "20C 20T 63T - ALARME…"),
  funcionais (`TAL`, `TPPM`, `ABBN`), e a família formulaica `AJUSTE PARA ALxx` / `81Ux`.

`AnalogSignals` (62 linhas com sigla, 55 únicas): quase todas medições
(`CORRENTE/TENSÃO/POTÊNCIA/TEMPERATURA/FREQUÊNCIA/ÂNGULO`), 4 ANSI (25, 61).

## Recipe de enriquecimento (o contrato exato)

Formato por linha, **append-only**:

```
<texto v1 EXATO> — <expansão da função> [, <2–4 termos de alto valor>]
```

- O texto da v1 fica **verbatim no início** ⇒ um diff mostra só o que foi acrescentado
  (auditável e reversível). O matcher canoniza/tokeniza (uppercase, remove pontuação),
  então o separador (` — `, parênteses) é só legibilidade humana — não vira token.
- A parte **compartilhada** da família fica curta (ex.: "ANSI 50 SOBRECORRENTE INSTANTÂNEA");
  os termos **distintivos** do sufixo (NEUTRO, FASE A, TEMPORIZADO…) são reforçados ⇒
  enriquecer **ajuda** a discriminar dentro da família, não embaça.
- Tudo em PT, maiúsculas (convenção do corpus). Não introduzir abreviações novas
  (usar palavras inteiras; o canonizador expande só um conjunto conhecido).

Exemplos (worked):

| sigla | v1 (preservado) | v5 (append moderado) |
|---|---|---|
| `50N` | `50 - SOBRECORRENTE INSTANTANEA NEUTRO` | `50 - SOBRECORRENTE INSTANTANEA NEUTRO — ANSI 50N, PROTEÇÃO INSTANTÂNEA DE SOBRECORRENTE NEUTRO/TERRA, DISPARO POR FALTA À TERRA` |
| `24` | `24 - TRIP SOBREEXCITACAO (VOLTS HERTZ)` | `24 - TRIP SOBREEXCITACAO (VOLTS HERTZ) — ANSI 24, RELÉ VOLTS/HERTZ, PROTEÇÃO CONTRA SOBREEXCITAÇÃO (FLUXO MAGNÉTICO)` |
| `IN` | `CORRENTE NEUTRO` | `CORRENTE NEUTRO — CORRENTE RESIDUAL DE NEUTRO/TERRA (IN), MEDIÇÃO AMPÈRES (A)` |

## Backbone de precisão (a salvaguarda central)

1. **Discretos ANSI-numerados** → tabela **ANSI/IEEE C37.2 verificada** (device-number →
   função canônica em PT), construída a partir do padrão e **web-verificada** nos códigos
   ambíguos. Os 26 códigos presentes são um conjunto fechado e pequeno → verificável.
   Mais um **glossário de sufixos** brasileiros (F=fase, N=neutro, T=temporizado/trip,
   I=instantâneo, CC=corrente contínua/comando, etc.).
2. **Não-ANSI (discretos + analógicos)** → sheets internas do próprio workbook como fonte
   (`DMS Signal Explanation` = 1140 linhas, `Information` = 109 linhas), + domínio ADMS
   (skills `especialista-ADMS`/`especialista-ADMS-TDT`), + `TIPO DE MEDIÇÃO`/`UNIDADE`
   para analógicos. Compostas (`263A`) reusam a tabela ANSI nos códigos embutidos.
3. **Sidecar de conflitos** (`docs/v5_conflitos_ansi.md`): toda sigla onde o
   padrão ANSI correto contradiz o **próprio texto da v1** entra numa lista para o
   usuário decidir. **Preservar v1, nunca sobrescrever sem aprovação.** (Nota: `24` e
   `61` NÃO são conflitos — a v1 está correta neles; foi a v3 que errou. O sidecar pode
   até sair vazio se a v1 não tiver erros próprios.)

## Artefatos de saída

- `docs/Pontos Padrao ADMS_v5.xlsx` — cópia da v2 com **só** a coluna `DESCRIÇÃO NOVA`
  de `DiscreteSignals` e `AnalogSignals` reescrita (append-only). Todo o resto idêntico à v2.
- `docs/v5_conflitos_ansi.md` — sidecar de conflitos v1×ANSI para revisão humana.
- `docs/v5_diff_descricoes.csv` — diff antes/depois (v1 → v5) de todas as descrições
  (colunas: sigla, sheet, descrição v1, descrição v5, termos acrescentados), para revisão.

## Validação

- **Limitação assumida de cara:** o ground-truth do benchmark tem só 28 pares
  (`bench/rotulos.py`). Logo o benchmark é **guarda de regressão** (pega se o
  enriquecimento quebra um match conhecido), **não** um medidor de melhoria ampla.
  Melhoria ampla é uma aposta fundamentada (mais termos corretos → casa mais
  fraseados reais); medir isso de verdade exigiria ampliar o ground-truth (item já
  pendente, fora deste escopo).
- Rodar `bench/benchmark.py` com a v5 vs o baseline (v1), **em lotes por família ANSI**,
  exigindo **precisão@decididos ≥ baseline** e acc@1 não-regredido. Se um lote regredir,
  ajustar o recipe daquele lote (menos termos), não desligar tudo.
- Revisão humana do `v5_diff_descricoes.md` + do sidecar de conflitos antes do switch de default.

## Switch de default (só após validação)

Trocar para v5 em: `src/tdt/defaults.py` (`DEFAULT_LISTA`), `src/tdt/cli.py`
(`--lista-padrao` default), `tests/test_ui_defaults.py` (assert), `docs/AGENTS.md`
(linha de fontes de verdade). Opcional: apontar `bench/benchmark.py` e os testes que
hoje usam v1 para a v5 — **decisão separada**, fora do caminho crítico.

## Não-objetivos (YAGNI / escopo fora)

- **Nenhuma mudança estrutural**: sem mexer em siglas, linhas, outras colunas, ou outras
  sheets. Sem dedupe de linhas analógicas. Só `DESCRIÇÃO NOVA`.
- **Não reescrever a v1**: append-only. Erros herdados da v1 vão pro sidecar, não são
  corrigidos silenciosamente.
- **Não editar v1/v2/v3/v4** (histórico).
- Não ampliar o ground-truth do benchmark aqui (esforço separado).
- Não mexer no canonizador/scorers/config.

## Riscos

- **Diluição de tf-idf**: append demais dilui os pesos dos termos núcleo. Mitigado pela
  profundidade "moderada" + termos compartilhados curtos + benchmark por lote.
- **Precisão ANSI**: errar um código-base repete o erro da v3. Mitigado por tabela
  verificada (26 códigos, conjunto fechado) + web-verify + append-only (texto v1 correto
  permanece ancorando) + sidecar de conflitos.
- **Benchmark fraco (28 pares)**: pega regressão grosseira, não melhoria fina. Assumido.

## Decomposição em fases (para o plano)

1. **Tabela ANSI C37.2 verificada** (26 códigos → função PT) + glossário de sufixos +
   detecção de conflito vs texto v1. Web-verify dos ambíguos. Teste: a tabela cobre os 26
   códigos presentes; o mecanismo de conflito marca uma sigla quando o texto v1 contradiz
   a função ANSI verificada (a lista resultante pode ser vazia).
2. **Compositor de enriquecimento** (puro): por linha → parse sigla (base+sufixo) → compõe
   o append moderado; não-ANSI → lookup nas sheets internas/domínio; analógico → grandeza+unidade.
   Append-only sobre o texto da linha. Testes unitários com casos-âncora (50N, 24, IN, 263A, AJUSTE).
3. **Geração da v5**: copia v2 → v5, reescreve `DESCRIÇÃO NOVA` (append-only) via openpyxl
   preservando o resto; emite sidecar de conflitos + diff antes/depois.
4. **Validação**: benchmark v5 vs v1 por família; revisão humana do diff + sidecar.
5. **Switch de default** (após validação): defaults.py, cli.py, AGENTS.md, tests.

## Limpeza (opcional)

Os scripts one-off `update_ansi_descriptions.py` e `update_ansi_uppercase_distinct.py`
(raiz do repo) produziram a v3 falha e não fazem parte de `src/`. Podem ser removidos
ou movidos para histórico — decisão à parte.
