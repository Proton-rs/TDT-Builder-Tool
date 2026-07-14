# SP A — Revisão UI: lote, endereçamento, módulo editável

**Data:** 2026-06-26
**Status:** Aguardando revisão do usuário
**Status 2026-07-13 (SP-CVA):** A1 (edição em lote/aprovar em lote — Tasks 10-11) e A3 (colunas de endereçamento Input/Output editáveis — Task 12, mais Pareado/Sheet origem — Task 13) cobertos por este SP. A2 (parte redo do undo/redo) e A5 (travar visão no sinal após reordenar) seguem pendentes, fora de escopo do SP-CVA.
**Origem:** `docs/observacoes26062026.md` §1.1, §1.2, §1.3, §1.4, §2.1, §4.4.
**Escopo:** 6 melhorias da tela de revisão que ainda faltam (descontado o já implementado pela spec `2026-06-25-sp-revisao-ui`): (A1) edição em lote por propagação à seleção; (A2) undo/redo completo; (A3) colunas de endereçamento Input/Output/Pareado; (A4) módulo + tipo de módulo editáveis; (A5) travar visão no sinal; (A6) reordenar colunas.

> Parte da decomposição das observações 26/06 (A/B/C/D). A depende de C só para o **valor** do tipo de módulo (C classifica automaticamente); A entrega o **campo** e a edição manual com a lista de tipos conhecidos.

---

## Estado atual (já implementado — não re-especificar)

`ui/tela_revisao.py` + `ui/estado.py` + `ui/modelo_tabela.py` já têm: remover/adicionar sinal, parear/desvincular D+C (`decidir_acao_pareamento`), `_snapshot`+`desfazer` (pilha de undo, **sem redo**), colunas Módulo/Equipamento/Tipo Equip./Barra/Nível Tensão, filtro de módulo por checkbox, edição da coluna **Sinal** (`DelegateSinal`), painel de scores por método.

O que **falta** e esta spec cobre está abaixo.

---

## A1 — Edição em lote por propagação à seleção (1.1)

**Decisão (usuário):** edição inline propaga à seleção — editar uma célula com N linhas selecionadas aplica o valor às demais linhas **da mesma coluna**.

- Colunas editáveis em lote: **Sinal**, **Equipamento**, **Módulo**, **Tipo de Módulo**, **Tipo (sinal)**. Status (confirmar/rejeitar) em lote fica como ação de botão (ver A1.2).
- Mecanismo: ao confirmar a edição de uma célula, se há ≥2 linhas selecionadas e a célula editada pertence à seleção, o valor é aplicado a todas. Um único `_snapshot()` antes ⇒ um único undo reverte o lote inteiro.
- Onde mora: `ui/tela_revisao.py` ganha `_aplicar_em_lote(coluna, valor, linhas)`; os delegates (Sinal e novos) chamam esse caminho em vez de escrever direto quando a seleção é múltipla. `ModeloSinais.setData` continua escrevendo 1 linha; a propagação é responsabilidade da tela (ela conhece a seleção; o modelo não).

`# ponytail: propagação lê selectedRows da view na hora do commit; sem "modo lote" persistente.`

### A1.2 — Confirmar/rejeitar em lote

Botões **"Confirmar"** e **"Enviar p/ revisão"** (habilitados com ≥1 linha): aplicam `status="decidido"`/`status="revisao"` a todas as selecionadas, com um `_snapshot`. Confirmar exige `sigla_sinal` não-nula (senão avisa quais linhas faltam sigla).

---

## A2 — Undo/Redo completo (1.3)

O `ui/estado.py` já antecipa isto no comentário ponytail (linha ~31). Implementar o upgrade path descrito lá:

- Trocar a pilha pura por `(_historico: list[list[SignalRecord]], _indice: int)`.
- `_snapshot()` trunca o histórico à frente do índice antes de empilhar (descarta o "redo" pendente após uma nova edição).
- `desfazer()` recua o índice; `refazer()` avança. Ambos devolvem bool (há/não há destino).
- Botões **← Desfazer** / **Refazer →** na barra de topo, desabilitados conforme o retorno; atalhos `Ctrl+Z` / `Ctrl+Y`.

`SignalRecord` é frozen ⇒ cópia rasa da lista basta (como já é hoje).

---

## A3 — Colunas de endereçamento (2.1)

**Decisão (usuário):** substituir a coluna genérica **"Endereço"** por três colunas derivadas:

| Coluna | Valor |
|--------|-------|
| **End. Input** | `indices` quando `direcao ∈ {Input, InputOutput}`; senão "" |
| **End. Output** | `indices_saida` quando `direcao == InputOutput`; `indices` quando `direcao == Output`; senão "" |
| **Pareado** | `✓` quando `direcao == InputOutput` (tem `indices_saida`); senão `—` |

Mudança em `ui/modelo_tabela.py`: `COLUNAS` perde "Endereço", ganha as três; `_texto()` cobre os três casos. A edição manual de endereço (A4) passa a editar End. Input / End. Output conforme a direção.

---

## A4 — Módulo + tipo de módulo editáveis (4.4)

### A4.1 Novo campo de contrato

`tdt/contracts.py` — `Modulo` ganha `tipo: str | None = None`:

```python
@dataclass(frozen=True)
class Modulo:
    nome: str | None
    origem_contexto: str
    tipo: str | None = None  # "Alimentador" | "Linha" | ... (vocabulário compartilhado)
```

Lista de tipos conhecidos como constante compartilhada (consumida pelo dropdown de A e pelo classificador de C):

```python
# tdt/contracts.py (ou tdt/vocabulario_modulo.py se crescer)
TIPOS_MODULO = (
    "Alimentador", "Linha de Transmissão", "Banco de Capacitores",
    "Alta do Transformador", "Baixa do Transformador", "Transformador",
    "Barra", "Transferência", "Outros",
)
```

### A4.2 Edição na tabela

- Coluna **Módulo** vira editável (`flags()` ganha `Qt.ItemIsEditable`); `setData` escreve `replace(rec, modulo=replace(rec.modulo, nome=valor))`.
- Nova coluna **Tipo Módulo** editável via `QComboBox` com `TIPOS_MODULO` (novo `DelegateTipoModulo`, no padrão de `DelegateSinal`); escreve `modulo.tipo`.
- Ambas participam da propagação em lote (A1).

---

## A5 — Travar visão no sinal (1.4)

Parear/editar reposiciona a linha (remover+adicionar ⇒ vai pro fim), fazendo o usuário perder o contexto.

- Após qualquer ação que reordene (`_parear_sinais`, lote, desvincular), re-selecionar e rolar até o registro pelo **`id`** (não pelo índice de linha, que mudou).
- Helper `ui/tela_revisao.py::_focar_id(id_)`: encontra a linha de origem com aquele id, mapeia pelo proxy, `setCurrentIndex` + `scrollTo`.

`# ponytail: foco por id após layoutChanged; sem "pin" persistente de múltiplas linhas.`

---

## A6 — Reordenar colunas (1.2)

`self.tabela.horizontalHeader().setSectionsMovable(True)` em `carregar()`. Uma linha.

`# ponytail: ordem não persiste entre sessões; QSettings se houver demanda.`

---

## Testes (TDD, 1 por item)

| Item | Teste | Asserção mínima |
|------|-------|-----------------|
| A1 | `test_ui_lote.py` | editar Módulo com 3 linhas selecionadas aplica às 3; 1 `_snapshot`; `desfazer` reverte as 3 de uma vez |
| A1.2 | `test_ui_lote.py` | "Confirmar" em lote marca `decidido`; linha sem sigla bloqueia com aviso |
| A2 | `test_appstate_redo.py` | `desfazer`→`refazer` restaura; novo `_snapshot` descarta o redo pendente; bools corretos nas pontas |
| A3 | `test_ui_modelo_tabela.py` (estende) | InputOutput ⇒ End.Input e End.Output preenchidos, Pareado=✓; Output puro ⇒ só End.Output; Input puro ⇒ só End.Input, Pareado=— |
| A4 | `test_contracts.py` / `test_ui_delegate_tipo_modulo.py` | `Modulo.tipo` default None; editar via combo persiste; Módulo editável persiste |
| A5 | `test_ui_focar_id.py` | após parear (linha vai pro fim), a seleção segue o `id` do registro fundido |

UI: `pytest-qt`. Sem benchmark (A não toca scoring).

---

## Critérios de Aceite

1. Editar uma célula (Sinal/Equip/Módulo/Tipo Módulo/Tipo) com várias linhas selecionadas aplica a todas; um Desfazer reverte o lote inteiro.
2. Botões Confirmar / Enviar p/ revisão agem sobre toda a seleção; Confirmar bloqueia linhas sem sigla.
3. ← Desfazer / Refazer → habilitam/desabilitam corretamente e restauram o estado; `Ctrl+Z`/`Ctrl+Y` funcionam.
4. Colunas End. Input, End. Output e Pareado substituem "Endereço" e refletem direção/pareamento corretamente.
5. Módulo é editável; Tipo Módulo é editável via dropdown com os 9 tipos conhecidos; ambos persistem no registro.
6. Após parear/editar, a visão permanece no sinal (segue o `id`), sem pular.
7. Colunas podem ser arrastadas para reordenar.
8. Testes verdes (pytest-qt); telas existentes sem regressão.

---

## Fora de escopo

- Classificação **automática** do tipo de módulo e identificação correta do módulo (nome real ≠ sheet) → spec C. A só consome `Modulo.tipo`/`Modulo.nome` e permite editar.
- Persistência de ordem de colunas entre sessões (QSettings) → ponytail, sob demanda.
- Mudanças no relatório de auditoria → já cobertas pela spec de revisão em curso.
