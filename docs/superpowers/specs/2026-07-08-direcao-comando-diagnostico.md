# Diagnóstico: como um comando (direção) aparece no dado real — SP-Unificado Fase 8

**Data:** 2026-07-08
**Status:** DIAGNÓSTICO — destrava a decisão de design D1-D4. Não implementado (decisão do usuário).
**Script:** `bench/diag_direcao_comando.py` → `bench/resultados/diag_direcao_comando.log`
**Método:** cruza por endereço DNP3 os sinais que o TDT real marca como comando
(coluna `Direction` ∈ {`Write`, `ReadWrite`}) com a direção que o nosso pipeline
atribui à mesma entrada, e dumpa o texto bruto de entrada.

## Números (GTD, `input_nao_homogeneo_1_GTA` × `exportTDT_UTR_GTD_1`)

- Comandos reais (ReadWrite): **243** (+ 2 `Write` puros como CDC).
- Nossa direção nesses 243 endereços:
  - `Input` (perdemos o comando): **156**
  - `InputOutput`: 48
  - `Output`: 22
  - `AUSENTE` (não geramos o ponto): 17
- **Acerto de direção (Output/InputOutput): 70/243 (~29%).**

## Achado central (o que destrava a decisão)

**A entrada NÃO sinaliza direção textualmente.** Nos 156 casos perdidos, o texto
de entrada é **puro status/posição**, sem nenhum verbo de comando:

| addr | nome real | texto de entrada | Message Mapping (real) |
|---|---|---|---|
| 13 | 89-2_SECC | `Secc. 89-2 (01Q1 Barra) - Aberta` | `ABRIR@FECHAR___ABERTO@FECHADO___SwitchStatus` |
| 628 | 52-10_DJF1 | `Disj. 52-10 (06Q4) - Desligado` | `DESLIGAR@LIGAR___DESLIGADO@LIGADO___SwitchStatus` |
| 51 | LTGTA_AJG2 | `Grupo de Ajustes 2 - Ativo` | `DESATIVAR@ATIVAR___DESATIVADO@ATIVADO___Custom` |
| 697 | TR1_P_87 | `Proteção - Diferencial (87) Bloqueado` | `INCLUIR@EXCLUIR___INCLUIDO@EXCLUIDO___Enabled` |
| 650 | TR1_CDC | (tap) | `AUMENTAR@DIMINUIR___null@null___TapIncrement` |

A "comandabilidade" vive só no **Message Mapping** do TDT real (o 1º segmento
`X@Y` antes de `___` são os estados de COMANDO). No dado de entrada só existe o
estado observado (status). Ou seja: **comando é uma propriedade do
equipamento/família-de-estado, não um marcador no texto**.

Os 70 que acertamos são justamente as sheets que trazem uma seção
`Comandos`/`Controle` explícita ou verbo de comando (`Abrir/Fechar`,
`Ligar/Desligar`) numa linha própria; a maioria das sheets lista só o status.

## Consequência para D1-D4 (decisão do usuário)

Não há regra determinística **de texto** que classifique direção — a evidência
não está na entrada. As opções reais são:

1. **Mapa equipamento/família-de-estado → comandável** (determinístico, sem
   texto). Ex.: seccionadora (`SwitchStatus`), disjuntor, comutador de tap
   (`TapIncrement`), enable/exclude de proteção (`INCLUIR@EXCLUIR`), modo
   mestre/individual → marcar `ReadWrite`. É o que o TDT real efetivamente faz
   (via catálogo de Message Mapping por família).
2. **Consumir o catálogo de Message Mapping** (a fonte de verdade da direção)
   em vez de inferir da entrada.
3. **Aceitar** que entradas de puro-status fiquem `Input` e a direção seja
   preenchida numa etapa posterior (catálogo/revisão), não pelo classificador.

**Recomendação para discussão:** opção 1/2 — a direção é dado de catálogo
(família de MM), não de linguagem natural. Nenhuma delas é código trivial nem
está no escopo desta rodada; requer decisão explícita antes de implementar.

## Ressalva

Amostra de 1 subestação (GTD). Confirmar o padrão em GAU/GPR/FWB antes de
fechar a regra — o script aceita trocar `_INPUT`/`_REAL` para rodar nas outras.
