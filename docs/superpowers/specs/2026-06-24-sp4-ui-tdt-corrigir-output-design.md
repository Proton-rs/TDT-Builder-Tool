# SP4 — Correção do Output TDT (Formatação + Padrão de Nomes)

**Data:** 2026-06-24
**Status:** Aprovado para implementação
**Escopo:** Corrigir os dois problemas reportados após testar a TDT gerada pela UI:
(1) formatação/fórmulas perdidas; (2) padrão de nomes de sinais errado.

---

## 1. Problemas Identificados

### 1.1 Formatação perdida no TDT de saída

O template `docs/dnp3_template.xlsx` tem formatação importante que não é
preservada no output:

| Item | Template (esperado) | Output (atual) |
|------|---------------------|----------------|
| **Table ref** | `A4:AQ5` (só header row 4 + 1ª data row 5) | `A1:AQ516` (rows 1-3 incluídas como dados) |
| **Conditional formatting** (13 regras) | Aplicado à row 5 (`A5`, `E5`, `T5`, `AE5`, etc.) | Aplicado APENAS à row 5 (não expandido) |
| **Data validations** (4) | Row 5 apenas (`AC5`, `AI5`, `AO5`, `AP5:AQ5`) | Row 5 apenas (não expandido) |
| **Header rows 1-3** (merged cells, green/gray fills) | Fora da tabela | Dentro da tabela = formatação visual corrompida |

#### Causas Raiz

1. **Bug `_expandir_tabela`**: `ws.tables[SHEET_DISCRETOS].ref = f"A1:..."` errado.
   Deve ser `f"A4:..."` para manter rows 1-3 (section headers, merged cells)
   FORA da tabela. O template original tinha `ref='A4:AQ5'`.

2. **Conditional formatting não expandido**: As 13 regras (ex: `A5`, `T5`, `AE5`,
   `AF5`, `AJ5`, `AK5`) são copiadas do template mas nunca expandidas para o range
   total de dados (5..última_linha). As regras de expressão referenciam `$R5`
   (coluna Direction), então a expansão precisa preservar a lógica relativa.

3. **Data validations não expandidos**: As 4 validações (`AC5`, `AI5`, `AO5`,
   `AP5:AQ5`) só valem para a row 5. Precisam cobrir todas as linhas de dados.

### 1.2 Padrão de nomes de sinais incorreto

| Aspecto | Atual (`engine_tdt._valores`) | Esperado |
|---------|-------------------------------|----------|
| **Formato** | `{subestacao}_{sigla}` (ex: `GTA_G2`) | Hierárquico (ex: `SE_AL11_52-22_43TC`) |
| **Componentes** | 2 partes | 3-5 partes dependendo da hierarquia do equipamento |

#### Gramática de nomes (analisada do Export Base Full)

A análise de 4996 nomes no `Export_base_Full__27_fev_2026.xlsx` (sheet `DNP3_DiscreteSignals`)
revelou a seguinte estrutura:

```
signal_name = prefix + "_" + signal_code

prefix (2-part names, 73.5%)  = {RTU_CustomID}        — ex: 1212973_BATA
prefix (3-part names, 3.2%)   = {RTU_ID}_{G1|G2|G3|79|F|N}  — ex: 904296_G1_NORMAL
prefix (4-part names, 19.4%)  = {SE}_{Module}_{EquipID}      — ex: CNC_AL11_52-22_43TC
prefix (5-part names, 3.9%)   = {SE}_{Module}_{EquipID}_{P|A} — ex: CNC_TR1_TR1_P_24I
prefix (6-part names, raro)   = {SE}_{Module}_{EquipID}_{P|A}_{Extra} — ex: CNC_TR3_TR3_A_27_T
```

**Distribuição real:**
| Partes | % | Exemplo | Significado |
|--------|---|---------|-------------|
| 2 | 73.5% | `1212973_BATA` | RTU ID (7 dígitos) + sigla |
| 3 | 3.2% | `904296_G1_NORMAL` | RTU ID + módulo + estado |
| 4 | 19.4% | `CNC_AL11_52-22_43TC` | SE + alimentador + equipamento + sigla |
| 5 | 3.9% | `CNC_TR1_TR1_P_24I` | SE + equip + ID + P/A + sigla |
| 6 | raro | `CNC_TR3_TR3_A_27_T` | idem + sub-nível |

**Infixos confirmados:**

| Infixo | Sentido | Exemplo |
|--------|---------|---------|
| `_P_` | Principal (equipamento primário) | `CNC_TR1_TR1_P_FA` |
| `_A_` | Auxiliar (equipamento secundário) | `CNC_TR1_TR1_A_FCOM` |

**`_prot` NÃO é infixo** — é um **signal code** comum (60 ocorrências),
ex: `1212973_PROT`, `CNC_TR3BT_TR3BT_PROT`. Faz parte do catálogo ADMS
(sinal "Proteção Atuada").

**Signal codes mais comuns** (186 únicos): FA(178), FB(178), FC(177),
79(169), 51N(165), 43LR(150), CAFL(148), HLT(147), SGFT(147), BLQR(147),
BATA(131), FALH(128), PROT(60), DJ(—).

**Module types em 4-part names:** AL11, AL12, TR1, TR1AT, LTKCA, MOD, BC1,
BC2, TRF2, IB, LTKCO, etc.

**Equipment IDs (3º elemento):** 52-1, 52-2, 24-4, 24-5, TR1, G1, G2, etc.

> **Implicação para o pipeline:** O padrão 4-part (`{SE}_{Module}_{EquipID}_{Sigla}`)
> é implementável com os dados atuais (`subestacao`, `modulo.nome`, `nome_equipamento`,
> `sigla_sinal`). O padrão 5-part (P/A) requer campo adicional (YAGNI por enquanto).
> O padrão 2-part (RTU ID numérico) não tem equivalente no pipeline — usar
> `{subestacao}_{sigla}` como fallback para sinais sem módulo/equipamento.

---

## 2. Tarefas de Correção

### Tarefa 1 — Corrigir table ref em `_expandir_tabela`

**Arquivo:** `src/tdt/engine_tdt.py:85-91`

**O que mudar:**
```python
# Atual (ERRADO):
ws.tables[SHEET_DISCRETOS].ref = f"A1:{ultima_col}{fim}"

# Correto:
ws.tables[SHEET_DISCRETOS].ref = f"A4:{ultima_col}{fim}"
```

**Teste:** Verificar que `ws.tables[SHEET_DISCRETOS].ref == "A4:AQ{n}"`
onde `n = PRIMEIRA_LINHA_DADOS + len(discretos) - 1`.

### Tarefa 2 — Expandir conditional formatting para todas as linhas

**Arquivo:** `src/tdt/engine_tdt.py`

**O que fazer:** Após escrever os dados e expandir a tabela, percorrer as 13
regras de formatação condicional e expandir cada `sqref` de row 5 para o range
completo (5..última_linha).

**Lógica de expansão:**
- `A5` → `A5:A{last_row}`
- `E5` → `E5:E{last_row}`
- `T5` → `T5:T{last_row}`
- `AE5` → `AE5:AE{last_row}`
- etc. (todas as 13 regras, cada uma na sua coluna)

**Expressões com referência `$R5`:** A fórmula condicional referencia
`$R5` (Direction). Ao expandir para `$R5..$R{last_row}`, a lógica é preservada
porque a referência já usa `$R` (coluna absoluta).

**Teste:** Verificar no output que `len(ws.conditional_formatting) == 13` e cada
regra cobre o range correto.

### Tarefa 3 — Expandir data validations para todas as linhas

**Arquivo:** `src/tdt/engine_tdt.py`

**O que fazer:** Após expandir as regras de formatação condicional, expandir as
4 data validations de row 5 para o range completo.

**Lógica:**
- `AC5` → `AC5:AC{last_row}`
- `AI5` → `AI5:AI{last_row}`
- `AO5` → `AO5:AO{last_row}`
- `AP5:AQ5` → `AP5:AQ{last_row}`

**Teste:** Verificar que cada `dataValidation.sqref` cobre o range correto.

### Tarefa 4 — Construir nome hierárquico do sinal

**Arquivo:** `src/tdt/engine_tdt.py:_valores`

**Atual:**
```python
nome = f"{subestacao}_{rec.sigla_sinal}" if subestacao else rec.sigla_sinal
```

**Novo formato (baseado na gramática do Export Base Full):**

```python
# Gramática: {prefix}_{sigla}
# prefix = SE_Module_EquipID (4-part)
# prefix = SE (2-part fallback quando não há equipamento)

def _nome_hierarquico(subestacao, modulo_nome, equipamento, sigla):
    prefixo = subestacao or ""
    if modulo_nome:
        # "LT 1" → "LT1", "AL 11" → "AL11"
        parte = modulo_nome.replace(" ", "")
        if prefixo:
            prefixo += "_" + parte
        else:
            prefixo = parte
    if equipamento:
        prefixo += "_" + equipamento
    if prefixo:
        return f"{prefixo}_{sigla}"
    return sigla
```

**Exemplos:**
- `subestacao="GTA", modulo="AL 11", equip="52-22", sigla="43TC"` → `GTA_AL11_52-22_43TC`
- `subestacao="GTA", modulo=None, equip=None, sigla="BATA"` → `GTA_BATA`
- `subestacao=None, modulo="LT 1", equip="52-10", sigla="DJ"` → `LT1_52-10_DJ`

**Não implementado (YAGNI):**
- Infixo `_P_`/`_A_` (principal/auxiliar) — requer campo de domínio não disponível
- RTU ID numérico de 7 dígitos — não disponível no pipeline atual

**Teste:** Verificar que Signal Names seguem o padrão hierárquico definido.

### Tarefa 5 — Ajustar equipamento_alvo se necessário

**Arquivo:** `src/tdt/contracts.py` e/ou upstream (identificador/estruturador)

Se o campo `eletrico.nome_equipamento` não estiver sendo preenchido
corretamente pelo pipeline upstream, ajustar o identificador ou mapeador
para extraí-lo. Só será necessário se a Tarefa 4 falhar por falta de dados.

---

## 3. Análise Realizada: Export Base Full

Análise concluída em 24/06/2026. Amostra de 4996 nomes da sheet
`DNP3_DiscreteSignals` do `Export_base_Full__27_fev_2026.xlsx`.

### Gramática de Nomes (resumo)

```
signal_name = prefix + "_" + signal_code

prefix (2/3 partes): RTU_CustomID (numérico, 7 dígitos) [+ subnível]
prefix (4/5 partes): SE_Module_EquipID [+ _P_|_A_]

signal_code = sigla ADMS padrão (FA, DJ, BATA, 43TC, 51N, PROT, etc.)
```

### Distribuição

| Partes | % | Máscara |
|--------|---|---------|
| 2 | 73.5% | `{RTUID}_{SIGLA}` |
| 4 | 19.4% | `{SE}_{MOD}_{EQUIP}_{SIGLA}` |
| 5 | 3.9% | `{SE}_{MOD}_{EQUIP}_{P|A}_{SIGLA}` |
| 3 | 3.2% | `{RTUID}_{G1..G3}_{NORMAL|CHAVE|ALTERNATIVO}` |

### Descobertas principais

- `PROT` é signal code, não infixo (60 ocorrências)
- `_P_` e `_A_` são infixos reais para principal/auxiliar (121 ocorrências combinadas)
- Module types mais comuns: AL11, AL12, TR1, TR1AT, LTKCA, MOD, BC1, TRF2, IB
- Equipment IDs: 52-1..52-23, 24-1..24-5, TR1..TR3, G1..G4

---

## 4. Especificação Final do Nome Hierárquico

### Regra de formação

```python
# Prioridade:
# 1. Se tem equipamento:  {subestacao}_{modulo_clean}_{equipamento}_{sigla}
# 2. Se tem só módulo:    {subestacao}_{modulo_clean}_{sigla}
# 3. Se tem só subestação: {subestacao}_{sigla}
# 4. Fallback:              {sigla}

def _nome_hierarquico(
    subestacao: str | None,
    modulo_nome: str | None,
    equipamento: str | None,
    sigla: str,
) -> str:
    partes = []
    if subestacao:
        partes.append(subestacao)
    if modulo_nome:
        # "LT 1" → "LT1", "TR 1" → "TR1", "AL 11" → "AL11"
        partes.append(modulo_nome.replace(" ", ""))
    if equipamento:
        partes.append(equipamento)
    partes.append(sigla)
    return "_".join(partes)
```

### Não implementado nesta sprint

- **Infixo P/A**: requer campo de domínio no `Eletrico` ou `SignalRecord` que
  indique se o sinal é principal ou auxiliar. O pipeline atual não extrai essa
  informação. Adicionar quando o input fornecer.
- **RTU ID numérico**: o pipeline não tem acesso ao CustomID da RTU. Para
  sinais sem módulo/equipamento, usar a subestação como prefixo é o melhor
  disponível. Se o ADMS rejeitar, implementar mapeamento RTU↔SE futuramente.

---

## 5. Considerações de Implementação

### Preservação do template original

A engine trabalha sobre uma cópia em memória via `load_workbook()`. Nenhuma
modificação é feita no arquivo de template original.

### Retrocompatibilidade

- Assinatura de `engine_tdt.gerar()` inalterada (retorna `openpyxl.Workbook`)
- Pipeline CLI/bench inalterados (não usam formatação expandida)
- Testes existentes permanecem verdes (a formatação expandida não afeta valores)

### Riscos

- openpyxl pode não preservar 100% da formatação condicional ao expandir
  sqref. Testar com o output real aberto no Excel.
- Se a fórmula condicional usar referência absoluta `$R$5` ao invés de `$R5`,
  a expansão quebrará a lógica. Verificar no template real.

---

## 6. Critérios de Aceite

1. Output TDT aberto no Excel mostra banded rows corretamente (rows 5+ alternadas)
2. Header rows 1-4 estão FORA da tabela e mantêm fill verde/cinza
3. Conditional formatting se aplica a todas as linhas de dados, não só row 5
4. Data validations se aplicam a todas as linhas de dados
5. Signal Names seguem a gramática definida na Seção 4
   - `GTA_AL11_52-22_43TC` (4-part, equipamento presente)
   - `GTA_BATA` (2-part, fallback sem módulo/equipamento)
   - `LT1_52-10_DJ` (sem subestação)
6. Testes existentes continuam verdes (140/140)
7. Novos testes em `test_engine_tdt.py` comprovam:
   - Table ref = `A4:AQ{n}` (não `A1:AQ{n}`)
   - CF rules expandidas para range completo
   - Data validations expandidas para range completo
   - Signal Names com formato hierárquico correto
