# SP-UI-CONTRASTE — Correção de contraste e numeração de linhas (design)

**Data:** 2026-07-08
**Status:** aprovado em brainstorming
**Escopo:** somente `src/tdt/ui/` (tema.qss, modelo_tabela.py, tela_revisao.py). Pipeline, scoring e contratos de dados intocados.

## Contexto e objetivo

Usuário reportou dois problemas visuais na UI (tema grafite, ver `2026-07-06-sp-ui-redesign-design.md`):

1. Nas barras de score por método (tela de Revisão), o texto fica ilegível quando o
   fundo colorido dinamicamente (verde/âmbar) é claro demais para o texto claro fixo.
2. A coluna de números de linha (vertical header) da tabela de Revisão aparece vazia,
   deixando um espaço sem uso à esquerda da tabela.

Investigação confirmou dois root causes pontuais (não é um problema de tema geral):

- **Barras de score**: `QProgressBar` global define `color: #e8ebf2` (quase branco) em
  `tema.qss:137`. Por método, `_atualizar_barras` (tela_revisao.py:485-497) sobrescreve
  só o `background-color` do `::chunk` via `cor_faixa()` (`COR_ALTO` `#35c48f`,
  `COR_MEDIO` `#e0a83f`, `COR_BAIXO` `#e0604c`, em modelo_tabela.py:36-40), sem ajustar
  a cor do texto. Texto claro sobre fundo verde/âmbar claro = baixo contraste.
- **Números de linha sumidos**: `ModeloSinais.headerData()` (modelo_tabela.py:93-97)
  retorna `None` incondicionalmente quando a orientação não é `Qt.Horizontal`, em vez
  de delegar a `super().headerData(...)`. Isso suprime a numeração automática de linhas
  do Qt na tela de Revisão. `ModeloAnalise.headerData()` (modelo_analise.py:49-52), usado
  na tela de Análise, já delega corretamente ao `super()` e por isso não tem o problema.

Adicionalmente, o usuário pediu um pequeno reforço geral de contraste nas cores base do
tema (texto secundário/dim, bordas), sem redesenhar a paleta.

## Correções

### 1. Cor de texto por faixa de score

Em `modelo_tabela.py`, ao lado de `COR_ALTO`/`COR_MEDIO`/`COR_BAIXO`, adicionar
constantes de cor de texto por faixa:

- `COR_ALTO_TEXTO = QColor("#0d2e21")` (texto escuro sobre o verde `#35c48f`)
- `COR_MEDIO_TEXTO = QColor("#2c2005")` (já usado em `tema.qss` como texto-sobre-aviso)
- `COR_BAIXO_TEXTO = QColor("#e8ebf2")` (mantém o texto claro atual — vermelho já tem
  contraste adequado)

Expor uma função `texto_faixa(score)` espelhando `cor_faixa(score)`, retornando a cor de
texto correspondente à mesma faixa (mesmos limiares: ≥0.70 alto, ≥0.45 médio, resto baixo).

Em `tela_revisao.py:_atualizar_barras`, o `setStyleSheet` de cada barra passa a incluir
também a regra de texto:

```python
cor = cor_faixa(v)
cor_texto = texto_faixa(v)
if cor is not None:
    barra.setStyleSheet(
        f"QProgressBar {{ color: {cor_texto.name()}; }}"
        f"QProgressBar::chunk {{ background-color: {cor.name()}; }}"
    )
```

Quando `v` é `None` (sem score), nenhuma cor é aplicada e a barra mantém o estilo padrão
do `tema.qss` (fundo `#232a38`, texto `#e8ebf2`).

### 2. Restaurar numeração de linhas

Em `modelo_tabela.py`, `ModeloSinais.headerData` passa a delegar ao `super()` no
fallback, no mesmo padrão de `ModeloAnalise`:

```python
def headerData(self, secao, orientacao, role=Qt.DisplayRole):
    if role == Qt.DisplayRole and orientacao == Qt.Horizontal:
        nome = COLUNAS[secao]
        return f"{nome} ✎" if nome in _EDITAVEIS else nome
    return super().headerData(secao, orientacao, role)
```

Isso restaura a numeração automática 1, 2, 3... do Qt na vertical header da tela de
Revisão, sem precisar de lógica própria de numeração.

### 3. Reforço pontual de contraste geral

Em `tema.qss`, revisar contraste das cores de texto secundário e bordas contra os fundos
onde são usadas, subindo levemente a luminosidade das que estiverem abaixo de ~4.5:1
(WCAG AA para texto normal):

- Texto secundário `#9aa3b5` sobre fundo painel `#1e2430`/`#232a38` — verificar e ajustar
  se necessário (candidato: `#a8b1c2` ou similar, levemente mais claro).
- Texto dim `#5f6880` sobre os mesmos fundos — candidato a maior ajuste, é o mais escuro.
- Borda `#2b3242` contra fundo base `#14161d` — se estiver quase invisível, subir para
  algo como `#333c4f`.

Valores finais exatos serão calculados durante a implementação com checagem de razão de
contraste (ferramenta simples de cálculo, sem dependência nova). Não há mudança de tom
(continua grafite escuro) nem redesenho de paleta — só ajuste de luminosidade pontual.

## Fora de escopo

- Redesenho completo do tema (já feito em SP-UI-0/SP-UI-redesign).
- Mudança de layout/tamanho da coluna de numeração de linhas (largura fica no cálculo
  automático do Qt).
- Outras telas além de Revisão para os itens 1 e 2 (tela de Análise já está correta).

## Testes

- Teste unitário para `ModeloSinais.headerData(Qt.Vertical, Qt.DisplayRole)` retornando
  o valor esperado do Qt (não `None`).
- Teste unitário para `texto_faixa(score)` cobrindo os três limiares (0.70, 0.45) e `None`.
- Verificação manual na tela de Revisão: números de linha visíveis; barras de score com
  texto legível nas três faixas.
