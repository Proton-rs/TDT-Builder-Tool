# SP Ajustes 20JUL — Device Mapping, Catálogo de Proteção, Datatype e Revisão

**Data:** 2026-07-20
**Status:** Proposto
**Origem:** `docs/anot.txt` (8 observações do usuário, 20/07) + análise do export fullbase real (`docs/Export_base_Full__27_fev_2026.xlsx`, 237.726 sinais discretos + 132.744 analógicos DNP3).
**Escopo:** 4 blocos — A) device mapping (sufixo de equipamento + disjuntor no ramo PROT de alimentador); B) catálogo/regras (flag `dm_prot` por sigla, aviso 43LR sem 43TC, gate de tipo duplicado por dispositivo); C) datatype (2 índices → MultiCoord); D) revisão UI (colunas) + bug do aviso de endereço duplicado.
**Relacionada:** [2026-07-08-sp-unificado-pendencias.md](../plans/2026-07-08-sp-unificado-pendencias.md) (mesmo formato de spec unificada de pendências).

---

## Diagnóstico (evidência da fullbase)

Análise executada sobre `DNP3_DiscreteSignals` (237.726 linhas) e `DNP3_AnalogSignals` (132.744 linhas), separando nomes estilo-SE (`^[A-Z]{2,5}_`) dos religadores de rede (nomes numéricos):

1. **Device mapping de equipamento termina com abreviação da família.** Últimos segmentos dominantes: discretos `DJ` 16.866, `TR` 4.610, `SEC` 2.157; analógicos `DJ` 4.570, `TC` 2.839, `TP` 710, `TR` 482. Hoje o engine emite o equipamento sem sufixo (`SE_MOD_52-1`).
2. **Ramo PROT de alimentador usa o disjuntor no lugar do 2º módulo.** Padrão `SE/AL*/52-x/PROT_<sigla>` com >7.000 ocorrências (ex.: `CNC_AL11_52-22_PROT_51F`). O equipamento entra SEM sufixo no ramo PROT; módulos não-alimentador mantêm módulo duplicado (`CNC_TR1BT_TR1BT_P_...`). Hoje o engine duplica o módulo sempre.
3. **`dm_prot` é por sigla, não por Signal Type.** `RelayTrip` é 99% PROT, mas `Enabled` é 87% e `RecloserLockout` 84% (religadores numéricos). Por sigla (estilo-SE): 50\*/51\*/59\*/27\*/46/61/67\*/21\*/25AT-FT-VT-IE/81-81SU-81SO-81E\*/87\*/5F\*-5N-5BKP/62BF/SGF-SGFT-SGT2/FA-FB-FC/LDF/PB → 96-100% PROT. Família 79 (79/79_1/79LO/79OK/79RE): 2.979 sinais, 98,7% → DJ, **zero** `PROT_79` em subestação (único `PROT_7933` da base é religador nº 7933). 43LR/43TC, 86, 63\*, 71\*, 81U1-U5, DJF1, MOLA → 0% PROT.
4. **2649 → PROT (decisão do usuário 20/07).** Linhas consistentes (ECA) mapeiam `..._PROT_2649`; as que caem no DJ são linhas sujas (SE do sinal ≠ SE do DM). Na lista padrão 2649 está como `Enabled` — é o caso-modelo do complemento.
5. **MultiCoord ⇔ duas coordenadas separadas por `;`.** `MultiCoord` com `;`: 9.449; `DoubleBit` com `;`: **zero** (4.862 sem). Confirma a regra do usuário.
6. **43LR/43TC:** ambos 0% PROT; caem no DJ/SEC. Historicamente ambos `Local` (43LR 7.246 Local × 892 Custom); catálogo v8 do usuário já mudou 43LR→Custom, 43TC→Local para evitar dois `Local` no mesmo dispositivo.
7. **Lista padrão documenta proteção via `SIGNAL TYPE = RelayTrip`** (211 de 692 siglas discretas). Instrução do usuário: **preservar o que está documentado; só adicionar** siglas ainda não marcadas (como 2649).

---

## Bloco A — Device Mapping (`src/tdt/engine_tdt.py`)

### A1. Sufixo de família no equipamento (não-proteção, discretos)

`_device_mapping()` ramo não-proteção: quando o DM cai em equipamento, acrescenta sufixo da família via `familia_do_id(nome_equipamento)`:

| Família | Sufixo |
|---|---|
| Disjuntor | `_DJ` |
| Seccionadora | `_SEC` |
| Transformador | `_TR` |
| Trafo de corrente | `_TC` |
| Trafo de tensão | `_TP` |

`SE_MOD_52-1` → `SE_MOD_52-1_DJ`. Família fora das 5 → sem sufixo (comportamento atual). Sem equipamento → fallback módulo-duplicado inalterado.

### A2. Disjuntor no ramo PROT de alimentador

`_device_mapping()` ramo proteção: se o módulo é alimentador (`_eh_alimentador`, já existe) e o módulo tem disjuntor único (`_disjuntor_por_modulo`, reuso do caminho analógico), o 2º módulo é substituído pelo nome do disjuntor **sem sufixo**:

- Alimentador: `CVA_AL11_AL11_PROT_CAFL` → `CVA_AL11_52-1_PROT_CAFL`
- Outros módulos: `CVA_TR1BT_TR1BT_PROT_X` (inalterado)
- Alimentador sem disjuntor único → fallback módulo-duplicado (inalterado; aviso de ambiguidade já existe no pipeline)

### A3. Sufixo `_DJ` no ramo disjuntor analógico

`_device_mapping_analog()`: `alvo = disjuntor` → `alvo = f"{disjuntor}_DJ"`. Ramos TC/TP já corretos (`<MOD>_TC`, `<MOD>_TP`).

---

## Bloco B — Catálogo e regras

### B1. Flag `dm_prot` por sigla (substitui `eh_prot = signal_type == "RelayTrip"`)

```
dm_prot(sigla, sp) = (sp.signal_type == "RelayTrip")          # lista padrão manda (inalterado)
                     or sigla in COMPLEMENTO_DM_PROT           # defaults.py
```

- **Fonte primária:** lista padrão. Tudo que está `RelayTrip` continua PROT — inclusive `TRIP` (fullbase diverge, mas instrução do usuário: não mexer no documentado).
- **Complemento (`COMPLEMENTO_DM_PROT` em `defaults.py`):** siglas presentes na lista padrão com SIGNAL TYPE ≠ RelayTrip cujo mapeamento na fullbase (nomes estilo-SE) seja ≥90% PROT com n≥20. Confirmado: `2649`. Candidatos a validar na implementação: `27`, `59`, `61` (Enabled na lista, 86-99% PROT na fullbase). Família 79, 43\*, 86, 63\*, 71\*, 81U\* ficam FORA (0-16% PROT).
- Nome `dm_prot` (não `eh_protecao`): o flag controla o **ramo do device mapping**, não o conceito ANSI de função de proteção (79 é função de proteção e mesmo assim cai no DJ).

### B2. Aviso 43LR sem 43TC

Dispositivo (mesmo alvo de DM) que tem `43LR` e não tem `43TC` → aviso "dispositivo sem sinal Local (43TC)" — nível aviso (tela de geração + evento de auditoria), não remove da TDT. Com ambos presentes, nada: catálogo v8 (43LR=Custom, 43TC=Local) já resolve o conflito.

### B3. Gate `particionar_tipo_duplicado`

Novo particionador no pipeline, junto de `particionar_custom_id_duplicado` / `particionar_endereco_duplicado`:

- Chave: `(device_mapping_final, signal_type)` com `signal_type != "Custom"`; registros sem sigla no catálogo (Signal Type Custom implícito) são isentos.
- Grupo com >1 → todos saem da TDT para revisão com motivo `tipo_duplicado_dispositivo` (mesmo padrão do custom_id: nunca sai calado no xlsx).
- Sinais em dispositivos PROT distintos têm DMs distintos — não colidem entre si (é o que permite repetido dentro de proteção).
- Depende do DM final (Bloco A) — ordem: A antes de B3.

---

## Bloco C — Datatype (item 4)

`estruturador.py` e `estruturador_homogeneo.py`: célula de endereço com 2 índices distintos → `MultiCoord` (hoje marca `DoubleBit`, contradizendo a fullbase: DoubleBit nunca tem `;`).

- `DoubleBit` permanece no domínio (`contracts.py`) reservado a ponto nativo de 1 endereço — hoje nenhuma origem o produz.
- Pré-requisito: mapear TODOS os consumidores de `"DoubleBit"` (fusão no `normalizador_estrutural`, `dc_pairer`, `engine_tdt`, `mescla`, UI) e garantir que o fluxo MultiCoord preserva o comportamento (regra de não-regressão do CLAUDE.md).

---

## Bloco D — Revisão UI e bug de avisos

### D1. Colunas da tabela de revisão (`ui/modelo_tabela.py`)

| Ação | Coluna | Nota |
|---|---|---|
| Adicionar | `Signal Name` | nome hierárquico que sai na TDT; derivada, read-only |
| Adicionar | `Device Mapping` | DM final (Bloco A); derivada, read-only |
| Adicionar | `Signal Type` | do catálogo ADMS; derivada, read-only |
| Renomear | `Sinal` → `Sigla` | desambigua do novo Signal Name |
| Renomear | `Descr. ADMS` → `Descr. lista padrão` | nome que reflete a fonte |
| Cortar | `Tokens`, `Descr. normalizada` | debug interno; o xlsx de auditoria já as tem |

Derivadas reusam as funções do engine (expor helper público; não duplicar lógica de DM na UI). Colunas derivadas recalculam quando o usuário edita sigla/módulo/equipamento.

### D2. Bug: aviso de endereço duplicado sem duplicata real

Sintoma (usuário): aviso aparece sem endereço repetido; hipótese dele: comparação cruzada input×output. Verificado no código: `particionar_endereco_duplicado` já separa espaços in/out. Duas hipóteses de raiz mapeadas:

1. **Módulo `None`/`""` agrupando tudo:** `enderecos_duplicados` (`ui/tela_geracao.py:24`) e o particionador usam `rec.modulo.nome` na chave; registros sem módulo caem todos na mesma chave e colidem entre sheets distintas.
2. **Espaço out: pareado × comando não-mesclado:** registro pareado contribui `indices_saida` no espaço "out"; se o DCpairer não mesclou o comando standalone (obs. anterior do usuário: DJF1 do 24-1 sem pareamento), os dois colidem no mesmo índice de escrita.

Método: systematic-debugging com lista real (GAU/SMF em `docs/`), reproduzir o aviso, confirmar hipótese, fix na raiz + teste de regressão com o caso real reduzido.

---

## Não-regressão e verificação (gate de closeout)

- Suíte completa + `python -m bench.regressao` + comparação de comportamento com as listas reais já suportadas (SAN2, CVA, LVA, GAU, GTD) — regra universal do CLAUDE.md.
- **Diff esperado e intencional:** Bloco A muda Device Mappings (sufixos + disjuntor em AL); Bloco C muda `Input Data Type` de pares fundidos (DoubleBit→MultiCoord). Golden files/fixtures que travem esses campos são atualizados com o diff documentado no PR.
- `Remote Point Custom ID` deriva do nome hierárquico, NÃO do DM — conferir que Bloco A não altera Custom IDs (senão colide com gate de unicidade).
- B3 roda depois do Bloco A (DM final) — validar ordem no pipeline.

## Fora de escopo

- Itens do `docs/observações_pendentes.txt` não citados em `anot.txt` (drag de colunas, undo/redo, ações em massa, sufixo numérico de arquivo, herança de equipamento por topologia de módulo etc.).
- Sufixos além das 5 famílias (RET, REG, COMTAP, BP observados na fullbase) — comportamento atual preservado.
- Scoring/matching (pesos, candidatos) — intocado.
