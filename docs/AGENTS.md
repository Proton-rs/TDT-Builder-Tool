# AGENTS.md — docs

## Purpose
Materiais de origem (pipeline, inputs, templates, lista padrão) e specs do projeto.

## Local Contracts
- `superpowers/specs/`: specs de design (formato brainstorming). Implementar via `superpowers:writing-plans` → `executing-plans`, ou "implemente <spec> via TDD".
  - `2026-06-23-sp1-backbone-deterministico-design.md` (SP1 base — implementado)
  - `2026-06-23-sp1-melhoria-analise-design.md` (calibração + e5 + consenso + opostos)
  - `2026-06-23-sp1-melhoria-motor-regras-design.md`
  - `2026-06-23-sp1-melhoria-normalizacao-design.md`
  - `2026-06-24-sp4-ui-desktop-design.md` (SP4 UI Desktop — implementado)
  - `2026-06-24-sp4-ui-correcoes-design.md` (SP4 correções de usabilidade — implementado)
  - `superpowers/specs/2026-06-24-sp7-analise-lista-homogenea-deterministica-design.md` (SP7 caminho determinístico p/ lista homogênea — implementado)
  - `superpowers/specs/2026-06-24-sp8-ui-filtros-tela-inicial-pendente-design.md` (SP8 UI: filtros por coluna, abas, status pendente — implementado)
  - `superpowers/specs/2026-06-24-sp9-tdt-completude-usabilidade-design.md` (SP9 TDT: Output Coordinates, dropdowns, Measurement Type/Display Unit — implementado)
   - `superpowers/specs/2026-06-24-sp10-djf1-pareamento-polaridade-design.md` (SP10 DJF1 + pareamento de polaridade — implementado)
   - `superpowers/specs/2026-06-25-sp-revisao-ui-design.md` (Revisão UI: pareamento D+C, equipamento colunas, add/remover, filtro módulo, relatório formatado — spec, não implementado)
   - `superpowers/specs/2026-06-25-sp-tdt-input-coordinates-format.md` (TDT: Input Coordinates numérico — implementado)
   - `superpowers/specs/2026-06-25-sp-performance-pipeline.md` (Performance: batch encoding, scorer cache, lazy encoder, progresso UI, profiling — spec)
   - `superpowers/specs/2026-06-25-sp-analise-qualidade-matching.md` (Análise: tabela de qualidade, estatísticas, relatório exportável — spec)
   - Decomposição das observações 26/06 (`observacoes26062026.md`) em 4 specs (cada uma seu ciclo spec→plano):
     - `superpowers/specs/2026-06-26-spA-revisao-ui-lote-enderecamento-modulo-design.md` (A: edição em lote, undo/redo, colunas End.Input/Output/Pareado, módulo+tipo editáveis, travar visão, reordenar colunas — spec; §1.1/1.2/1.3/1.4/2.1/4.4)
     - `superpowers/specs/2026-06-26-spB-correcoes-scoring-pareamento-design.md` (B: confiança ausente/calibrada, motor de regras como filtro pós-normalização, DCpairer robusto, fusão de duplicados — spec; §2.2/3.1/3.2)
     - `superpowers/specs/2026-06-26-spC1-identidade-tipo-modulo-design.md` (C1: identidade real do módulo + classificação de tipo, determinístico — spec; §4.2/4.3). Raiz da decomposição C.
     - `superpowers/specs/2026-06-26-spC2-inferencia-equipamento-topologia-design.md` (C2: inferir equipamento pela topologia típica do módulo — spec; §4.1; depende de C1, alimenta guard-rail da B)
     - `superpowers/specs/2026-06-26-spC3-mineracao-full-base-design.md` (C3: minerar Export Full Base → catálogo de sinais por contexto + mapa Measurement Type, offline → artefatos JSON — spec; §5.1/5.3)
     - `superpowers/specs/2026-06-26-spC4-contexto-estendido-planilha-design.md` (C4: capturar título/observações/células superiores da sheet como contexto — spec; §5.2)
     - `superpowers/specs/2026-06-26-spD-qualidade-saida-design.md` (D: não sobrescrever saída, gate de falsos positivos, corpus adversarial — spec; §6.1/6.2/7.1)
   - `superpowers/specs/2026-06-26-spE-treinamento-calibracao-probabilistica-design.md` (E: calibração por-método + pesos de mescla aprendidos contra correção + mescla probabilística + troca e5 + calibrador Platt/isotonic — spec; eixo de treinamento; dona das pendências de calibração que B2/C deixaram em aberto)
   - `superpowers/specs/2026-06-26-lista-adms-v6-enriquecimento-por-auditoria-design.md` (v6: descrições enriquecidas com variantes reais mineradas de `Auditoria_Revisao.xlsx`, por sigla e sem boilerplate compartilhado, para matching — spec)
   - `superpowers/specs/2026-06-29-sp-categoria-dual-pass-fix-design.md` (Categoria: barreira de domínio no dual-pass — elimina 213 FPs de categoria trocada — **implementado**)
   - `superpowers/specs/2026-06-29-sp-ancoragem-sigla-explicita-design.md` (Ancoragem: detecta sigla explícita na descrição → injeta candidato + filtrar_subarvore limita ao sub-ramo da âncora; resolve 132 erros de família errada — **implementado**)
   - `superpowers/specs/2026-06-29-sp-pareamento-double-bit-posicao-design.md` (Pareamento double-bit: catálogo de 9 siglas de posição; pareamento_polaridade generalizado para Seccionadora (7 SEC* por palavra-função) + DJA1; posicao_ambigua para sem keyword — **implementado**)
   - Planos de implementação correspondentes em `superpowers/plans/2026-06-24-sp{7,8,9,10}-*.md`.
- Fontes de verdade de dados: `Pontos Padrao ADMS_v2.xlsx` (lista padrão de **ANÁLISE/matching**, **default** — descrições da v1 + fixes de campo + DJF1 enriquecido; descrições limpas, sem diluição). `Pontos Padrao ADMS_v5.xlsx` = mesma base v2 com a coluna `DESCRIÇÃO NOVA` **enriquecida** (append-only, ANSI C37.2 + domínio) para **DESCRIÇÕES/referência humana** — NÃO usar para matching (o texto compartilhado dilui a discriminação; comprovado por regressão no benchmark: acc 82→68%, prec 95→68%). v1/v3/v4 = histórico, não editar. `dnp3_template.xlsx` (template TDT), `input_*.xlsx` (exemplos), `Export_base_Full*.xlsx` (base real com multiplas Subestações e padrões de escrita diferentes, 97MB — não abrir inteiro).
- Não editar os `.xlsx` de origem; são insumos.

## Ledger de decisões arquiteturais
Decisão registrada ≠ estado do código. Antes de afirmar "foi decidido X, então o código faz X", conferir aqui. Atualizar no closeout de cada SP (junto com o DOX pass): toda decisão de spec ganha uma linha com status `implementado | pendente | revertido | superado`.

| Decisão | Spec/commit | Status no código |
|---|---|---|
| B2: motor de regras como filtro bounded (clamp+renormaliza, deltas em [0,1], recalibrar thresholds) | spB 26jun §B2 | **pendente por decisão** — SP-Unificado 08jul: usuário optou por pular a Fase 5 (alto risco de regressão; sintoma >100% já resolvido pelo clamp de exibição). Deltas seguem unbounded. Parcialmente superado: E4 (calibrador platt pós-mescla) + clamp de exibição no boundary (08jul) |
| Remoção de candidatos contraditórios | filtro_preciso (F1, SP-G Task 6) | implementado — módulo próprio; motor_regras nunca remove |
| TFIDF → BM25 | SP-H 03jul | implementado (com fix de dedup de sigla duplicada) |
| type_severidade no corpus vetorial | SP-METADADOS Task 5 | **revertido** (36c2b68) — regrediu o gate |
| Stemmer N6 | 26jun | **gateado off** — regrediu bench |
| Lista v5 (descrições enriquecidas) para matching | 26jun | **rejeitado** — diluição comprovada (acc 82→68%); matching usa v2 |
| B1: confiança de decisão por regra (candidatos=() → UI vazia) | spB 26jun §B1 | implementado 08jul (display-only: "1.00 (regra)" em modelo_tabela/tela_revisao) |
| Gate `equipamento_ambiguo` (C2) | spC2 26jun | **superado** — Spec C: dc_pairer arbitra (sem-comando→TDT, comando→pareamento_ambiguo); teste garante que o motivo NÃO aparece |
| e5/reranker (troca de embedding) | spE 26jun / spD3 01jul | **rejeitado** (3ª rodada, empate com MiniLM e modelo 1GB maior); capacidade dorme em `dados/encoder`+`indice_vetorial` (param `prefixo`); `config.e5_prefixos` é o knob dormente (bench/diag usa) — não remover |
| `matchers/cross_encoder.rerank` | SP-G | **dormente** — implementado, só teste usa; wiring pendente de decisão (mesma família do e5) |
| 7 regras SE/ENTÃO propostas (79LO/86, SF6 estágios, 50BF, mola→BB*, CDC/OLTC, SECG, sincronismo) | conhecimento_sinais.md §"Itens acionáveis" / SP-Unificado 08jul | **fechadas** — item 3 (f_sf6, gate 66.9→67.4), item 6 (f_79lo), item 1 (f_50bf), item 2 (mola→bobina) implementados individualmente com gate ≥ baseline; item 4 (SECG) já coberto (status sozinho não é gap), item 5 (CDC/OLTC) já coberto (normalizador), item 7 (sincronismo) já coberto (especificidade_qualificador) |
| `f_posicao` fora do registro `_FILTROS` | SP-G Task 6 | **deliberado** — aplicado separado (filtro_preciso:226); registrar duplicaria aplicação |
| spC3 (mineração full base), spE2 (mescla probabilística/pesos aprendidos) | specs 26jun | **pendente** — nunca viraram plano; specs grandes, cada uma exige ciclo spec→plano→gate |
| spC4 (contexto de topo da sheet no corpus) | spC4 26jun / SP-Unificado 08jul | **testada, revertida** — implementada e medida; contexto constante por sheet dilui embedding: gate 67.4→50.1. Arquivada (bench/resultados/spUNI_spC4.txt) |
| spD (corpus adversarial anti-FP) | spD 26jun / SP-Unificado 08jul | **implementado** — tests/corpus_adversarial.py trava invariantes de normalização (religamento≠desligamento, SGF/ATUADO, fase A, mola→bobina); 50F1/51N1 truncadas ficam xfail (gate real: casos_travados.csv) |
| Dataclass `Pareamento` (contrato tipado D+C p/ UI) | SP-REVISAO-UI / SP-Unificado 08jul | **implementado** — contracts.py (frozen); lógica de pareamento segue em dc_pairer (não alterado) |
| Classificação de direção/comando | D1-D4 / SP-Unificado Fase 8 | **bloqueada por dado** — diagnóstico 08jul: entrada não sinaliza direção textualmente (156/243 comandos reais têm texto de puro status). Direção é propriedade de família de Message Mapping, não regra de texto. Decisão de design pendente do usuário (docs/superpowers/specs/2026-07-08-direcao-comando-diagnostico.md) |
| Categoria DiscreteAnalog (TAP) — 3ª aba da lista padrão + sheet de saída | SP-Pendencias-09jul Fase 3 (Tasks 6-8) | **implementado** — v7=v2+aba DiscreteAnalog (default→v7; matching v2 intacto); `lista_padrao` lê a aba (+5 campos, retrocompat); `engine_tdt.gerar` roteia por sigla (3-vias) p/ `DNP3_DiscreteAnalog`; hoje só TAP (exceção só em transformadores) |
| Lista v7 = v2 + aba, NÃO v6 | SP-Pendencias-09jul 09jul (decisão usuário) | **implementado** — basear em v6 adotaria descrições enriquecidas que mudam o matching de todos os sinais (fora de escopo + confunde gate); v7 preserva matching da v2 |
| Auto-tuning de pesos de mescla | SP-Pendencias-09jul Fase 5 (Task 10) | **MANTER 0.70/0.25/0.05** — `bench/tune_pesos.py` (grid simplex + validação no gate real): nenhum combo supera o atual em acertos absolutos no gate (atual iguais=649 vs 626/626/613). Estágio-1 (ROTULOS) favorece rebalancear mas não generaliza. Config inalterado; combos de maior *pct* (menos decididos) são trade-off de produto (follow-up) |
| Remote Point Alias / measurement types / device mapping homogêneo / nomes de arquivo | SP-Pendencias-09jul Fase 1-2 (Tasks 1-4) | **implementado** — alias `%Y%m%d`; `_MEASUREMENT_TYPE_PT_EN` cobre 12 tipos (KMDF→Unitless); módulo homogêneo compõe tipo+nº operativo do header (AL+23=AL23); nomes `TDT_<SUB>_<YYYYMMDD>[_vN].xlsx` (`nomes_saida`) |
| Boot da UI lazy-load (encoder + pipeline) | SP-Pendencias-09jul Fase 4 (Task 9) | **implementado** — `worker.py`/`ui_main.py`/`tela_geracao.py` não importam encoder/pipeline no topo; boot 17.8s→1.18s; teste de regressão `test_boot_sem_transformers` (subprocess) trava transformers/sklearn fora do boot |
| Gate `gate_tdt_real` Input Coordinates por sheet | SP-Pendencias-09jul Task 8 | **parcial (deliberado)** — DiscreteSignals=31, DiscreteAnalog=34 (índices reais). AnalogSignals mantido em 31 (índice real=47) p/ preservar baseline; **FOLLOW-UP**: analógicos são silenciosamente excluídos do gate (bug latente pré-existente) e o keying por endereço achatado colide entre categorias (TAP@1023 vs discreto) |
| 10 siglas homogêneas faltando na lista padrão (FGOO, 86RM, família TCT/81) | SP-Pendencias-09jul Task 5 (diagnóstico) | **FOLLOW-UP** — `bench/diag_pendentes_homogeneo.py` classificou; adicionar à lista padrão exige dado de domínio (desc/signal type/MM/severidade), não fabricar. Fora do escopo desta SP |

## Verification
Specs revisadas pelo usuário antes de implementar.
