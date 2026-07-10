# SP Identificação de Módulo por Coluna — Gênero Sheet-por-Tipo

**Data:** 2026-07-10
**Status:** Proposto
**Origem:** `docs/input_não_homogeneo_5_SMF.xlsx` — lista não-homogênea cujas sheets separam por **tipo de ponto** (ESTADOS/MEDIDAS/COMANDOS), não por módulo. O módulo fica numa **coluna dedicada** (col A, header "Módulo"), varia por linha, em blocos contíguos. Alimentado hoje, todo sinal da sheet recebe módulo = nome da sheet ("ESTADOS") — errado.
**Escopo:** Detectar e atribuir módulo por linha no caminho não-homogêneo; canonizar/reconciliar nomes de módulo divergentes entre sheets. Implementa o follow-up já previsto em `identidade_modulo.py:4-6` (`ResolucaoModulo.por_linha`, sempre `None` hoje).
**Relacionada:** [2026-06-30-sp-sigla-nao-homogeneo-design.md](2026-06-30-sp-sigla-nao-homogeneo-design.md) — aquela spec trata coluna de **sigla** (SAN2, condensada, sem coluna MODULO); esta trata coluna de **módulo** explícita. Genéros distintos, caminho não-homogêneo compartilhado.

---

## Diagnóstico

### Problema

O caminho não-homogêneo assume que **módulo é constante por sheet** e vem do nome da sheet:

- `analise_colunas.py:11-12` — decisão explícita de **não** detectar módulo por coluna ("ambíguo com IED"); módulo vem do nome da sheet (responsabilidade do chamador).
- `estruturador.py:61` — `nome_mod = modulo if modulo is not None else sheet_name` — um único módulo para a sheet inteira.
- `identidade_modulo.py:31` — `resolver_modulo(sheet_name, ...)` canoniza a partir do **nome da sheet**.

Esse pressuposto quebra no gênero SMF:

| Aspecto | Homogêneo (atual) | Gênero SMF (este) |
|---|---|---|
| Sheets separam por | Módulo (1 sheet = 1 módulo) | Tipo de ponto (ESTADOS/MEDIDAS/COMANDOS) |
| Fonte do módulo | Nome da sheet | Coluna dedicada, por linha |
| Nº módulos por sheet | 1 | 28–36 (SMF real) |

### Estrutura real do arquivo (`input_não_homogeneo_5_SMF.xlsx`)

3 sheets: `ESTADOS` (discretos), `MEDIDAS` (analógicos), `COMANDOS`.

Layout por sheet (header na linha 4):

| A (Módulo) | B (Descrição) | C (Tipo de Ponto) | D (Origem/IED) | E (NOME padronizado) | F (Index DNP3) |
|---|---|---|---|---|---|
| `LTSM3C1` | `DISJ 52-6 - ESTADO DISJUNTOR ABERTO` | `Ponto Simples` | `SEL-411L` | `SMF_LTSM3C1_52-6_DJF1_A` | `1` |

- Col A: módulo, **varia por linha em blocos contíguos** (LTSM3C1 repete, depois LTSM3C2, TR1, TR2, AL11...).
- Col B: descrição humana (linguagem natural) — é a que `_col_descricao` escolhe (multi-palavra, alta diversidade).
- Col D: IED/Origem (`SEL-411L`) — também repete em blocos, mas é vocabulário de relé, **não** casa prefixo de módulo.
- Col E: NOME padronizado `{SE}_{MODULO}_{...}` — código, não usado para scoring.
- **Sem coluna de sigla própria** — o caminho `_col_sigla` não dispara (diferente da SAN2).

### Divergência de nomes cross-sheet

O mesmo módulo físico aparece com strings diferentes entre sheets:

| ESTADOS | MEDIDAS / COMANDOS |
|---|---|
| `AL 11 - 13.8kV` | `AL11 - 13.8kV` |
| `AL 15 - 13.8kV` | `AL15 - 13.8kV (FUTURO)` |

Sem reconciliação, viram módulos distintos no TDT (duplicação).

---

## Proposta

### Arquitetura

```
Pipeline não-homogêneo (existente, estendido):

  analisar(rows, ..., siglas_set)
    ├── _col_descricao()  (existente)
    ├── _col_indice()     (existente)
    ├── _col_tipo()       (existente)
    ├── _col_sigla()      (existente)
    └── _col_modulo()     ← NOVO: coluna de módulo por linha
         │
         ▼
  estruturar(rows, mapa, sheet_name, ...)
    └── se "modulo" no mapa: lê célula por linha → modulo.nome,
        origem_contexto="coluna:MODULO"  (por linha, não por sheet)
         │
         ▼
  aplicar_identidade(sinais, sheet_name, rows, config)
    └── p/ sinais origem="coluna:MODULO": canonizar_modulo() por célula
        ├── canoniza (prefixo+nº)        → nome canônico, alta
        ├── não canoniza (sem prefixo)   → valor cru limpo, alta
        └── célula vazia                 → baixa → revisão modulo_indefinido
        classificar_tipo agrupado POR MÓDULO CANÔNICO (não 1/sheet)
```

Nenhuma rota nova. O identificador já classifica ESTADOS/MEDIDAS/COMANDOS como sheets de dados (têm coluna de inteiros + texto) e a rota como não-homogênea (header na linha 4, não no topo).

### 1. Detecção — `_col_modulo` (`analise_colunas.py`)

Detecta a coluna de módulo por linha, por **conteúdo**, com header como desempate (híbrido — consistente com `_col_indice`, que usa `_ROTULO_ENDERECO` como bônus).

```python
_MODULO_ROTULO = ("MODULO", "MÓDULO", "BAY", "VAO", "VÃO")
_MODULO_BONUS = 0.10

def _col_modulo(rows, inicio, ncols, config, reservadas: set[int]) -> int | None:
    """Coluna de módulo por linha: valores em BLOCOS contíguos + alta taxa de
    canonização por prefixo de módulo. Header 'Módulo' soma bônus de desempate.

    - Estrutura de bloco: transições (valor != anterior) / nº linhas é BAIXA.
      Separa {módulo, IED} de {descrição, índice} (que não repetem em runs).
    - Taxa de canonização: fração de valores DISTINTOS cujo 1º token alfabético
      ∈ config.mapa_prefixo_modulo (ou canoniza p/ módulo). IED (SEL-411L) ~0.
    - Exclui colunas já reivindicadas (descricao/indice/tipo/sigla) via `reservadas`.
    - Exclui baixa diversidade (< 2 valores distintos) e colunas numéricas.
    - Score = taxa_canon * (bloco) [+ bônus se header casa _MODULO_ROTULO].
    - Threshold mínimo p/ evitar falso positivo em sheets sem coluna de módulo.
    """
```

Notas de robustez:
- **Módulo vs IED:** ambos têm estrutura de bloco; a taxa de canonização por prefixo desempata (LTSM3C1/AL11/TR1 vs SEL-411L).
- **Nem todo módulo canoniza** (LTSM3C1 → token "LTSM" ∉ prefixos): a taxa não precisa ser 100%; AL/TR/BC canonizam e, com bloco + header "Módulo", a coluna vence com folga.
- **Sheet sem coluna de módulo** (gênero homogêneo/SAN2): nenhuma coluna atinge o threshold → retorna `None`, comportamento atual preservado.

`analisar` adiciona `"modulo"` a `MapaColunas.colunas`. As colunas já reivindicadas por descricao/indice/tipo/sigla entram em `reservadas` para não competir.

### 2. Canonização por célula — `canonizar_modulo` (`identidade_modulo.py`)

Refatorar a lógica de token/prefixo+número de `resolver_modulo` (que hoje recebe `sheet_name` e ignora `rows` no corpo) para função pura reusável por célula:

```python
def canonizar_modulo(valor: str, config: Config) -> ResolucaoModulo:
    """Canoniza um NOME de módulo (de sheet_name OU de célula da coluna Módulo).
    Estratégia 1: alias direto (mapa_sheet_modulo). Estratégia 2: prefixo
    mapeado + número seguinte. Sem canonização → valor cru LIMPO, alta confiança
    (coluna de módulo é explícita — o módulo é dado, não inferido)."""

def resolver_modulo(sheet_name, rows, config) -> ResolucaoModulo:
    return canonizar_modulo(sheet_name, config)  # comportamento preservado
```

Regra de "cru limpo" (sem canonização por prefixo): remover sufixos de ruído — `- NNkV` / `- NN.NkV`, `(FUTURO)`, `(RESERVA)` — e colapsar espaços. Mantém o token de módulo legível.

Comportamento esperado:

| Entrada | Saída | Confiança |
|---|---|---|
| `AL 11 - 13.8kV` | `AL11` | alta |
| `AL15 - 13.8kV (FUTURO)` | `AL15` | alta |
| `TR1` | `TR1` | alta |
| `TIE-AT` | `TIE-AT` | alta (cru limpo) |
| `LTSM3C1` | `LTSM3C1` | alta (cru limpo) |
| `` (vazio) | — | baixa (revisão) |

> **Diferença do caminho sheet_name:** lá, "baixa confiança" = chute do nome da sheet pode estar errado. Aqui, a coluna é explícita: o módulo é dado. Não-canonizar é só "não há forma canônica curta", não incerteza — por isso alta confiança. Só célula **vazia** é incerteza real.

### 3. Estruturação — `estruturar` (`normalizacao/estruturador.py`)

Quando `mapa.colunas` tem `"modulo"`:

- Lê a célula da coluna de módulo **por linha** → `Modulo(nome=valor_cru, origem_contexto="coluna:MODULO")`. A canonização acontece em `aplicar_identidade` (mantém `estruturar` sem dependência de `config.mapa_*`).
- **Precedência:** coluna MODULO explícita > extração do NOME padronizado. No SMF não há coluna de sigla, então o ramo de pré-classificação por sigla (`estruturador.py:110-138`) nem executa; a regra de precedência existe para robustez se um input futuro tiver ambos.
- O status do sinal segue normal (`pendente` → scoring). A coluna de módulo **não** pré-classifica o sinal (diferente da coluna de sigla, que decide a sigla do sinal).

### 4. Identidade por linha — `aplicar_identidade` (`identidade_modulo.py`)

Estender para sinais com `origem_contexto == "coluna:MODULO"`:

- Canoniza cada `modulo.nome` via `canonizar_modulo`.
- Célula vazia (nome vazio) → `ItemRevisao(motivo="modulo_indefinido")` **por linha**, não a sheet inteira. A confiança deixa de ser um único valor por sheet: os sinais com módulo válido seguem decididos; só os de célula vazia vão à revisão.
- `classificar_tipo` passa a rodar **por grupo de módulo canônico** (agrupa os sinais da sheet por `modulo.nome` após canonização, classifica cada grupo). Hoje classifica 1 tipo para a sheet inteira usando o primeiro módulo — errado quando a sheet tem 30 módulos.
- Sinais `origem_contexto == "sheet_name"` mantêm o fluxo atual intacto.

`particionar_por_confianca` passa a receber a partição já decidida por linha (não um único booleano de sheet).

### 5. Reconciliação cross-sheet

**Automática, sem código extra.** A canonização é determinística e pura: `AL 11 - 13.8kV` (ESTADOS) e `AL11 - 13.8kV` (MEDIDAS) resolvem ambos para `AL11`. O agrupamento downstream por `modulo.nome` (montagem de RTUs/seções do TDT) unifica os sinais dos 3 tipos de ponto sob o mesmo módulo. `AL15`/`AL15 (FUTURO)` idem.

---

## Isolamento e contratos

| Unidade | Faz | Depende de | Testável isolado |
|---|---|---|---|
| `_col_modulo` | acha índice da coluna de módulo | rows, config.mapa_prefixo_modulo | sim (rows sintéticas) |
| `canonizar_modulo` | string módulo → nome canônico + confiança | config.mapa_* | sim (pura) |
| `estruturar` (ramo modulo) | célula → Modulo por linha | mapa.colunas | sim |
| `aplicar_identidade` (ramo coluna) | canoniza + tipo por grupo + revisão vazio | canonizar_modulo | sim |

Mudança de interface mínima: `MapaColunas.colunas` ganha chave opcional `"modulo"`; `ResolucaoModulo.por_linha` deixa de ser sempre `None` (contrato já existia). Nenhuma assinatura pública removida.

---

## Testes

Unitários:
- `_col_modulo` escolhe col A (módulo), **não** col D (IED `SEL-411L`) nem col B (descrição); retorna `None` numa sheet sem coluna de módulo (regressão do gênero homogêneo/SAN2).
- `canonizar_modulo`: `AL 11 - 13.8kV`→`AL11`, `AL15 - 13.8kV (FUTURO)`→`AL15`, `TR1`→`TR1`, `TIE-AT`→`TIE-AT`, `LTSM3C1`→`LTSM3C1`, vazio→baixa.
- `estruturar`: módulo atribuído por linha, muda ao cruzar bloco (LTSM3C1→LTSM3C2).
- `aplicar_identidade`: 2 módulos na mesma sheet → 2 tipos distintos; célula vazia → `modulo_indefinido`.
- `resolver_modulo` inalterado (regressão via delegação a `canonizar_modulo`).

Integração (smoke, `input_não_homogeneo_5_SMF.xlsx`):
- 3 sheets processadas; módulos por linha corretos; `AL 11`/`AL11` unificados em `AL11` cross-sheet; contagem de módulos canônicos distintos coerente (~36 base, unificada).

---

## Fora de escopo

- Alteração de scoring, `dc_pairer`, expansão de candidatos.
- Qualquer rota nova (usa o caminho não-homogêneo existente).
- Detecção multi-idioma de header além do desempate `_MODULO_ROTULO`.
- Casamento do NOME padronizado (col E) para scoring — col B (descrição humana) segue como fonte.
