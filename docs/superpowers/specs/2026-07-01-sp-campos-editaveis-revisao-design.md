# Spec: campos editáveis na tela de revisão (dropdowns de domínio)

Data: 2026-07-01

## Contexto

A tela de revisão (`src/tdt/ui/tela_revisao.py` + `modelo_tabela.py`) mostra
uma tabela de `SignalRecord`s (decididos + revisão) com 21 colunas. Hoje só a
coluna **Sinal** é editável (combo com candidatos + busca ADMS, via
`DelegateSinal`). Todo o resto — incluindo campos de domínio elétrico que o
usuário eventualmente precisa corrigir manualmente (Fase, Módulo, Nível
Tensão, Barra, Tipo Equip., Tipo, Escala) — é texto derivado só-leitura.

Objetivo: tornar esses 7 campos editáveis direto na tabela, com dropdown de
valores válidos onde o domínio é fechado (evita erro de digitação e sinal
inválido pro `engine_tdt`).

## Escopo

**Editável (novo), com domínio fechado (dropdown fixo):**

| Coluna | Opções | Fonte do domínio |
|---|---|---|
| Tipo | `Discrete/Input`, `Discrete/Output`, `Discrete/InputOutput`, `Analog/Input`, `Analog/Output` | `contracts.TipoSinal` (`categoria`,`direcao`); exclui `DiscreteAnalog` — é placeholder de incerteza (dual-pass), não estado-alvo válido de edição manual |
| Fase | `—`,`A`,`B`,`C`,`N`,`AB`,`BC`,`CA`,`ABC` | `motor_regras.fase_da_sigla` (valores que a função retorna) |
| Nível Tensão | `—`,`AT`,`BT` | `contracts.Eletrico.nivel_tensao` docstring |
| Barra | `—`,`Principal`,`Auxiliar` | `engine_tdt._BARRA_SUFIXO` / `normalizador._BARRA` |
| Tipo Equip. | `—`,`Disjuntor`,`Seccionadora` | `config.Config.topologia_por_tipo` (união dos `equipamentos` de todos os tipos de módulo) |

**Editável (novo), domínio aberto:**

| Coluna | Editor |
|---|---|
| Módulo | combo editável — sugere nomes de módulo já presentes nos registros (mesma fonte que `tela_revisao._construir_menu_coluna` já usa pro filtro) + aceita texto livre |
| Escala | editor de texto padrão (numérico); vazio = `None` |

**Fora de escopo** (permanece só-leitura): `Equipamento` (`eletrico.nome_equipamento`,
texto livre tipo `"52-10"` — não tem domínio fechado nem lista de sugestão
natural, editar tende a gerar rótulo inconsistente com dedup/pareamento),
`Confiança`, `Status`, `Motivo`, `Descr. ADMS/bruta/normalizada`, `Tokens`,
`Endereço`/`Endereço Output`, `Score *`, `Justificativa` — todos calculados
pelo pipeline; editá-los quebraria a rastreabilidade da decisão sem
corresponder a nenhuma mutação real do sinal.

## Comportamento

- Editar qualquer um dos 7 campos **não** promove o registro de `revisao`
  para `decidido` (diferente de editar Sinal, que promove). Motivo: corrigir
  um campo de domínio não necessariamente resolve o motivo original da
  revisão (ex.: `score_baixo` não tem relação com Fase estar errada).
- Editar **Tipo Equip.** zera `eletrico.equipamento_inferido` para `False` —
  o campo já existe pra distinguir "extraído/definido explicitamente" de
  "inferido por topologia" (C2.2); uma edição manual é uma definição
  explícita.
- Editar **Tipo** grava `categoria_confiavel=True` — o usuário está
  resolvendo a incerteza que o dual-pass (`categoria_confiavel=False`)
  representa.
- Nenhum dos 7 setters cria snapshot de undo (`AppState._historico`). Mesma
  limitação que `definir_sigla` já tem hoje — não é regressão nova, é
  consistência com o padrão existente. (Undo pra edição de campo fica fora
  de escopo; abrir se for pedido depois.)

## Componentes

### 1. `AppState` (`src/tdt/ui/estado.py`)

Helper genérico + 7 setters finos:

```python
def _editar_nested(self, indice: int, campo: str, **kwargs) -> None:
    r = self.registros[indice]
    novo = replace(getattr(r, campo), **kwargs)
    self.registros[indice] = replace(r, **{campo: novo})

def definir_tipo(self, indice: int, categoria: str, direcao: str) -> None:
    self._editar_nested(indice, "tipo_sinal", categoria=categoria,
                         direcao=direcao, categoria_confiavel=True)

def definir_fase(self, indice: int, fase: str | None) -> None:
    self._editar_nested(indice, "eletrico", fase=fase)

def definir_nivel_tensao(self, indice: int, nivel: str | None) -> None:
    self._editar_nested(indice, "eletrico", nivel_tensao=nivel)

def definir_barra(self, indice: int, barra: str | None) -> None:
    self._editar_nested(indice, "eletrico", barra=barra)

def definir_tipo_equip(self, indice: int, equip: str | None) -> None:
    self._editar_nested(indice, "eletrico", equipamento_alvo=equip,
                         equipamento_inferido=False)

def definir_modulo(self, indice: int, nome: str | None) -> None:
    self._editar_nested(indice, "modulo", nome=nome)

def definir_escala(self, indice: int, valor: float | None) -> None:
    self._editar_nested(indice, "grandezas_analogicas", escala_transmissao=valor)
```

Nenhuma dependência de Qt — testável puro, igual ao resto de `estado.py`.

### 2. `ModeloSinais` (`src/tdt/ui/modelo_tabela.py`)

`flags()` abre `Qt.ItemIsEditable` pras 7 colunas (hoje só "Sinal"):

```python
_EDITAVEIS = frozenset({
    "Sinal", "Tipo", "Fase", "Nível Tensão", "Barra", "Tipo Equip.",
    "Módulo", "Escala",
})
```

`setData()` novo (a classe não tem hoje — todo estado passa por
`definir_sigla` chamado direto pelo delegate). Dispatcha por nome de coluna
pro setter certo do `AppState`, converte texto → valor tipado, emite
`dataChanged` na linha inteira (mesmo padrão de `definir_sigla`):

```python
def setData(self, index, value, role=Qt.EditRole):
    if role != Qt.EditRole or not index.isValid():
        return False
    nome = COLUNAS[index.column()]
    linha = index.row()
    texto = str(value).strip()
    if nome == "Tipo":
        if "/" not in texto:
            return False
        categoria, direcao = texto.split("/", 1)
        self._estado.definir_tipo(linha, categoria, direcao)
    elif nome == "Fase":
        self._estado.definir_fase(linha, texto or None)
    elif nome == "Nível Tensão":
        self._estado.definir_nivel_tensao(linha, texto or None)
    elif nome == "Barra":
        self._estado.definir_barra(linha, texto or None)
    elif nome == "Tipo Equip.":
        self._estado.definir_tipo_equip(linha, texto or None)
    elif nome == "Módulo":
        self._estado.definir_modulo(linha, texto or None)
    elif nome == "Escala":
        try:
            valor = float(texto.replace(",", ".")) if texto else None
        except ValueError:
            return False
        self._estado.definir_escala(linha, valor)
    else:
        return False
    topo = self.index(linha, 0)
    fim = self.index(linha, len(COLUNAS) - 1)
    self.dataChanged.emit(topo, fim)
    return True
```

Escala não precisa de delegate custom — editor padrão (`QLineEdit` via
`QStyledItemDelegate` default) já chama `model.setData()` no commit.

### 3. `DelegateCombo` novo (`src/tdt/ui/delegate_sinal.py`)

Uma classe parametrizada por lista fixa de opções, reusada pras 5 colunas de
domínio fechado (Tipo/Fase/Nível Tensão/Barra/Tipo Equip.) — evita 5 classes
quase-idênticas:

```python
class DelegateCombo(QStyledItemDelegate):
    def __init__(self, opcoes: list[str], parent=None):
        super().__init__(parent)
        self._opcoes = opcoes

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self._opcoes)
        return combo

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText().strip(), Qt.EditRole)
```

`DelegateModulo` (mesmo arquivo): combo editável, itens = nomes de módulo
distintos já presentes em `self._estado.registros` (mesma fonte de
`tela_revisao._construir_menu_coluna`) + `setEditable(True)` pra aceitar
módulo novo digitado. `setModelData` também delega pro `model.setData`.

### 4. `TelaRevisao.carregar()` (`src/tdt/ui/tela_revisao.py`)

Registra os delegates nas colunas certas, mesmo padrão do `DelegateSinal`
existente:

```python
_OPCOES_COMBO = {
    "Tipo": ["Discrete/Input", "Discrete/Output", "Discrete/InputOutput",
             "Analog/Input", "Analog/Output"],
    "Fase": ["", "A", "B", "C", "N", "AB", "BC", "CA", "ABC"],
    "Nível Tensão": ["", "AT", "BT"],
    "Barra": ["", "Principal", "Auxiliar"],
    "Tipo Equip.": ["", "Disjuntor", "Seccionadora"],
}
```

`carregar()` itera `_OPCOES_COMBO` e chama `setItemDelegateForColumn`; +1
chamada dedicada pra `Módulo` com `DelegateModulo`.

## Testes

- `AppState`: 1 teste por setter novo (pure Python, sem Qt) — grava, lê de
  volta o campo aninhado, confirma que o resto do registro não mudou.
- `ModeloSinais`: teste de `flags()` (7 colunas editáveis, resto não) +
  teste de `setData()` por coluna (happy path + valor inválido em Escala
  retorna `False` sem mutar estado).
- Sem teste de Qt widget/delegate (createEditor) — comportamento do
  `QComboBox` é do framework, não lógica nossa; cobertura para via os testes
  de `setData`/`AppState` que já exercitam o caminho de dados real.

## Fora de escopo (não fazer nesta spec)

- Undo por edição de campo (mesma lacuna que Sinal já tem).
- Tornar "Equipamento" (nome_equipamento) editável — domínio aberto sem
  fonte de sugestão natural, risco de quebrar dedup/pareamento por nome.
- Validação cruzada (ex.: impedir Fase=`N` num sinal cuja sigla não é de
  neutro) — os dropdowns já restringem a valores fisicamente válidos; regra
  de coerência sigla↔campo é responsabilidade do `motor_regras`/scorer, não
  da edição manual.
