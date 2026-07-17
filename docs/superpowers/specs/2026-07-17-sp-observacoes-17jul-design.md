# SP-OBS-17JUL — Observações de revisão, configuração e classificação (anot.txt 17/07)

**Status:** spec aguardando revisão do usuário
**Origem:** `docs/anot.txt` (5 pontos, 17/07/2026)
**Método:** investigação de código (2 scouts cavecrew, 17/07) + medição real da lista padrão v8 + ledger `docs/AGENTS.md` + `docs/fluxo_dados.md`.

---

## 1. Contexto e evidências

Os 5 pontos do anot.txt, com a causa raiz encontrada na investigação:

| # | Observação | Causa raiz (evidência) |
|---|---|---|
| P1 | Sinal classificado como output mostra endereço na coluna "endereço input" | UI exibe `enderecamento.indices` sempre na coluna "Endereço", ignorando a direção (`modelo_tabela.py:221-224`). O `engine_tdt.py:186-199` já interpreta por direção (Output → coordenada vai pra Output Coordinates); a UI não replica essa semântica |
| P2 | Extrair informação extra guiada pela lista padrão + atualizar regras dos dados já buscados | Loader lê 3 sheets e ignora 7 (`lista_padrao.py:138-175`); medição 17/07: parte das colunas não lidas tem dado real utilizável, parte está vazia (§4) |
| P3 | Botão para reparear sinais em lote na sheet selecionada | Só existe pareamento manual de linhas selecionadas 1×1 (`tela_revisao.py:628 _parear_sinais`, botão "Parear D+C" em `tela_revisao.py:202`). O `dc_pairer.parear` é função pura reutilizável (`dc_pairer.py:135-176`), mas nada na UI o reexecuta sobre um subconjunto |
| P4 | Configurações mostram pesos 0,33 mas o calibrado é BM25-dominante | `config.toml` na raiz tem snapshot integral antigo (`peso_tfidf=0.34, peso_vetorial=0.33, peso_fuzzy=0.33`), gravado antes da calibração; `config_io.carregar_config` sobrepõe os defaults calibrados (0.70/0.25/0.05, `config.py:38-40`) com o snapshot, para sempre. **As execuções via UI rodam hoje com pesos não calibrados** — não é só vitrine |
| P5 | Descrições contendo a sigla vão pra revisão por score baixo | Âncora de sigla injeta candidato com `score=0.85` (`ancoragem_sigla.py:143-173`, `config.ancora_sigla_score`), mas o roteador aplica quadrantes/piso normalmente (`roteador.py:145-163`): variantes pai/filho da mesma família sobrevivem ao `filtrar_subarvore` com scores próximos → gap pequeno → revisão com motivo `score_baixo` |

### Princípios herdados (obrigatórios)

1. **Regra universal de não-regressão e fluxo de dados** (CLAUDE.md §Não-regressão): nada aqui pode desligar/degradar funcionalidade existente; informação adquirida não pode ser apagada para etapas seguintes.
2. **Uma mudança de scoring = uma rodada de gate** (`bench/gate_tdt_real.py`, `pct >= baseline`); regrediu → reverter e registrar (disciplina do SP-Unificado 08jul, comprovada).
3. **Fixture limpa não substitui dado real** (lição SP-CVA2): toda regra nova nasce de medição nos inputs reais / lista padrão real — esta spec já aplicou isso (as colunas LINHA/BARRA/etc. pareciam úteis e estão vazias, §4.1).
4. Edição do usuário na revisão nunca é revertida sem comando explícito (correção 16645f4).

---

## 2. Escopo

**Dentro:** os 5 pontos P1–P5, decompostos em workstreams independentes, cada um com design, testes e critério de aceite próprios.
**Fora:**
- Classificação de direção/comando por texto (bloqueada por dado — ledger, diagnóstico 08jul). P1 só corrige *exibição* da direção já conhecida.
- Reintroduzir `type_severidade` no corpus vetorial (revertido em 36c2b68 por regressão de gate — não reabrir).
- spC3 (mineração da Export Full Base) — continua workstream separado.
- Qualquer mudança nos `.xlsx` de origem (insumos, não editáveis).

---

## 3. P1 — Endereço de Output na coluna errada (UI de revisão)

### Problema

`Enderecamento` (`contracts.py:42-46`) tem `indices` (endereço próprio) e `indices_saida` (OUTCOORDS pós-pareamento). Para **comando órfão** (direção `Output`), o endereço próprio fica em `indices` — e é semanticamente um endereço de *escrita*. A UI exibe cru:

```python
# modelo_tabela.py:221-224 (hoje)
if nome == "Endereço":
    return ";".join(str(i) for i in rec.enderecamento.indices)
if nome == "Endereço Output":
    return ";".join(str(i) for i in rec.enderecamento.indices_saida) or "—"
```

Resultado: um Output puro aparece com endereço na coluna de input e "—" na de output. O `engine_tdt.py:188-199` já resolve isso para o TDT gerado (`direcao == "Output"` → `coords_entrada = None`, endereço vai para Output Coordinates); a UI diverge do TDT.

### Alternativas consideradas

- **(a) Corrigir a camada de exibição/edição por direção — RECOMENDADA.** Display e `setData` do modelo mapeiam coluna↔campo conforme `tipo_sinal.direcao`, espelhando a semântica do `engine_tdt`. Mudança local (1 arquivo + testes), zero risco de pipeline.
- **(b) Mudar o modelo de dados** (endereço de Output sempre em `indices_saida`). Rejeitada: `indices` é a identidade de endereçamento auditada (I1–I4, `fluxo_dados.md`), consumida por dc_pairer, engine, auditoria, conservação; mover o campo reescreve semântica em todo o pipeline por um problema de exibição. Viola o ponytail e arrisca exatamente o tipo de regressão que a regra de fluxo de dados proíbe.

### Design (a)

Tabela de verdade da exibição (única fonte: `tipo_sinal.direcao`):

| Direção | Coluna "Endereço" (input) | Coluna "Endereço Output" |
|---|---|---|
| `Input` | `indices` | `indices_saida` se houver, senão "—" (hoje, mantém) |
| `InputOutput` (fundido D+C) | `indices` | `indices_saida` (hoje, mantém) |
| `Output` (comando órfão) | **"—"** | **`indices`** |

- Extrair um helper puro (ex. `enderecos_exibicao(rec) -> tuple[str, str]`) usado por `data()` — e pelo tooltip, se existir — para não duplicar o ramo.
- **Edição simétrica** (`modelo_tabela.py:342-350 setData`): editar "Endereço Output" de um registro `Output` escreve em `indices` (endereço próprio dele); editar "Endereço" de um `Output` é rejeitado (célula "—", não editável), igual ao comportamento atual de célula vazia. Nenhum caminho de edição pode gravar o endereço próprio de um Output em `indices_saida` — isso corromperia o dado que o engine interpreta.
- Renomear header da coluna "Endereço" → "Endereço Input" fica a critério da revisão do usuário (observações_pendentes item 2 pede colunas distintas; a coluna Output já existe — só o rótulo da primeira é ambíguo). Custo zero, decidir na revisão da spec.

### Testes / aceite

- `tests/test_modelo_tabela.py`: display das 3 direções (tabela acima); `setData` de Output escreve em `indices`; edição da célula "—" rejeitada.
- Aceite: comando órfão real (ex. os casos `Write` legítimo AUTC/PB/CMD do GTD) aparece com endereço só na coluna Output; TDT gerado byte-idêntico ao de antes da mudança (é só UI).

---

## 4. P2 — Informação extra guiada pela lista padrão

### 4.1 Medição real (17/07, `Pontos Padrao ADMS_v8.xlsx`)

O workbook tem 10 sheets; o loader lê 3 (`DiscreteSignals`, `AnalogSignals`, `DiscreteAnalog` — `lista_padrao.py:138-175`, 16 campos em `SinalPadrao`). Medição das colunas/sheets não consumidas:

| Fonte | Conteúdo medido | Veredito |
|---|---|---|
| `DiscreteSignals`: LINHA, BARRA, TRANSFORMADOR, ALIMENTADOR, TRANSFERÊNCIA | **0/692 preenchidas** | Matriz de aplicabilidade por módulo NÃO existe no dado. Descartar; re-medir se a v9+ preencher |
| `DiscreteSignals`: CONTROL CODE | 0/692 | Descartar |
| `DiscreteSignals`: SEVERIDADE | 690/692, 8 valores ("Severidade 3"…"Severidade 8") | Utilizável como **metadado de saída/revisão** (nunca corpus — vetado pelo ledger) |
| `DiscreteSignals`: Funcionamento | 22/692, texto livre | Baixo valor p/ matching; útil como tooltip/conhecimento na revisão (opcional) |
| `AnalogSignals`: FASES | **62/62**, vocabulário fechado (`L1 L2 L3`, `L1`, `N`…) | **Utilizável**: discriminador de fase estruturado p/ analógicos |
| `AnalogSignals`: LADO | 0/62 | Descartar |
| Sheet `DE->PARA` | **100 pares** sigla-de-entrada → canônica (`90→R90`, `20T87T→2087T`, `21_1→21Z1`) | **Alto valor**: normalização determinística de sigla de entrada — exatamente a correção apontada no follow-up FGOO→GOOSE (ledger 09jul) |
| Sheet `Message Mapping` | 809 linhas: MM → estados (`State (Message)`), `Commanding message`, `Abnormal Status`, severidade | **Utilizável**: hoje o MM da LP é validado só por fixture de teste (`tests/fixtures/mm_catalogo_real.txt`); estados por MM podem reforçar `filtro_semantica_estados` (D2) com dado estruturado em runtime |
| Sheet `DMS Signal Explanation` | 1141 linhas: `MatchingString` → template, signalType, measurementType, phaseCode | **Utilizável**: fonte oficial p/ Measurement Type (pendência KMDF, observações item 16) e phase code — substitui/valida o mapa hardcoded `_MEASUREMENT_TYPE_PT_EN` |
| Sheets `MANUT_DiscreteSignals`/`Manut_AnalogSignals` | 21+12 linhas de sinais de manutenção/prediais com exemplos reais (contém **`79_L — RELIGAMENTO LOCAL`**) | **Utilizável**: vocabulário/catálogo extra; `79_L` é justamente o falso-positivo conhecido "religamento local" do corpus adversarial |
| Campos já carregados sem consumo: `type_severidade`, `output_data_type`, `aplicabilidade` (0 refs a jusante) | — | `type_severidade` ganha uso no 2D abaixo (fora do corpus); os outros dois ficam documentados como dormentes |

### 4.2 Workstreams (cada um = 1 mudança + 1 rodada de gate; ordem = valor/risco)

**2A — `DE->PARA`: normalização de sigla de entrada (valor mais alto, determinístico).**
- Loader ganha `carregar_de_para(path) -> dict[str, str]` (nova função, mesma planilha).
- Aplicação no ponto único onde a sigla de entrada é reconhecida/pré-classificada (estruturador/normalização de sigla — o plano localiza o choke point exato), ANTES de ancoragem e matching: sigla presente no mapa → substituir pela canônica, registrando aviso INFO (`sigla_normalizada_de_para`) para o fluxo de dados ficar auditável (a sigla bruta permanece na descrição bruta preservada).
- Cobre o padrão FGOO→GOOSE: se o mapa não tiver a entrada, NÃO inventar fuzzy — pendência continua com o proprietário da lista.
- Teste: pares reais do mapa; conservação (nenhum sinal some). Gate obrigatório.

**2B — `AnalogSignals.FASES`: fase estruturada para analógicos.**
- `SinalPadrao` ganha campo `fases` (só analógicos; default `None`, retrocompat).
- Consumo: no matching analógico, candidato cuja `fases` da LP contradiz a fase extraída do texto do sinal (extração já existe — `normalizador._fase_no_texto`) é penalizado/filtrado pelo mesmo mecanismo do discriminador de fase discreto (motor_regras `fase` / filtro fino — o plano decide o registro certo, sem criar módulo novo).
- Gate: usa `threshold_*_analog`; atenção ao follow-up do ledger (analógicos hoje silenciosamente excluídos do gate — ver §8, precisa de verificação manual em lista real com analógicos, ex. GTA).

**2C — `Message Mapping`: estados por MM em runtime.**
- Loader ganha leitura opcional da sheet (dict `mm -> estados/abnormal/severidade`).
- Uso 1 (barato): validação de integridade na carga — MM referenciado pelas 3 abas e ausente do catálogo → aviso (hoje isso só existe como teste offline).
- Uso 2 (gated): `filtro_semantica_estados` (D2) passa a poder usar os estados do catálogo MM quando a coluna FUNÇÃO da aba estiver vazia/divergente. Uma coisa por vez: uso 1 entra sem gate (não toca scoring), uso 2 é rodada própria.
- `Commanding message` por MM fica REGISTRADO como insumo futuro para a decisão bloqueada de direção (Fase 8 do SP-Unificado) — não implementar aqui.

**2D — `SEVERIDADE` como metadado de saída/revisão (não-scoring).**
- Campo `severidade` no `SinalPadrao` (aba DiscreteSignals, coluna direta; já vem resolvida com `data_only`).
- Exibir na UI de revisão (coluna opcional) e/ou carregar no relatório — ajuda o operador a julgar candidato (alarme grave × evento). NÃO entra em corpus nem em score (veto do ledger permanece).
- Sem gate (não toca matching); teste de loader + UI.

**2E — `MANUT_*` como vocabulário/catálogo auxiliar.**
- Diagnóstico primeiro (padrão Fase 8): script `bench/diag_manut_lp.py` cruza as 33 linhas MANUT com as listas reais — quantos sinais de entrada casariam com siglas MANUT (`79_L`, `J124`…) que hoje caem em revisão/FP?
- Se a medição justificar (≥ N casos reais), incluir as MANUT como 4ª fonte do catálogo de matching com flag `origem="manut"` e gate individual. Se não, arquivar com o número medido. **Não incluir às cegas** — mais 33 candidatos podem diluir (lição v5).

**2G — `DMS Signal Explanation` como fonte de Measurement Type / phaseCode.**
- Diagnóstico primeiro: cruzar o mapa hardcoded `_MEASUREMENT_TYPE_PT_EN` (12 tipos) com as 1141 linhas da sheet (`MatchingString → signalType/measurementType/phaseCode`); listar divergências e tipos que o mapa não cobre (o caso KMDF das observações item 16 é o teste ácido: a referência oficial dele está aqui).
- Se a cobertura da sheet for superior: loader opcional da sheet e mapa hardcoded vira fallback (com teste garantindo que os 12 mapeamentos atuais não mudam de resultado — não-regressão). Se for só complementar, apenas acrescentar as entradas que faltam ao mapa. Não toca scoring; sem gate, mas com a suíte e verificação em lista real com analógicos.

**2F — Auditoria dos dados já buscados (a segunda metade do pedido).**
- Fechar a lacuna registrada em `fluxo_dados.md` §Lacunas: coluna EQUIPAMENTO dedicada (LVA) não é detectada por `analise_colunas` — hoje só a varredura de linha inteira pega IDs da whitelist. Detectar a coluna rotulada e integrá-la ao ramo de equipamento do estruturador (ramos independentes, regra I2).
- Revisar consumo dos campos `estados_brutos`/`valores_scada`/`direction` do `SinalPadrao` contra o que 2C traz — se o catálogo MM virar fonte de estados, documentar qual fonte prevalece em divergência (proposta: coluna FUNÇÃO da aba > catálogo MM, com aviso na divergência; decisão final na revisão desta spec).

---

## 5. P3 — Repareamento em lote na revisão

### O que já existe (reusar, não duplicar)

| Peça | Onde | Papel |
|---|---|---|
| `dc_pairer.parear(registros, config) -> (decididos, revisao)` | `dc_pairer.py:135-176` | Pareamento completo por grupo (módulo, equipamento, sigla), função pura |
| `fundir/separar` | `dc_pairer.py:29-74` | Fusão/desfusão 1×1, já reusada pela UI |
| `normalizador_estrutural.fundir_pares_posicao` | `normalizador_estrutural.py:52-88` | Par de posição (2 Inputs) antes do dc_pairer |
| Botão "Parear D+C" manual | `tela_revisao.py:202,628` | Só nas linhas selecionadas, 1 status + 1 comando |
| `AppState._snapshot()` / undo | `estado.py` | 1 snapshot por operação em lote (padrão `aprovar_ids`) |
| Abas por sheet na revisão | `tela_revisao.py` (`_atualizar_abas_sheet`) | Dá a noção de "sheet selecionada" que o pedido usa |
| Dataclass `Pareamento` | `contracts.py:129-137` | Contrato tipado p/ exibição |

### Alternativas consideradas

- **(a) Reusar o pipeline de pareamento sobre o subconjunto da sheet — RECOMENDADA.** `fundir_pares_posicao` + `dc_pairer.parear` já implementam toda a lógica (incluindo reconciliação de posição e catch-all por similaridade). A UI só seleciona o subconjunto elegível, roda as funções puras e aplica o resultado com 1 snapshot.
- **(b) Loop na UI chamando `decidir_acao_pareamento`/`fundir` par a par.** Rejeitada: reimplementa agrupamento e ambiguidade que o `dc_pairer` já resolve; divergiria do pipeline (dois algoritmos de pareamento = manutenção dupla).

### Design (a)

**Núcleo puro** (testável sem Qt), em `estado.py` ou módulo novo `ui/reparear.py`:

```python
@dataclass(frozen=True)
class ResultadoReparear:
    fundidos: tuple[SignalRecord, ...]      # pares novos (InputOutput)
    ambiguos: tuple[ItemRevisao, ...]       # pareamento_ambiguo novos
    intocados: int                          # elegíveis que continuaram sós

def reparear(registros: Sequence[SignalRecord], config) -> ResultadoReparear
```

- **Elegibilidade** (o coração da regra de fluxo de dados): entram no repareamento apenas registros do escopo que (i) têm `sigla_sinal` atribuída (inclusive a recém-corrigida pelo usuário — é o caso de uso), (ii) direção `Input` sem `indices_saida` OU `Output` puro, e (iii) não são fusões existentes (`InputOutput` fica fora — repareamento NUNCA desfaz par existente; para refazer um par o usuário desvincula antes, fluxo que já existe).
- Internamente: rodar `fundir_pares_posicao` (pega pares de posição que a reclassificação criou, ex. DJA1→DJF1 dupla) e depois `dc_pairer.parear` no subconjunto. Registros que o pairer devolveria como `ItemRevisao` de ambiguidade não perdem nada: continuam na tabela com motivo atualizado para `pareamento_ambiguo`.
- **UI**: botão/ação "Reparear sheet" na tela de revisão (ao lado do "Parear D+C" manual): escopo = aba de sheet atual; com 2+ linhas selecionadas, oferecer "só a seleção" (menu do botão ou diálogo). Fluxo: calcular `ResultadoReparear` → diálogo de confirmação com o resumo ("N pares formados, M ambíguos, K sem par") → aplicar com 1 `_snapshot()` (desfazer restaura tudo) → `refresh()` + status bar com o resumo.
- **Perda de vista do sinal** (observações item 10): ao aplicar, selecionar/scrollar até o primeiro registro fundido — barato e resolve a queixa correlata.

### Testes / aceite

- Núcleo: par formado após reclassificação (2 registros que não pareavam por sigla divergente passam a parear depois de `sigla_sinal` corrigida); `InputOutput` existente intocado; edição de usuário preservada; N×M ambíguo vira motivo, não fusão; conservação (nenhum registro some: fundidos absorvem id do comando, mesma contabilidade do pipeline).
- UI (smoke): 1 clique → 1 snapshot; desfazer restaura o estado exato pré-repareamento.
- Aceite (cenário do anot.txt): na sheet AL11, reclassificar vários D+C e reparear todos com um clique, sem parear um a um.

---

## 6. P4 — Configuração persistida divergente do calibrado

### Causa raiz

`config.toml` (raiz do projeto) foi salvo com o snapshot integral dos escalares quando os defaults eram 0.34/0.33/0.33. `carregar_config` (`config_io.py:75-91`) aplica tudo que está no arquivo por cima do `Config()` — então a recalibração de 03/07 (BM25 0.70/0.25/0.05, confirmada pelo tuning de 09/07: "MANTER 0.70/0.25/0.05") **nunca chegou às execuções via UI**. Medição do arquivo atual: só os 3 pesos de mescla divergem dos defaults (thresholds e `pesos_regras` coincidem por sorte — snapshot antigo bateu com o default atual).

Duas consequências:
1. Corrigir o arquivo atual (imediato).
2. Impedir recorrência: qualquer recalibração futura sofrerá o mesmo silenciamento se o formato continuar snapshot-integral.

### Alternativas consideradas

- **(a) Persistir só deltas + botão "Restaurar padrão calibrado" — RECOMENDADA.** `salvar_config` grava em `[config]`/`[pesos_regras]` apenas campos com valor ≠ `Config()` default; `carregar_config` já é naturalmente compatível (aplica só o que está lá). Quem nunca mexeu num knob recebe defaults calibrados novos automaticamente; quem mexeu, mantém a escolha (que é o contrato correto de um override).
- **(b) Chave de versão de calibração + reset automático no load.** Rejeitada como mecanismo principal: exige disciplina de bump manual a cada calibração e apaga overrides intencionais do usuário no reset (viola "escolha do usuário prevalece"). O delta-only de (a) obtém o efeito sem estado extra.
- **(c) Só o botão de restaurar, sem mudar persistência.** Rejeitada sozinha: não previne recorrência (o próximo `aplicar()` regrava o snapshot integral).

### Design (a)

- `config_io.salvar_config`: comparar cada escalar de `_ESCALARES` e cada chave de `pesos_regras` com `Config()`; gravar só divergentes. Arquivo sem seção `[config]` é válido.
- **Migração one-time do arquivo existente**: na primeira carga com o código novo, valores iguais a defaults *históricos conhecidos* (o trio exato `0.34/0.33/0.33`) são tratados como stale e descartados com log INFO. Implementação mínima: constante `_STALE_CONHECIDOS = {("peso_tfidf", 0.34), ("peso_vetorial", 0.33), ("peso_fuzzy", 0.33)}` no `config_io` — remove-se numa versão futura. (Alternativa mais simples ainda: apagar manualmente as 3 linhas do `config.toml` junto do merge — a migração automática protege outras máquinas/cópias do arquivo; manter as duas.)
- **UI (`tela_config.py`)**: (i) botão "Restaurar padrões calibrados" (reseta spinboxes para `Config()`; só grava no Aplicar, como hoje); (ii) marcador visual em campo ≠ default (rótulo em itálico/asterisco + tooltip "padrão calibrado: X") — o usuário enxerga na hora o que é override dele. Isso responde diretamente "verificar se configurações ainda representam escolhas reais": passa a ser visível.
- Corrigir também o aviso existente de soma ≠ 1.0 (`tela_config.py:242-249`): hoje só avisa; continuar não-bloqueante (pesos são renormalizados na mescla? o plano confirma — se não forem, bloquear Aplicar com soma ≠ 1.0).

### Testes / aceite

- `config_io`: roundtrip default → arquivo sem `[config]`; override → só o campo gravado; migração remove o trio stale e preserva override legítimo (ex. `threshold_pct` customizado).
- Aceite: abrir a UI numa máquina com o `config.toml` atual → pesos exibidos 0.70/0.25/0.05; rodar pipeline via UI usa os calibrados. Gate `gate_tdt_real` roda com config default (não muda), mas registrar uma rodada manual via UI numa lista real para confirmar o efeito.

---

## 7. P5 — Sigla explícita na descrição indo pra revisão por `score_baixo`

### Mecanismo mapeado

1. `ancoragem_sigla.detectar` acha a sigla no texto (match exato de token + junção de tokens); `ancorar` injeta candidato com `score = config.ancora_sigla_score = 0.85`, `fonte="ancora_sigla"` (`ancoragem_sigla.py:66-173`); `filtrar_subarvore` restringe candidatos ao sub-ramo da âncora.
2. Segue o fluxo normal: filtros → motor de regras → roteador (`pipeline.py:275-282`).
3. `roteador._quadrante` (`roteador.py:145-163`): quadrantes `threshold_pct × threshold_gap`, depois piso absoluto (`confianca_top1 = topo.score - regras_delta`; `< piso_decisao (0.20)` → `score_baixo`).
4. Caso especial já tratado: âncora com múltiplas famílias → motivo `sigla_multipla` (`pipeline.py:453`). O caso do usuário é o de **uma família só** que mesmo assim cai em revisão.

### Hipóteses de falha (a confirmar no diagnóstico — nenhuma correção entra sem ele)

- **H1 (principal): empate pai/filho dentro da família.** `filtrar_subarvore` mantém o ramo inteiro (ex. `79`, `79OK`, `79LO`); a âncora garante a família, mas as variantes têm scores próximos → gap < threshold → revisão. O motivo exibido (`score_baixo`) é enganoso: a família está decidida, falta escolher a variante.
- **H2: desconto do delta de regras no piso.** `confianca_top1` subtrai `regras_delta`; âncora + regras podem deixar `score - delta < 0.20` mesmo com top-1 óbvio.
- **H3: âncora não sobrevive à mescla/calibração** em algum caminho (ordem de calibração vs injeção). Menos provável (injeção é pós-mescla), mas o diagnóstico fecha a questão.

### Fase 0 obrigatória — diagnóstico instrumentado (padrão Fase 8 do SP-Unificado)

- `bench/diag_ancora_revisao.py`: varrer as listas reais (GTD, CVA, LVA, GAU, SMF, GPR…), listar todo registro com âncora detectada que terminou em revisão: motivo, top-3 candidatos com scores, gap, delta de regras, família da âncora, variante esperada (quando o gate real tiver o endereço).
- Saída classificada por hipótese (H1/H2/H3/outra) em `docs/superpowers/specs/2026-07-17-diag-ancora-revisao.md`. **As correções abaixo só se aplicam às hipóteses confirmadas com contagem.**

### Correções propostas (cada uma gated, condicionada ao diagnóstico)

- **C1 (para H1): desambiguação de variante ancorada.** Quando o top-1 é da família ancorada e a revisão seria por gap/percentual entre variantes da MESMA família: aplicar os discriminadores existentes (fase, estágio, qualificador — `especificidade_qualificador`, discriminador de fase D2) como tie-break; se seguem inconclusivos, decidir pela **variante-pai exata da âncora** (o texto diz "79" → decidir `79`, não `79OK`) com flag de diagnóstico; se a âncora não corresponde a nenhuma variante-pai (só filhos), revisão continua, mas com motivo novo **`variante_ambigua`** (label na UI: "família decidida pela sigla; escolher variante") — muito mais acionável que "score baixo".
- **C2 (para H2): piso não desconta âncora.** Se H2 confirmada: candidato top com `fonte="ancora_sigla"` usa o score sem desconto de `regras_delta` no piso (o piso existe para proteger contra top-1 textual fraco — 51F→FC87; âncora exata não é top-1 fraco). `piso_decisao` continua intacto para candidatos não ancorados.
- **C3 (para H3): correção de ordem/escala** conforme o achado (sem design antecipado — depende do que aparecer).
- **Salvaguarda comum:** âncoras por *junção de tokens* (mais arriscadas que match exato) NÃO ganham os privilégios C1/C2 na primeira rodada — só âncora exata. Ampliar depois se o diagnóstico mostrar que junção é confiável.

### Testes / aceite

- Corpus: casos reais do diagnóstico viram testes (padrão `casos_travados.csv`/corpus adversarial): descrição com sigla explícita → decide ou cai em `variante_ambigua`, nunca `score_baixo`.
- Gate individual por correção; `pct >= baseline` obrigatório.
- Aceite (métrica do diagnóstico): nº de registros "âncora exata → revisão score_baixo" nas listas reais cai a ~0, sem regressão de gate e sem crescer falso-positivo no corpus adversarial.

---

## 8. Ordem de implementação, riscos e verificação

**Ordem proposta** (risco crescente, dependências mínimas):

| Fase | Item | Risco | Gate |
|---|---|---|---|
| 1 | P4 (config delta-only + migração + UI) | Baixo (não toca scoring; muda o *efetivo* da UI p/ calibrado — mudança de comportamento DESEJADA e visível) | 1 rodada p/ registrar novo comportamento via UI |
| 1 | P1 (colunas de endereço na UI) | Zero (display/edição) | suíte |
| 2 | P3 (reparear em lote) | Baixo (reusa pipeline puro; só UI/estado) | suíte + smoke UI |
| 3 | P2-2A (DE->PARA), depois 2D (severidade), 2C-uso1 (integridade MM) | Baixo/médio | gate individual p/ 2A |
| 4 | P5 Fase 0 (diagnóstico) → C1/C2 conforme confirmação | Médio (mexe em roteador/decisão) | gate individual por correção |
| 5 | P2-2B (FASES analógicos), 2C-uso2 (estados MM no D2), 2E (MANUT, condicionada a diagnóstico), 2F (coluna EQUIPAMENTO), 2G (DMS Signal Explanation → Measurement Type) | Médio | gate individual cada (2G: suíte + lista real, sem gate) |

**Riscos transversais:**
- P4 muda os pesos efetivos das execuções via UI de 0.33→0.70/0.25/0.05: o usuário verá diferenças de classificação nas listas que reprocessar. Isso é a correção, mas precisa estar dito no changelog/commit para não parecer regressão aleatória.
- Gate e analógicos: o ledger registra que analógicos são hoje silenciosamente excluídos do `gate_tdt_real` (follow-up SP-Pendencias-09jul Task 8). 2B (FASES analógicos) não pode se apoiar só no gate — exige verificação manual em lista real com analógicos (GTA) e, se o esforço couber, é o gatilho natural para fechar aquele follow-up.
- P5-C1 toca o roteador — a peça mais sensível; por isso diagnóstico primeiro e uma correção por rodada.

**Verificação obrigatória antes do closeout (CLAUDE.md §Não-regressão item 4):**
1. Suíte completa (`PYTHONPATH=src python -m pytest`).
2. `bench/gate_tdt_real.py` — `pct >= baseline` após cada mudança gated (baseline congelado no início da implementação).
3. `scripts/relatorio_fluxo_real.py` — 0 PERDAS nas listas reais (conservação/identidade).
4. Comparação de comportamento com as listas reais já suportadas (SAN2, CVA, LVA, GAU, GTD) — em especial após P4 (pesos efetivos mudam via UI).
5. Ledger `docs/AGENTS.md`: uma linha por decisão implementada/revertida; DOX pass.

---

## 9. Decisões abertas (para a revisão desta spec)

1. **P1:** renomear o header "Endereço" → "Endereço Input"? (custo zero; recomendo sim, alinha com observações_pendentes item 2).
2. **P4:** além da migração automática do trio stale, apagar já as 3 linhas do `config.toml` versionado neste repo? (recomendo sim, no mesmo commit da implementação).
3. **P5-C1:** quando os discriminadores não resolvem a variante, preferir decidir a variante-pai exata da âncora (recomendado) ou sempre `variante_ambigua` para revisão? Trade-off: taxa de decisão × risco de variante errada (o gate arbitra, mas a preferência de produto é sua).
4. **P2-2F:** em divergência de estados entre a coluna FUNÇÃO da aba e o catálogo `Message Mapping`, qual fonte prevalece? (proposta: FUNÇÃO da aba, com aviso).
5. **Prioridade:** a ordem do §8 (P4/P1 primeiro) atende? Se o incômodo maior for o P3 (produtividade na revisão), ele pode subir para a Fase 1 sem custo técnico.

## 10. Referências

- Evidências de código: `modelo_tabela.py:221-224,342-350`, `engine_tdt.py:174-225`, `contracts.py:42-46,108-137`, `dc_pairer.py:29-176`, `normalizador_estrutural.py:52-88`, `estado.py:68-197`, `tela_revisao.py:49-81,202,600-672`, `config.py:38-48`, `config_io.py:27-104`, `tela_config.py:122-140,234-275`, `lista_padrao.py:19-36,138-175`, `ancoragem_sigla.py:66-173`, `roteador.py:47-163`, `pipeline.py:252-282,326-328,453`.
- Medições 17/07: colunas/sheets da `Pontos Padrao ADMS_v8.xlsx` (§4.1); `config.toml` da raiz (§6).
- Ledger: `docs/AGENTS.md` (v5 diluição; type_severidade revertido; tuning 09jul "MANTER 0.70/0.25/0.05"; follow-ups FGOO e gate-analógicos; direção bloqueada por dado).
- `docs/fluxo_dados.md` (mapa lê/escreve/sobrescreve + lacuna coluna EQUIPAMENTO).
- Backlog correlato ainda aberto: `docs/observações_pendentes.txt` itens 2 (colunas de endereço — parcialmente coberto por P1), 10 (seguir sinal pareado — coberto por P3), 16 (KMDF — coberto por 2G, DMS Signal Explanation como fonte).
