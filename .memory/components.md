# Componentes

## UI — tabela de revisão (SP4, `src/tdt/ui/`)

Campos editáveis (2026-07-01): Sinal (pré-existente) + Tipo, Fase, Nível Tensão, Barra, Tipo Equip., Módulo, Escala. Domínio fechado (Tipo/Fase/Nível Tensão/Barra/Tipo Equip.) via `DelegateCombo`; Módulo via `DelegateModulo` (combo editável, sugere nomes já presentes nos registros); Escala usa editor padrão (numérico livre).

**Contrato:** editar os 7 campos de domínio NÃO promove `status` pra `"decidido"` (só editar Sinal promove — via `definir_sigla`). Nenhum snapshot de undo nos 7 setters novos (mesma lacuna que `definir_sigla` já tinha). Editar Tipo Equip. zera `equipamento_inferido`; editar Tipo marca `categoria_confiavel=True`. Domínio de Tipo exclui `DiscreteAnalog` (placeholder de incerteza do dual-pass, não é alvo de edição manual).

**Armadilha corrigida:** delegates de combo (`DelegateCombo`/`DelegateModulo`) precisam implementar `setEditorData` pra pré-selecionar o valor atual da célula — sem isso, o combo sempre abre no índice 0 e confirmar sem editar reescreve o campo silenciosamente. Sentinela de exibição `"—"` (vazio) mapeia pra opção `""` no combo.

Spec: `docs/superpowers/specs/2026-07-01-sp-campos-editaveis-revisao-design.md`. Plano: `docs/superpowers/plans/2026-07-01-campos-editaveis-revisao.md`.
