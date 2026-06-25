# SP4 UI Desktop — Resumo de Implementação

## Estrutura da UI

```
src/tdt/ui/
├── app.py           # MainWindow com QStackedWidget (3 telas)
├── config_io.py     # carregar/salvar config.toml
├── estado.py        # AppState compartilhado entre telas
├── modelo_tabela.py # ModeloSinais (QAbstractTableModel, 15 colunas)
├── tela_config.py   # Tela de configurações (paths, thresholds, pesos)
├── tela_inicial.py  # Tela inicial (input, modo, sheets, executar, log)
├── tela_revisao.py  # Tela de revisão (tabela + painel de detalhe)
├── tema.qss         # Tema roxo/cinza (QSS)
├── worker.py        # PipelineWorker (QThread com cancelamento)
└── __init__.py
src/tdt/ui_main.py   # Entry-point
```

Entry-point: `python -m tdt.ui_main` ou comando `tdt-ui`.

## O que foi feito

### Tasks 1–11 (SP4 base)
1. **Diagnóstico**: contrato `Diagnostico` + scores por método no pipeline
2. **Cancelamento cooperativo**: `threading.Event` no `executar`
3. **Auditoria streaming**: `on_evento` callback conectado ao log da UI
4. **Dependências**: PySide6, tomli-w, pytest-qt + `config_io` TOML
5. **AppState**: dataclass mutável com config, paths, flags, aliases, resultado
6. **ModeloSinais**: 15 colunas (Sinal, Confiança, Status, Scores etc.)
7. **PipelineWorker**: QThread com log streaming, PARAR, erro
8. **TelaConfig**: formulário com paths, thresholds (pct/gap/topn), pesos (tfidf/vetorial/fuzzy), modelo/k
9. **TelaInicial**: input/output buttons, modo, flags, sheets checkboxes, EXECUTAR/PARAR, log
10. **TelaRevisao**: QTableView + painel de detalhe + busca ADMS + gerar TDT
11. **MainWindow + tema**: QStackedWidget, tema QSS roxo/cinza

### Correções de Usabilidade (8 issues)

| # | Problema | Solução | Arquivos |
|---|----------|---------|----------|
| 1 | TelaInicial não atualiza após salvar config | `recarregar()` lê paths do estado; MainWindow chama ao voltar | `tela_inicial.py`, `app.py` |
| 2 | Log vazio ao executar | Pipeline emite progresso (por sheet, a cada 50 sinais) + warnings | `pipeline.py`, `worker.py` |
| 3 | Círculo do QRadioButton invisível | `QRadioButton::indicator` no QSS (14x14, fill roxo) | `tema.qss` |
| 4 | Sheets não renomeáveis | `ItemIsEditable` + aliases salvos em AppState; usados no TDT | `tela_inicial.py`, `estado.py`, `pipeline.py` |
| 5 | Check mark do QCheckBox invisível | `QCheckBox::indicator` no QSS | `tema.qss` |
| 6 | Spin buttons pequenos/colados | QSS 20x14px + padding-right:24px; form spacing 6px | `tema.qss`, `tela_config.py` |
| 7 | Spin boxes muito largos | `setFixedWidth(120)` | `tela_config.py` |
| 8 | Placeholder Subestação/Input/Output | Subest: placeholderText sem item fake; I/O: QLineEdit read-only com placeholder | `tela_inicial.py` |

### Correção de Bug (transição revisão)

**Problema**: `_ir_para_revisao` usava `list.index(r)` dentro do loop de auto-approval —
O(n²) e podia lançar `ValueError` quando `definir_sigla` substituía o registro na lista.

**Solução**: `enumerate` no lugar de `index(r)`, `QApplication.processEvents()` a cada
100 iterações (UI responsiva), `try/except` com `QMessageBox.critical` em caso de erro.

**Worker**: `traceback.format_exc()` no lugar de `str(e)` — log exibe stacktrace completo.

### Eventos de Log Adicionados no Pipeline

- `[INFO] pipeline: iniciando processamento…`
- `[INFO] identificador: Sheet {nome}: {n} sinais lidos`
- `[INFO] pipeline: Sheet {nome}: {j}/{total} sinais processados` (a cada 50 + final)
- `[AVISO] pipeline: {id}: sem endereço — pulando`
- `[AVISO] pipeline: {n} sinais analógicos pulados (fora do escopo)`
- `[INFO] pipeline: decididos={n} revisão={n} analógicos_pulados={n}`

### Aliases de Sheet

- Sheets na lista ganham flag `ItemIsEditable` — duplo-clique para renomear
- Aliases salvos em `AppState.aliases: dict[str, str]` (sheet original → apelido)
- `pipeline.gerar_tdt()` aceita `aliases` opcional: aplica via `_aplicar_aliases()`
  substituindo `Modulo.nome` e prefixo do `id` antes do pareamento

## Arquivos Modificados (resumo)

| Arquivo | Mudanças |
|---------|----------|
| `src/tdt/pipeline.py` | Progresso + warnings no log; `aliases` em `gerar_tdt`; `_aplicar_aliases()` |
| `src/tdt/ui/app.py` | `_voltar_config` chama `recarregar`; `_ir_para_revisao` corrigido (enumerate, processEvents, try/except) |
| `src/tdt/ui/tela_inicial.py` | `recarregar()`; sheets editáveis + aliases; placeholder em Subest; I/O como QLineEdit |
| `src/tdt/ui/tela_config.py` | `setFixedWidth(120)`; `setVerticalSpacing(6)` |
| `src/tdt/ui/tela_revisao.py` | Passa `aliases` para `gerar_tdt` |
| `src/tdt/ui/estado.py` | Campo `aliases: dict[str, str]` |
| `src/tdt/ui/worker.py` | `traceback.format_exc()`; log inicial |
| `src/tdt/ui/tema.qss` | Indicadores Radio/Checkbox; spin buttons |
| `AGENTS.md` | Atualizado (SP4 implementado; UI stack; entry-point) |
| `src/tdt/AGENTS.md` | Atualizado (SP4; aliases; UI contratos) |
| `docs/AGENTS.md` | Atualizado (novas specs) |

## Testes

- **140/140 testes passando** (`python -m pytest -q`)
- Cobertura: pipeline (executar, cancelamento, gerar_tdt), UI (telas, worker, modelo, config_io)
- UI usa pytest-qt com worker injetável (`worker_factory`) para testar sem thread real
