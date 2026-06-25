# SP7 — Caminho Determinístico para Lista Homogênea

**Data:** 2026-06-24
**Status:** Aguardando revisão do usuário
**Escopo:** Item "ANALISE DE LISTA" de `docs/ObservacoesProgramaTDT.txt`. Lista homogênea passa hoje pelo mesmo motor pesado (scorers + motor de regras + roteador) da lista não-homogênea, apesar de já trazer sigla, equipamento, módulo e tipo em colunas fixas e conhecidas — o que explica a nomenclatura pior observada (informação estruturada disponível, mas nunca lida).

---

## 0. Contexto e Causa Raiz Confirmada

`identificador.py:classificar()` calcula `Rota.homogeneo` (bool), mas **nenhum lugar do código usa esse valor** além de um log (`pipeline.py:230`). Lista homogênea e não-homogênea seguem exatamente o mesmo caminho: `analise_colunas.analisar()` (detecção de coluna por embedding/densidade) → `estruturador.estruturar()` (marcador de seção + N0 heurístico sobre texto livre) → 3 scorers → motor de regras → roteador.

Inspecionei `docs/input_homogeneo.xlsx` (fixture real) pra confirmar a estrutura. Cada sheet de dados homogênea (`SE`, `LT 3`, `AL 11`, `TR 1`, etc.) tem duas partes:

1. **Bloco de legenda** (linhas 0-N, antes de uma linha vazia): tabela `EQUIPAMENTO` → `NÚMERO OPERATIVO / MNEMÔNICO` por módulo (ex.: `DJ` → `52-11`, `SECC` → `29-8`). Referência por módulo, não por sinal individual.
2. **Tabela de sinais** (depois da linha vazia), com cabeçalho fixo e sempre na mesma ordem:

```
Utilizado? | SUBESTAÇÃO | MÓDULO | EQUIPAMENTO | TIPO | DESCRIÇÃO DO PONTO | SIGLA SINAL | NOME | Tipo | Nível Lógico 0 | Nível Lógico 1 | Escala | Control Code / Qualificador | INDEX DNP3
```

Exemplo real (sheet `AL 11`):
```
SIM | IMA | AL | TC | A | CORRENTE FASE A | IA | IMA_AL11_AL11_IA | - | - | - | 1 | - | 70
```

**A sigla, o módulo, o equipamento e o tipo (A/C/D) já vêm prontos em colunas dedicadas.** O pipeline atual não lê nenhuma dessas colunas por nome — `analise_colunas.py` só detecta descrição/índice/tipo por conteúdo (e nem `EQUIPAMENTO` nem `SIGLA SINAL` fazem parte do que ele procura); `MÓDULO` só é lido do nome da sheet, nunca da coluna. Por isso a lista homogênea acaba dependendo da mesma extração heurística de texto livre (N0) que a não-homogênea, perdendo a informação estruturada que já estava ali — confirma a observação original.

---

## 1. Design

### 1.1 Detecção do formato homogêneo (por nome de coluna, não heurística)

Novo módulo `src/tdt/estruturador_homogeneo.py`. Detecta a tabela de sinais procurando, dentro das primeiras `_MAX_SCAN` linhas, uma linha cujo conteúdo bate **exatamente** (case-insensitive, sem acento) com o conjunto mínimo de cabeçalhos esperados: `{"UTILIZADO?", "SUBESTACAO", "MODULO", "EQUIPAMENTO", "TIPO", "DESCRICAO DO PONTO", "SIGLA SINAL", "NOME", "INDEX DNP3"}`.

Isso é deliberadamente **diferente** da detecção por densidade/embedding usada em `analise_colunas.py` pra sheets não-homogêneas — aqui o formato é fixo e conhecido, então comparar nomes literais é mais simples, mais rápido e não precisa de encoder/modelo nenhum (sem custo de embedding pra essas sheets).

```python
_CABECALHO_ESPERADO = {
    "UTILIZADO?", "SUBESTACAO", "MODULO", "EQUIPAMENTO", "TIPO",
    "DESCRICAO DO PONTO", "SIGLA SINAL", "NOME", "INDEX DNP3",
}


def detectar_header(rows: list[tuple]) -> int | None:
    """Devolve o índice 0-based da linha de cabeçalho, ou None se a sheet
    não seguir o formato homogêneo fixo."""
```

`pipeline.executar()` passa a usar essa detecção, por sheet, **quando `rota.homogeneo` for `True`** (finalmente usando o campo que hoje só vira log): se `detectar_header()` achar a linha, processa por esse caminho determinístico; senão, cai no caminho heurístico de hoje (`analise_colunas` + `estruturador`) como fallback — uma sheet "homogênea" que não bate no formato exato não quebra, só não ganha o atalho.

### 1.2 Extração determinística por linha

```python
def estruturar_homogeneo(
    rows: list[tuple], header_idx: int, sheet_name: str, lp: ListaPadraoADMS, config: Config,
) -> tuple[list[SignalRecord], list[SignalRecord]]:
    """Devolve (decididos, pendentes_de_scoring).

    decididos: sigla já validada contra a Lista Padrão ADMS — não passa
    pelos scorers.
    pendentes_de_scoring: SIGLA SINAL vazia ou não encontrada na Lista
    Padrão — seguem pro caminho heurístico de hoje como fallback (mesma
    function estruturador.estruturar não reaproveita a leitura de coluna
    daqui; estes registros são reconstruídos a partir da DESCRIÇÃO DO PONTO
    e processados pelos scorers normalmente)."""
```

Por linha (pulando `Utilizado? != "SIM"` — linha inativa, nunca vira sinal):

| Coluna do input | Campo do `SignalRecord` |
|---|---|
| `SIGLA SINAL` | `sigla_sinal` — **decisão confiada por padrão**, decisão do usuário: só validar que existe na Lista Padrão ADMS (`lp.por_sigla(sigla)`), sem rodar scoring |
| `MÓDULO` | `modulo.nome` (em vez do nome da sheet) |
| `EQUIPAMENTO` | `eletrico.equipamento_alvo` — mapeado por uma tabela pequena (`{"DJ": "Disjuntor", "SECC": "Seccionadora", "SECF": "Seccionadora", "SECT": "Seccionadora", "SECG": "Seccionadora"}` — mesmos dois grupos do SP6, mais os sinônimos de seccionadora vistos no fixture real; igual ao SP6, expandir quando aparecer outro real) |
| `TIPO` (A/C/D) | `tipo_sinal.categoria`/`direcao` via `vocabulario_tipo.CODIGOS_TIPO` (já existe, SP5) — `categoria_confiavel=True` sempre (vem de coluna explícita) |
| `DESCRIÇÃO DO PONTO` | `descricoes.bruta`; `descricoes.normalizada` ainda passa por `extrair_contexto_estrutural` (N0) + `canonizar()` — barato, e cobre fase quando a descrição tiver ("CORRENTE FASE A" → `eletrico.fase="A"`), informação que a coluna fixa não dá |
| `INDEX DNP3` | `enderecamento.indices` — mesmo parser de índices já usado em `estruturador._parse_indices` (reaproveitar, não duplicar) |

**Se `SIGLA SINAL` está vazia ou não existe na Lista Padrão:** o registro vai pro grupo `pendentes_de_scoring` — não é erro nem motivo de revisão imediata, só significa "essa linha não tem atalho, processa normal". `pipeline.executar()` junta esses registros com o restante do fluxo de sheets não-homogêneas (mesma chamada de `estruturador.estruturar`/scorers que já existe), preservando o comportamento atual como rede de segurança. Isso responde à decisão já tomada com o usuário: confiar na sigla, só validando existência — sem inventar comportamento pra sigla inválida além de cair no caminho que já existia antes deste spec.

### 1.3 Onde isso entra no `pipeline.executar()`

```python
for sn in rota.sheets_dados:
    rows = ler_rows(wb_in[sn])
    header_homog = detectar_header(rows) if rota.homogeneo else None
    if header_homog is not None:
        decididos_homog, pendentes = estruturar_homogeneo(rows, header_homog, sn, lp, config)
        decididos.extend(decididos_homog)
        sinais = pendentes  # só os pendentes entram no caminho de scoring abaixo
    else:
        mapa = analisar(rows, encoder, ref_emb)
        sinais = list(estruturar(rows, mapa, sheet_name=sn, config=config, vocab=vocab))
    # ... loop de classificação de `sinais` continua igual a hoje
```

Sem mudança de assinatura pública do pipeline; `decididos`/`revisao` continuam os mesmos acumuladores.

### 1.4 Por que não usar `analise_colunas` pra detectar essas colunas

`analise_colunas.py` foi desenhado pra sheets **não-homogêneas**, onde nomes de coluna variam e cabeçalho pode estar em qualquer posição — daí a detecção por conteúdo/embedding. Aqui o formato é fixo (confirmado no fixture real, mesmo cabeçalho nas 20+ sheets de dados do arquivo) — usar comparação literal de string é mais simples, mais rápido (sem `encoder()`/FAISS) e mais fácil de entender/depurar. Rodar a heurística cara numa estrutura que já é conhecida seria over-engineering.

---

## 2. Testes

- `tests/test_estruturador_homogeneo.py` (novo): `detectar_header` acha a linha certa no formato do fixture real (cabeçalho com os 9 nomes esperados); devolve `None` numa sheet sem esse formato. `estruturar_homogeneo`: linha com `Utilizado?="SIM"` e sigla existente na lista padrão fake vira `decidido` com `eletrico.equipamento_alvo`/`modulo.nome`/`enderecamento.indices` populados direto das colunas; linha com `Utilizado?="NÃO"` é ignorada (não aparece em nenhum dos dois grupos); linha com sigla vazia ou inexistente na lista padrão cai em `pendentes_de_scoring`.
- `tests/test_pipeline.py` ou novo `test_pipeline_homogeneo.py`: ponta a ponta com uma sheet no formato do fixture (`docs/input_homogeneo.xlsx` já existe como fixture de teste) — confirma que sinais com sigla válida saem decididos sem rodar os scorers (pode-se confirmar indiretamente checando que `diagnostico` fica `None`/vazio nesses registros, já que scorers não rodaram), e que módulo/equipamento vêm da coluna, não da sheet/heurística.
- `tests/test_identificador.py` (se existir) ou `test_pipeline.py`: sheet marcada `rota.homogeneo=True` mas que não bate no formato fixo (ex.: cabeçalho diferente) cai no caminho heurístico de hoje sem erro.

---

## 3. Critérios de Aceite

1. `rota.homogeneo` passa a alterar comportamento de fato (hoje só gera log).
2. Sinal de sheet homogênea com `SIGLA SINAL` preenchida e existente na Lista Padrão ADMS é decidido sem rodar tfidf/vetorial/fuzzy.
3. `eletrico.equipamento_alvo`, `modulo.nome` e `enderecamento.indices` vêm das colunas dedicadas (`EQUIPAMENTO`, `MÓDULO`, `INDEX DNP3`), não de heurística sobre texto livre.
4. `Utilizado? = "NÃO"` nunca gera `SignalRecord` (nem decidido, nem revisão).
5. Sigla vazia ou não encontrada na Lista Padrão cai no caminho de scoring existente (fallback), sem quebrar o pipeline.
6. Sheet marcada homogênea que não bate no formato de cabeçalho fixo usa o caminho heurístico de hoje, sem erro.
7. Testes existentes continuam verdes; os 3 grupos da seção 2 cobrem o comportamento novo.
