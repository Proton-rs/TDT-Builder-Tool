# SP D — Qualidade (testes de FP/adversariais) e geração de saída

**Data:** 2026-06-26
**Status:** Aguardando revisão do usuário
**Origem:** `docs/observacoes26062026.md` §6.1 (testes p/ falsos positivos), §6.2 (testes adversariais), §7.1 (não sobrescrever arquivos).
**Escopo:** (D1) gerar saída sem sobrescrever arquivos existentes; (D2) detecção de falsos positivos no benchmark com gate duro; (D3) corpus adversarial que sobe a confiança da análise sem introduzir FP.

> Parte da decomposição das observações 26/06 (A/B/C/D).

---

## D1 — Não sobrescrever arquivos de saída (7.1)

**Problema:** a saída é escrita com nome fixo em dois pontos — `cli.py:58` (`wb.save(out)`) e `tela_revisao._gerar` (`TDT.xlsx` + `Auditoria_Revisao.xlsx`). Rodar de novo sobrescreve a saída anterior.

**Solução:** helper puro em `src/tdt/io_saida.py` (ou junto de `engine_tdt`):

```python
def caminho_unico(path: Path) -> Path:
    """Se `path` existe, devolve `path` com sufixo numérico livre.
    resultado.xlsx -> resultado_1.xlsx -> resultado_2.xlsx ..."""
    if not path.exists():
        return path
    base, ext = path.stem, path.suffix
    n = 1
    while (cand := path.with_name(f"{base}_{n}{ext}")) .exists():
        n += 1
    return cand
```

Aplicado nos dois pontos de escrita (CLI: `out`, e os `.revisao.json`/`.log.txt`/`.auditoria.json` derivados; UI: `TDT.xlsx` e `Auditoria_Revisao.xlsx`). A mensagem de sucesso na UI passa a mostrar o caminho **efetivo** (pode ter sufixo).

`# ponytail: sufixo sequencial simples; sem timestamp/UUID (a obs pede _1, _2).`

---

## D2 — Detecção de falsos positivos no benchmark (6.1)

`bench/` já tem ground-truth (`rotulos.py`) e gate de regressão (`benchmark.py`). Estender:

- **Definição de FP:** registro com `status="decidido"` cuja `sigla_sinal` **diverge** do rótulo (decidiu, e decidiu errado). Distinto de "não decidiu" (revisão) — esse não é FP.
- **Relatório:** lista cada FP com `(id, sigla_decidida, sigla_esperada, justificativa, método que decidiu)` — a justificativa já carrega o método (roteador/regras), então o relatório expõe **padrões de erro** (qual método/regra mais erra).
- **Métrica:** taxa de FP = FP / decididos, adicionada ao log do benchmark.

### Gate duro (decisão do usuário)

A taxa de FP atual vira **teto**; o `benchmark.py` **falha** (exit ≠ 0) se a contagem de FP aumentar. O teto é um knob versionado (ex.: `bench/limites.py` ou constante no harness), ajustável conscientemente quando o corpus/rótulos mudam — nunca silenciosamente.

`# ponytail: gate compara contagem de FP contra o teto versionado; subir o teto é uma mudança explícita no PR.`

---

## D3 — Corpus adversarial (6.2)

Conjunto de casos deliberadamente difíceis (fixtures em `bench/` reusando o formato de `rotulos.py`): descrições ambíguas, pares opostos (ligado/desligado, sobre/subtensão), equipamento ausente, siglas confusáveis, double-bit/pareamento limítrofes.

**Moral (decisão do usuário):** o objetivo do corpus é **subir a confiança/taxa de decisão da análise sem introduzir falsos positivos**. Daí duas camadas de avaliação:

1. **Constraint dura (gate):** **zero FP** no corpus adversarial. Um caso decidido errado quebra o build. Caso genuinamente ambíguo com confiança baixa **deve** ir pra revisão — isso é sucesso, não falha.
2. **Métrica a maximizar (não-gate):** % de casos adversariais **decididos corretamente com alta confiança**. É o número que melhorias futuras (specs B/C, novas regras, e5) devem **subir**, sob a constraint dura de não criar FP. Reportado no log; não falha o build se baixo — é alvo, não piso.

Assim o corpus vira o instrumento que a obs descreve: "garantir que melhorias não aumentem falsos positivos" (constraint) enquanto "melhora a robustez" (métrica).

---

## Testes / entregáveis (TDD)

| Item | Teste | Asserção mínima |
|------|-------|-----------------|
| D1 | `test_io_saida.py` | arquivo inexistente ⇒ inalterado; existente ⇒ `_1`; `_1` ocupado ⇒ `_2` |
| D1 | `test_cli.py` / `test_ui_gerar` (estende) | rodar 2× não sobrescreve; caminho efetivo reportado |
| D2 | `bench/benchmark.py` (estende) + `test_benchmark_fp.py` | FP corretamente identificado (decidido≠rótulo); relatório lista método; gate falha se FP > teto |
| D3 | `test_adversarial.py` + fixtures | zero FP no corpus (gate); métrica de "decidido certo c/ alta confiança" calculada e logada |

---

## Critérios de Aceite

1. Gerar saída (CLI e UI) nunca sobrescreve arquivo existente; usa sufixo `_1`, `_2`…; o caminho efetivo é reportado ao usuário.
2. O benchmark identifica e lista os falsos positivos (decididos errados) com o método/justificativa que decidiu.
3. O benchmark **falha** se a contagem de FP subir acima do teto versionado.
4. Existe um corpus adversarial com gate de **zero FP** e uma métrica logada de "decididos corretamente com alta confiança" (alvo a maximizar).
5. Todos os testes verdes; o gate de FP integra o fluxo de verificação do projeto.

---

## Fora de escopo

- Corrigir as regras/heurísticas que os FPs revelarem → as correções saem em specs B/C; D só **expõe e barra** regressões.
- Mudar a UI de revisão → spec A.
