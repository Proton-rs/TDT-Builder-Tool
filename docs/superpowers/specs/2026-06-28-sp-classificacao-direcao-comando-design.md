# SP-Direção — Classificação de direção (comandos lidos como Input)

**Data:** 2026-06-28
**Status:** Aguardando revisão do usuário
**Origem:** Medição real (`input_nao_homogeneo_1`, GTA). Comandos estão sendo
classificados como `Input`, o que impede o pareamento D+C e infla
`pareamento_ambiguo`.

## Problema

A direção do sinal (`Input` = status / telemetria; `Output` = comando) é
definida em [estruturador.py](../../../src/tdt/normalizacao/estruturador.py):

1. por linha, pela **coluna Tipo** (`vocabulario_tipo.classificar(row[c_tipo])`), ou
2. pelo **marcador de seção** na coluna 1 (ex.: "Comandos/Controle"), ou
3. **default** `("Discrete", "Input")` quando nada é reconhecido.

Na medição real, sinais que são comandos aparecem como `Input`:

```
(TR1, 52-2, CMD)  -> [Input 611, Input 612]   # CMD = comando, mas Input
(TR1, FCMR)       -> {Input: 5, Output: 2}     # mistura
(AL11, P51N)      -> {Input: 2, Output: 1}
```

### Por que importa (impacto medido)

`dc_pairer.parear` funde **1 Input (status) + 1 Output (comando)** da mesma
chave `(módulo, equip, sigla)` num ponto `ReadWrite` (como a TDT real:
`dir=ReadWrite`, `INCOORDS` do status + `OUTCOORDS` do comando). Quando o
comando é lido como `Input`, o grupo vira "N inputs, 0 ou poucos outputs" →
**não pareia** → vai pra revisão (`pareamento_ambiguo`, 142 sinais na medição).
Também contamina `endereco_duplicado` (dois "inputs" de mesma sigla que na
verdade são status + comando).

### Ground-truth (TDT real)

`docs/TDT/exportTDT_UTR_{GTD,FWB}_*.xlsx`, sheet `DNP3_DiscreteSignals`:
coluna `SIGNAL_DIRECTION` e os blocos `REMOTEINPUT…INCOORDS` /
`REMOTEOUTPUT…OUTCOORDS`. Pontos comandáveis saem como `ReadWrite` com os dois
conjuntos de coordenadas — é o alvo do pareamento.

## Escopo

Diagnóstico + correção da **detecção de direção** na leitura da planilha.
**Não** mexe em scoring, regras ou na lógica de fusão do `dc_pairer` (essa já
está correta; só recebe direções erradas).

### D1 — Diagnóstico: por que o comando vira Input

Levantar, nas sheets reais (GTD V11, FWB V13), **como** os comandos são
marcados:

- Há uma **coluna Tipo** com valor de comando que `vocabulario_tipo` não
  reconhece? (ex.: "CMD", "C", "Comando", "Controle", "Saída", "DO").
- Os comandos estão numa **seção** cujo marcador não está no vocabulário de
  seção? (ex.: "COMANDOS", "CONTROLE", "TELECOMANDO").
- O endereço de comando está numa **coluna separada** (Endereço Output) na
  mesma linha do status — caso em que não é "outra linha Input", e sim a mesma
  linha com IN+OUT? (a TDT real tem INCOORDS e OUTCOORDS na mesma linha).

Esse último ponto é o mais provável e muda o desenho: se a planilha já traz
endereço de input **e** de output na mesma linha, o sinal nasce `ReadWrite` —
não precisa parear duas linhas.

### D2 — Estender o vocabulário de direção/seção

Em `vocabulario_tipo` (e nos marcadores de seção): adicionar os termos de
comando observados em D1 → `("Discrete", "Output")`. Tabela em `config.py`
(calibrável), nunca hardcoded fora dela. Mesmo princípio das abreviações.

### D3 — Linha com endereço de input E output (se confirmado em D1)

Se as sheets trazem as duas colunas de endereço na mesma linha:

- O estruturador lê `indices` (input) **e** `indices_saida` (output) da linha.
- O sinal nasce `direcao="InputOutput"` com os dois conjuntos — sem depender do
  `dc_pairer` para parear. (O `dc_pairer` continua para o caso de status e
  comando em **linhas separadas**.)
- A coluna de endereço Output já existe no contrato (`Enderecamento.indices_saida`)
  e na UI/TDT (engine usa `OUTCOORDS`). Falta a **leitura** no estruturador
  quando a coluna existir.

### D4 — Validação

- Recontar `pareamento_ambiguo` antes/depois na `input_nao_homogeneo_1`
  (esperado: queda forte — os pares status+comando passam a fundir).
- `python -m pytest -q` verde.
- `bench/benchmark.py` sem regressão (direção não afeta o matching de sigla,
  mas o gate é obrigatório).
- Conferir contra a TDT real: comandos viram `ReadWrite` com INCOORDS+OUTCOORDS.

## Fora de escopo

- Inferir direção pelo **texto** da descrição (ex.: "Ligar"/"Desligar" ⇒
  comando) — heurística arriscada; só usar se D1 mostrar que não há coluna/seção
  confiável. Fica como fallback opcional, separado.
- Lógica de fusão (`dc_pairer`) — já correta.
- Classificação Discrete vs Analog — ortogonal.

## Dependências

- Independe das specs C, v6 e SP-GT. Pode ir em paralelo.
- Sinérgica com a chave `(módulo, equip, sigla)` já implementada (o pareamento
  por equipamento só rende se as direções estiverem certas).

## Critérios de aceite

1. D1 documenta como os comandos são marcados nas sheets reais (coluna/seção/
   coluna de endereço output).
2. Vocabulário de direção/seção reconhece os termos de comando reais.
3. Se aplicável (D3), estruturador lê endereço de output da mesma linha →
   sinal `InputOutput`.
4. `pareamento_ambiguo` cai na medição real, sem novos falsos pareamentos.
5. `python -m pytest -q` verde; `bench/benchmark.py` sem regressão.
