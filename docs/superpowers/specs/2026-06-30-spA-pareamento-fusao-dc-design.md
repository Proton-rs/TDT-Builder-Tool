# SP-A — Pareamento & fusão D+C (status+comando → ReadWrite)

**Data:** 2026-06-30
**Status:** ⛔ DROPADA — incorporada na Spec D (decisão do usuário, 30jun). Mantida
como registro do diagnóstico A1, que é a entrada para a D.
**Origem:** Comparação `OUTPUT_TDT.xlsx` (gerado da `GTD - Lista de Pontos V11.xlsx`)
× TDT real `exportTDT_UTR_GTD_1_20260626.xlsx`, sheets de sinais.

## ⛔ Decisão (30jun): Spec A incorporada na Spec D

O diagnóstico A1 (rodado no código atual, pós-commit `3b30fba` "ancoragem por
sigla explícita") **derrubou a premissa desta spec**:

- **Verbos já resolvidos** — `3b30fba` corrigiu `LIGAR`/`DESLIGAR` virarem sigla
  (`verbo: 0` no diagnóstico). O `OUTPUT_TDT.xlsx` com 73 Write / 32 siglas-verbo
  era **pré-`3b30fba`**, stale.
- **Não-fusão restante (111 de 126 comandos) é matching, não pareamento:**
  - **68** comandos casaram uma sigla que **nenhum status do módulo tem** →
    comando e status do mesmo sinal físico casaram **siglas diferentes**
    (inconsistência de matching).
  - **42** casaram sigla **catch-all** que múltiplos status têm → ambíguo qual
    parear (precisaria do ID de equipamento, ausente no comando).
  - **1** funde limpo relaxando o equipamento.
- A chave do `dc_pairer` `(módulo, equip, sigla)` está **correta**; o gargalo é a
  **resolução de sigla do comando** (que comando e status convirjam para a mesma
  sigla padrão) — eixo de **qualidade de matching**, não de pareamento.

**Decisão:** abandonar A como spec separada; a **consistência comando↔status**
(comando deve resolver para a mesma sigla padrão do status do mesmo sinal) entra
como um eixo da **Spec D (qualidade de matching)**. Nova ordem: B → C → D.
Os invariantes de domínio abaixo seguem válidos e devem guiar esse eixo da D.

---

> Spec **A** da decomposição da análise comparativa (A pareamento/fusão D+C ·
> B fidelidade de campo · C política `equipamento_ambiguo` · D qualidade de
> matching). Maior impacto combinado correção+cobertura. Diagnóstico-first:
> alguns vínculos comando↔status precisam ser mapeados nos dados reais antes
> de fixar o mecanismo.

## Problema (medido na comparação real)

Coluna `Direction` da `DNP3_DiscreteSignals`:

| Valor | TDT real | OUTPUT atual |
|---|--:|--:|
| `Read` | 1396 | 722 |
| `ReadWrite` (fundido) | **243** | **22** |
| `Write` (órfão) | 2 | **73** |

E **32 siglas-infinitivo** no OUTPUT (`LIGAR`×25, `DESLIGAR`×7) — verbos de
comando que viraram sigla própria do ponto, em vez de fundir no status do
equipamento.

A TDT real funde status+comando em **243 pontos `ReadWrite`** (INCOORDS do
status + OUTCOORDS do comando, mesma sigla padrão da função). Nós fundimos só
22; 73 comandos viram `Write` órfão e 32 viram siglas-verbo.

## Invariantes de domínio (confirmados pelo usuário, travados)

- **Comando = Output, status = Input, e são o MESMO sinal físico** — fundem num
  ponto `ReadWrite` (INCOORDS do status + OUTCOORDS do comando).
- **A sigla que persiste após a fusão é a da Lista Padrão ADMS** (a do status,
  ex. `DJF1`/`81U2`/`SECB`) — **nunca** o verbo de comando (`LIGAR`/`DESLIGAR`/
  `CMD`/`ABRIR`/`FECHAR`).
- **Não há comando para analógicos** — fusão D+C é só discreto+discreto.
- **Double-bit dividido em 2 linhas** é pareamento de POLARIDADE (mesmo tipo,
  discreto+discreto, `pareamento_polaridade.py`) — distinto da fusão D+C
  (`dc_pairer.py`). Esta spec não mexe na polaridade.

## Causa-raiz (confirmada no código + dados)

A chave de fusão do `dc_pairer` é
`(modulo.nome, nome_equipamento, sigla_sinal)`
([dc_pairer.py:18](../../../src/tdt/dc_pairer.py)) e **está correta para o
pareamento por função**: na TDT real, as 12 funções do mesmo disjuntor `52-22`
(DJF1, 51N, 81U2, 2649, 79...) são `ReadWrite` distintos — cada status funde com
o comando da **sua** função, pela sigla. A chave por sigla é o que mantém eles
separados.

O problema é **upstream**: a linha de comando precisa resolver para a **mesma
sigla padrão** do seu status para a chave casar. Hoje:

1. **Comandos por-função já casam** — "81 Estágio 2 - Excluir/Incluir" contém o
   nome da função → casa `81U2` (mesma sigla do status) → funde. Esses estão
   entre os 22 que já funcionam.
2. **Comandos genéricos de abre/fecha NÃO casam** — "Disj. 52-1 (01Q0) -
   Desligar/Ligar" casa o **verbo** (`LIGAR`/`DESLIGAR`), não a sigla do
   disjuntor (`DJF1`); "Secc. 89-2 - Abrir/Fechar" idem (deveria ser a sigla da
   seccionadora). Sigla divergente do status → grupos diferentes → não funde →
   vira `Write` órfão ou sigla-verbo.
3. **Comando sem ID de equipamento** — "Religamento Automático (79) -
   Excluir/Incluir" pode não trazer `52-x`/`89-x`, então `nome_equipamento`
   fica `None` e o componente de equipamento da chave diverge do status.

> A distribuição exata de (2) vs (3) entre os ~221 comandos não-fundidos é o que
> o diagnóstico A1 quantifica antes de fixar o mecanismo.

## Escopo

### A1 — Diagnóstico (mapear o vínculo comando↔status nos dados reais)

Nas sheets GTD V11 (e validando contra a TDT real exportada), levantar para
cada linha de comando (Output) **por que não funde hoje**:

- A sigla casada é um **verbo** (`LIGAR`/`DESLIGAR`/`ABRIR`/`FECHAR`/`CMD`/
  `INCLUIR`/`EXCLUIR`) em vez da sigla do status? Quantos.
- O `nome_equipamento` está ausente no comando mas presente no status (ou
  vice-versa)? Quantos.
- O comando casa uma sigla de função **correta** (ex. `81U2`) e já funde?
  (baseline dos 22).
- Cruzar com a TDT real: para cada `ReadWrite` real, qual a sigla persistida e
  qual o equipamento — confirma o alvo por função.

Saída: tabela quantificada (categoria → contagem) que define o mecanismo de A2.

### A2 — Fusão correta (mecanismo informado por A1)

Aplicar os invariantes de domínio. Com base no que A1 mostrar, o mecanismo
provável (a confirmar):

- **Verbos de comando nunca persistem como sigla.** Uma linha Output cuja sigla
  casada é um verbo de abre/fecha é re-associada à sigla **padrão do
  equipamento** do mesmo `(módulo, equipamento)`: disjuntor (`52-x`) → sigla de
  status do disjuntor (`DJF1`); seccionadora (`89-x`) → sigla da seccionadora
  (`SECB`/`SECF`/`SECC`, conforme o status presente). Aí a chave atual funde.
- **Comando sem ID de equipamento** (caso A1.3): herda o equipamento do status
  correspondente quando determinável pela função/seção; senão permanece sem
  fundir e vai pra revisão (sem inventar — mantém "sem falso positivo").
- A fusão em si (`dc_pairer.fundir`) e a chave **não mudam** — já estão certas;
  o que muda é a **resolução da sigla/equipamento do comando** antes do pareamento.

> O ponto exato onde corrigir (na resolução de sigla do comando, antes do
> `dc_pairer`; provavelmente um passo novo entre o scoring e o `dc_pairer.parear`
> em `pipeline.py`, ou na normalização do comando) sai de A1. `dc_pairer.py` e
> a chave permanecem como contrato estável.

### A3 — Validação

- `Direction`: `ReadWrite` sobe de 22 em direção aos 243 da real; `Write` órfão
  cai de 73 → ~2; zero siglas-verbo (`LIGAR`/`DESLIGAR`) no OUTPUT.
- `pareamento_ambiguo` na GTD V11 cai (hoje 144).
- `python -m pytest -q` verde.
- `PYTHONPATH=src python bench/benchmark.py` sem regressão (o matching de sigla
  de status não muda; só a resolução do comando).
- Conferir contra a TDT real: pontos comandáveis saem `ReadWrite` com a sigla
  padrão da função + INCOORDS (status) e OUTCOORDS (comando).

## Fora de escopo

- Pareamento de polaridade / double-bit (`pareamento_polaridade.py`) — mesmo
  tipo, distinto de D+C.
- Cobertura por `score_baixo` (matching incerto) → Spec D.
- Política `equipamento_ambiguo` → Spec C.
- Fases / nomenclatura → Spec B.
- Comando para analógicos — não existe.

## Critérios de aceite

1. A1 entrega tabela quantificada das causas de não-fusão (verbo / sem-ID /
   já-funde) nos dados reais.
2. Verbos de comando (`LIGAR`/`DESLIGAR`/`ABRIR`/`FECHAR`/`CMD`/...) nunca
   persistem como sigla no OUTPUT.
3. Pontos comandáveis fundem em `ReadWrite` com a sigla **padrão do status**
   (lista ADMS), INCOORDS do status + OUTCOORDS do comando.
4. `dc_pairer.fundir` e a chave `(módulo, equip, sigla)` permanecem o contrato
   de fusão (a correção é na resolução de sigla/equipamento do comando).
5. `ReadWrite` sobe e `Write` órfão / siglas-verbo caem na GTD V11; benchmark
   sem regressão; `python -m pytest -q` verde.
6. Comando não-resolvível (sem vínculo determinável ao status) vai pra revisão,
   nunca funde errado.
