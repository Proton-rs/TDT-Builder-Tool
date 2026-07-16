# Fluxo de dados do pipeline — quem lê, escreve e sobrescreve identidade

Identidade = `sigla_sinal`, `modulo.nome`, `eletrico.nome_equipamento`,
`enderecamento.indices`. Invariantes I1–I4 na spec
`docs/superpowers/specs/2026-07-16-sp-fluxo-dados-transparente-design.md`.

| Etapa | Lê | Escreve | Sobrescreve/descarta | Como é auditado |
|---|---|---|---|---|
| normalização N0–N5 (`normalizador.canonizar`) | descrição bruta | `descricoes.normalizada`, `eletrico.*` (N0) | descarta ruído do texto (EXCEÇÃO da regra) | `descricoes.bruta` sempre preservada |
| `analise_colunas.analisar` | rows | `MapaColunas` | — | — |
| `estruturador.estruturar` | rows + mapa | `SignalRecord` completo (sigla, módulo, equipamento, endereços, tipo) | — | I2: módulo/sigla/equipamento em ramos INDEPENDENTES (regressão LVA AL21) |
| `identidade_modulo.aplicar_identidade` | sinais + rows | `modulo.nome`, confiança | saneia módulo fora do padrão p/ dominante da sheet | aviso `identidade_modulo` + `aud.sobrescritas()` (Task 3) |
| `inferencia_topologia.subdividir_transformador_at_bt` | sinais | `modulo.nome` (+sufixo AT/BT) | renomeia módulo | `aud.sobrescritas()` (Task 3) |
| `inferencia_topologia.inferir_equipamento` | sinais | `eletrico.equipamento_alvo` | — | flag `equipamento_inferido` |
| `inferencia_topologia.atribuir_id_por_registro` | sinais | `eletrico.nome_equipamento` (só None→valor) | nunca sobrescreve | aviso `registro_equipamentos` p/ ambíguo |
| scoring/roteador (`_classificar_roteado`) | descrições | `sigla_sinal`, `candidatos`, `status` | — | `diagnostico`/candidatos |
| `normalizador_estrutural.fundir_pares_posicao` | decididos | `indices` (a+b), datatype MultiCoord | absorve o id do segundo registro | `aud.sobrescritas()` (Task 3) + conservação por contagem |
| `dc_pairer.parear` | decididos | `indices_saida`; re-chaveia sigla de posição divergente | absorve o id do comando na fusão (upgrade path na docstring de `dc_pairer.separar`) | `aud.sobrescritas()` (Task 3) + conservação por contagem |
| `normalizador_estrutural.corrigir` | pareados | — | particiona duplicata/sem-endereço p/ revisão | `ItemRevisao` |
| `criador_lista_homogenea.montar` + `engine_tdt.particionar_*` | lista | nomes de saída | move grupos p/ revisão | eventos `engine` |
| UI (`AppState`) | registros | edições do usuário | NUNCA reverte edição sem comando explícito (bug aprovar 16/07, 16645f4) | `_snapshot()`/desfazer |

## Lacunas conhecidas (follow-ups, fora deste plano)

- Coluna EQUIPAMENTO dedicada (LVA) não é detectada por `analise_colunas` —
  hoje só a varredura de linha inteira pega IDs da whitelist nela.
- Id do comando é perdido na fusão D+C (rastreável só por endereço) —
  upgrade path documentado em `dc_pairer.separar`.
