# SP C4 — Contexto estendido da planilha

**Data:** 2026-06-26
**Status:** Aguardando revisão do usuário
**Origem:** `docs/observacoes26062026.md` §5.2 (explorar cabeçalhos, títulos, observações, células superiores e estrutura da sheet — além do conteúdo das linhas).
**Escopo:** capturar o contexto da sheet que hoje é **descartado** (título, células acima do cabeçalho de dados, colunas de observação, células mescladas) e disponibilizá-lo para C1 (identidade do módulo), motor de regras, revisão e auditoria.

> Sub-spec da decomposição **C**. Independente para implementar; **alimenta** C1 (o módulo real costuma estar no título da sheet) e o motor de regras (tokens extras de contexto).

---

## Estado atual (confirmado)

`analise_colunas` localiza o `header_row` por densidade-do-topo e devolve `MapaColunas(header_row, colunas)` ([contracts.py:130](../../../src/tdt/contracts.py)); o `estruturador` lê **da linha de cabeçalho para baixo**. Tudo **acima** do cabeçalho (título da sheet, subtítulos, observações, células mescladas) e colunas não-mapeadas (ex.: "Observações") são ignorados. Para a sheet homogênea, o `estruturador_homogeneo` lê colunas fixas e também não capta o contexto superior.

Isso joga fora pistas valiosas: o título "ALIMENTADOR AL15 — 13,8 kV" identifica módulo, tipo e nível de tensão de uma vez.

---

## C4.1 — Extrator de contexto da sheet

Novo módulo puro `src/tdt/contexto_sheet.py`:

```python
@dataclass(frozen=True)
class ContextoSheet:
    titulo: str | None            # texto das células acima do header (concatenado)
    observacoes: tuple[str, ...]  # conteúdo de colunas/células de observação
    tokens: frozenset[str]        # tokens normalizados do título+observações (p/ regras)

def extrair_contexto(rows: list[tuple], header_row: int, config: Config) -> ContextoSheet
```

- **Título / células superiores:** concatena o texto não-vazio das linhas `1..header_row-1` (inclui o que veio de células mescladas — openpyxl repete o valor na âncora; ler a primeira ocorrência basta).
- **Observações:** colunas cujo header casa termos de observação (`OBS`, `OBSERVAÇÃO`, `NOTA`, `COMENTÁRIO` — tabela em `config.colunas_observacao`); o conteúdo por linha vira observação do registro.
- **Tokens:** `normalizador.canonizar` sobre título+observações, para o motor de regras consumir como contexto adicional.

`# ponytail: título = células acima do header concatenadas; sem parsing de layout rico (sem detectar caixas/áreas).`

---

## C4.2 — Onde o contexto se acopla

1. **Por sheet → C1:** `ContextoSheet.titulo`/`tokens` entram em `identidade_modulo.resolver_modulo`/`classificar_tipo` como sinal adicional (título identifica módulo/tipo melhor que o nome da sheet).
2. **Por registro → observações:** `SignalRecord` ganha o contexto de observação da sua linha. Para não inchar o contrato, anexa-se em `Descricoes` um campo opcional `observacao: str | None = None` (a descrição bruta continua intacta; a observação é separada para a revisão exibir e as regras opcionalmente usarem).
3. **Motor de regras:** `Contexto.de` (em `motor_regras`) passa a unir `ContextoSheet.tokens` aos tokens da descrição, dando às regras (número de proteção, fase, lado) pistas do título/observações.
4. **Revisão/auditoria:** nova coluna **Observação** na tabela de revisão (spec A pode incorporar) e no relatório de auditoria, exibindo o contexto capturado.

---

## C4.3 — Integração no pipeline

`estruturador`/`estruturador_homogeneo` chamam `extrair_contexto(...)` ao processar cada sheet (já têm `rows` e `header_row`); propagam `ContextoSheet` para C1 e gravam `Descricoes.observacao` por registro. Ocorre **antes** de C1/C2/scoring.

Módulos novos conhecem só `contracts`/`config`. `pipeline.py` orquestra.

---

## Testes (TDD)

| Item | Teste | Asserção mínima |
|------|-------|-----------------|
| C4.1 | `test_contexto_sheet.py` | título acima do header é capturado; coluna "Obs" vira `observacoes`; tokens normalizados |
| C4.1 | `test_contexto_sheet.py` | célula mesclada no título lida pela âncora; sheet sem contexto ⇒ campos vazios, sem erro |
| C4.2 | `test_identidade_modulo.py` (estende) | título "ALIMENTADOR AL15" ajuda a resolver módulo `AL15`/tipo `Alimentador` quando o nome da sheet é ambíguo |
| C4.2 | `test_motor_regras.py` (estende) | token do título (ex. fase/nível de tensão) influencia a regra correspondente |
| C4.3 | `test_pipeline.py` (estende) | `Descricoes.observacao` preenchida; contexto disponível antes do scoring |

**Gate:** `bench/benchmark.py` — contexto extra **deve** ajudar (mais pistas) sem aumentar FP.

---

## Critérios de Aceite

1. Título e células acima do cabeçalho são capturados como `ContextoSheet.titulo`; células mescladas resolvidas.
2. Colunas de observação viram `observacoes`/`Descricoes.observacao` por registro, sem poluir a descrição bruta.
3. O contexto da sheet melhora a identificação de módulo/tipo (C1) e fica disponível ao motor de regras.
4. A revisão/auditoria pode exibir a observação capturada (coluna Observação).
5. Benchmark sem regressão (idealmente melhora); testes verdes.

---

## Fora de escopo

- Parsing de layout rico (detectar blocos/áreas visuais, cores, agrupamentos) → fora; só texto de células acima do header + colunas de observação.
- Usar o contexto para inferir equipamento/topologia → C2 (C4 só fornece os tokens).
- OCR/imagens embutidas na planilha → fora.
