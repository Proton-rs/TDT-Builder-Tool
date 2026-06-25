# AGENTS.md — tests

## Purpose
Suíte TDD do SP1: um `test_*.py` por módulo.

## Local Contracts
- Test-first (RED→GREEN). Sem frameworks pesados além de pytest + asserts.
- Fixtures de arquivos reais em `conftest.py` (apontam para `docs/`).
- Módulos com embeddings: usar **encoder/scorer fake** injetado; nunca baixar modelo num teste unitário.
- Casos de borda do domínio (double-bit, D+C, dedup, header esparso, coluna por conteúdo) têm teste dedicado porque já causaram bug.

## Verification
`python -m pytest -q` (da raiz). Todos verdes antes de concluir qualquer tarefa.
