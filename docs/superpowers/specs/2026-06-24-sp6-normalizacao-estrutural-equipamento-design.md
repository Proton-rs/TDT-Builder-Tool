# SP6 — Normalização Estrutural (Equipamento, Barra, Fase) + Limpeza de Tokens

**Data:** 2026-06-24
**Status:** Aguardando revisão do usuário
**Escopo:** Grupos 1+2 das observações em `docs/ObservacoesProgramaTDT.txt` — corrige a ordem de extração no pipeline de normalização (hífen é destruído antes do código de equipamento ser detectado), extrai estruturalmente equipamento/barra/fase em vez de descartar ou perder essa informação, e limpa pontuação residual (parênteses) do token de matching.

---

## 0. Contexto

`docs/ObservacoesProgramaTDT.txt` lista observações da Lista 1 (GTA) em vários grupos. Este spec cobre:

- **TOKEN:** parênteses não são removidos no pré-processamento; pontuação deveria virar espaço; "Tensão BARRA P fases AB" — o "P" (Principal, vs "A" Auxiliar) é ruído pra análise mas é nomenclatura útil pra TDT.
- **FASES:** o token "A" de "CORRENTE FASE A" é ignorado no pré-processamento; pergunta se a fase vem do input ou da lista padrão; por que sinais discretos às vezes têm a coluna Fase vazia.
- **CÓDIGO DE EQUIPAMENTOS:** pré-processar `52-{n}`→Disjuntor, `89-{n}`→Seccionadora; identificar o código de equipamento; aplicar regra no motor de regras pra descartar candidatos de equipamento errado.

Investigação no código confirmou uma causa raiz comum aos três: a ordem de execução do pipeline de normalização destrói a informação antes que qualquer extração estrutural consiga usá-la.

### 0.1 Causa raiz confirmada

`normalizador.py:canonizar()` chama `normalizar()` primeiro:
```python
def normalizar(texto, config):
    texto = _sem_acentos(texto).upper()
    texto = _SEPARADORES.sub(" ", texto)  # "/", "-", "." -> espaço
    tokens = texto.split()
    sem_stop = [t for t in tokens if t not in config.stopwords]  # remove "A" (artigo)
    return expandir_abreviacoes(" ".join(sem_stop), config)

def canonizar(texto, config, vocab=None):
    base = normalizar(texto, config)  # hífen já virou espaço; "A" como stopword já foi removido
    texto2, _ctx = separar_ids_equipamento(base, config)  # N2: procura "\d+-\d+" — não existe mais!
    ...
```

Dois bugs reais, mesma causa:
1. **Equipamento:** `separar_ids_equipamento` (N2) procura literalmente um hífen (`\d+-\d+`), mas `normalizar()` já o substituiu por espaço antes de N2 rodar. `"52-1"` chega em N2 como `"52 1"` — a regex nunca casa, os dois números ficam soltos no texto de matching como ruído (exatamente o que o usuário reportou: "fica só dois números").
2. **Fase:** `STOPWORDS_PADRAO` (config.py) inclui `"A"` (artigo português). `normalizar()` remove esse "A" do texto **antes** que qualquer regra de fase rode. `"CORRENTE FASE A"` → tokens `["CORRENTE","FASE","A"]` → stopword remove `"A"` → `"CORRENTE FASE"`. A regra `r3_fase` (`motor_regras.py`) nunca vê o "A" de fase, porque ele já foi tratado como artigo e descartado.

A pergunta "de onde vem a fase" também tem resposta no código: hoje `eletrico.fase` só é preenchido **depois da decisão**, por `pipeline._com_fase()`, derivado da SIGLA escolhida (via `motor_regras.fase_da_sigla`) — nunca a partir da descrição de entrada. Sinais que vão para revisão (não decidem) ou cuja sigla não expõe fase ficam com `fase=None` na TDT. Isso explica a coluna vazia.

---

## 1. Novo passo N0 — `extrair_contexto_estrutural`

Roda **antes** de `normalizar()` consumir hífen/pontuação, no texto bruto (só maiúsculas + sem acento). Extrai três informações pro `SignalRecord`, removendo-as do texto de matching:

### 1.1 Equipamento (Disjuntor/Seccionadora)

```python
_EQUIPAMENTO_ANSI: dict[str, str] = {
    "52": "Disjuntor",
    "89": "Seccionadora",
    "29": "Seccionadora",  # seccionadora de aterramento
}
_ID_EQUIPAMENTO = re.compile(r"\b(\d+)-(\d+)\b")  # mesma forma de hoje, roda ANTES do colapso de separadores
```

Tabela pequena de propósito — cobre exatamente os dois equipamentos da observação original do usuário (Disjuntor/Seccionadora). Adicionar mais códigos ANSI é uma linha no dict, quando aparecer um caso real nos dados — não adiantar agora (YAGNI).

Quando casa, o equipamento vai para `Eletrico.equipamento_alvo`; o texto do match (`52-1`) é removido do texto de matching (como já era a intenção do N2 antigo, só que agora de fato funciona).

Números fora da tabela (`67-1`, se algum dia aparecer) continuam sendo removidos do texto de matching como ruído de ID (comportamento atual preservado), só não populam `equipamento_alvo`.

### 1.2 Barra (Principal/Auxiliar)

```python
_BARRA: dict[str, str] = {"P": "Principal", "A": "Auxiliar"}
```

Padrão: token `BARRA` seguido de um token de uma letra que esteja em `_BARRA` (ex.: `"BARRA P"` → `Eletrico.barra = "Principal"`, token `"P"` removido do texto de matching). Sem o marcador `"BARRA"` antes, a letra isolada não é tocada — evita falso positivo em qualquer "P" que apareça por outro motivo.

**Campo novo:** `Eletrico.barra: str | None = None` em `contracts.py`. Justificado pela necessidade de nomenclatura na TDT (confirmado com o usuário) — hoje não existe nenhum campo equivalente.

### 1.3 Fase (A/B/C/N/AB/BC/CA/ABC)

Reaproveita a lógica já existente em `motor_regras._fase_no_texto` (procura `"FASE" + letra(s)` ou `"NEUTRO"`/`"TRIFASICO"`), mas executada aqui — em N0, sobre tokens que ainda não passaram pelo filtro de stopwords — em vez de só em tempo de scoring sobre texto já filtrado. A função é movida/exportada de `motor_regras.py` para `normalizador.py` (ou um módulo compartilhado) pra evitar import circular; `motor_regras.r3_fase` passa a só ler `ctx.eletrico.fase` (já preenchido), sem precisar re-detectar do texto.

Quando casa, vai para `Eletrico.fase` (preenchido na normalização, **antes** da decisão — diferente de hoje). O token de fase é removido do texto de matching (evita ruído quando o resto da descrição já basta pra decidir a sigla, e evita repetir a mesma informação em dois lugares).

### 1.4 Assinatura

```python
@dataclass(frozen=True)
class ContextoEstrutural:
    equipamento_alvo: str | None = None
    barra: str | None = None
    fase: str | None = None


def extrair_contexto_estrutural(texto: str) -> tuple[str, ContextoEstrutural]:
    """N0: extrai equipamento/barra/fase do texto BRUTO (antes do colapso de
    separadores), devolvendo o texto remanescente + o contexto extraído."""
```

**Onde N0 é chamado:** não dentro de `canonizar()` (que mantém a assinatura `texto -> str` para não quebrar os outros chamadores — ex. `pipeline._corpus()` canoniza descrições da lista padrão, que não têm ID de equipamento embutido e não precisam de N0). Quem chama N0 é `estruturador.py`, explicitamente, **antes** de chamar `canonizar()`:

```python
# estruturador.py, no lugar onde hoje só se faz canonizar(str(bruta), config, vocab)
remanescente, ctx_estrutural = extrair_contexto_estrutural(str(bruta))
eletrico = Eletrico(
    fase=ctx_estrutural.fase,
    equipamento_alvo=ctx_estrutural.equipamento_alvo,
    barra=ctx_estrutural.barra,
)
descricoes = Descricoes(str(bruta), canonizar(remanescente, config, vocab))
# SignalRecord(..., descricoes=descricoes, eletrico=eletrico, ...)
```

O texto remanescente devolvido por N0 segue para `canonizar()` normalmente (N1 + colapso de separadores agora estendido → N3 boilerplate → N4 typos → N5 unidades → tokenizer), sem mudança de assinatura. `separar_ids_equipamento` (N2 antigo) é removido de `canonizar()` — N0 já cobre o caso de uso, sem destruir a informação.

---

## 2. Limpeza de pontuação residual no token

`_SEPARADORES = re.compile(r"[/\-.]")` em `normalizador.py` não cobre parênteses nem outras pontuações comuns (`,`, `;`, `:`). Estende para:

```python
_SEPARADORES = re.compile(r"[/\-.(),;:]")
```

Roda dentro de `normalizar()`, **depois** de N0 já ter extraído equipamento/barra/fase do texto bruto — então não compete com a detecção de hífen do equipamento (que agora roda antes, sobre o texto intacto).

---

## 3. Motor de regras — `r_equipamento`

Nova regra em `motor_regras.py`, espelhando `r3_fase`:

```python
_EQUIPAMENTO_SIGLA: tuple[tuple[str, str], ...] = (
    ("DJ", "Disjuntor"),
    ("SEC", "Seccionadora"),
)


def equipamento_da_sigla(sigla: str) -> str | None:
    for prefixo, nome in _EQUIPAMENTO_SIGLA:
        if sigla.startswith(prefixo):
            return nome
    return None


def r_equipamento(rec, cand, ctx, cfg) -> AjusteRegra:
    """Penaliza candidato de família de equipamento diferente da detectada
    na descrição (Disjuntor vs Seccionadora)."""
    alvo = getattr(ctx.eletrico, "equipamento_alvo", None)
    if not alvo:
        return _ZERO
    equip_cand = equipamento_da_sigla(cand.sigla.upper())
    if equip_cand is None or equip_cand == alvo:
        return _ZERO
    peso = cfg.pesos_regras["equipamento"]
    return AjusteRegra(-peso, f"equipamento: candidato é {equip_cand}, descrição indica {alvo}")
```

`Config.pesos_regras` ganha a chave `"equipamento": 0.12` (mesma faixa das outras regras de domínio). Regra entra na tupla de regras aplicadas em `aplicar_rastreado`/`aplicar` (mesmo registro, sem mudar a orquestração).

---

## 4. Testes

- `tests/test_normalizador.py` (já existe, cobre `normalizar`/`canonizar`/N1-N5 — estender com os casos novos de N0): `extrair_contexto_estrutural("DISJUNTOR 52-1 ABERTO")` → equipamento="Disjuntor", texto remanescente sem "52-1"; idem pra `"89-3"`→Seccionadora; `"TENSAO BARRA P FASES AB"` → barra="Principal", "P" removido; `"CORRENTE FASE A"` → fase="A", "A" removido do texto (e não aparece mais como stopword problemático); número fora da tabela (`"67-1"`) removido do texto mas sem popular `equipamento_alvo`; parênteses e pontuação extra (`,`, `;`, `:`) virando espaço, sem quebrar siglas existentes.

Nota: `tests/test_normalizador_estrutural.py` é um arquivo diferente (testa `normalizador_estrutural.corrigir`, mesclagem de endereços double-bit) — não confundir, não é o lugar pra estes testes.
- `tests/test_motor_regras.py`: `equipamento_da_sigla("DJ")` → "Disjuntor"; `r_equipamento` penaliza candidato `SEC*` quando `eletrico.equipamento_alvo == "Disjuntor"`, neutro quando não há informação de equipamento.
- `tests/test_pipeline.py` ou `test_estruturador.py`: ponta a ponta, `eletrico.fase`/`eletrico.equipamento_alvo`/`eletrico.barra` preenchidos a partir da descrição de entrada **antes** da decisão (não só depois, via sigla).

---

## 5. Critérios de Aceite

1. `"52-1"`/`"89-3"` na descrição populam `eletrico.equipamento_alvo` ("Disjuntor"/"Seccionadora") e não deixam números soltos no texto comparado pelos scorers.
2. `"BARRA P"`/`"BARRA A"` populam `eletrico.barra` ("Principal"/"Auxiliar"); a letra não fica como ruído no texto de matching, mas continua disponível pra TDT.
3. `"FASE A"` (e B/C/N/AB/BC/CA/ABC/NEUTRO/TRIFASICO) populam `eletrico.fase` **na normalização**, antes da decisão — disponível mesmo para sinais que vão pra revisão.
4. Parênteses e pontuação extra (`,`, `;`, `:`) não aparecem mais no texto canônico usado pelos scorers.
5. Candidato de família de equipamento errada (Disjuntor vs Seccionadora) é penalizado quando a descrição indica claramente o equipamento.
6. Testes existentes continuam verdes; os 4 grupos de teste da seção 4 cobrem o comportamento novo.
