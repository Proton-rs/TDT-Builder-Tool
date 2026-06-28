# AGENTS.md — Projeto TDT v2 (DOX root)

DOX é a hierarquia de contratos AGENTS.md deste projeto. Todo agente deve segui-la em qualquer edição.

## Core Contract
- AGENTS.md são contratos vinculantes para suas subárvores.
- Todo trabalho deve permanecer compreensível a partir do AGENTS.md mais próximo + todos os pais acima dele.

## Read Before Editing
1. Leia este root AGENTS.md.
2. Identifique cada arquivo/pasta que vai tocar.
3. Caminhe da raiz até cada alvo, lendo cada AGENTS.md no caminho.
4. O AGENTS.md mais próximo é o contrato local; os pais valem para regras globais.
5. Em conflito, o doc mais próximo controla detalhes locais, mas nenhum filho enfraquece o DOX.

Não confie na memória — releia a cadeia DOX aplicável na sessão antes de editar.

## Update After Editing
Toda mudança significativa exige um DOX pass antes de concluir. Atualize o AGENTS.md dono mais próximo quando a mudança afetar: propósito/escopo/responsabilidade; estrutura/contratos/workflow; entradas/saídas/restrições/artefatos; preferências do usuário; criação/remoção/índice de AGENTS.md. Remova texto obsoleto na hora.

## Closeout
1. Recheque os caminhos alterados contra a cadeia DOX.
2. Atualize docs donos e pais/filhos afetados; atualize os Child DOX Index.
3. Remova texto obsoleto. 4. Rode a verificação. 5. Reporte docs deixados inalterados e por quê.

---

## Purpose
Transformar planilha Excel de pontos de subestação em arquivo **TDT** (EcoStruxure ADMS). Pipeline em `docs/Pipeline-projetoTDT v2.svg`.

## Ownership
- Decomposição: **SP1** backbone determinístico+embeddings (DNP3) — implementado; **SP2** agentes LLM (em espera); **SP4** UI desktop — implementado. SP3 absorvido no SP1.
- Código vive em `src/tdt/` (pipeline: módulos raiz + sub-dirs `normalizacao/`, `analise/`, `scoring/`, `matchers/`, `dados/`) e `src/tdt/ui/` (UI PySide6). Specs em `docs/superpowers/specs/`.

## Local Contracts (regras globais do projeto)
- **SRP**: 1 módulo = 1 responsabilidade; função pura quando possível; tipos trocados via `src/tdt/contracts.py`. Só `pipeline.py` conhece todos os módulos.
- **TDD obrigatório**: teste primeiro (RED→GREEN→refactor); 1 `test_*.py` por módulo em `tests/`.
- **Domínio TDT**: ver skill `especialista-ADMS-TDT`. Regras críticas: localizar coluna por field name/display name; DNP3_DiscreteSignals=43 colunas; double-bit nunca perde 2º índice; pareamento D+C por sigla+módulo (pós-classificação); `is_command()` com parênteses.
- **Goal da análise**: certeza do sinal **sem falsos positivos** + taxa de decisão alta.
- Não apagar métodos originais ao experimentar novos (benchmarkar; ver `bench/`).

## Work Guidance
- Stack: Python 3.14, pytest 9, openpyxl, scikit-learn, sentence-transformers, faiss-cpu, rapidfuzz.
- UI (SP4): PySide6, pytest-qt. AppState como estado compartilhado mutável entre telas.
- QSS em `src/tdt/ui/tema.qss`; entry-point `python -m tdt.ui_main` ou comando `tdt-ui`.
- Embeddings: e5 vence MiniLM no benchmark (82%/95%) — troca pendente; calibração é pré-requisito.

## Verification
- `python -m pytest -q` (raiz). Todos verdes antes de concluir.
- Qualidade de matching: `PYTHONPATH=src python bench/benchmark.py` (gate de regressão; log em `bench/resultados/`).

## Child DOX Index
- `src/tdt/AGENTS.md` — código do SP1 (módulos, contrato, orquestração) + SP4 (UI PySide6 em `src/tdt/ui/`).
- `scripts/AGENTS.md` — scripts utilitários de calibração, treino e enriquecimento.
- `tests/AGENTS.md` — convenções de teste/fixtures.
- `bench/AGENTS.md` — harness de benchmark e ground-truth.
- `docs/AGENTS.md` — specs, inputs e templates.
