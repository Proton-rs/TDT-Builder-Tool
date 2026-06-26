# Roadmap consolidado — Observações 26/06 + Treinamento

**Data:** 2026-06-26
**Status:** Consolidação para o plano de implementação
**Propósito:** juntar as 8 specs criadas nesta sessão num único índice com dependências e ordem de implementação em fases. Cada spec mantém seu detalhe próprio; este doc é o mapa.

---

## As specs

| Spec | Título | Observações | Risco |
|------|--------|-------------|-------|
| **A** | Revisão UI: lote, endereçamento, módulo editável | §1.1/1.2/1.3/1.4/2.1/4.4 | baixo |
| **B** | Correções de scoring e pareamento | §2.2/3.1/3.2 | **alto (B2 recalibra)** |
| **C1** | Identidade e tipo do módulo (determinístico) | §4.2/4.3 | médio |
| **C2** | Inferência de equipamento por topologia | §4.1 | médio |
| **C3** | Mineração da Full Base (catálogo + Measurement Type) | §5.1/5.3 | médio (offline) |
| **C4** | Contexto estendido da planilha | §5.2 | baixo |
| **D** | Qualidade (FP/adversarial) e geração de saída | §6.1/6.2/7.1 | baixo |
| **E** | Treinamento / calibração probabilística | encoder e5, pesos, calibrador | **alto** |

**Já entregue nesta sessão:** lista padrão **v4** (v3 + DJF1 enriquecido da v2) como novo default.

---

## Dependências (grafo)

- **Contrato compartilhado:** `Modulo.tipo` + `TIPOS_MODULO` — criado por quem entrar primeiro entre **A4** e **C1**.
- **C1 → C2** (topologia precisa do tipo de módulo); **C1 → A4** (auto-preencher tipo).
- **C1/C2 → B4** (guard-rail de fusão usa equipamento definido).
- **C3** é offline/independente; seu catálogo **popula** as tabelas de C1 (tipos) e C2 (topologia).
- **Mockup (corruptor 5 níveis)** — pré-requisito compartilhado: **E** (treino/validação) e **D3** (corpus adversarial = nível 5). Usa a lista v4.
- **E** é dona da calibração que **B2** e **C** deferiram; **E supersede** o temperature mínimo da B2 quando madura.
- **D2/D3** (gate de FP) protege as mudanças arriscadas (B, E) — deve existir **antes** delas.

---

## Ordem de implementação (gate-first, TDD)

### Fase 0 — Fundações (paralelas, sem dependências)
- **D1** — `caminho_unico` (não sobrescrever saída). Trivial.
- **Mockup** — gerador determinístico de 5 níveis sobre a lista v4 (design detalhado pendente — retomar as 2 perguntas dispensadas: método/volume/formato).
- **C3** — script offline de mineração → `catalogo_sinais.json` + `measurement_type.json` versionados.

### Fase 1 — Rede de segurança + raiz de domínio
- **D2/D3** — gate duro de FP + corpus adversarial (usa o mockup). Estabelece a malha de proteção **antes** das mudanças de scoring.
- **C1** — identidade/tipo do módulo + contrato `Modulo.tipo`/`TIPOS_MODULO`.

### Fase 2 — Domínio + UI
- **C2** — inferência de equipamento por topologia (depende de C1; pode usar catálogo da C3).
- **C4** — contexto estendido da planilha (alimenta C1/regras).
- **A** — revisão UI (lote, undo/redo, End.Input/Output/Pareado, módulo+tipo editáveis, travar visão, reordenar). A4 reusa o contrato da C1.

### Fase 3 — Correções de scoring
- **B1/B3/B4** — confiança de regra, DCpairer robusto, fusão de duplicados (bug-fix; B4 usa equipamento da C1/C2).
- **B2** — motor de regras como filtro pós-normalização + confiança via temperature (passo intermediário antes da E).

### Fase 4 — Treinamento / calibração (mais arriscada, protegida pela D)
- **E1 → E2 → E3 → E4** — calibração por-método, pesos aprendidos (acerto@top-1, FP=0), troca e5, calibrador Platt/isotonic por ECE. Usa mockup + bench/rotulos. Supersede o temperature da B2.

---

## Princípios transversais (de todas as specs)

- **Sem falsos positivos:** todo caso ambíguo vai pra revisão, nunca decide errado. B3/B4/C2 só adicionam itens a revisão.
- **Determinístico:** SP2/LLM em espera; tudo por regras + calibração.
- **Benchmark como gate:** nenhuma mudança mergeia com regressão de decisão/FP (`bench/benchmark.py`).
- **DOX:** cada mudança atualiza o AGENTS.md dono mais próximo.
- **Knobs só em `config.py`; contratos em `contracts.py`; `pipeline.py` é o único orquestrador.**
