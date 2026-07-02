# SP-J — UI de revisão + auditoria estendida — Design

**Data:** 2026-07-02
**Arquivos-alvo:** `src/tdt/ui/tela_revisao.py`, `src/tdt/ui/proxy_revisao.py`,
`src/tdt/ui/modelo_tabela.py`, `src/tdt/auditoria.py`.

## Problema

1. Filtro atual da tabela de revisão é fraco (filtro global de todas as
   colunas) e não indica quando uma coluna está sob efeito de filtro por
   palavra.
2. Não há como revisar por sheet do excel de input.
3. Auditoria exportada tem pouca informação para análise de erro.

## Design

### 1. Abas por sheet (substitui o filtro global)

Remover o filtro de todas as colunas. Na posição que ele ocupava, colocar
abas (`QTabBar`): uma aba por sheet do excel de input + aba **"Tudo"**.
Selecionar aba filtra a tabela pela sheet de origem do sinal (requer sheet de
origem no modelo — já existe no `SignalRecord`; expor no modelo se faltar).

### 2. Filtro estilo Excel por coluna

Botão de filtro no header de cada coluna abre popup com:
- campo de busca de texto;
- lista de valores únicos da coluna com checkboxes (+ "Selecionar tudo");
- OK/Limpar.
Filtros combinam entre colunas (AND). Implementar via `QSortFilterProxyModel`
existente (`proxy_revisao.py`) estendido para predicado por coluna.

### 3. Indicador de filtro ativo

Coluna sob filtro mostra ícone/estado visual no header (ex. ícone de funil),
para o usuário nunca olhar dados filtrados sem saber.

### 4. Auditoria estendida (máximo de informação)

Adicionar colunas ao `Auditoria_Revisao.xlsx`:
- sheet de origem;
- descrição normalizada E canônica (tokens que os scorers viram);
- contexto N0: equipamento_alvo, nome_equipamento, barra, fase;
- estado semântico extraído (SP-E);
- regras do motor aplicadas com ajuste e justificativa;
- gap calculado e gap exigido (chave de confiança do roteador);
- etapa do pipeline que decidiu (scorer/ancoragem/polaridade/pré-classificação
  por sigla/resgate por regras);
- endereço bruto lido e coluna de onde veio.

## Critérios de aceite

1. Abas por sheet funcionam com input multi-sheet real (LISTA 1 - GTD) e a aba
   "Tudo" mostra tudo; filtro global antigo removido.
2. Filtro por coluna: busca + checkboxes + combinação entre colunas; teste de
   proxy model (filtra/combina/limpa).
3. Indicador visível em coluna filtrada; some ao limpar.
4. Auditoria contém as novas colunas preenchidas para decididos E revisões;
   teste que verifica presença/consistência das colunas.
5. Performance aceitável com ~2.3k linhas (LISTA 1) — sem travar a UI.

## Fora de escopo

- Edição em massa na revisão (SP anterior de campos editáveis cobre edição).
- Mudanças na tela inicial (SP-K).
