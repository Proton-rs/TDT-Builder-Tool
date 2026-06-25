# SP-TDT-01: Input Coordinates — Formato Numérico

## Problema

`_valores()` e `_valores_analog()` em `engine_tdt.py` escrevem Input Coordinates como string:

```python
coords = ";".join(str(i) for i in rec.enderecamento.indices)
# coords_entrada = coords  →  "6" em vez de 6
```

O Export Base Full (`Export_base_Full__27_fev_2026.xlsx`) usa **número** quando há 1 índice, e string com `;` quando há múltiplos.

## Mudança

Em `engine_tdt.py`:

- `_valores()` linha 148: converter `coords_entrada` p/ `int` quando `len(indices) == 1`
- `_valores_analog()` linha 209: idem

```python
coords = ";".join(str(i) for i in rec.enderecamento.indices)
# após:
coords = indices[0] if len(indices) == 1 else ";".join(str(i) for i in indices)
```

Onde `indices = rec.enderecamento.indices` (tuple[int, ...]).

## Testes

Nenhum — a engine não tem teste unitário hoje (integração via pipeline). Adicionar `assert` no `__main__` da engine ou cobrir no test_pipeline existente.
