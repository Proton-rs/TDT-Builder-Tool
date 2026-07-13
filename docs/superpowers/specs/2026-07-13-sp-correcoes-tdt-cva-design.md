# SP-CVA — Correções pós-revisão das TDTs da SE CVA — Design

**Data:** 2026-07-13
**Fonte:** `docs/anot.txt` (13 observações do usuário sobre as últimas TDTs geradas da **SE CVA**). Input real: `C:\Users\vinic\Documents\docs importantes\RGE\CVA\CVA - Pontos Por Equipamentos DNP_V03 - COS - resumida.xlsx` ("lista CVA resumida", sheets confirmadas: CAPA, IP, CVA11-14, CVA21-23, TRF, BC1, BC2, BC3_4, BC5_6, S4_LOG). Outputs gerados: `output/TDT_CVA_20260713_v3.xlsx` + `output/Auditoria_CVA_20260713_v3.xlsx` (versão mais recente; há também v1/v2 no mesmo diretório, geradas na mesma sessão de revisão).
**Correção 13jul:** a versão anterior deste documento citava por engano `docs/RGE GAU 2026 - Lista de Pontos v09.xlsx` como fonte — arquivo não relacionado a estas observações. Confirmado por leitura direta do input real: as sheets BC1/BC2/BC5_6/CVA11 citadas no anot.txt existem na lista CVA, não na GAU.
**Verificação de código:** 13jul (scouts pipeline + UI), cruzada com o Ledger de decisões (`docs/AGENTS.md`) e specs existentes (spA 26jun, spI 02jul, SP-Unificado 08jul).

---

## 1. Contexto e método

O usuário revisou as últimas TDTs geradas para a SE CVA e anotou 13 observações (`docs/anot.txt`), mais uma reportada em conversa (item 14, tensão CA×AC — 13jul). Este design mapeia cada observação à causa verificada no código atual e agrupa as correções em 6 eixos. Itens cuja causa depende do dado real (a lista CVA resumida e o TDT/Auditoria gerados) ganham **diagnóstico reproduzível primeiro** — regra do projeto: não codar correção de pareamento/endereço sem reproduzir o caso (histórico: Fase 8 do SP-Unificado, "bloqueada por dado").

Sobreposição com `docs/observações_pendentes.txt` e com a spec A (26jun, "revisão UI lote/endereçamento/módulo" — 3/9 itens implementados até hoje): os itens re-reportados no anot.txt entram aqui; o restante da spec A permanece lá.

## 2. Mapa observação → causa verificada → eixo

| # | Observação (anot.txt) | Causa verificada (código) | Eixo |
|---|---|---|---|
| 1a | BC1: DJA1 deveria ser DJF1 | `pareamento_polaridade` exige equipamento=Disjuntor; sem módulo/equipamento o sinal passa intacto e o scoring escolhe DJA1. Usuário: causa (falta de módulo) é aceitável; falta **caminho de correção pelo operador** (ver 6) | E5 |
| 1b | BC1: comando faltando "endereço 80 dos comandos" | Não determinável sem o arquivo — diagnóstico | E1→E3 |
| 2 | BC1: 50N E2 não identificado | `filtro_preciso.f_r4` (linhas 96-107): texto com estágio (E2) **remove** candidatos cuja sigla não termina no dígito. Se a família 50N não tem variante "…2" na lista padrão, o próprio 50N correto é removido/penalizado. Upgrade path já anotado no código | E2 |
| 3 | BC2: DJF1 classificado sem comando | `dc_pairer`: comando pode ficar preso em revisão (`pareamento_ambiguo`, `comando_sem_discreto`) ou o par fundido sai inteiro pelo gate `custom_id_duplicado` (`pipeline.py:715-735`). Na UI o motivo renderiza "—" (ver 13) e não há coluna "Pareado" → comando parece sumir. Confirmar cadeia no diagnóstico | E1→E3, E5 |
| 4 | BC2: 51F/51F1 → FC87 (descrições muito discrepantes) | `roteador._quadrante`: decide com `pct≥0.45 e gap≥0.08`; **não existe piso absoluto** de similaridade — top-1 fraco com gap grande decide mesmo com texto discrepante | E2 |
| 5 | BC2: comando do DJF1 não pareado | Mesma cadeia do item 3 — diagnóstico | E1→E3 |
| 6 | CVA11/GERAL: DJA1→DJF1 sem como o operador corrigir (sem par multicoord/double-bit na UI) | UI de revisão não tem editor de par de posição: `decidir_acao_pareamento` só trata Input/Output/InputOutput; não há "formar par MultiCoord" nem swap DJA1↔DJF1 preservando o par | E5 |
| 7 | GERAL: marca múltiplas linhas mas não aprova/renomeia/edita múltiplas; double-click quebra formatação | Seleção múltipla existe (`SelectRows`); em lote só Remover e Parear. `_aprovar_e_proximo` é linha-a-linha; edição não propaga (spA §A1 nunca implementada). Bug de formatação no double-click: sem causa conhecida — reproduzir | E5 |
| 8 | CVA11: VAB com tipo=input, classificação errada (tipo na linha × na coluna) | `estruturador.py:86-89`: tipo vem da célula TIPO ou do marcador de seção precedente. Layout do CVA11 precisa de diagnóstico (qual coluna `_col_tipo` escolheu) | E1 |
| 9 | GERAL: endereço editável; nome completo do sinal; painel de info; contagem de pendentes/totais por sheet | Endereço não está em `_EDITAVEIS`; nome hierárquico não é exibido; painel lateral **existe** (scores/candidatos/busca); abas já mostram pendentes por sheet, falta o **total** | E5 |
| 10 | BC5_6: comando DJF1 desaparecido | Mesma cadeia do item 3 (candidato forte: par fundido removido por `custom_id_duplicado` — colisão causada pelo item 11) — diagnóstico | E1→E3 |
| 11 | BC1/BC2: módulo incorretamente nomeado na origem → sinais iguais que pareciam do mesmo módulo; gerar aviso | Dado do cliente errado (fora de alcance corrigir); o sistema detecta colisão só no fim (`particionar_custom_id_duplicado`) com motivo genérico. Falta aviso explícito "sinais iguais no mesmo módulo vindos de sheets distintas" | E4 |
| 12 | GERAL: identificador da sheet de origem | `sheet_origem()` já existe (`modelo_tabela.py:60`, usada nas abas/proxy) — só não é coluna nem vai destacada no relatório | E5 |
| 13 | GERAL: "futuro" → "sem endereço"; melhorar descrição dos motivos | `_MOTIVO_LABEL` mapeia 9 motivos; o pipeline emite 14 (`pareamento_ambiguo`, `custom_id_duplicado`, `posicao_ambigua`, `comando_sem_discreto`, `comando_tap_nao_modelado`, `decisao_por_projeto`, `descartado_*`… ficam de fora). Não mapeado renderiza **"—"** (`modelo_tabela.py:145`). Label atual "Futuro (sem endereço)" | E6 |
| 14 | Tensão fase CA: na TDT deve sair "AC" (domínio ADMS); identificar as fases e usar a ordem certa | **Causa confirmada no template** (13jul): domínio `PhaseCode` da sheet `DMSMatchingTemplateInfo` = {N, A, B, C, AB, BC, **AC**, ABC} — ADMS usa par alfabético. O pipeline usa `CA` internamente (`normalizador.FASES:72`) e `engine_tdt._fase_saida` (`:144-148`) escreve `CA` na coluna Phases — valor fora do domínio, ADMS rejeita. E o inverso: input com "AC" não é extraído (fase=None → "ABC") | E2 |

## 3. Eixos de correção

### E1 — Diagnóstico reproduzível na lista CVA (bloqueia E3 e o fix do item 8)

Script `bench/diag_cva.py` (padrão dos `bench/diag_*.py` existentes): roda o pipeline sobre `CVA - Pontos Por Equipamentos DNP_V03 - COS - resumida.xlsx` e compara com o já gerado `output/TDT_CVA_20260713_v3.xlsx`/`Auditoria_CVA_20260713_v3.xlsx`, rastreando caso a caso:

- **Comandos** (BC1 "endereço 80", BC2 DJF1, BC5_6 DJF1): para cada linha de comando do input, onde terminou — TDT ReadWrite / Write órfão / revisão (qual motivo) / **ausente** (perda silenciosa). Instrumenta a cadeia `dc_pairer → corrigir → montar → particionar_custom_id_duplicado → gerar`.
- **CVA11 VAB**: qual coluna `_col_tipo` escolheu, qual categoria/direção cada sinal analógico recebeu, e onde o layout difere (tipo em linha de seção × coluna).
- **Tensões entre fases (item 14, verificação)**: causa já confirmada no template (domínio `PhaseCode` usa `AC`); o diag só confere no TDT da CVA quais tensões saíram com Phases fora do domínio antes/depois da correção.
- **BC1/BC2 módulos**: quais Custom IDs colidiram e de quais sheets vieram os registros de cada grupo.

Saída: `docs/superpowers/specs/2026-07-13-diag-cva-achados.md`. As correções de E3 são instanciadas a partir dele — **uma causa = uma task = um gate**.

### E2 — Classificação (2 correções independentes, gate individual)

1. **`f_r4` estágio com fallback** (item 2): quando o texto tem estágio E1-E4 mas **nenhum** candidato da família termina no dígito, manter o candidato sem-estágio (hoje ele é removido). Só remover quem termina em dígito *diferente*. É o upgrade path já anotado no próprio código.
2. **Piso absoluto de decisão** (item 4): novo knob `config.piso_decisao` — se o score do top-1 (mesclado, pós-calibrador E4, antes do motor de regras) ficar abaixo do piso, rotear para revisão com motivo `score_baixo` mesmo com pct/gap ok. Valor inicial calibrado contra o gate (partida: 0.20). Protege contra o padrão "descrições muito discrepantes decididas".
3. **Fases na ordem certa fim-a-fim** (item 14) — duas metades, uma task:
   - **Extração (interno):** `_fase_no_texto` reconhece também os pares alfabéticos/invertidos (`AC`, `BA`, `CB`) e canoniza para a representação interna já usada (`CA`, `AB`, `BC` — como o texto de campo escreve). Interno não muda de convenção: textos, `f_r3` e a UI seguem `CA`.
   - **Boundary de saída (TDT):** `engine_tdt._fase_saida` traduz interno → domínio `PhaseCode` do template (`CA→AC`) e valida contra o domínio real da `DMSMatchingTemplateInfo` ({N, A, B, C, AB, BC, AC, ABC}, fallback `ABC`). `CA` nunca mais chega ao xlsx.
   Decisão: tradução só no boundary (padrão do projeto — mesmo racional do clamp de confiança na exibição); trocar a convenção interna inteira para `AC` mexeria em extração/lista padrão/UI sem ganho.

### E3 — Pareamento/comando (pós-diagnóstico)

Correções instanciadas do E1. Hipóteses mapeadas (não codar antes do diag): limiar greedy de similaridade (60.0) alto demais para os textos da CVA; gate `compatibilidade_texto` (D5) bloqueando par legítimo; captura do endereço de output do comando falhando na análise de colunas; par fundido removido por colisão de Custom ID (consequência do item 11).

Independente do achado, entra **uma garantia permanente**: teste de invariante de conservação — *todo sinal de comando que entra no pipeline aparece no TDT ou na revisão; nunca some silenciosamente* (fixture sintética + contagem fim-a-fim).

### E4 — Aviso de módulo suspeito (item 11)

No ponto do `particionar_custom_id_duplicado`: quando um grupo colidido tem registros de **sheets de origem distintas**, emitir motivo específico `modulo_duplicado_entre_sheets` (em vez do genérico `custom_id_duplicado`) e listar as sheets no texto da revisão/relatório. É o sinal de que a origem nomeou o módulo errado (BC2 rotulada como BC1). O sistema não corrige o dado do cliente — só torna o problema visível e acionável.

### E5 — UI de revisão (sem risco de gate; testes de UI/modelo)

1. **Aprovar em lote**: `_aprovar_e_proximo` ganha variante para todas as linhas selecionadas.
2. **Aplicar à seleção**: após editar célula de coluna editável com N linhas selecionadas, ação explícita (menu de contexto/botão) propaga o valor às selecionadas. Explícito, não automático — evita edição acidental em massa; integra com o undo existente (snapshot único).
3. **Endereço editável**: "Endereço" e "Endereço Output" entram em `_EDITAVEIS` com validação (inteiros, faixa DNP3 0..65535, lista `N;M`).
4. **Coluna "Pareado"**: derivada de `direcao`/`indices_saida` (dado já existe em `contracts.Pareamento`/SignalRecord) — resolve "não sei se o sinal tem comando" sem abrir o TDT.
5. **Coluna "Sheet origem"**: expõe `sheet_origem()` como coluna (função já existe).
6. **Nome hierárquico**: preview do Custom ID ADMS (`SE_MODULO_EQUIP_SIGLA`) no painel lateral — mesmo formato do `engine_tdt`.
7. **Par de posição na revisão** (item 6): com 2 linhas selecionadas, ação "Formar par de posição" — valida mesmo módulo/equipamento, funde como MultiCoord e pede a sigla (DJF1/DJA1/SEC\*); e swap de sigla DJA1↔DJF1 preservando o par. É o caminho de correção do operador para o erro de classificação por falta de módulo.
8. **Contadores**: abas passam a mostrar `pendentes/total` por sheet + total geral.
9. **Double-click × formatação** (item 7): tentativa de reprodução; se reproduzir, corrigir (suspeito: DisplayRole formatado sendo gravado via EditRole); se não, reportar e pedir passo-a-passo ao usuário.

### E6 — Motivos e relatório (item 13 + metade do 3)

1. Completar `_MOTIVO_LABEL` com **todos** os motivos emitidos (14 hoje) e trocar o fallback "—" por exibir o motivo cru — motivo existente nunca mais aparece vazio.
2. Renomear "Futuro (sem endereço)" → "Sem endereço".
3. Descrições mais explicativas (tooltip por motivo: o que aconteceu + o que o operador pode fazer).
4. Relatório de revisão destaca sheet de origem e o novo motivo de módulo duplicado.

## 4. Alternativas consideradas

- **A (recomendada): um SP faseado único** — mesma receita do SP-Unificado 08jul (funcionou): fases independentes, diagnóstico primeiro, scoring com gate individual, UI por último (sem gate). Um ciclo de plano, priorizável por fase.
- **B: dois SPs (pipeline × UI)** — separa riscos, mas duplica cerimônia e a UI depende de contratos do pipeline (Pareado, motivo novo); ordenação já resolve isso dentro do A.
- **C: só diagnóstico agora, spec depois** — mais seguro para E3, porém E2/E4/E5/E6 têm causa já verificada no código e não dependem do dado; atrasá-los não compra nada.

## 5. Fora de escopo

- Classificação de direção/comando por texto — **bloqueada por dado** (ledger, diagnóstico 08jul).
- Redo, "seguir sinal pareado" (focar id), drag de colunas — spec A §A2/A5, re-reportados em `observações_pendentes.txt`, não pedidos no anot.txt.
- Inferência de tipo de módulo por topologia (item 7 das observações pendentes) — spC2, ciclo próprio.
- Corrigir a nomenclatura errada na planilha de ORIGEM (BC2 rotulada BC1) — dado do cliente; o sistema avisa (E4), não corrige.
- spB-B2 (motor bounded) — segue "pendente por decisão" no ledger; o piso do E2 atua no roteador, não muda a escala do motor.

## 6. Critérios de sucesso

- Gate `bench/gate_tdt_real.py`: `pct >= baseline` em toda task que toca scoring/roteamento (E2, E3), medida individualmente.
- Invariante de conservação de comando testada: nenhum comando de entrada some sem aparecer no TDT ou na revisão.
- Motivo de revisão nunca renderiza "—" quando existe motivo.
- Operador consegue, na tela de revisão: aprovar N linhas de uma vez, propagar edição à seleção, editar endereço, formar/trocar par de posição DJA1↔DJF1, ver sheet de origem e contadores pendentes/total.
- Casos do anot.txt reproduzidos no diag (BC1 endereço 80, BC2/BC5_6 comando, CVA11 VAB) com causa documentada e correção aplicada ou explicitamente adiada com motivo.
- Coluna Phases da TDT sempre dentro do domínio `PhaseCode` do template (par alfabético: AB/BC/**AC**); extração interna reconhece o par em qualquer ordem (CA ou AC) e o filtro de fase continua funcionando.

## 7. Questões em aberto (não bloqueiam o plano; confirmar na revisão da spec)

1. **"endereço 80 dos comandos" (BC1)**: interpretado como endereços de output do bloco de comandos (~80+) não capturados. O diag confirma ou corrige a interpretação.
2. **Piso de decisão**: partida 0.20 calibrada pelo gate — ajustar se derrubar decididos demais.
3. **Lote**: propagação **explícita** ("Aplicar à seleção") em vez de automática ao editar — confirmar preferência.
4. **Double-click quebra formatação**: se a reprodução falhar, precisaremos do passo-a-passo exato (qual coluna, qual valor).
