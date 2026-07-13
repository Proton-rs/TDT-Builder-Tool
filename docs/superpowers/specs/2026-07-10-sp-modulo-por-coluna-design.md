# SP Identificação de Módulo por Coluna — Gênero Sheet-por-Tipo

**Data:** 2026-07-10
**Status:** Proposto
**Origem:** `docs/input_não_homogeneo_5_SMF.xlsx` — lista não-homogênea cujas sheets separam por **tipo de ponto** (ESTADOS/MEDIDAS/COMANDOS), não por módulo. O módulo fica numa **coluna dedicada** (col A, header "Módulo"), varia por linha, em blocos contíguos. Alimentado hoje, todo sinal da sheet recebe módulo = nome da sheet ("ESTADOS") — errado.
**Escopo:** Detectar e atribuir módulo por linha no caminho não-homogêneo; canonizar/reconciliar nomes de módulo divergentes entre sheets. Implementa o follow-up já previsto em `identidade_modulo.py:4-6` (`ResolucaoModulo.por_linha`, sempre `None` hoje).

**Princípio (auditado):** SÓ ADICIONA um método de aquisição de módulo. Nenhum caminho existente (homogêneo, sheet_name, coluna:SIGLA) muda de comportamento. Quem decide qual método usar é o próprio programa: a detecção `_col_modulo` dispara (novo gênero) ou retorna `None` (comportamento atual preservado); a `origem_contexto` de cada sinal registra qual método forneceu o módulo, e os métodos coexistem entre sheets. Ver seção **Preservação de comportamento**.
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
        origem_contexto="coluna:MODULO_POR_LINHA"  (TAG NOVA, por linha)
        └── célula vazia → status="revisao", justificativa="modulo_indefinido"
         │
         ▼
  aplicar_identidade(sinais, sheet_name, rows, config)
    └── p/ sinais origem="coluna:MODULO_POR_LINHA": canonizar_modulo(explicito=True)
        ├── canoniza (prefixo+nº)        → nome canônico, alta
        └── não canoniza (sem prefixo)   → valor cru limpo, alta
        classificar_tipo agrupado POR MÓDULO CANÔNICO (só p/ esta tag)
```

Nenhuma rota nova. O identificador já classifica ESTADOS/MEDIDAS/COMANDOS como sheets de dados (têm coluna de inteiros + texto) e a rota como não-homogênea (header na linha 4, não no topo).

> **Tag `coluna:MODULO_POR_LINHA` (nova, distinta de `coluna:MODULO`):** o caminho homogêneo (`identidade_homogenea.py`) já emite `origem="coluna:MODULO"` e `"coluna:MODULO+header:NUMERO_OPERATIVO"`, e esses sinais passam por `aplicar_identidade`. Reusar a tag faria o novo branch capturar sinais homogêneos. A tag nova isola o novo gênero — os branches de `aplicar_identidade`/`estruturar` que a tratam nunca tocam os sinais existentes.

### 1. Detecção — `_col_modulo` (`analise_colunas.py`)

Detecta a coluna de módulo por linha, por **conteúdo**, com header como desempate (híbrido — consistente com `_col_indice`, que usa `_ROTULO_ENDERECO` como bônus).

**Gating (preserva testes existentes de `analisar`):** `analisar` ganha parâmetro `config: Config | None = None`. `_col_modulo` só roda quando `config is not None`. Os ~20 testes atuais de `test_analise_colunas.py` chamam `analisar` **sem** config → `"modulo"` nunca é detectado → saída idêntica. O pipeline passa `config`, então o novo gênero é coberto em produção.

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

Refatorar a lógica de token/prefixo+número de `resolver_modulo` (que hoje recebe `sheet_name` e ignora `rows` no corpo) para função pura reusável por célula. **O fallback (sem canonização) difere por origem** — por isso o parâmetro `explicito`:

```python
def canonizar_modulo(valor: str, config: Config, *, explicito: bool = False) -> ResolucaoModulo:
    """Canoniza um NOME de módulo (de sheet_name OU de célula da coluna Módulo).
    Estratégia 1: alias direto (mapa_sheet_modulo). Estratégia 2: prefixo
    mapeado + número seguinte. Sem canonização:
      - explicito=False (sheet_name): valor CRU, confiança BAIXA  [inalterado]
      - explicito=True  (coluna):     valor cru LIMPO, confiança ALTA
    """

def resolver_modulo(sheet_name, rows, config) -> ResolucaoModulo:
    return canonizar_modulo(sheet_name, config)  # explicito=False → comportamento byte-idêntico
```

**Preservação:** com `explicito=False` (default), o fallback é `(valor cru, "baixa")` — exatamente o que `resolver_modulo` faz hoje (`identidade_modulo.py:67`). O teste `test_resolver_modulo_sem_numero_cai_em_baixa_confianca` (`"SLOT GERAL"` → nome cru, baixa) e todos os demais testes de `resolver_modulo` seguem verdes. Estratégias 1 e 2 (canonização) são idênticas para ambos os modos.

Regra de "cru limpo" (só no ramo `explicito=True`, sem canonização por prefixo): remover sufixos de ruído — `- NNkV` / `- NN.NkV`, `(FUTURO)`, `(RESERVA)` — e colapsar espaços. Mantém o token de módulo legível. **Nunca aplicada ao caminho sheet_name.**

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

Novo ramo **gated em `"modulo" in mapa.colunas`** — quando ausente (todos os testes atuais de `test_estruturador.py`, que montam `mapa` sem essa chave), o ramo é pulado e `estruturar` roda idêntico.

- Lê a célula da coluna de módulo **por linha** → `Modulo(nome=valor_cru, origem_contexto="coluna:MODULO_POR_LINHA")`. A canonização acontece em `aplicar_identidade` (mantém `estruturar` sem dependência de `config.mapa_*`).
- **Célula de módulo vazia** → `status="revisao"`, `justificativa="modulo_indefinido"`. Reusa o roteamento existente `pipeline.py:662` (`rec.status=="revisao"` → `ItemRevisao(motivo=rec.justificativa)`) e um motivo já existente (`modulo_indefinido`, usado em `particionar_por_confianca` e `pipeline.py:694`). Sem nova rota de revisão, sem novo motivo, sem mudar assinatura de `aplicar_identidade`/`particionar_por_confianca`.
- **Precedência:** coluna MODULO explícita > extração do NOME padronizado. No SMF não há coluna de sigla, então o ramo de pré-classificação por sigla (`estruturador.py:110-138`) nem executa; a regra de precedência existe para robustez se um input futuro tiver ambos.
- Fora a célula vazia, o status do sinal segue normal (`pendente` → scoring). A coluna de módulo **não** pré-classifica o sinal (diferente da coluna de sigla, que decide a sigla do sinal).

### 4. Identidade por linha — `aplicar_identidade` (`identidade_modulo.py`)

Novo ramo **gated em `origem_contexto == "coluna:MODULO_POR_LINHA"`** (tag nova — não colide com `coluna:MODULO`/`coluna:MODULO+header:NUMERO_OPERATIVO` do caminho homogêneo, nem com `coluna:SIGLA`/`sheet_name`):

- Canoniza cada `modulo.nome` via `canonizar_modulo(nome, config, explicito=True)`.
- `classificar_tipo` roda **por grupo de módulo canônico** (agrupa os sinais desta tag por `modulo.nome` após canonização, classifica cada grupo). **Escopo estrito:** só para sinais desta tag. Sinais `sheet_name`, `coluna:SIGLA` e `coluna:MODULO*` (homogêneo) continuam pela lógica atual (um `tipo` via `nome_ref`), byte-idêntica.
- **Assinatura preservada:** `aplicar_identidade` continua retornando `(sinais, confianca:str)` e `particionar_por_confianca` continua recebendo `(sinais, str)` — os 2 testes que desempacotam `novos, conf` seguem válidos. Para esta tag a confiança de lote é `"alta"` (como `coluna:SIGLA` hoje); a revisão de célula vazia já foi resolvida em `estruturar` via `status`, não aqui.
- Célula vazia (revisão) é tratada por linha em `estruturar` (acima), não pela confiança de sheet inteira — evita mandar a sheet toda à revisão.

Sinais existentes (`sheet_name`, `coluna:SIGLA`, `coluna:MODULO*`) mantêm o fluxo atual intacto; `ResolucaoModulo.por_linha` permanece disponível no contrato mas não é necessário nesta implementação (a atribuição por linha já ocorre em `estruturar`).

### 5. Reconciliação cross-sheet

**Automática, sem código extra.** A canonização é determinística e pura: `AL 11 - 13.8kV` (ESTADOS) e `AL11 - 13.8kV` (MEDIDAS) resolvem ambos para `AL11`. O agrupamento downstream por `modulo.nome` (montagem de RTUs/seções do TDT) unifica os sinais dos 3 tipos de ponto sob o mesmo módulo. `AL15`/`AL15 (FUTURO)` idem.

---

## Isolamento e contratos

| Unidade | Faz | Depende de | Testável isolado |
|---|---|---|---|
| `_col_modulo` | acha índice da coluna de módulo | rows, config.mapa_prefixo_modulo | sim (rows sintéticas) |
| `canonizar_modulo` | string módulo → nome canônico + confiança | config.mapa_* | sim (pura) |
| `estruturar` (ramo modulo) | célula → Modulo por linha + vazio→revisão | mapa.colunas | sim |
| `aplicar_identidade` (ramo tag nova) | canoniza + tipo por grupo | canonizar_modulo | sim |

Mudança de interface mínima e **aditiva**: `analisar` ganha `config=None` (default preserva chamadas atuais); `MapaColunas.colunas` ganha chave opcional `"modulo"`; `canonizar_modulo` ganha kwarg `explicito=False` (default = comportamento de `resolver_modulo`); nova `origem_contexto="coluna:MODULO_POR_LINHA"`. Nenhuma assinatura removida; nenhuma assinatura de `aplicar_identidade`/`particionar_por_confianca` alterada.

---

## Preservação de comportamento (auditoria 2026-07-10)

Cada caminho existente e por que **não muda**:

| Caminho | Entra em `_col_modulo`? | Entra nos novos ramos? | Resultado |
|---|---|---|---|
| **Homogêneo** (1 sheet=1 módulo) | Não — usa `estruturar_homogeneo`, nunca chama `analisar` | Não — origem é `coluna:MODULO*`, ≠ tag nova | Idêntico |
| **Não-homog. sheet_name** (sem coluna módulo) | Sim, mas `_col_modulo`→`None` (sem coluna que canonize em bloco) | Não | Idêntico |
| **Não-homog. coluna:SIGLA** (SAN2) | Sim, mas `_col_modulo`→`None` (regressão a validar) | Não — origem `coluna:SIGLA` | Idêntico |
| **`resolver_modulo`** (qualquer sheet_name) | — | Delega `canonizar_modulo(explicito=False)` | Byte-idêntico (fallback raw/baixa) |
| **Testes `analisar` sem config** | `_col_modulo` não roda (config None) | — | Idêntico |
| **Testes `estruturar` sem `"modulo"`** | — | Ramo gated pulado | Idêntico |

**Gate crítico:** o único ponto que pode vazar é um **falso positivo de `_col_modulo`** num input não-homogêneo existente — isso ativaria o ramo novo de `estruturar` e trocaria a origem do módulo. Mitigações: (1) `_col_modulo` só roda com `config`; (2) threshold conservador exigindo estrutura de bloco **e** taxa de canonização por prefixo **e** diversidade mínima; (3) **critério de aceite:** a suíte de testes atual (incl. `test_analise_colunas.py`, `test_estruturador.py`, `test_identidade_modulo.py`) passa sem alteração, e os inputs não-homogêneos de regressão (SAN2) produzem saída idêntica à baseline.

---

## Testes

Unitários (novos):
- `_col_modulo` escolhe col A (módulo), **não** col D (IED `SEL-411L`) nem col B (descrição); retorna `None` numa sheet sem coluna de módulo.
- `canonizar_modulo(explicito=True)`: `AL 11 - 13.8kV`→`AL11`, `AL15 - 13.8kV (FUTURO)`→`AL15`, `TR1`→`TR1`, `TIE-AT`→`TIE-AT` (cru limpo, alta), `LTSM3C1`→`LTSM3C1` (cru limpo, alta).
- `canonizar_modulo(explicito=False)`: `"SLOT GERAL"`→`("SLOT GERAL", "baixa")` (igual a `resolver_modulo`, sem limpeza de sufixo).
- `estruturar` (com `"modulo"` no mapa): módulo atribuído por linha, muda ao cruzar bloco (LTSM3C1→LTSM3C2); célula vazia → `status="revisao"`, `justificativa="modulo_indefinido"`.
- `aplicar_identidade` (tag `coluna:MODULO_POR_LINHA`): 2 módulos na mesma sheet → 2 tipos distintos.

Regressão (existentes devem passar sem edição):
- `test_resolver_modulo_*`, `test_aplicar_identidade_*`, `test_particionar_*` (`test_identidade_modulo.py`) — inclui `test_aplicar_identidade_preserva_nome_de_coluna`, que usa `coluna:MODULO` (homogêneo) e **não** deve entrar no ramo novo.
- `test_analise_colunas.py` e `test_estruturador.py` inteiros.

Integração (smoke, `input_não_homogeneo_5_SMF.xlsx`):
- 3 sheets processadas; módulos por linha corretos; `AL 11`/`AL11` unificados em `AL11` cross-sheet; contagem de módulos canônicos distintos coerente (~36 base, unificada).
- Baseline: um input não-homogêneo existente (ex. SAN2) produz saída idêntica à de antes da mudança (guarda contra falso positivo de `_col_modulo`).

---

## Fora de escopo

- Alteração de scoring, `dc_pairer`, expansão de candidatos.
- Qualquer rota nova (usa o caminho não-homogêneo existente).
- Detecção multi-idioma de header além do desempate `_MODULO_ROTULO`.
- Casamento do NOME padronizado (col E) para scoring — col B (descrição humana) segue como fonte.
