# SP C2 — Inferência de equipamento por topologia do módulo

**Data:** 2026-06-26
**Status:** Aguardando revisão do usuário
**Origem:** `docs/observacoes26062026.md` §4.1 (inferir equipamento usando topologia típica do módulo).
**Escopo:** quando a linha **não** informa o equipamento explicitamente, inferi-lo a partir da topologia típica do tipo de módulo (ex.: num alimentador, sinal não associado a seccionadora ⇒ disjuntor principal) — determinístico, com fallback a revisão sob ambiguidade.

> Sub-spec da decomposição **C**. Depende de **C1** (precisa do `Modulo.tipo`). Alimenta o guard-rail de fusão da **spec B** (que só funde com equipamento definido) e reduz erros por equipamento ausente (obs §4 abre dizendo que é a causa-raiz da maioria dos erros).

---

## Estado atual (confirmado)

N0 (`normalizador.extrair_contexto_estrutural`) extrai `equipamento_alvo` (Disjuntor/Seccionadora via ANSI `52`/`89`/`29`) e `nome_equipamento` (ID `52-2`) **só quando há um ID hifenado no texto** ([normalizador.py:77](../../../src/tdt/normalizador.py)). Sem esse ID, `equipamento_alvo`/`nome_equipamento` ficam `None` — e a maioria das planilhas não traz o ID. O motor de regras (`r_equipamento`, `r3_fase`) só atua quando esses campos existem, então um equipamento ausente derruba várias pistas.

---

## C2.1 — Modelo de topologia por tipo de módulo

Tabela configurável (em `config.py`) que descreve a composição típica de cada `TIPOS_MODULO` (de C1):

```python
# config.py — composição esperada e equipamento "default" do módulo
topologia_por_tipo: dict[str, Topologia] = {
    "Alimentador": Topologia(
        equipamentos=("Disjuntor", "Seccionadora"),
        default="Disjuntor",          # equipamento principal
        cardinalidade={"Disjuntor": 1, "Seccionadora": (2, 3)},
    ),
    # Linha de Transmissão, Banco de Capacitores, Transformador... idem
}
```

`default` é o equipamento ao qual um sinal sem equipamento explícito é atribuído **quando a topologia tem um principal não-ambíguo** (alimentador: 1 disjuntor). Tipos sem default claro (ex.: barra com vários elementos) não inferem — vão pra revisão.

> O conteúdo real de `topologia_por_tipo` (cardinalidades, defaults) deve ser **confirmado com o domínio / Full Base** no início da implementação — pode reusar o catálogo minerado pela **C3** (quais equipamentos aparecem por tipo de módulo). Registrar os valores no plano.

---

## C2.2 — Regra de inferência

Novo módulo puro `src/tdt/inferencia_topologia.py`:

```python
def inferir_equipamento(registros: list[SignalRecord], config: Config) -> list[SignalRecord]
```

Por módulo (agrupado por `modulo.nome`), para cada registro com `eletrico.equipamento_alvo is None`:

1. Se a descrição/sigla casa **explicitamente** outro equipamento da topologia (ex.: token "SECCIONADORA"/marca de seccionadora) ⇒ atribui esse, não o default.
2. Senão, se o tipo de módulo tem `default` não-ambíguo ⇒ atribui o `default` (ex.: alimentador ⇒ Disjuntor), marcando a **origem** (`eletrico` ganha rastro `equipamento_inferido=True` ou via justificativa) para a auditoria distinguir inferido de extraído.
3. Senão (sem default claro, ou múltiplos equipamentos plausíveis) ⇒ deixa `None` e o registro vai pra **revisão** (`motivo="equipamento_ambiguo"`).

`nome_equipamento` (o ID `52-2`) **não** é inventado pela inferência — só `equipamento_alvo` (a família) é inferido. Se a fusão/pareamento exigir o ID e ele não existir, o caso continua indo pra revisão (mantém o invariante "sem falso positivo").

`# ponytail: inferência só do default quando a topologia tem 1 principal; o resto vai pra revisão.`

---

## C2.3 — Integração no pipeline

`pipeline.executar`, **após C1** (tipo de módulo resolvido) e N0, **antes** do scoring e do `pareamento_polaridade`/`dc_pairer` — para que o motor de regras (`r_equipamento`, `r3_fase`) e a fusão da B já vejam o equipamento inferido.

`inferencia_topologia.py` conhece só `contracts` + `config`. `pipeline.py` segue o único orquestrador.

---

## Testes (TDD)

| Item | Teste | Asserção mínima |
|------|-------|-----------------|
| C2.1 | `test_inferencia_topologia.py` | tabela de topologia acessível; alimentador tem default Disjuntor |
| C2.2 | `test_inferencia_topologia.py` | alimentador, sinal sem equipamento e sem pista de seccionadora ⇒ `equipamento_alvo="Disjuntor"`, marcado inferido |
| C2.2 | `test_inferencia_topologia.py` | sinal com pista de seccionadora ⇒ Seccionadora (não o default) |
| C2.2 | `test_inferencia_topologia.py` | tipo sem default claro ⇒ permanece None, vai pra revisão (`equipamento_ambiguo`) |
| C2.3 | `test_pipeline.py` (estende) | equipamento inferido visível ao motor de regras antes do scoring |

**Gate:** `bench/benchmark.py` — inferir o equipamento principal **deve** subir a taxa de decisão (mais pistas pras regras) **sem** aumentar FP. Se aumentar FP, a inferência está agressiva demais (apertar para revisão).

---

## Critérios de Aceite

1. Sinal sem equipamento explícito num alimentador, sem pista de outro equipamento, recebe o disjuntor principal; a auditoria marca como **inferido** (distinto de extraído).
2. Sinal com pista explícita de outro equipamento (seccionadora) recebe esse, não o default.
3. Módulo de tipo sem principal não-ambíguo não infere — vai pra revisão (`equipamento_ambiguo`).
4. `nome_equipamento` (ID) nunca é inventado; só a família é inferida.
5. Benchmark: taxa de decisão sobe sem aumentar FP.
6. Testes verdes.

---

## Fora de escopo

- Classificar o tipo de módulo / identificar o módulo real → C1 (pré-requisito).
- Minerar a Full Base para popular a tabela de topologia → C3 (C2 consome a tabela; pode ser semente manual até C3 existir).
- Refinamento por LLM de casos ambíguos (SP2) → fora; ambíguo vai pra revisão.
