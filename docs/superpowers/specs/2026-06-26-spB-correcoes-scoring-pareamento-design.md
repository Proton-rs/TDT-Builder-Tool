# SP B — Correções de scoring e pareamento

**Data:** 2026-06-26
**Status:** Aguardando revisão do usuário
**Origem:** `docs/observacoes26062026.md` §2.2, §3.1, §3.2.
**Escopo:** 4 itens, em ordem: (B1) confiança ausente em decisões por regra; (B2) reordenar normalização↔regras — motor de regras vira filtro final sobre candidatos normalizados, confiança = probabilidade em [0,1]; (B3) DCpairer robusto a lados não-decididos; (B4) fusão de duplicados consecutivos (double-bit). B1/B3/B4 são bug-fix; **B2 é mudança de arquitetura de scoring** (reordenação + recalibração). Não toca UI de revisão (spec A) nem contexto de módulo (spec C).

> Decomposição das observações 26/06: **A** Revisão UI (lote, travar visão, colunas End.Input/Output/Pareado, editar módulo) · **B** (esta) · **C** Contexto de módulo/equipamento (4.x, 5.x) · **D** Qualidade/saída (6.x testes FP, 7.1 não sobrescrever). Cada uma com seu ciclo spec→plano.

---

## Diagnóstico (raízes confirmadas no código)

| Obs | Raiz | Arquivo |
|-----|------|---------|
| 2.2 confiança ausente | decisão fora do scorer (`pareamento_polaridade`) marca `status="decidido"` mas deixa `candidatos=()`; a UI lê `candidatos[0].score if candidatos else None` → vazio | `pareamento_polaridade.py:59`, `ui/modelo_tabela.py:152` |
| 2.2 confiança > 1 | `mescla.mesclar` é `Σ(peso×score)` sem normalizar; motor de regras ainda soma `delta`. O número exibido é score acumulado, não probabilidade | `scoring/mescla.py:18`, `motor_regras.py:360` |
| 3.1 DCpairer não pareia | `parear` agrupa por `(modulo.nome, sigla_sinal)` e só funde 1 Input + 1 Output **decididos com sigla idêntica**; lado em revisão (sigla `None`) ou sigla divergente nunca agrupa | `dc_pairer.py:18,85` |
| 3.2 duplicados não fundidos | `dc_pairer` só funde Input+Output (D+C); dois sinais de mesma direção (DJF1 900/901, ambos Input) nunca consolidam em double-bit | `dc_pairer.py:77` |

---

## B1 — Confiança ausente em decisões por regra

**Problema:** qualquer decisão tomada fora do scorer (hoje `pareamento_polaridade`; amanhã motor de regras isolado) não tem `candidatos`, e a coluna Confiança fica vazia.

**Decisão de contrato:** não injetar `Candidato` sintético na tupla de scoring (poluiria o pareamento/roteamento). Em vez disso, a confiança é uma função de leitura sobre o registro:

- Decisão por regra ⇒ `status=="decidido"` **e** `candidatos == ()` ⇒ confiança = **1.0** com rótulo `(regra)`.
- A coluna exibe `100% (regra)` nesse caso, em vez de vazio.

**Mudança:** `ui/modelo_tabela.py` — onde hoje faz `rec.candidatos[0].score if rec.candidatos else None`, passa a chamar um helper `confianca_exibida(rec)` (ver B2) que cobre os três casos (candidatos calibrados / regra / sem decisão). Cor da faixa segue a confiança resultante.

`# ponytail: confiança de regra = 1.0 fixo; se regras passarem a ter força variável, derivar do delta.`

---

## B2 — Normalização primeiro, motor de regras como filtro final, confiança = probabilidade

**Problema (estado atual confirmado):** a calibração (`scoring/calibracao.py`) **não está plugada** no pipeline. O fluxo é `mescla.mesclar(scores CRUS, pesos) → motor_regras (deltas aditivos) → roteador` ([pipeline.py:139-146](../../../src/tdt/pipeline.py)). As regras somam deltas sobre um acumulador sem teto, então o número exibido passa de 1 e não é probabilidade. Pior: aplicar a normalização *depois* das regras faria o softmax herdar a inflação dos deltas — a regra dominaria a probabilidade (superconfiança).

**Princípio de design (a invariante desta seção):** **normalizar primeiro, regras como filtro final sobre candidatos já normalizados — e re-normalizar.** As regras nunca operam sobre, nem produzem, scores fora de [0,1]; assim não "dessignificam" a normalização. A confiança exibida é a probabilidade do top-1 da distribuição final.

### B2.1 Reordenação do scoring (`pipeline._classificar_sinal`)

Nova ordem para cada registro:

1. **Mescla** dos métodos como hoje (`mescla.mesclar` dos `c_tfidf/c_vet/c_fuzzy`). Calibração **por-método** continua fora de escopo (é o projeto de calibração pendente → spec C); aqui normaliza-se o resultado mesclado.
2. **Normalizar os mesclados** → distribuição em [0,1] que soma 1, via `calibrar([c.score …], "temperature", {"T": T_FINAL})`. Esses são os "candidatos normalizados".
3. **Motor de regras como filtro final** sobre os candidatos **já normalizados**. Para preservar a normalização, o ajuste é **bounded**:
   - boost/penalidade limitada com **clamp em [0,1]** por candidato, e/ou
   - eliminação *hard* de violadores de restrição (fase/equipamento divergente → candidato zerado),
   - **seguido de re-normalização** (renormalizar para somar 1).
   `motor_regras.aplicar_rastreado` ganha modo "filtro" (clamp+renormaliza) sem perder os `AjusteRegra`/justificativa; os deltas passam a ser interpretados na escala [0,1].
4. **Roteador** decide sobre a distribuição final normalizada.

### B2.2 Confiança exibida (`ui/modelo_tabela.py`)

Novo `confianca_exibida(rec) -> tuple[float, str] | None`:
   - `candidatos` não vazio ⇒ `(rec.candidatos[0].score, "")` — já é a probabilidade pós-filtro (B2.1 garante [0,1] e soma 1). Sem re-calibrar na UI.
   - `candidatos == ()` e `status=="decidido"` ⇒ `(1.0, "regra")` (decisão puramente determinística, B1).
   - senão ⇒ `None`.

### B2.3 Calibração e recalibração

- `Config.temperatura_confianca` (knob calibrável; nunca hardcoded fora de `config.py`) substitui o `0.1` default. Ajustado por **ECE** contra o ground-truth: novo `scripts/calibrar_confianca.py` roda o pipeline sobre os rotulados (`bench/rotulos.py`), coleta `(prob_top1, acertou?)` e varre um grid de `T` (`0.05..1.0`) — sem dependência nova.
- **Recalibração obrigatória dos thresholds:** mudar a escala dos scores que chegam ao roteador desloca `threshold_pct`/`threshold_gap`/`gaps_por_confianca`/`pesos_regras`. Recalibrar via `scripts/calibrar.py` e validar no benchmark (gate). Esta é a parte cara de B2 — não é só exibição.

`# ponytail: filtro bounded = clamp+renormaliza (preserva [0,1]); softmax/T como normalizador. Isotonic/Platt e calibração por-método só se o ECE não cair o bastante → spec C.`

---

## B3 — DCpairer robusto a lados não-decididos

**Problema:** o caso DJF1 do equipamento 24-1 (input_nao_homogeneo_1) fica sem par Input/Output porque um lado não está decidido com a sigla idêntica, e `_chave = (modulo, sigla_sinal)` não agrupa quando `sigla_sinal is None` ou diverge.

**Passo 0 (obrigatório antes de fixar o critério):** reproduzir contra `docs/input_nao_homogeneo_1.xlsx` e confirmar qual é o estado real do par DJF1 24-1 (Output em revisão? sigla divergente? sem endereço?). O critério exato de B3 sai dessa reprodução — registrar o achado no plano de implementação.

**Mudança proposta (a confirmar pelo passo 0):** o agrupamento de pareamento passa a considerar a **sigla sugerida** (top-1 dos `candidatos_sugeridos`/`candidatos`) quando `sigla_sinal is None`, não só a sigla decidida:

- Grupo `(modulo, sigla_efetiva)` onde `sigla_efetiva = sigla_sinal or top1(candidatos)`.
- 1 Input + 1 Output **ambos decididos** ⇒ funde (comportamento atual, mantém).
- 1 Input + 1 Output mas **um lado em revisão** ⇒ **não funde**; emite par candidato em revisão com `motivo="pareamento_pendente"` e referência cruzada ao id do outro lado (UI da spec A oferece "Parear"). Mantém o invariante "sem endereço/sem decisão nunca auto-aprovado".
- Demais combinações ⇒ inalterado.

**Não auto-fundir lados não-decididos** preserva o goal "sem falsos positivos": a robustez aqui é *enxergar* o par, não confirmá-lo sozinho.

`# ponytail: sigla_efetiva via top-1; se o top-1 for instável, exigir gap mínimo antes de agrupar.`

---

## B4 — Fusão de duplicados consecutivos (double-bit)

**Problema:** dois DJF1 do mesmo equipamento com endereços sequenciais (900, 901), mesma direção, não consolidam num double-bit. `dc_pairer` só funde D+C; consolidação de mesma-direção é do normalizador estrutural mas não cobre este caso.

**Novo passo:** consolidação de duplicados antes/junto do `normalizador_estrutural` (dono do double-bit). Regra:

- Agrupa por `(modulo.nome, sigla_efetiva, direcao)`.
- Funde **somente** quando, dentro do grupo, há um par com:
  - mesmo equipamento **definido** (`eletrico.nome_equipamento` não nulo e igual), **e**
  - endereços **consecutivos** (`b == a+1`), **e**
  - mesma direção (Input+Input ou Output+Output).
- Resultado: um `SignalRecord` double-bit `enderecamento.indices=(a, b)`, `tipo_sinal.is_double_bit=True`. Não perde o 2º índice (contrato DOX).

**Guard-rail (decisão do usuário):** se o equipamento **não** estiver definido e não puder ser decidido por lógica, **não funde** — os dois sinais vão pra revisão com `motivo="duplicado_pendente"` e referência cruzada, para o usuário confirmar na UI. Alinhado a "sem falsos positivos".

Onde mora: novo módulo `src/tdt/fusao_duplicados.py` (função pura `fundir_consecutivos(registros) -> tuple[saida, revisao]`), chamado pelo `pipeline.py` na sequência do pareamento, antes do `normalizador_estrutural`. `pipeline.py` é o único que o conhece (SRP).

`# ponytail: só pares consecutivos (b==a+1); se aparecer double-bit com gap de endereço, generalizar para janela.`

---

## Testes (TDD, 1 por mudança)

| Item | Teste | Asserção mínima |
|------|-------|-----------------|
| B1 | `test_ui_modelo_tabela.py` (estende) | decisão por regra (`candidatos=()`, decidido) ⇒ confiança `1.0`, rótulo `regra` |
| B2 | `test_motor_regras.py` (estende) | regras em modo filtro mantêm candidatos em [0,1] e a soma ≈ 1 após re-normalizar; violador hard é zerado |
| B2 | `test_confianca_calibrada.py` | candidatos normalizados ∈ [0,1] e somam ≈ 1; `confianca_exibida` ∈ [0,1]; `candidatos=()` decidido ⇒ `(1.0,"regra")`; vazio sem decisão ⇒ `None` |
| B2 | `scripts/calibrar_confianca.py` | self-check: ECE pós-calibração ≤ ECE com T default no conjunto rotulado |
| B3 | `test_dc_pairer.py` (estende) | Input decidido + Output em revisão, mesma sigla/módulo ⇒ par candidato em revisão (`pareamento_pendente`), **não** fundido |
| B4 | `test_fusao_duplicados.py` | 900/901 mesma sigla/equip/direção ⇒ 1 double-bit `(900,901)`; equipamento ausente ⇒ 2 em revisão (`duplicado_pendente`), não fundidos |

**Gate de regressão:** `PYTHONPATH=src python bench/benchmark.py` não pode piorar a taxa de decisão nem aumentar FP. B3/B4 só adicionam itens a revisão (nunca decidem sozinhos). **B2 reordena normalização↔regras e muda a escala que chega ao roteador → exige recalibrar thresholds e revalidar no benchmark antes de mergear** (é o ponto de maior risco de regressão da spec).

---

## Critérios de Aceite

1. Sinal decidido por regra (ex.: DJF1 via polaridade) exibe `100% (regra)` na coluna Confiança, não vazio.
2. O motor de regras opera como **filtro final sobre candidatos já normalizados** (clamp + re-normalização); nenhum candidato sai de [0,1] e a distribuição soma ≈ 1 — a normalização não é "dessignificada" pelas regras.
3. Nenhuma confiança exibida é > 1.0 nem < 0.0; o valor é a probabilidade (temperature) do top-1 pós-filtro. `Config.temperatura_confianca` ajustado por ECE, recalibrável por script, sem hardcode fora de `config.py`.
3b. Thresholds do roteador recalibrados para a nova escala; benchmark revalidado sem regressão.
4. Caso DJF1 24-1 reproduzido; par Input/Output aparece como par candidato na revisão (não fica órfão), sem auto-fusão de lado não-decidido.
5. DJF1 900/901 (mesma sigla/equipamento/direção, consecutivos) consolida em double-bit `(900,901)`; equipamento ambíguo ⇒ vai pra revisão, não funde.
6. Benchmark sem regressão de decisão/FP. Todos os testes verdes.

---

## Fora de escopo (vira spec A/C)

- UI de "Parear"/confirmar par e revisão dos itens `pareamento_pendente`/`duplicado_pendente` → spec A.
- Inferir o equipamento quando ausente (topologia do módulo) → spec C; aqui só usamos o equipamento **se já definido**.
- Calibração **por-método** (tfidf/e5/fuzzy antes da mescla) e troca de encoder e5 → projeto de calibração pendente, spec C. B2 normaliza só o resultado mesclado.
