# SP Metadados da Lista Padrão na Decisão + ALIAS da v1

**Data:** 2026-07-08
**Status:** Implementado parcialmente (2026-07-08) — §1 (ALIAS v1) e §2 (loader `type_severidade`) mantidos; §3 (r8_direcao, r9_type_severidade) e §5 (corpus vetorial) implementados, gatearam abaixo do baseline (`gate_tdt_real`) e foram revertidos (ver `bench/resultados/spMET_baseline_gate.txt`); §4 (classe MODO) idem, revertido. Detalhe em `.superpowers/sdd/progress.md`.
**Origem:** Dois pontos levantados pelo usuário: (1) as colunas da lista padrão além da descrição (`SIGNAL TYPE`, `DIRECTION`, `TYPE SEVERIDADE`, `MM`) carregam informação discriminante que o matching hoje ignora ou usa parcialmente — mesmo quando descrições empatam, essas colunas diferem; (2) na TDT gerada, a coluna `Signal Alias` deve conter a descrição do sinal da **lista padrão v1** (a original), não a descrição bruta da lista do cliente.
**Escopo:** Regras estruturadas de desempate (direction, type severidade), ampliação do vocabulário de estados do MM, `TYPE SEVERIDADE` no corpus vetorial (embeddings apenas), e `Signal Alias` sourceado da v1. Abordagem C escolhida em brainstorm (regras + corpus vetorial, bench separado).
**Relacionada:** SP-G/SP-H (motor de regras, BM25), SP-E (semântica de estados D1–D5).

---

## Diagnóstico

### Estado atual do uso das colunas

| Coluna | Lida? | Usada na decisão? |
|---|---|---|
| `DESCRIÇÃO NOVA` | sim | corpus principal (BM25 + fuzzy + embeddings) |
| `DIRECTION` | sim | só no corpus enriquecido de embeddings (`pipeline._corpus_enriquecido`) |
| `MM` | sim | parcial: `classe_do_mm` em r7 (`motor_regras`) e filtro D2 (`semantica_estados`) |
| `SIGNAL TYPE` | sim | não discrimina scoring; só output (`RelayTrip`→proteção) e whitelist `SwitchStatus` |
| `TYPE SEVERIDADE` | **não** | — |

### Fatos levantados (dados reais)

- **v1 = v2** nas descrições (0 diferenças em 639 sinais discretos). **v6** tem 130 descrições enriquecidas com sufixos de matching ("– ATUADO, HABILITADA"). Pipeline usa v2 por default (`defaults.DEFAULT_LISTA`).
- `Signal Alias` hoje = `rec.descricoes.bruta` (descrição da lista do **cliente**) — `engine_tdt.py:172` e `:225`.
- `DIRECTION` (discretos): Read 623, ReadWrite 62, Write 7. Analógicos: coluna `DIREÇÃO DO FLUXO`, vazia nos dados.
- `TYPE SEVERIDADE` (discretos): 7 classes — PROT (305), FALHAS FCOM/VCA/VCC (141), ALARMES PREDIAIS/VF/GRUPO (70), FUNÇÕES/43/PARALELISMO (62), DEFEITOS (46), DJ (8), DJ BC/SEC (7).
- `classe_do_mm` cobre 95% dos MMs: 692 presentes, 35 sem classe. Gaps reais: par `MANUAL@AUTOMATICO` (25AM, 43AM) fora do `_LEXICO`; comandos puros (79_EXC/79_INC, estados `null@null`) — sem classe **correto**.
- Decisão do usuário: ALIAS vem da **v1 sem exceção**; basta o mapa sigla→descrição, não a lista inteira.

### Lição de histórico (gates)

Stemmer N6 e a hipótese R8 (sufixo EXC/INC) eram plausíveis e não ajudaram no bench — regra plausível ≠ regra que ajuda. Tudo desta spec nasce gateável e passa por `gate_tdt_real`.

---

## Proposta

### §1 — ALIAS da v1 (ponto 2)

- Mapa `sigla → descrição` carregado de `docs/Pontos Padrao ADMS_v1.xlsx` reusando `ListaPadraoADMS.carregar` (discretos + analógicos). Sem parser novo.
- `engine_tdt._valores` / `_valores_analog`: `"Signal Alias" = mapa[sigla]` quando o sinal tem sigla decidida e ela existe no mapa; caso contrário (Custom/sem sigla) mantém `rec.descricoes.bruta` (comportamento atual).
- Path da v1 vira `defaults.DEFAULT_LISTA_ALIAS`. Arquivo ausente → fallback ao comportamento atual + aviso na auditoria (nunca quebra a geração).
- O mapa é threadeado por `pipeline.gerar_tdt` até o engine (parâmetro opcional; `None` = comportamento atual, retrocompat).

### §2 — Loader

- `SinalPadrao` ganha campo `type_severidade: str | None`.
- Mapeamento: coluna `TYPE SEVERIDADE` no sheet `DiscreteSignals`; `None` no mapa dos analógicos (sheet não tem a coluna).

### §3 — Regras novas no `motor_regras`

Funções puras no registro `_REGRAS`, pesos novos em `config.pesos_regras` (calibráveis; peso 0 = regra desligada). Ambas exigem `ctx.lista_padrao`; ausente = no-op (mesmo contrato da r7).

**r8_direcao — assimétrica (comando exige escrita):**
- Se `rec.tipo_sinal.direcao` ∈ {`Output`, `InputOutput`}: candidato com `direction` ∈ {ReadWrite, Write} ganha boost; candidato Read puro é penalizado.
- Se `rec.tipo_sinal.direcao == "Input"`: **no-op**. Motivo: status de equipamento manobrável (ex. DJ) casa sigla ReadWrite legitimamente — o par comando+status é resolvido pelo `dc_pairer`; penalizar ReadWrite para inputs quebraria esse caminho.

**r9_type_severidade — pistas lexicais → classe do candidato (desempate fraco):**
- Léxico `pista no texto canônico → classe TYPE SEVERIDADE`, modelado como dado (mesmo padrão de `_PARES_OPOSTOS`):
  - TRIP / número ANSI de proteção / PROTECAO → `PROT`
  - FALHA + (FCOM|VCA|VCC|COMUNICACAO|TENSAO CA|TENSAO CC) → `FALHAS FCOM/VCA/VCC`
  - 43 / PARALELISMO / TRANSFERENCIA / habilitação de função → `FUNÇÕES/43/PARALELISMO`
  - DEFEITO → `DEFEITOS`
- Léxico definitivo construído na implementação a partir dos dados reais (`docs/Export_base_Full__27_fev_2026.xlsx` + sheet `Severidades` da lista padrão), não de intuição.
- Sem pista no texto OU pista ambígua (duas classes) → no-op. Casa → boost; diverge → penalidade. Peso **fraco** (ordem de grandeza de desempate, abaixo de `numero_protecao`): a regra desempata descrições parecidas, nunca decide sozinha.

### §4 — Vocabulário MM (`semantica_estados`)

- Auditar os 35 MMs sem classe; adicionar ao `_LEXICO` os pares de estado reais faltantes (confirmado: `MANUAL`/`AUTOMATICO` — classe a definir na auditoria, candidata: nova entrada na família de seleção de modo).
- Benefício em cascata: r7 e filtro D2 passam a cobrir esses sinais sem mudança de código neles.
- Comandos puros (estados `null@null`) permanecem sem classe — comportamento correto, não é gap.

### §5 — Corpus vetorial (parte "C")

- `pipeline._corpus_enriquecido` acrescenta `type_severidade` às `partes` (junto de `tipo_medicao`/`unidade`/`direction` existentes). **Só embeddings** — BM25/fuzzy intocados (corpus lexical limpo).
- Cache de scorers invalida sozinho (chave = corpus enriquecido).
- Medido em bench **separado** do §3: se regredir, reverte sem afetar as regras.

### §6 — Gates, testes e ordem de medição

- Bench `gate_tdt_real` é o juiz. Ordem: baseline → §4 (vocabulário MM) → §3 r8 → §3 r9 → §5 corpus. Cada passo medido isolado; o que regredir sai (peso 0 / revert) sem derrubar o resto.
- TDD: teste unitário por regra nova (casos: casa, diverge, sem evidência, sem lista_padrao), teste do loader (`type_severidade` lido, analógico None), teste do alias (sigla no mapa, Custom fallback, arquivo ausente).
- §1 (ALIAS) não passa por bench — não afeta matching, só output; validado por teste de geração.

---

## Riscos

| Risco | Mitigação |
|---|---|
| r9 com léxico ambíguo gera falsos desempates | peso fraco + no-op em ambiguidade + gate no bench |
| r8 penalizar ReadWrite p/ status quebraria dc_pairer | regra assimétrica: no-op para `Input` |
| §5 poluir embeddings (lição N6) | bench separado, revert isolado |
| v1 divergir da lista carregada no futuro (v7+) | ALIAS não depende da lista carregada; fonte fixa v1 |

## Fora de escopo

- `SEVERIDADE` (Severidade 2–8) na decisão ou no output TDT — sem uso identificado agora.
- `CONTROL CODE`, colunas de contexto (LINHA/BARRA/TRANSFORMADOR/...) — nada consumindo.
- Refinar `Measurement Type` por signal_type (ponytail existente em `engine_tdt.py:173`) — outro tema.
- Enriquecimento lexical BM25/fuzzy (abordagem B) — rejeitada no brainstorm.

## Critérios de sucesso

1. `gate_tdt_real` ≥ baseline após cada passo mantido; nenhum passo com regressão permanece ligado.
2. TDT gerada com lista v6 carregada exibe `Signal Alias` = descrição v1 (sem sufixos "–").
3. Cobertura `classe_do_mm`: todo MM com par de estados real ganha classe; sem classe restam apenas comandos puros (`null@null`) e customizações sem par de estado (contagem exata sai da auditoria do §4).
4. Testes unitários novos passando; suíte existente intacta.
