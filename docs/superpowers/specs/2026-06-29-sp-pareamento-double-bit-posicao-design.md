# SP — Pareamento de sinais double-bit de posição (chave aberto/fechado)

**Status:** Implementado
**Data:** 2026-06-29
**Escopo:** Catalogar todos os sinais **double-bit de posição** da base real (`docs/Export_base_Full_limpo.json`) e da lista padrão (`Pontos Padrao ADMS`), e usar esse catálogo para corrigir o **pareamento de polaridade** (`pareamento_polaridade.py`), que hoje só converge **Disjuntor**. Seccionadoras com par aberto/fechado não pareiam — bug identificado em campo.
**Relacionada:** `pareamento_polaridade.py` (convergência pré-scoring), `normalizador_estrutural.py` (fusão double-bit por endereço consecutivo), `dc_pairer.py` (fusão D+C pós-classificação).

---

## Diagnóstico

### Bug observado

Um sinal de **seccionadora** com duas linhas de polaridade oposta (aberta / fechada) do mesmo equipamento **não foi pareado** para a sigla de posição (`SEC*`) — as duas linhas seguiram para o scorer de texto e divergiram, em vez de convergir direto para a posição da chave.

### Causa-raiz

`pareamento_polaridade.forcar_polaridade_equipamento` faz a convergência de polaridade **só para Disjuntor**:

```python
# src/tdt/pareamento_polaridade.py:14
_SIGLA_POSICAO: dict[str, str] = {"Disjuntor": "DJF1"}
```

- O mecanismo de detecção de polaridade **já cobre aberto/fechado** (`_LIGADO_PREFIXOS=("LIGAD","FECHAD")`, `_DESLIGADO_PREFIXOS=("DESLIGAD","ABERT")` — `pareamento_polaridade.py:18-19`).
- O `equipamento_alvo` **já é setado como `"Seccionadora"`** a partir do ANSI 89/29 ou da palavra SECCIONADORA (`normalizador.py:57-69`).
- **O único elo faltante é o mapa `_SIGLA_POSICAO`**: não há entrada `"Seccionadora"`.

Mas há uma complicação que impede um simples `{"Seccionadora": "SECC"}`: **seccionadora tem 7 siglas de posição por função** (carga, bypass, transferência, terra, fonte, interbarras, interlinhas). É preciso **resolver a variante** a partir da descrição, não mapear para uma sigla fixa.

---

## Catálogo: sinais double-bit (evidência)

### A. Siglas double-bit na lista padrão (`Pontos Padrao ADMS_v2`)

Marcador autoritativo: `_D_` no campo `mm` (Double) e/ou `signal_type=SwitchStatus`. **12 siglas**:

| Sigla | Equipamento | Estados (status) | Comandos | Pareável por polaridade? |
|-------|-------------|------------------|----------|--------------------------|
| `DJF1` | Disjuntor NF | `DESLIGADO@LIGADO` | `DESLIGAR@LIGAR` | ✅ sim (já coberto) |
| `DJA1` | Disjuntor NA | `DESLIGADO@LIGADO` | `DESLIGAR@LIGAR` | ✅ sim |
| `SECB` | Seccionadora **Bypass** | `ABERTO@FECHADO` | `ABRIR@FECHAR` | ✅ sim (faltando) |
| `SECC` | Seccionadora **Carga** | `ABERTO@FECHADO` | `ABRIR@FECHAR` | ✅ sim (faltando) |
| `SECF` | Seccionadora **Fonte** | `ABERTO@FECHADO` | `ABRIR@FECHAR` | ✅ sim (faltando) |
| `SECG` | Seccionadora **Terra/Aterramento** | `ABERTO@FECHADO` | `ABRIR@FECHAR` | ✅ sim (faltando) |
| `SECI` | Seccionadora **Interbarras** | `ABERTO@FECHADO` | `ABRIR@FECHAR` | ✅ sim (faltando) |
| `SECL` | Seccionadora **Interlinhas** | `ABERTO@FECHADO` | `ABRIR@FECHAR` | ✅ sim (faltando) |
| `SECT` | Seccionadora **Transferência** | `ABERTO@FECHADO` | `ABRIR@FECHAR` | ✅ sim (faltando) |
| `DJIE` | Disjuntor extraível (posição) | `EXTRAIDO@INSERIDO` | — | ⚠️ não-polaridade (extraído/inserido), `Custom_S` (single) |
| `79_INC` | Religamento incluir | `null@null` | `INCLUIR@null` | ❌ comando, não posição |
| `79_EXC` | Religamento excluir | `null@null` | `null@EXCLUIR` | ❌ comando, não posição |
| `CDCO` | CDC modo de operação | `MESTRE@INDIVIDUAL@COMANDO` | idem | ❌ multi-estado, não polaridade |

> **As 9 primeiras** (DJF1, DJA1, SEC×7) são as **posições de chave** alvo do pareamento de polaridade. As 4 últimas são double-bit mas **não** são posição aberto/fechado e ficam **fora** do escopo de convergência de polaridade.

### B. Sinais `SwitchStatus` na base real (`Export_base_Full_limpo.json`)

23 sinais, todos `signal_type=Discrete`, `measurement_type=SwitchStatus` (único marcador de double-bit no export — não há campo `mm`). Distribuição por sigla e exemplos de alias:

| Sigla | Qtde | ANSI equip. | Aliases observados (ruído real) |
|-------|------|-------------|----------------------------------|
| `SECB` | 6 | 89, 29 | SECCIONADORA BYPASS · SEC BYPS · SEC BY PASS · SECCIONADORA BY-PASS |
| `SECC` | 4 | 89, 29 | SECCIONADORA CARGA · SEC CARG · **SECCIONADORA BARRA P** |
| `SECT` | 3 | 89, 29 | SECCIONADORA TRANSFERENCIA · **SECCIONADORA ATERRAMENTO** · **SECCIONADORA BARRA PT** |
| `SECG` | 2 | 29 | SECCIONADORA TERRA · **LMN TERR** |
| `SECF` | 2 | 89 | SEC FONT · SECF |
| `DJF1` | 2 | 52 | Disjuntor NF · DJF1 |
| `SECI` | 1 | (TRUCK) | SECCIONADORA INTERBARRAS |
| `SECL` | 1 | 89 | SECCIONADORA INTERLINHAS |
| `DJA1` | 1 | 24 | DISJUNTOR NA |
| `DJIE` | 1 | (TRUCK) | DISJUNTO (extraível) |

> **Ruído conhecido na base** (em negrito acima): a atribuição humana de sigla nem sempre bate com a palavra-função — `SECCIONADORA ATERRAMENTO` está como `SECT` (deveria ser `SECG`); `SECCIONADORA BARRA P`/`BARRA PT` viraram `SECC`/`SECT`. A resolução por palavra-chave é heurística e tem **ambiguidade residual** → casos sem keyword clara devem ir para **revisão**, não chutar.

---

## Tabela de referência para o motor de regras

Mapa **equipamento → variante de posição**, derivado da descrição-padrão. Resolução por palavra-função (prefixo, robusto a "BY PASS"/"BY-PASS"/"BYPS"):

| `equipamento_alvo` | Palavra-função na descrição | Sigla de posição |
|--------------------|------------------------------|------------------|
| Disjuntor | (qualquer; default) | `DJF1` (NF) — `DJA1` se "NA"/normalmente aberto |
| Seccionadora | CARGA | `SECC` |
| Seccionadora | BYPASS / BY PASS / BY-PASS / BYPS | `SECB` |
| Seccionadora | TRANSFERENCIA / TRANSF | `SECT` |
| Seccionadora | TERRA / ATERRAMENTO | `SECG` |
| Seccionadora | FONTE / FONT | `SECF` |
| Seccionadora | INTERBARRAS / INTERBARRA | `SECI` |
| Seccionadora | INTERLINHAS / INTERLINHA | `SECL` |
| Seccionadora | (sem palavra-função reconhecida) | **→ revisão** (`motivo="posicao_ambigua"`) |

Estados de polaridade (já detectados por prefixo em `pareamento_polaridade`):
- **Disjuntor:** `LIGADO`/`FECHADO` (fechado) ↔ `DESLIGADO`/`ABERTO` (aberto)
- **Seccionadora:** `FECHADO`/`FECHADA` ↔ `ABERTO`/`ABERTA`

---

## Proposta de melhoria do pareamento

### 1. Generalizar `pareamento_polaridade` para Seccionadora

Substituir o mapa fixo `_SIGLA_POSICAO: dict[str, str]` por uma resolução que:

1. Aceite `equipamento_alvo ∈ {"Disjuntor", "Seccionadora"}`.
2. Para **Disjuntor**: mantém `DJF1` (default), `DJA1` se a descrição indicar "NA"/normalmente aberto.
3. Para **Seccionadora**: aplica a **Tabela de referência** (palavra-função → `SEC*`). Sem palavra-função reconhecida → **não força** (deixa para o scorer/revisão), nunca chuta `SECC`.
4. Mantém a invariante atual: só converge quando há **exatamente 1 linha "fechado" + 1 linha "aberto"** do mesmo `(modulo, equipamento_alvo, nome_equipamento)`.

### 2. Catálogo de posição como fonte única

Extrair o catálogo (Seção A, 9 posições) para uma estrutura derivada da própria lista padrão (siglas com `signal_type=SwitchStatus` e estados `ABERTO@FECHADO`/`DESLIGADO@LIGADO`), evitando hardcode que envelhece quando a LP muda de versão. A LP já carrega `signal_type` e `mm` (`SinalPadrao`).

### 3. Consistência double-bit pós-pareamento

Após a convergência de polaridade, as duas linhas (mesma sigla `SEC*`, endereços consecutivos) já são fundidas em **um sinal double-bit** por `normalizador_estrutural.corrigir` (`indices=(n, n+1)`, `is_double_bit=True`). Confirmar que o caminho seccionadora passa por ele igual ao do disjuntor.

---

## Casos de borda

| Caso | Hoje | Proposto |
|------|------|----------|
| Seccionadora aberta + fechada (mesmo equip.) | não pareia → diverge | converge para `SEC*` por palavra-função |
| Seccionadora sem palavra-função ("SECF" cru / "LMN TERR") | — | revisão `posicao_ambigua` (não chuta) |
| `SECCIONADORA ATERRAMENTO` (ruído: base tem como `SECT`) | — | resolve `SECG` por keyword TERRA/ATERRAMENTO |
| Disjuntor NA ("DISJUNTOR NA") | converge `DJF1` (errado p/ NA) | converge `DJA1` |
| `DJIE` extraível (extraído/inserido) | — | **fora** do pareamento de polaridade (não é aberto/fechado) |
| 3+ linhas do mesmo equipamento | não converge | mantém: só 1+1 converge, resto → revisão |

---

## Artefatos implementados

- **`src/tdt/pareamento_polaridade.py`** — `_SIGLA_POSICAO` substituído por `_SECC_KEYWORDS` (prefixo → SEC*) + `_sigla_disjuntor` (DJA1 via token "NA") + `_sigla_seccionadora`. Retorno alterado para `tuple[list[SignalRecord], list[ItemRevisao]]`.
  - **Guarda TRANSF vs TRANSFORMADOR:** keyword usa `"TRANSFER"` (8 chars), não `"TRANSF"` — `"TRANSFORMADOR"` começa com `"TRANSFOR"`, não `"TRANSFER"`, evitando falso positivo de `TR` → `TRANSFORMADOR` → `SECT`.
- **`src/tdt/pipeline.py`** — desempacota a tupla em `(sinais, rev_polaridade)`; `revisao.extend(rev_polaridade)`.
- **`src/tdt/contracts.py`** — `ItemRevisao.motivo` documenta `"posicao_ambigua"` e `"pareamento_ambiguo"`.
- **`tests/test_pareamento_polaridade.py`** — 31 testes: 17 variantes SEC* paramétricas, DJA1, seccionadora ambígua → revisão, TRANSFORMADOR não ativa SECT, 3 linhas, flag off, módulo/equipamento diferente, terceiro sinal passa intacto.

---

## Não escopo

- Não altera `dc_pairer` (fusão D+C status×comando) — pareamento de polaridade é status×status.
- Não trata as siglas double-bit **não-posição** (`79_INC`, `79_EXC`, `CDCO`, `DJIE`) — só posições aberto/fechado / ligado/desligado.
- Não corrige o ruído de atribuição da base real — apenas documenta para que a heurística por keyword decida pela palavra-função, divergindo conscientemente da sigla "errada" gravada na base quando houver conflito.
