# SP9 — TDT: Output Coordinates, Dropdowns, Measurement Type/Display Unit

**Data:** 2026-06-24
**Status:** Aguardando revisão do usuário
**Escopo:** Itens "TDT" e "COISAS FALTANDO NAS COLUNAS" de `docs/ObservacoesProgramaTDT.txt`. Todas as mudanças ficam em `src/tdt/engine_tdt.py` (+ 2 campos novos em `src/tdt/dados/lista_padrao.py`) — mesmo arquivo, mesma família de funções (`_valores`/`_valores_analog`/geração de sheet).

---

## 1. Output Coordinates não duplica comando simples

**Confirmado:** `_valores()` calcula `coords = ";".join(indices)`; quando o comando tem 1 índice só (`(1500,)`), `coords_saida` sai `"1500"`. Segundo a skill ADMS-TDT, comando simples deve sair `"1500;1500"` (mesmo endereço como entrada e saída do bit de comando).

Fix — sempre que `tem_comando` e os índices de saída tiverem exatamente 1 elemento, duplica:

```python
def _coords_comando(indices: tuple[int, ...]) -> str:
    if len(indices) == 1:
        return f"{indices[0]};{indices[0]}"
    return ";".join(str(i) for i in indices)
```

Usado nos dois lugares onde `coords_saida` é montado em `_valores()`:
- comando órfão (`direcao == "Output"`): `coords_saida = _coords_comando(rec.enderecamento.indices)`
- comando pareado (D+C): `coords_saida = _coords_comando(rec.enderecamento.indices_saida)`

Endereço já double-bit (2 índices reais, ex. status de disjuntor `(100, 101)`) não entra nesse caminho — só comandos (`Output`/parte de saída de `InputOutput`), então não há risco de duplicar um double-bit por engano.

---

## 2. Dropdowns (Data Validation) nas colunas categóricas

**Confirmado:** `docs/dnp3_template.xlsx` não tem nenhuma Data Validation tipo lista (só 4 DVs numéricas em campos de timing). `_expandir_dv()` (`engine_tdt.py:254`) só **estende** validações que já existem na row 5 — não cria nova. Pra ganhar os dropdowns sem depender do template mudar, `engine_tdt.gerar()` cria as DVs em código, nas colunas onde já temos um conjunto fechado e confiável de valores (não inventa opções sem grounding):

| Coluna | Valores | Fonte |
|---|---|---|
| Phases | `ABC, AB, BC, CA, A, B, C, N` | `normalizador.FASES` (hoje `_FASES`, privado — expor como público, mesmo motivo do SP6: já é a fonte de verdade usada no código) |
| Direction | `Read, Write, ReadWrite` | `engine_tdt._DIRECAO.values()` |
| Remote Point Type | `Status, Analog` | valores literais já escritos hoje em `_valores`/`_valores_analog` |

`Side` fica de fora: hoje só escrevemos a constante `"None"`, sem evidência de outros valores reais usados — não vou inventar um domínio sem dado de produção que confirme.

```python
from openpyxl.worksheet.datavalidation import DataValidation

_DV_LISTAS: dict[str, tuple[str, ...]] = {
    "Phases": FASES,  # importado de tdt.normalizador
    "Direction": tuple(_DIRECAO.values()),
    "Remote Point Type": ("Status", "Analog"),
}


def _adicionar_dv_lista(ws, colunas: dict[str, int], ultima_linha: int) -> None:
    for display, valores in _DV_LISTAS.items():
        col = colunas.get(display)
        if col is None:
            continue
        letra = get_column_letter(col)
        dv = DataValidation(type="list", formula1=f'"{",".join(valores)}"', allow_blank=True)
        dv.add(f"{letra}{PRIMEIRA_LINHA_DADOS}:{letra}{ultima_linha}")
        ws.add_data_validation(dv)
```

Chamado em `_escrever_sheet()`, depois de `_expandir_dv` (que continua cuidando das DVs numéricas pré-existentes — sem conflito, são ranges/colunas diferentes).

---

## 3. Measurement Type / Display Unit (analógicos)

**Confirmado:** a Lista Padrão ADMS (`docs/Pontos Padrao ADMS_v1.xlsx`, sheet `AnalogSignals`) já tem as colunas `TIPO DE MEDIÇÃO` e `UNIDADE DE EXIBIÇÃO` — só nunca são lidas. `SinalPadrao` (`dados/lista_padrao.py`) ganha 2 campos:

```python
@dataclass(frozen=True)
class SinalPadrao:
    ...
    tipo_medicao: str | None = None       # "Corrente", "Tensão", ... (lista padrão, PT)
    unidade_exibicao: str | None = None   # "A", "kV", "Grau", "-", ...
```

Lidos em `_ler_sheet` (mapa de colunas do `AnalogSignals`, hoje com `"mm": None, "estados": None, "valores": None` porque essa sheet não usa esses campos — adicionar 2 chaves novas):

```python
ana = _ler_sheet(
    wb["AnalogSignals"], "Analog",
    {
        "sigla": "SINAL", "descricao": "DESCRIÇÃO NOVA", "signal_type": "SIGNAL TYPE",
        "direction": "DIREÇÃO DO FLUXO", "mm": None, "estados": None, "valores": None,
        "tipo_medicao": "TIPO DE MEDIÇÃO", "unidade_exibicao": "UNIDADE DE EXIBIÇÃO",
    },
)
```

`_valores_analog()` em `engine_tdt.py` usa `sp.tipo_medicao` traduzido PT→EN (a TDT espera os enums em inglês, confirmado no export real: Current/Voltage/ActivePower/ReactivePower/Temperature) e `sp.unidade_exibicao` passado direto (já está na forma que a TDT espera, ex. "A"/"kV"/"C" — exceções por sigla, como `VBC`→"V" em vez de "kV", já vêm certas da Lista Padrão por linha, sem precisar de regra extra no código):

```python
_MEASUREMENT_TYPE_PT_EN: dict[str, str] = {
    "CORRENTE": "Current",
    "TENSÃO": "Voltage",
    "POTÊNCIA ATIVA": "ActivePower",
    "POTÊNCIA REATIVA": "ReactivePower",
    "TEMPERATURA": "Temperature",
}


def _measurement_type(sp: "SinalPadrao | None") -> str | None:
    if sp is None or not sp.tipo_medicao:
        return None
    return _MEASUREMENT_TYPE_PT_EN.get(sp.tipo_medicao.strip().upper())
```

Em `_valores_analog`, adiciona ao dict:
```python
"Measurement Type": _measurement_type(sp),
"Display Unit": sp.unidade_exibicao if sp and sp.unidade_exibicao not in (None, "-") else None,
```

**Sem entrada na tabela de tradução** (ex. "Ângulo de Tensão", se existir e não estiver mapeado): fica `None` — mesmo comportamento de hoje (vazio), não regride nada; só não ganha o ganho. `# ponytail: tabela cobre os 5 tipos confirmados no export real; ampliar quando aparecer outro tipo de medição real nos dados.`

---

## Testes

- `tests/test_engine_tdt.py`: comando órfão com 1 índice gera `"Output Coordinates" == "N;N"`; comando pareado idem; double-bit (2 índices reais) não passa por essa duplicação.
- Dropdown: `_adicionar_dv_lista` cria uma `DataValidation` tipo "list" coprindo `row5:última_linha` pras 3 colunas, com os valores esperados no `formula1`.
- `tests/test_lista_padrao.py`: `SinalPadrao.tipo_medicao`/`unidade_exibicao` lidos corretamente de uma sheet `AnalogSignals` fake com essas colunas.
- `tests/test_engine_tdt.py`: `_valores_analog` preenche "Measurement Type"/"Display Unit" pra sigla com `tipo_medicao` mapeado; fica `None` pra sigla sem essa info (sem regressão).

## Critérios de Aceite

1. TDT gerada nunca tem "Output Coordinates" com índice único sem duplicar.
2. Colunas Phases/Direction/Remote Point Type têm dropdown na TDT gerada, cobrindo todas as linhas de dados.
3. Sinais analógicos com `tipo_medicao` conhecido saem com Measurement Type em inglês e Display Unit preenchido.
4. Sinais sem essa info na Lista Padrão continuam vazios (sem regressão, sem valor inventado).
5. Testes existentes continuam verdes.
