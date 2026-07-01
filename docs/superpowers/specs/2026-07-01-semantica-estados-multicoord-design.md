# Spec: Semântica de estados + MultiCoord + comando×discreto (SP-E)

Data: 2026-07-01. Status: aprovada pelo usuário (rodadas de perguntas 1–3).
Origem: comparação `output/LISTA 1 - GTD/TDT.xlsx` × `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`
× `docs/Export_base_Full__27_fev_2026.xlsx` (237.726 sinais DNP3 discretos).

## 1. Problema (medido)

| Métrica (DNP3_DiscreteSignals) | Gerado | Real GTD |
|---|---|---|
| Sinais | 792 | 1641 |
| SingleBit / MultiCoord / DoubleBit | 703 / **0** / 89 | 1595 / 44 / 2 |
| Double-bit comprovadamente falso | **39** | — |
| Read / ReadWrite / Write | 678 / 41 / **73** | 1396 / 243 / 2 |

Quatro defeitos encadeados:

1. **Colapso filho-vs-pai no matching**: "SGF **Atuado**" casa `SGF` (Enabled,
   incluído/excluído) em vez de `SGFT` (RelayTrip, "TRIP SGF"). A descrição da
   LP v6 de SGF ("FUNCAO SGF — EXCLUIDA, **ATUADO**, SENSIVEL") contém o estado
   do irmão. Mesmo padrão: SF6A/SF6B→SF6, 71TH/71TL→71T, 61_1/61_2→61N,
   BBA1/BBA2→(verbo), VF+FVF→VF, CAAQ pátio/sala. A LP **tem** todas as
   siglas-irmãs; o texto sozinho não discrimina.
2. **Fusão estrutural ingênua**: `normalizador_estrutural.corrigir` funde
   QUALQUER par mesma-(módulo,equip,sigla) com endereços consecutivos em
   "double-bit". SGF@1534 + SGFT-mal-classificado@1535 → DoubleBit falso 1534;1535.
3. **Datatype errado**: o real usa `MultiCoord` para o par de posição fundido
   (DJF1 `1500;1501`, SEC*) e `DoubleBit` SÓ para CDC AUMENTAR/DIMINUIR (Write,
   sem input). O engine só conhece SingleBit/DoubleBit.
4. **Comando órfão silencioso**: 73 comandos saem `Write` (real: 2, só CDC).
   Regra de domínio: **todo comando tem um discreto de status** (vira ReadWrite).

Defeito auxiliar: N3 `remover_boilerplate` dropa o token "SECCIONADORA" líder;
os scorers de texto não veem o tipo de equipamento ("Secc. 29-1 (01Q4 Terra) -
Libera Manobra" → tokens `TERRA LIBERA MANOBRA`).

## 2. Regras de domínio confirmadas pelo usuário

- **Estado detectado no texto restringe o candidato (filtro DURO)**:

  | Par de estados (base full) | Classe | Compatível com |
  |---|---|---|
  | NORMAL@ATUADO (108k) | trip | RelayTrip e Custom com par `NORMAL@ATUADO` |
  | INCLUIDO@EXCLUIDO (27,8k) | função | Enabled / ReclosingEnabled / Local com par `INCLUIDO@EXCLUIDO` |
  | ABERTO@FECHADO, DESLIGADO@LIGADO | posição | SwitchStatus |
  | DESATIVADO@ATIVADO, DESABILITADO@HABILITADO | ativação | Custom com par correspondente |
  | REMOTO@LOCAL | local/remoto | Local / Custom com par `REMOTO@LOCAL` |
  | NORMAL@{FALHA,DEFEITO,FALTA}, BLOQUEADA@LIBERADA etc. | alarme | Custom com par correspondente |

  A referência de compatibilidade do candidato é o **par de estados do MM da LP**
  (`mm.split("___")[1]`), não o signal_type sozinho (trips Custom existem, ex. 79_1).
- **Fusão de 2 pontos → `MultiCoord`, sempre.** `DoubleBit` só quando o INPUT
  já traz endereço duplo numa linha (ex. IMA `D SECC addr=1100;1101`) ou CDC
  raise/lower. DoubleBit nativo permanece DoubleBit.
- **Fusão só para posição**: whitelist de siglas fundíveis (derivada da LP:
  signal_type `SwitchStatus`; extensível por config) **e** estados de posição
  opostos nas duas linhas **e** endereços consecutivos. Incluído/excluído,
  atuado, local/remoto: NUNCA fundem.
- **Par complementar LOCAL/REMOTO (43LR)**: gera 1 ponto single-bit usando o
  bit **Local**; o outro é descartado com registro (`descartado_redundante`).
- **Estado "Indefinido/Indefinida"** de equipamento de posição: nunca vira
  ponto (é o transit do MultiCoord); descarte com registro.
- **Comando órfão → revisão** (`comando_sem_discreto`). Exceção: CDC
  (AUMENTAR/DIMINUIR) é Write legítimo, não tem input.
- **Comando D → OUTCOORDS `N;N`; Comando S → OUTCOORDS `N`** (coluna
  "Comando D"/"Comando S" do input GTD; conferido no real: SGF out=`1502;1502`,
  81U1 out=`1504`).
- **LIBM** (Libera Manobra): casa normalmente, mas sai como **revisão**
  (decisão por projeto — o real GTD descartou; a base tem 36).
- Sinais de seccionadora são poucos: whitelist observada na base full (34
  siglas: SECF/SECC/SECG/SECB/SECT MultiCoord; DSEC, 43LR, CC*, FSEC, OI,
  LIBM, BSEC, MANI… single-bit Read).

## 3. Design — 6 mudanças

### D1. `semantica_estados.py` (novo módulo, ~80 loc)
Função pura `detectar_estado(descricao_normalizada) -> ClasseEstado | None`
com léxico dos pares acima (prefixos robustos a gênero: ATUAD*, EXCLUID*,
INCLUID*, ABERT*, FECHAD*, LIGAD*, DESLIGAD*, ATIVAD*, DESATIVAD*, HABILITAD*,
LOCAL, REMOT*, BLOQUEAD*, LIBERAD*, INDEFINID*, FALHA, DEFEITO, FALTA).
Segunda função `classe_do_mm(mm: str) -> ClasseEstado | None` (parse do par de
estados do MM da LP). Tabela de compatibilidade classe×classe.

### D2. Filtro duro no pipeline de matching
Após gerar candidatos e antes do scoring final: elimina candidato cuja
`classe_do_mm` é incompatível com o estado detectado no input. Sem estado
detectado → filtro não age. Filtro zera candidatos → item vai a revisão
(`estado_sem_candidato`). Gateado por config (`filtro_semantica_estados`,
default ON).

### D3. Fusão restrita + MultiCoord (`normalizador_estrutural.py`)
Substitui a regra "consecutivo mesma-sigla" por: funde apenas se sigla ∈
whitelist de posição (LP SwitchStatus + config) **e** `detectar_estado` das
duas linhas devolve estados de posição opostos **e** endereços consecutivos.
Resultado: `datatype=MultiCoord`. Também: descarte registrado de estado
Indefinido e do bit complementar de LOCAL/REMOTO (fica o bit Local). Par
consecutivo que NÃO se encaixa na whitelist/estados segue como 2 sinais
single-bit independentes; duplicata de MESMO endereço continua revisão
`endereco_duplicado`.

### D4. Contracts + engine
`TipoSinal.is_double_bit: bool` → `TipoSinal.datatype: "SingleBit" | "DoubleBit"
| "MultiCoord"` (5 usos hoje). Engine emite o valor direto em Input Data Type.
DoubleBit nativo: linhas do input com 2 índices distintos numa linha só (`N;M`,
M≠N) continuam DoubleBit. OUTCOORDS: comando D → `N;N`, comando S → `N`
(capturar tipo de comando do input; estruturador ganha o campo).

### D5. Comando×discreto (`dc_pairer.py`)
- Órfão: `Output` sem par → revisão `comando_sem_discreto`; exceção CDC
  (TapIncrement) permanece Write.
- Pareamento semântico: comando com verbo de função (incluir/excluir,
  habilitar/desabilitar, ativar/desativar) só casa status de classe
  função/ativação — nunca trip. Reduz casamento errado no catch-all N×M.
- Comando herda sigla do discreto (regra já vigente, mantida).

### D6. Restrição de candidatos por equipamento
Quando `eletrico.equipamento_alvo == "Seccionadora"`: candidatos restritos à
whitelist de siglas de seccionadora (config, semente = 34 siglas medidas na
base). Idem preparado para Disjuntor (whitelist maior, 353 — aplicar só se
medição mostrar ganho; default OFF para DJ). Resolve a perda do token
"SECCIONADORA" (N3 intocado). LIBM decidido → rebaixa para revisão
(`decisao_por_projeto`).

## 4. Validação / aceite

1. Regerar LISTA 1 - GTD e comparar com o real (script de comparação vira
   `scripts/diag_estrutura_gtd.py` reutilizável):
   - double-bit falso: 39 → **0**
   - MultiCoord: 0 → ≈44 (DJF1/SEC*/EST do real)
   - `GTD_*_SGFT` presente; SGF single-bit RW; SF6A/SF6B, 71TH/71TL, 61_1/61_2,
     BBA1/BBA2 separados
   - Write: 73 → ≈0 não-CDC (órfãos em revisão com motivo)
2. Benchmark combo (calib-minmax): decididos/acc@1/prec@dec sem regressão.
3. Testes unitários novos: semantica_estados (léxico + compatibilidade),
   fusão restrita (SGF+SGFT NÃO funde; DJF1 par funde → MultiCoord; nativo
   N;M preservado), dc_pairer órfão→revisão + exceção CDC, OUTCOORDS D/S.

## 5. Fora de escopo (specs próprias)

- Prefixo de relé P_/A_ (proteção principal/alternada dos módulos LT).
- Equipamento no nome via topologia do vão (GTD_AL11_**52-11**_SGF) — spec C.
- Cobertura geral de matching / desambiguação por qualificador — spec D eixo 1.
- Edição da LP (descrição poluída de SGF): o filtro D2 torna desnecessária.

## 6. Referências

- Real GTD: `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx` (AL11 e LTGTA como
  vãos de referência; SGF 1534 + SGFT 1535; DJF1 1500;1501 out 1500;1500).
- Base full: pares de estado × datatype e siglas por equipamento medidos em
  2026-07-01 (scripts de diagnóstico da sessão; ver §2).
- Código: `src/tdt/normalizador_estrutural.py`, `src/tdt/dc_pairer.py`,
  `src/tdt/engine_tdt.py:184`, `src/tdt/normalizacao/normalizador.py:305` (N3),
  `src/tdt/dados/lista_padrao.py` (campo `mm`).
