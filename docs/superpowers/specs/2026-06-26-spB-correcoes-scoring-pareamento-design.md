# SP B — Correções de scoring e pareamento

**Data:** 2026-06-26
**Status:** Aguardando revisão do usuário
**Origem:** `docs/observacoes26062026.md` §2.2, §3.1, §3.2.
**Escopo:** 4 correções de bug, em ordem: (B1) confiança ausente em decisões por regra; (B2) confiança calibrada em [0,1] como probabilidade; (B3) DCpairer robusto a lados não-decididos; (B4) fusão de duplicados consecutivos (double-bit). É spec de bug-fix — não toca UI de revisão (spec A) nem contexto de módulo (spec C).

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

## B2 — Confiança como probabilidade calibrada em [0,1]

**Problema:** o score exibido é soma ponderada acumulada (pode passar de 1); não é comparável entre sinais nem é probabilidade.

**Solução (reusa `scoring/calibracao.py`):** temperature scaling sobre os scores dos candidatos finais de cada registro produz uma distribuição em [0,1] que soma 1 — uma probabilidade sobre as siglas candidatas. A confiança exibida é a probabilidade do top-1.

1. **Função de exibição** — novo `ui/modelo_tabela.py::confianca_exibida(rec) -> tuple[float, str] | None`:
   - `candidatos` não vazio ⇒ `probs = calibrar([c.score for c in rec.candidatos], "temperature", {"T": T_FINAL})`; retorna `(probs[0], "")`.
   - `candidatos == ()` e `status=="decidido"` ⇒ `(1.0, "regra")`.
   - senão ⇒ `None` (sem decisão; mostra vazio).
   - O resultado é sempre `[0,1]`.

2. **Calibração de `T_FINAL`** — `T` deixa de ser o `0.1` default e passa a ser ajustado contra o ground-truth:
   - Novo `scripts/calibrar_confianca.py` (ou estende `scripts/calibrar.py`): roda o pipeline sobre os inputs rotulados (`bench/rotulos.py`), coleta `(prob_top1, acertou?)`, e busca o `T` que minimiza o **ECE** (Expected Calibration Error) — varredura simples num grid de `T` (ex.: `0.05..1.0`), sem dependência nova.
   - `T_FINAL` gravado em `config.py` como knob calibrável (`Config.temperatura_confianca`), default = melhor `T` encontrado. Nunca hardcoded fora do `config.py`.

3. **Escopo da mudança:** B2 é **só exibição/calibração da confiança**. NÃO altera a mescla nem o roteador — as decisões continuam pelos scores acumulados de hoje (mexer no roteador é regressão de matching, fora do escopo deste bug-fix). Os scores brutos por método permanecem nas colunas Score embedding/tf-idf/fuzzy.

`# ponytail: temperature scaling (1 parâmetro) cobre o caso; isotonic/Platt só se o ECE não cair o suficiente.`

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
| B2 | `test_confianca_calibrada.py` | `confianca_exibida` ∈ [0,1] para qualquer registro; soma das probs ≈ 1; lista vazia ⇒ `None` |
| B2 | `scripts/calibrar_confianca.py` | self-check: ECE pós-calibração ≤ ECE com T default no conjunto rotulado |
| B3 | `test_dc_pairer.py` (estende) | Input decidido + Output em revisão, mesma sigla/módulo ⇒ par candidato em revisão (`pareamento_pendente`), **não** fundido |
| B4 | `test_fusao_duplicados.py` | 900/901 mesma sigla/equip/direção ⇒ 1 double-bit `(900,901)`; equipamento ausente ⇒ 2 em revisão (`duplicado_pendente`), não fundidos |

**Gate de regressão:** `PYTHONPATH=src python bench/benchmark.py` não pode piorar a taxa de decisão nem aumentar FP (B3/B4 só adicionam itens a revisão, nunca decidem sozinhos; B2 não toca o roteador).

---

## Critérios de Aceite

1. Sinal decidido por regra (ex.: DJF1 via polaridade) exibe `100% (regra)` na coluna Confiança, não vazio.
2. Nenhuma confiança exibida é > 1.0 nem < 0.0; o valor é a probabilidade calibrada (temperature) do top-1.
3. `Config.temperatura_confianca` ajustado por ECE contra o ground-truth; recalibrável por script, sem hardcode fora de `config.py`.
4. Caso DJF1 24-1 reproduzido; par Input/Output aparece como par candidato na revisão (não fica órfão), sem auto-fusão de lado não-decidido.
5. DJF1 900/901 (mesma sigla/equipamento/direção, consecutivos) consolida em double-bit `(900,901)`; equipamento ambíguo ⇒ vai pra revisão, não funde.
6. Benchmark sem regressão de decisão/FP. Todos os testes verdes.

---

## Fora de escopo (vira spec A/C)

- UI de "Parear"/confirmar par e revisão dos itens `pareamento_pendente`/`duplicado_pendente` → spec A.
- Inferir o equipamento quando ausente (topologia do módulo) → spec C; aqui só usamos o equipamento **se já definido**.
- Mudar mescla/roteador para usar a confiança calibrada na decisão → não é bug-fix; avaliar em spec própria.
