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
   - Planos de implementação correspondentes em `superpowers/plans/2026-06-24-sp{7,8,9,10}-*.md`.
- Fontes de verdade de dados: `Pontos Padrao ADMS_v2.xlsx` (lista padrão de **ANÁLISE/matching**, **default** — descrições da v1 + fixes de campo + DJF1 enriquecido; descrições limpas, sem diluição). `Pontos Padrao ADMS_v5.xlsx` = mesma base v2 com a coluna `DESCRIÇÃO NOVA` **enriquecida** (append-only, ANSI C37.2 + domínio) para **DESCRIÇÕES/referência humana** — NÃO usar para matching (o texto compartilhado dilui a discriminação; comprovado por regressão no benchmark: acc 82→68%, prec 95→68%). v1/v3/v4 = histórico, não editar. `dnp3_template.xlsx` (template TDT), `input_*.xlsx` (exemplos), `Export_base_Full*.xlsx` (base real com multiplas Subestações e padrões de escrita diferentes, 97MB — não abrir inteiro).
- Não editar os `.xlsx` de origem; são insumos.

## Verification
Specs revisadas pelo usuário antes de implementar.
