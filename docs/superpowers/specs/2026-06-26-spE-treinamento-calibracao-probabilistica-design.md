# SP E — Treinamento / calibração probabilística do matching

**Data:** 2026-06-26
**Status:** Aguardando revisão do usuário
**Origem:** pendências de calibração/encoder registradas na memória do projeto (e5 vence MiniLM 82%/95%, troca pendente; calibração é pré-requisito) + pedido do usuário: "ao final da normalização, ponderar os métodos e calibrar esses pesos; testar o benefício dos pesos para a mescla probabilística final".
**Escopo:** o **projeto de calibração** que estava sem dono — (E1) calibração por-método plugada antes da mescla; (E2) pesos de mescla aprendidos contra o ground-truth de correção → mescla probabilística; (E3) troca do encoder para e5; (E4) calibrador treinado (Platt/isotonic) para a confiança final. Tudo offline/determinístico; runtime só carrega parâmetros calibrados.

> Não é parte da decomposição A/B/C/D das observações 26/06 — é o eixo de **treinamento** que faltava. **E é a dona** das peças de calibração que B2 e C marcaram como "fora de escopo / pendente".

---

## Estado atual (confirmado)

- `config.py`: `peso_tfidf/peso_vetorial/peso_fuzzy` (~0.33 cada, **fixados à mão**), `calibracao_metodo="minmax"` existente mas **não plugado** no pipeline, `modelo_embedding="...MiniLM..."`.
- `scripts/calibrar.py`: varre pesos/thresholds num input, mas mede **taxa de decisão** (decididos/revisão), **não correção** — não usa rótulos ([calibrar.py:70](../../../scripts/calibrar.py)). Otimizar contagem pode aumentar FP.
- `bench/rotulos.py`: ground-truth real, hoje só consumido pelo benchmark de regressão.
- `scoring/calibracao.py`: `calibrar(scores, "minmax"|"temperature")` puro, sem uso no pipeline.

Conclusão: os pesos não são aprendidos contra correção, a calibração por-método não roda, e o encoder superior (e5) não está em uso.

---

## E1 — Calibração por-método plugada antes da mescla

Calibrar tfidf-cosine, e5-cosine e fuzzy-ratio para [0,1] comparável **antes** de `mescla.mesclar` (cada método vive em escala distinta; e5 comprime em ~0.8–0.9 — mesclar cru dá peso enganoso).

- Estender `scoring/calibracao.py` com calibradores **treinados**: além de minmax/temperature (não-supervisionados), ajustar **isotonic**/**Platt** por método contra os rótulos (`sklearn.isotonic`/`LogisticRegression` — já no stack).
- Parâmetros por método persistidos em `config.py` (`calibracao_por_metodo: dict[str, dict]`), nunca hardcoded fora dele.
- Plugar no `pipeline._classificar_sinal`: cada `c_tfidf/c_vet/c_fuzzy` passa por `calibrar(...)` antes da mescla.

E1 destrava E2/E3 (escalas comparáveis são pré-requisito de pesar e de trocar o encoder).

---

## E2 — Pesos de mescla aprendidos → mescla probabilística (pedido central)

**Objetivo:** ao fim da normalização+calibração, **ponderar** os métodos com pesos **aprendidos contra a correção** e produzir a probabilidade final, em vez dos `0.33` manuais.

- Reescrever o alvo de `scripts/calibrar.py`: otimizar **acerto vs rótulo** (`bench/rotulos.py` + mockup), **não** taxa de decisão, sob a restrição de **zero FP** (amarra no gate da spec D).
- Busca dos pesos: varredura/otimização (grid ou coordenada; `scipy` se já disponível, senão grid simples) **maximizando acerto@top-1** no conjunto de validação, com **FP=0 como constraint dura** (alvo escolhido pelo usuário — não taxa de decisão, não objetivo combinado).
- **Mescla probabilística:** após calibração por-método (E1) + pesos (E2), a combinação ponderada normalizada vira a distribuição de probabilidade sobre siglas (a mesma confiança que a B2 exibe — E refina como ela é produzida).
- **Entregável de ablação (o "testar benefício"):** relatório comparando, no benchmark, quatro configs — (a) cru + pesos iguais (baseline atual), (b) calibrado + pesos iguais, (c) cru + pesos aprendidos, (d) calibrado + pesos aprendidos. Mede acerto, taxa de decisão e FP de cada, **quebrado por nível de dificuldade do mockup** (onde os pesos ajudam: fácil vs adversarial). Decide se os pesos valem a pena com número, não opinião.

Pesos resultantes → `config.peso_*` (versionados). Discretos e analógicos calibrados separadamente (já há knobs `*_analog`).

---

## E3 — Encoder e5 (decisão do usuário: trocar agora, fine-tune só se precisar)

- Trocar `config.modelo_embedding` para o e5 (`intfloat/multilingual-e5-*`); `e5_prefixos` (já existe no config) ativa o prefixo assimétrico `query:`/`passage:` que o e5 exige.
- Recalibrar E1/E2 com o e5 (escalas mudam) e revalidar no benchmark — é o gate.
- **Sem fine-tuning agora.** Gancho documentado: se o benchmark estagnar, fine-tunar nos pares (descrição→sigla) da Full Base (cross-ref C3) vira spec própria (precisa de GPU/infra/dataset limpo).

`# ponytail: troca de encoder pré-treinado + recalibração; fine-tune é projeto à parte, só se o ganho do pré-treinado saturar.`

---

## E4 — Calibrador treinado para a confiança final

Upgrade do temperature-T (B2) para um calibrador **treinado**:

- Treinar **Platt** (logistic) e **isotonic** sobre `(prob_top1, acertou?)` do conjunto de validação; escolher por **ECE** (menor erro de calibração) — Platt tende a vencer com poucos dados, isotonic com mais; o ECE decide, sem chute.
- O calibrador escolhido + parâmetros vão pra `config.py`; a UI exibe `calibrador(prob_top1)` como confiança.
- Substitui o `Config.temperatura_confianca` da B2 quando E estiver pronta (B2 continua válida como passo intermediário).

---

## Dados de treino/validação (decisão do usuário: mockup + bench/rotulos)

Duas fontes combinadas, com split treino/validação **estável** (seed fixa) para não vazar:

1. **`bench/rotulos.py`** — ground-truth real existente. Pequeno e limpo; ancora a calibração na distribuição verdadeira.
2. **Gerador de mockup (corruptor determinístico de 5 níveis)** — para cada sinal da Lista Padrão (v4), descrições degradadas em 5 níveis de dificuldade (trivial→adversarial), cada uma rotulada com a sigla verdadeira. Dá **cobertura de todos os sinais** e um eixo de **dificuldade controlada** — ideal para a curva confiança×acerto do calibrador (E4) e para a ablação dos pesos (E2). É **pré-requisito compartilhado** com a spec D (corpus adversarial = nível 5); a ser detalhado em spec própria (método: corruptor determinístico reusando as tabelas de domínio; o design ficou pendente após dispensa das perguntas — retomar quando priorizado).

**Caveat:** o mockup é sintético — pode não refletir a distribuição real. Mitigação: sempre combinar com `bench/rotulos.py` (real) e reportar métricas separadas por fonte, para não calibrar só no sintético. A validação final de gate roda no benchmark real.

- Expansão futura (opcional): pares (descrição→sigla) da Full Base via **C3** — mais dado real para isotonic, ao custo de ruído no join. Não obrigatório.
- Nenhum acesso a disco em runtime: scorers/regras recebem parâmetros já calibrados (convenção de `scoring/AGENTS.md`).

---

## Testes (TDD)

| Item | Teste | Asserção mínima |
|------|-------|-----------------|
| E1 | `test_calibracao.py` (estende) | calibrador isotonic/Platt treinado mapeia scores→[0,1] monotônico; plugado, candidatos saem calibrados |
| E2 | `test_calibrar_pesos.py` | otimização usa rótulos (acerto), não contagem; respeita constraint FP=0; devolve pesos somando 1 |
| E2 | `bench/benchmark.py` (estende) | relatório de ablação das 4 configs (cru/calibrado × iguais/aprendidos) com acerto/decisão/FP |
| E3 | `test_encoder_e5.py` / bench | e5 com prefixos carrega; benchmark com e5 ≥ MiniLM sem aumentar FP |
| E4 | `test_calibrador_confianca.py` | Platt e isotonic treinados; escolhe o de menor ECE na validação |

**Gate:** `bench/benchmark.py` — E só entra se **melhorar (ou empatar) acerto/taxa de decisão sem aumentar FP**. A ablação da E2 é o juiz do benefício dos pesos. Não apagar o método atual: adicionar candidato e benchmarkar (contrato DOX, `bench/`).

---

## Critérios de Aceite

1. Calibração por-método plugada no pipeline antes da mescla; parâmetros em `config.py`.
2. Pesos de mescla **aprendidos contra correção** (não taxa de decisão), com FP=0 como constraint; mescla probabilística final.
3. Relatório de ablação quantifica o benefício dos pesos (4 configs) — decisão por número.
4. Encoder e5 em uso, recalibrado, com benchmark ≥ MiniLM e sem aumento de FP; fine-tune deixado como gancho.
5. Confiança final vem de um calibrador treinado (Platt/isotonic escolhido por ECE), substituindo o temperature da B2.
6. Benchmark sem regressão (idealmente melhora); testes verdes; métodos originais preservados para comparação.

---

## Fora de escopo

- Fine-tuning do encoder e classificador supervisionado fim-a-fim → projeto próprio (precisa de GPU/infra); E só troca o pré-treinado e calibra.
- Mineração da Full Base em si → C3 (E só consome o artefato, opcionalmente).
- Reordenação normalização↔regras → B2 (E assume essa ordem como dada).
