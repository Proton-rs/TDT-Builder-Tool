# SP C1 — Identidade e tipo do módulo (determinístico)

**Data:** 2026-06-26
**Status:** Aguardando revisão do usuário
**Origem:** `docs/observacoes26062026.md` §4.2 (módulo real ≠ nome da sheet; sheets *slot*), §4.3 (classificar o tipo do módulo).
**Escopo:** identificar o **nome real** do módulo a partir da sheet/conteúdo (em vez de usar o nome da sheet cru) e **classificar** o módulo num dos 9 tipos conhecidos — tudo determinístico (regras + tabelas em `config.py`), sem LLM (SP2 em espera).

> Raiz da decomposição **C** (C1 identidade/tipo · C2 inferência de equipamento por topologia · C3 mineração da Full Base · C4 contexto estendido da planilha). C1 desbloqueia: A4 (auto-preencher `Modulo.tipo`), C2 (topologia depende do tipo) e o guard-rail de equipamento da spec B.

---

## Problema (estado atual confirmado)

`Modulo.nome` recebe o **nome da sheet cru** ([estruturador.py:90](../../../src/tdt/estruturador.py), `Modulo(nome_mod, "sheet_name")`); a única correção é o dict de **aliases manual** na UI. Consequências (obs 4.2):

- `AL FWB15` deveria ser `AL15`; `GTD_11` deveria ser `AL11` — o nome cru não é o módulo.
- Um módulo pode estar espalhado em **várias sheets**.
- Sheets **slot** contêm sinais de **vários módulos** (ex.: `input_nao_homogeneo_3`) — um único `modulo.nome` por sheet está errado.

E não há tipo de módulo nenhum (4.3).

---

## Dependência de contrato

`Modulo.tipo: str | None` e a constante `TIPOS_MODULO` são introduzidos pela **spec A4**. C1 **popula** esses campos. Se C1 for implementada antes de A, mover a adição do campo/constante para C1 (uma ou outra cria; não as duas). Marcar no plano.

---

## C1.1 — Resolver o nome real do módulo

Novo módulo puro `src/tdt/identidade_modulo.py`. Função central:

```python
def resolver_modulo(sheet_name: str, rows: list[tuple], config: Config) -> ResolucaoModulo
```

onde `ResolucaoModulo` traz `nome: str | None`, `por_linha: dict[int, str] | None` (slot), e `confianca: str` (`"alta"|"baixa"`).

### Algoritmo (determinístico)

1. **Tokenizar** o nome da sheet; extrair o **número** do módulo (regex `\d+`) e os **prefixos textuais** (`AL`, `GTD`, `FWB`, `LT`, …).
2. **Resolver o prefixo canônico** por uma tabela configurável de aliases:
   ```python
   # config.py
   mapa_prefixo_modulo: dict[str, str] = {"GTD": "AL", "FWB": "AL", "AL": "AL", "LT": "LT", ...}
   ```
   `AL FWB15` → prefixo canônico `AL`, número `15` → **`AL15`**. `GTD_11` → `AL`, `11` → **`AL11`**.
3. **Compor** `prefixo_canonico + numero`. Se faltar número **ou** o prefixo não estiver no mapa ⇒ `confianca="baixa"`, `nome = sheet_name` cru (fallback), e o registro vai pra **revisão** (`motivo="modulo_indefinido"`) — nunca inventa (alinha com "sem falsos positivos"; A4 deixa o usuário corrigir).

### Sheets slot (vários módulos numa sheet)

4. **Detecção:** a sheet é *slot* quando o módulo não é único por sheet — sinalizado por uma **coluna de módulo** (detectada por conteúdo) ou por tokens de módulo que **variam entre linhas**. (Hoje `analise_colunas` declara que "Módulo NÃO é detectado por coluna"; C1 abre exceção: detecção de coluna de módulo **apenas** para sheets slot.)
5. **Resolução por linha:** quando slot, `resolver_modulo` devolve `por_linha[i] = <módulo da linha i>` aplicando os passos 1–3 ao valor de módulo daquela linha; o `estruturador` usa `por_linha[i]` em vez do nome da sheet.

> O conjunto-semente de prefixos/aliases (`AL`, `GTD→AL`, `FWB→AL`, `LT`, …) e o critério de detecção de slot precisam ser **confirmados contra `input_nao_homogeneo_3.xlsx`** (exemplo de slot) e os demais inputs no início da implementação — registrar os valores reais no plano. A tabela vive em `config.py` (calibrável), nunca hardcoded fora dela.

---

## C1.2 — Classificar o tipo do módulo

Função pura no mesmo módulo:

```python
def classificar_tipo(modulo_nome: str, registros: list[SignalRecord], config: Config) -> str
```

Devolve um valor de `TIPOS_MODULO` (A4): `Alimentador`, `Linha de Transmissão`, `Banco de Capacitores`, `Alta do Transformador`, `Baixa do Transformador`, `Transformador`, `Barra`, `Transferência`, `Outros`.

Estratégia em cascata (para no primeiro acerto):

1. **Por prefixo** — tabela configurável `tipo_por_prefixo` (ex.: `AL → Alimentador`, `LT → Linha de Transmissão`, `BC → Banco de Capacitores`, `TR → Transformador`, `BARRA → Barra`).
2. **Por conteúdo** (quando o prefixo não decide) — palavras-chave nos sinais/descrições do módulo: presença de sinais de capacitor ⇒ `Banco de Capacitores`; AT/BT do transformador ⇒ `Alta/Baixa do Transformador`; tokens de barra/transferência ⇒ `Barra`/`Transferência`. Tabela `palavras_chave_tipo` em `config.py`.
3. **Fallback** ⇒ `Outros` (e, se o usuário quiser, A4 permite corrigir manualmente).

`# ponytail: cascata prefixo→conteúdo→Outros; cresce adicionando linhas nas tabelas de config, não código.`

---

## C1.3 — Integração no pipeline

`pipeline.executar`, após a extração estrutural e **antes** do scoring/pareamento (para que C2 e o motor de regras já vejam módulo/tipo corretos):

1. Para cada sheet, `resolver_modulo(...)` → aplica `nome`/`por_linha` aos `SignalRecord` (substitui o nome cru).
2. `classificar_tipo(...)` por módulo resolvido → grava `modulo.tipo`.
3. Registros com `confianca="baixa"` (passo 3 de C1.1) entram na revisão com `motivo="modulo_indefinido"`.

`pipeline.py` continua o único orquestrador que conhece o novo módulo (SRP). `identidade_modulo.py` só conhece `contracts` + `config`.

---

## Testes (TDD)

| Item | Teste | Asserção mínima |
|------|-------|-----------------|
| C1.1 | `test_identidade_modulo.py` | `AL FWB15`→`AL15`, `GTD_11`→`AL11`; sem número ⇒ `confianca="baixa"`, fallback ao nome cru |
| C1.1 slot | `test_identidade_modulo.py` | sheet slot ⇒ `por_linha` com módulos distintos por linha (caso de `input_nao_homogeneo_3`) |
| C1.2 | `test_identidade_modulo.py` | prefixo `AL`⇒`Alimentador`; sinais de capacitor⇒`Banco de Capacitores`; desconhecido⇒`Outros` |
| C1.3 | `test_pipeline.py` (estende) | módulo resolvido e `modulo.tipo` preenchidos antes do scoring; `modulo_indefinido` vai pra revisão |

**Gate:** `bench/benchmark.py` não pode regredir — resolver o módulo corretamente **deve** ajudar (ou no mínimo não piorar) a taxa de decisão e os FP.

---

## Critérios de Aceite

1. `AL FWB15`→`AL15` e `GTD_11`→`AL11` (e os demais casos reais confirmados nos inputs); mapa de prefixos vive em `config.py`.
2. Sheet slot resolve módulo **por linha**, não um único por sheet.
3. Módulo não resolvível com confiança ⇒ fallback ao nome cru **e** revisão (`modulo_indefinido`), nunca um módulo inventado.
4. Todo módulo recebe um `Modulo.tipo` dentre os 9 (ou `Outros`); classificação por prefixo→conteúdo→fallback.
5. Pipeline grava nome/tipo antes do scoring; benchmark sem regressão.
6. Testes verdes.

---

## Fora de escopo (vira C2/C3/C4)

- Inferir o **equipamento** a partir da topologia do tipo de módulo (4.1) → C2.
- Minerar a Full Base para saber quais sinais existem por tipo (5.1) ou o Measurement Type (5.3) → C3.
- Extrair cabeçalhos/títulos/observações da sheet como contexto (5.2) → C4.
- Refinamento por LLM de casos ambíguos (SP2) → fora; C1 manda ambíguo pra revisão.
