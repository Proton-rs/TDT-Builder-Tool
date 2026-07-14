# SP-CVA2 — 2ª rodada de correções da revisão CVA (BC2 posição/comando + CVA11 direção) — Design

**Data:** 2026-07-14
**Status:** Implementado e validado no dado real (E1-E6 + follow-up; gate `bench.regressao` idêntico ao baseline em todas as tasks — ver ledger em `docs/AGENTS.md`)
**Fonte:** `docs/anot.txt` (2ª rodada de observações do usuário sobre a lista CVA resumida, pós-SP-CVA 13jul). Input real: `C:\Users\vinic\Documents\docs importantes\RGE\CVA\CVA - Pontos Por Equipamentos DNP_V03 - COS - resumida.xlsx`.
**Evidência:** rodada nova de `bench/diag_cva.py` sobre o main atual (`bench/resultados/diag_cva_rodada2.log`) + sonda pré-scoring nas sheets BC2/CVA11 (estruturação → identidade → pareamento_polaridade, com dump de células cruas). Números e textos abaixo são do dado real, não estimados.
**Nota de build:** as 17 tasks do SP-CVA entraram no main DEPOIS da geração dos TDTs revisados (v3 de 13jul). Parte do que o usuário viu já mudou; o diag rodada 2 estabelece o que AINDA falha no código atual — e é só isso que esta spec corrige.

---

## 1. Contexto e método

O usuário reportou 2 fatos por sheet + 2 hipóteses ("pensamentos"). Cada fato foi reproduzido no código atual e a causa cravada com evidência executável. As hipóteses do usuário se confirmaram parcialmente: os módulos da BC2 vêm rotulados `BC1` no conteúdo (colisão já detectada pelo `modulo_duplicado_entre_sheets`), e no CVA11 a direção errada de fato impede o pareamento — mas a causa primária não é colisão de endereço, é a evidência estrutural de tipo/direção que o parser não lê.

Conforme pedido, a spec cobre também as melhorias que se destravam assumindo os fatos corrigidos ("o que mais poderia melhorar em cima delas") — eixos E2, E4, E5 e E6.

## 2. Mapa observação → causa verificada

| # | Observação (anot.txt) | Causa verificada (evidência) |
|---|---|---|
| 1 | BC2: DJF1 incorretamente classificado como DJA1 (o comando do DJF1) | O comando `'Disjuntor 52-06 (28QO) - Abrir/Fechar'` (BC2:14) não converge para a sigla do par de status. `forcar_polaridade_equipamento` exige par ligado/desligado EXATO — `len(ligado)==1 and len(desligado)==1` (`pareamento_polaridade.py:133`). O grupo real `('BC1','Disjuntor','52-06')` tem, além de `'Aberto'` (BC2:21), 3+ linhas `'Supervisão Circ Abertura'` cujo token `ABERTURA` bate o prefixo `ABERT` → `len(desligado)>1` → `continue`. **Ninguém é forçado** (sonda: `forcados=[]`); o scorer decide status=DJF1 (por sorte certo) e comando=DJA1. A fixture da Task 8.1 passou porque só tinha 3 registros limpos — o dado real tem ruído no grupo. |
| 2 | BC2: comando de endereço 90 não atribuído ao DJF1 | Consequência do item 1: `dc_pairer._chave` agrupa por sigla (`dc_pairer.py:21-25`) → comando DJA1 fica num grupo sem input → `comando_sem_discreto` (diag rodada 2, BC2 linha 14). Mesmo padrão em BC1 (endereço 80) e BC5_6 (100 e 102). |
| 3 | BC2: "o comando nem aparece na revisão" | No código atual o comando ESTÁ na revisão (`comando_sem_discreto`, motivo rotulado desde a Task 2). Duas explicações possíveis: (a) a sessão de revisão do usuário usou o build anterior às correções; (b) visibilidade — a linha aparece com sigla **DJA1**, e quem procura o comando do DJF1 (por sigla ou por endereço output) não a encontra. Verificação de UI incluída no E6; recomendação: regenerar o TDT com o main atual antes da próxima revisão. |
| 4 | BC2: módulos todos errados (BC1 em vez de BC2) | Confirmado no dado: a coluna de módulo da sheet BC2 diz `'BC1'` em todas as linhas (dado de origem errado — col 1 e prefixo dos nomes col 6/8). Colisão já detectada e roteada (`modulo_duplicado_entre_sheets`, Task 6). **Achado novo:** o módulo-por-linha derivado do nome produz módulos-lixo — `BC1_CORRENTE_IB` (BC2:9), `(LógicainternadeIntertravamento!)` (BC2:26) — sem sanitização, fragmentando o módulo em nomes espúrios. |
| 5 | CVA11: comando/controle classificado como Input | A sheet é organizada por marcadores de seção — `MEDIÇÃO` (linha 4), `CONTROLE` (linha 13), `SINALIZAÇÃO` (linha 19) — e o vocabulário JÁ mapeia todos (`classificar('CONTROLE') = ('Discrete','Output')`). Mas `_eh_marcador` exige a linha com **exatamente 1 célula preenchida** (`estruturador.py:34-39`) e no CVA11 as linhas de marcador têm um número de sequência na col 0 (`('1','MEDIÇÃO')`, `('10','CONTROLE')`, `('16','SINALIZAÇÃO')`) → 2 células → marcador nunca reconhecido → comandos (linhas 14-18) caem no default `Input`. Na BC2 a linha `CONTROLE` tem 1 célula só — por isso lá o comando vira Output e no CVA11 não. |
| 6 | CVA11 (hipótese do usuário: tipo errado em outras sheets → colisões de endereço) | Confirmada a mecânica: com direção Input, os endereços de comando (0..n do espaço Output) colidem com os inputs de mesmo índice. **Achado bônus:** a sheet TEM coluna de tipo com códigos `AI`/`DI`/`DO` (col 5, presente também na BC2) que `_col_tipo` não reconhece (vocabulário não tem os códigos) — evidência por-linha mais forte que o marcador, hoje ignorada. |
| 7 | (colateral, sonda) `'Falta de Potencial'` (CVA11:47) classificado Analog | `_grandeza_continua` casa `POTENCIA` por substring (`estruturador.py:56-58`) — `FALTA DE POTENCIAL` vira Analog/Input. É status discreto (falta de potencial). Match sem fronteira de palavra + sem guarda para contexto `FALTA/PERDA`. |

## 3. Eixos de correção

Cada eixo é independente, com gate individual (`bench/gate_tdt_real.py` ≥ baseline) quando toca scoring/roteamento.

### E1 — Par de posição robusto a ruído do grupo (fatos 1-2, causa primária)

`forcar_polaridade_equipamento`: a seleção dos candidatos ao par ligado/desligado passa a exigir **texto residual de posição pura** — depois de remover tokens do equipamento, o texto normalizado é essencialmente o particípio de polaridade (`ABERTO/A`, `FECHADO/A`, `LIGADO/A`, `DESLIGADO/A`, palavra exata, não prefixo). Linhas com qualificadores (`SUPERVISAO`, `CIRC*`, `MOLA`, `FALTA`…) não entram no par. Os prefixos atuais continuam valendo para `eh_texto_de_posicao` (gate de decisão), que tem outra função.

Com o par forçado, a convergência do comando toggle (código existente, `pareamento_polaridade.py:153-163`) volta a disparar — BC1:14, BC2:14, BC5_6:8 e BC5_6:10 convergem para DJF1 sem tocar no scorer.

### E2 — Reconciliação comando↔status no dc_pairer (melhoria em cima do E1)

Rede de segurança para quando o par NÃO for forçado e o scorer divergir (o modo de falha exato desta rodada): antes de agrupar, se um grupo `(módulo, equipamento)` tem comando toggle órfão com sigla de POSIÇÃO (`DJA1`/`DJF1`/`SEC*`) diferente da sigla de posição dos status decididos do mesmo equipamento, re-chavear o comando para a sigla dominante do status. Determinístico, só re-chaveia dentro do catálogo `_SIGLAS_POSICAO`, nunca mexe em score.

### E3 — Evidência estrutural de tipo/direção (fatos 5-6)

Três correções no parser, todas com fixture do layout real:
1. **`_eh_marcador` tolerante a numeração:** aceitar linha onde UMA célula classifica como categoria e as demais preenchidas são numeração/índice (inteiro curto ou vazio semântico). Mantém a exigência de linha "estruturalmente vazia" — não afrouxa para linhas de dados.
2. **Códigos de tipo `AI`/`AO`/`DI`/`DO` no vocabulário** (`vocabulario_tipo`): `AI→(Analog,Input)`, `AO→(Analog,Output)`, `DI→(Discrete,Input)`, `DO→(Discrete,Output)`. Com isso `_col_tipo` detecta a col 5 do CVA11/BC2 e a direção fica por-linha (evidência mais forte que seção; a precedência atual coluna>seção já existe em `estruturador.py:101-104`). Cuidado de calibração: códigos de 2 letras são curtos — exigir match de célula inteira (célula == código), não substring.
3. **`_grandeza_continua` com fronteira de palavra + guarda:** match por token (não substring) e não disparar quando o texto começa com `FALTA`/`PERDA` (é status de ausência, não medição). Corrige o fato 7 sem reintroduzir o problema da Task 9.

Nota de coerência com o ledger: "classificação de direção por texto do sinal" segue **bloqueada por dado** — E3 usa evidência ESTRUTURAL (marcador de seção, coluna de códigos), não o texto da descrição.

### E4 — Fusão do par de posição antes do dc_pairer (melhoria em cima; destrava o par completo)

Hoje o double-bit funde só no `normalizador_estrutural`, que roda DEPOIS do `dc_pairer`. Consequência: mesmo com E1/E2 corrigidos, o grupo DJF1 chega ao pairer como **2 inputs + 1 output** e cai no catch-all greedy (`dc_pairer.py:111-114`) — funde com um bit só, ou nem isso se a similaridade `'ABRIR FECHAR'`×`'ABERTO'` ficar abaixo do limiar (60.0) e o comando cair em `pareamento_ambiguo`. Correção: fundir o par de posição (mesma sigla de posição, mesmo equipamento, 2 inputs) num único registro `MultiCoord` ANTES do `dc_pairer` → 1 input × 1 output → ReadWrite limpo, INCOORDS `320;321`, OUTCOORDS `90`.

Resolve de brinde dois itens re-reportados de `observações_pendentes.txt`: "dois DJF1 com endereços sequenciais 900/901 não mesclados" (item 1) e "DCpairer não está funcionando na revisão, DJF1 do 24-1 sem pareamento" (item 13). Risco: mudança de ordem no pipeline — exige gate + invariante de conservação verde.

### E5 — Módulo por linha: sanitização + caminho do operador (fato 4)

1. **Sanitização:** valor de módulo derivado por linha que não casa o padrão de módulo conhecido (prefixo de tipo + número operativo, tabelas de `config.py`) → fallback para o módulo dominante da sheet + aviso em `avisos` (não silencioso, não vira nome de módulo lixo).
2. **Aviso de divergência sheet×conteúdo:** quando o módulo resolvido por linha difere do nome canônico da sheet na maioria das linhas (caso BC2→BC1), emitir aviso explícito no relatório e na UI ("sheet BC2: conteúdo rotulado BC1 — verificar módulo na origem"). O operador corrige em lote com o que já existe (coluna módulo editável + "Aplicar à seleção", Tasks 11-12).
3. O requisito do usuário "mesmo com módulo errado, a revisão deve ter todos os sinais" vira invariante testada (E6.1).

### E6 — Invariantes e visibilidade (melhorias em cima; garantem o contrato com o operador)

1. **Conservação total:** estender `tests/test_conservacao_comandos.py` para TODAS as direções — todo sinal da entrada termina no TDT ou na revisão, nunca some. (Hoje o invariante cobre só comandos.)
2. **Gate `endereco_duplicado`:** dois registros com mesma direção e mesmo índice no workbook final → ambos para revisão com motivo próprio, texto sugerindo verificação de direção/tipo ("endereço N duplicado em X e Y — possível tipo de sinal errado na origem"). É o detector genérico do sintoma que o usuário descreveu na hipótese do CVA11.
3. **UI — comando visível e acionável:** coluna "Pareado" mostra `"Comando (sem par)"` para Output com `indices` (hoje mostra `"—"`, só Output sem endereço vira "Órfão", `modelo_tabela.py:223-229`); teste de UI garantindo que item `comando_sem_discreto` renderiza com endereço + sigla + motivo legível (fecha a verificação do fato 3).
4. **Linhas de marcador não viram sinal:** com E3.1, `MEDIÇÃO`/`CONTROLE`/`SINALIZAÇÃO` passam a ser consumidas como marcador (hoje viram registros-lixo, ex. CVA11:4/13/19 na sonda).

## 4. Alternativas consideradas

- **A (recomendada): SP único faseado**, receita do SP-CVA/SP-Unificado — E1→E2→E3 (pipeline, gate individual), E4 (ordem do pipeline, gate + invariantes), E5→E6 por último. Um ciclo de plano.
- **B: corrigir só os fatos (E1+E3), melhorias depois** — menor risco imediato, mas E2/E4 são exatamente a robustez que impede a 3ª rodada da mesma observação (scorer divergindo de novo em outra SE), e E4 destrava dois itens já re-reportados 2×.
- **C: atacar pela direção por texto** ("Abrir/Fechar" → Output) — rejeitada: decisão do ledger (bloqueada por dado, 156/243 comandos reais têm texto de puro status); os casos desta rodada se resolvem com evidência estrutural.

## 5. Fora de escopo

- Corrigir o dado de origem (BC2 rotulada BC1 nas células) — dado do cliente; o sistema avisa (E5.2) e dá o caminho de correção em lote.
- Direção/comando por texto da descrição — segue bloqueada por dado (ledger).
- Inferência de equipamento por topologia de módulo (observações_pendentes item 7) — spC2, ciclo próprio.
- Demais itens de `observações_pendentes.txt` não re-reportados no anot.txt (rearranjo de colunas, redo, scores de ambíguos etc.) — permanecem na spec A/backlog.

## 6. Critérios de sucesso

- **Casos reais (diag rodada 3, mesmo input):** BC1:14 (end. 80), BC2:14 (end. 90), BC5_6:8/10 (end. 100/102) → fundidos ReadWrite com sigla DJF1 (ou, com módulo colidido, em revisão como par fundido com endereço de output visível — nunca `comando_sem_discreto`); CVA11:14-18 com direção Output; CVA11:47 Discrete/Input; zero linhas de marcador viram sinal.
- `bench/gate_tdt_real.py` ≥ baseline em toda task de pipeline, medida individualmente.
- Invariantes verdes: conservação total (E6.1); nenhum módulo-lixo (E5.1); `endereco_duplicado` detecta o cenário sintético de direção trocada.
- Operador: comando sem par visível na revisão com endereço e rótulo claro ("Comando (sem par)").

## 7. Questões em aberto (não bloqueiam o plano)

1. **E2 — re-chavear automático × sugerir na revisão:** re-chavear muda uma decisão do scorer sem passar pelo operador. Partida proposta: re-chavear só quando o status de posição do equipamento é único e inequívoco; senão, revisão com motivo `posicao_divergente`. Confirmar na revisão da spec.
2. **E4 — onde fundir:** estender `pareamento_polaridade` (que já conhece o par) ou puxar a fusão do `normalizador_estrutural` para antes do `dc_pairer`? Decidir no plano com o mapa de dependências dos dois módulos.
3. **Fato 3 — build antigo:** confirmar com o usuário se a revisão que gerou o anot.txt usou TDT anterior ao merge do SP-CVA (v3 de 13jul). Se sim, parte da queixa de visibilidade já está resolvida; o E6.3 vira só cinto de segurança.
