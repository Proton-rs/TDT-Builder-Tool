# Decisões

**Método de matching de sinal (produção atual):** tfidf+vetorial(MiniLM)+fuzzy. Benchmark original (28 pares): acc@1 79-82%, prec@decididos 88-95% (`bench/rotulos.py` + `bench/benchmark.py`). **Escopo do benchmark:** só gateia matching/scoring — não chama `pipeline.executar`, não gateia mudanças estruturais (estruturador, identidade_modulo, pareamento, roteação). Gate real dessas é a suíte pytest completa.

**Pesos atuais em `config.py` (verificado 2026-07-01, diverge do valor de benchmark acima — recalibrado depois via `calibrar.py` E2):** peso_tfidf=0.70 peso_vetorial=0.25 peso_fuzzy=0.05, threshold_pct=0.45 threshold_gap=0.08. Analógicos têm pesos próprios iguais aos discretos + threshold_pct_analog=0.35/threshold_gap_analog=0.05.

**e5/BGE swap CANCELADO** (3ª rodada, pós-melhoria de normalização): tfidf+vet(MiniLM)+fuzzy = tfidf+e5+fuzzy (82/95/75), e5 perdeu a vantagem, modelo ~1GB mais pesado sem ganho. `config.e5_prefixos=False`. Capacidade e5 assimétrica dorme em `indice_vetorial`/`encoder`.

**Calibração per-query (minmax/temperature) e consenso/gap-dinâmico: histórico "NÃO wirados"** — per-query piora prec (95→80%); consenso sobre scores crus tem 93% decid mas só 35% prec (FP). `config.usar_consenso=False` confirmado ainda off.
⚠️ **Atualização (verificado 2026-07-01):** `config.calibracao_por_metodo` (minmax por tfidf/vetorial/fuzzy) ESTÁ ativo por default e é aplicado em `pipeline._classificar_sinal` — isso é diferente do calibrador per-query descrito acima que piorava prec; não há registro de novo benchmark validando esse minmax-por-método específico. Além disso `config.confianca_calibrador` (E4, pós-mescla, método platt com params treinados `coef_=2.0403 intercept_=-0.9391`) está ATIVO por default — é um passo novo, distinto do calibrador per-query antigo, sem menção anterior na memória. Tratar como featura já wirada em produção, não dormente; se investigar regressão de precisão, checar esses dois primeiro.

**Regras de domínio (R1-R6, motor_regras) wiradas** mesmo neutras no benchmark — defendem casos de FP fora do escopo dos 28 pares do ground-truth (12 testes unitários provam os casos-alvo).

**Política de revisão por módulo baixa-confiança:** decisão do usuário (26jun) — MANTER sinal com sigla decidida mas módulo indefinido em revisão (mais seguro/auditável), não promover automaticamente.

## Roadmap de specs (pós-comparação TDT real, 30jun)

Gaps priorizados viraram specs B/C/D (Spec A dropada, incorporada na D):
- **Spec B** (pronta, spec+plano) — fidelidade de campo (Phases inválido/vazio, TRF03).
- **Spec C** (só spec) — política equipamento_ambiguo.
- **Spec D** (spec + plano SP-D2) — matching: eixo 1 desambiguação por qualificador (fase/estágio), eixo 2 consistência comando↔status (deferido).

Ordem: SP-GT (ground-truth automático) → SP-Cleanup → (v6 ∥ SP-Direção ∥ spC1) → spC2 → SP-Decision.

**Princípio do usuário:** criar métodos como candidatos SEM apagar os originais; benchmarkar pelo que performa antes de trocar.
