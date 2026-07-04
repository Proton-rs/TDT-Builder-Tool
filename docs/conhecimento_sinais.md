# Base de conhecimento de sinais — Lista Padrão ADMS

Documento gerado automaticamente por `bench/minerar_lp_conhecimento.py` a partir de `docs/Pontos Padrao ADMS_v2.xlsx` (sheets `DiscreteSignals`, `AnalogSignals`, `DE->PARA`, `Message Mapping`).

Agrupamento por família reusa `tdt.motor_regras._numero_lider` (prefixo ANSI de 2 dígitos, ex.: `67N` -> `67`). Siglas sem prefixo ANSI numérico são agrupadas por prefixo alfabético de 2 letras (`ALPHA_xx`); o restante cai em **Outras / Não classificadas** — nenhuma sigla é descartada.

Este é o **esqueleto** (Task 1 do plano SP-L): dados minerados diretamente da LP, sem curadoria de conteúdo além de formatação. Task 2 (este commit) adiciona nomenclatura real observada em TDT de campo + regras de domínio já provadas em specs do projeto. Task 3 adiciona cross-references adicionais.

---

## Regras do projeto (provadas em specs anteriores)

Regras de domínio abaixo são **decisões travadas** — confirmadas em produção/diagnóstico real e citadas aqui só como resumo com ponteiro para a spec de origem (o compilado não copia o design por extenso, ver princípio do plano SP-L). Aplicam-se transversalmente a várias famílias; onde uma regra é específica de uma família ela também é referenciada na seção correspondente.

1. **Fusão D+C: comando = output = mesmo sinal físico, status = input** — comando e status do mesmo equipamento/função fundem num único ponto `ReadWrite` (`INCOORDS` do status + `OUTCOORDS` do comando). Confirmado no TDT real: 243 pontos `ReadWrite` (ver `Direction` acima). Fonte: [`2026-06-30-spA-pareamento-fusao-dc-design.md`](superpowers/specs/2026-06-30-spA-pareamento-fusao-dc-design.md).
2. **Sigla que persiste na fusão é a da Lista Padrão (a do status), nunca o verbo de comando** — `LIGAR`/`DESLIGAR`/`ABRIR`/`FECHAR`/`CMD`/`INCLUIR`/`EXCLUIR` nunca sobrevivem como sigla decidida; o comando herda a sigla padrão do status do mesmo `(módulo, equipamento)`. Fonte: [`2026-06-30-spA-pareamento-fusao-dc-design.md`](superpowers/specs/2026-06-30-spA-pareamento-fusao-dc-design.md).
3. **Não existe comando para sinal analógico** — a fusão D+C é exclusivamente discreto+discreto; medições (`IA`, `VAB`, `P`, `Q`, ...) nunca têm par de comando. Fonte: [`2026-06-30-spA-pareamento-fusao-dc-design.md`](superpowers/specs/2026-06-30-spA-pareamento-fusao-dc-design.md).
4. **Sigla de coluna dedicada (lista já padronizada) tem prioridade sobre scoring por descrição** — quando o input não-homogêneo traz uma coluna própria de sigla (não uma "descrição" a interpretar), e a sigla é válida na Lista Padrão, o sinal é pré-classificado sem passar pelo scoring textual; validação cruzada contra o NOME padronizado (`{SE}_{MODULO}_{EQUIP}_{SIGLA}`) detecta inconsistência (`nome_sigla_inconsistente`). Evita o anti-padrão de tentar casar a sigla já certa contra a descrição genérica de outra família. Fonte: `docs/superpowers/specs/2026-06-30-sp-sigla-nao-homogeneo-design.md` e plano irmão `docs/superpowers/plans/2026-06-30-sp-sigla-nao-homogeneo.md` (à data deste commit, ainda não integrados neste branch — existem como trabalho em andamento no worktree principal do repo; motivadores: `docs/SAN2_LISTA_PADRONIZADA_PARA_TESTE.xlsx`).
5. **DJF1/DJA1: par ligado/desligado do mesmo disjuntor converge para a sigla de posição, mesmo com descrição genérica** — a Lista Padrão descreve `DJF1` apenas como "DISJUNTOR NF" (sem termo de estado); quando o input não-homogêneo traz duas linhas separadas (`Desligado`/`Ligado`) do mesmo equipamento, elas não devem ser tratadas como sinais distintos — pareiam pela sigla de posição do equipamento (`Disjuntor` → `DJF1`) antes do scoring de texto, como rede de segurança independente da qualidade da descrição padrão. Fonte: [`2026-06-24-sp10-djf1-pareamento-polaridade-design.md`](superpowers/specs/2026-06-24-sp10-djf1-pareamento-polaridade-design.md).
6. **Semântica de estados restringe candidatos (filtro duro)** — o par de estados detectado no texto de entrada (ex. `NORMAL@ATUADO`, `INCLUIDO@EXCLUIDO`, `ABERTO@FECHADO`/`DESLIGADO@LIGADO`, `DESATIVADO@ATIVADO`, `REMOTO@LOCAL`) deve ser compatível com o par de estados do Message Mapping da sigla candidata (coluna "Estados / MM" desta doc) — candidato incompatível é eliminado antes do scoring final. Sem estado detectado, o filtro não age. Fonte: [`2026-07-01-semantica-estados-multicoord-design.md`](superpowers/specs/2026-07-01-semantica-estados-multicoord-design.md).
7. **Fusão de par posição → `MultiCoord`, nunca "DoubleBit" ingênuo** — dois pontos (status aberto + status fechado) do mesmo equipamento de posição fundem em `MultiCoord` (endereço duplo consecutivo), não em `DoubleBit`; `DoubleBit` só quando o próprio input já traz endereço duplo numa linha (nativo) ou para comando CDC (aumentar/diminuir). Confirmado no TDT real: 44 `MultiCoord` vs. apenas 2 `DoubleBit` (CDC). Fonte: [`2026-07-01-semantica-estados-multicoord-design.md`](superpowers/specs/2026-07-01-semantica-estados-multicoord-design.md).
8. **Todo comando tem, por regra, um discreto de status correspondente** — comando sem par de status vira revisão (`comando_sem_discreto`), exceto exceções whitelistadas (`config.siglas_write_legitimo`, ver regra 9). Fonte: [`2026-07-01-semantica-estados-multicoord-design.md`](superpowers/specs/2026-07-01-semantica-estados-multicoord-design.md) (D5) e [`2026-07-02-spH-camada-decisao-design.md`](superpowers/specs/2026-07-02-spH-camada-decisao-design.md).
9. **Whitelist de siglas "write legítimo" (sem discreto de status por natureza)** — `config.siglas_write_legitimo` (`src/tdt/config.py`) cresceu de `{"CDC"}` para `{"CDC", "AUTC", "PB", "CMD"}` nesta sessão (SP-I Task 2): `CDC` é comutador (aumentar/diminuir, sem input); `AUTC` (rearme de automatismo/reset), `PB` (seleção de barra preferencial) e `CMD` (comando de iluminação/automatismo sem retorno modelado) são comandos tipo pulso confirmados, nos dados reais (`PSACA_CC:20/21/22`), sem NENHUM status correspondente em lugar nenhum do input de origem. Fonte: [`2026-07-02-spI-relatorio-outputs.md`](superpowers/specs/2026-07-02-spI-relatorio-outputs.md).
10. **Whitelist de siglas por equipamento (`config.siglas_por_equipamento`)** — quando o equipamento-alvo é identificado (ex. `Seccionadora`), os candidatos de sigla são restritos à whitelist medida em dado real (`Export_base_Full`, 2103 sinais com equipamento `89-*`/`29-*`): `SECF, DSEC, SECC, 43LR, SECG, SECB, SECT, CCCO, CCFL, CCMO, FSEC, OI, LIBM, CCCM, CCAL, BSEC, MANI, MDCM, FLFC, BBFC, BBAB, FLAB, FALH, PROT, CCLO, VMTC, BBA2, SOBC, BATA, MINC` (30 siglas no frozenset atual de `src/tdt/config.py`; a spec de origem menciona uma semente de 34 medidos — o código convergiu para 30). Evita decisão de sigla de outra classe de equipamento mesmo quando o texto casa por similaridade. Fonte: [`2026-07-01-semantica-estados-multicoord-design.md`](superpowers/specs/2026-07-01-semantica-estados-multicoord-design.md) (D6), whitelist em `src/tdt/config.py`.
11. **`LIBM` (Libera Manobra) decide normalmente mas é rebaixado a revisão por decisão de projeto** — casa a sigla certa, mas o real GTD descartou esse sinal na prática (a base tem 36 ocorrências); `config.siglas_revisao_projeto` gateia essa política, não é um erro de matching. Fonte: [`2026-07-01-semantica-estados-multicoord-design.md`](superpowers/specs/2026-07-01-semantica-estados-multicoord-design.md).


## Família ANSI 20

_14 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 2063 | 20C 20T 63T - TRIP VALVULA OU BUCHHOLZ | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 206T | 20T 63T - TRIP VALVULA OU BUCHHOLZ  TRAFO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 2087T | 20 87 - TRIP VALVULA OU DIFERENCIAL TRAFO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20A | 20 - ALARME VALVULA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20C | 20 - VALVULA COMUTADOR | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20CA | 20 - ALARME VALVULA CDC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20CD | 20 - TRIP VALVULA CDC | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20D | 20 - TRIP VALVULA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20T | 20 - VALVULA TRANSFORMADOR | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20T1 | 20 - TRIP VALVULA TRAFO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20T2 | 20 - TRIP VALVULA TRAFO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20TA | 20 - ALARME VALVULA TRAFO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20TC | 20 - TRIP VALVULA TRAFO OU CDC | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 20TD | 20 - TRIP VALVULA TRAFO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 21

_25 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 21 | 21 - FUNCAO DISTANCIA | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 21 | 21 - FUNCAO DISTANCIA | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 21D | 21 - DISPARO LOCALIZADOR DE FALTA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21EF | 21 - TRIP DISTANCIA ESTENDIDA FASES | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21EM | 21 - TRIP DISTANCIA ESTENDIDA MONOFASICA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21F1 | 21 - TRIP FASE ZONA 1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21F2 | 21 - TRIP FASE ZONA 2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21F3 | 21 - TRIP FASE ZONA 3 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21F4 | 21 - TRIP FASE ZONA 4 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21FA | 21 - TRIP DISTANCIA FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21FB | 21 - TRIP DISTANCIA FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21FC | 21 - TRIP DISTANCIA FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21MF | 21 - TRIP DISTANCIA MULTI FASES | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21MO | 21 - TRIP DISTANCIA MONOFASICO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21N | 21 - TRIP DISTANCIA NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21N1 | 21 - TRIP NEUTRO ZONA 1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21N2 | 21 - TRIP NEUTRO ZONA 2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21N3 | 21 - TRIP NEUTRO ZONA 3 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21N4 | 21 - TRIP NEUTRO ZONA 4 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21Z1 | 21 - TRIP ZONA 1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21Z2 | 21 - TRIP ZONA 2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21Z3 | 21 - TRIP ZONA 3 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21Z4 | 21 - TRIP ZONA 4 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21Z5 | 21 - TRIP ZONA 5 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 21_T | 21 - TRIP DISTANCIA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (ANSI 21)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx` (`DNP3_DiscreteSignals`, sheet real de UTR). Descrições de campo estão em branco nesse export (nomenclatura real vem só do Signal Name padronizado `{SE}_{MODULO}_{EQUIP}_{SIGLA}`); a evidência de campo é estrutural: cardinalidade e datatype por sinal, não texto.

- Só as zonas de fase aparecem no dado real: `GTD_LTGTA_LTGTA_P_21`, `..._21Z1`, `..._21Z2`, `..._21Z3`, `..._21Z4` — **4 zonas por módulo de linha** (`21Z1..21Z4`), sempre `Read`/`SingleBit`, uma ocorrência por lado de relé (`_P`/`_A`, principal/alternado — 2 relés por linha nesta subestação). `21Z5` e as variantes de terra (`21N*`) da LP não aparecem nesta TDT real — famílias presentes na LP mas sem instância nesta amostra.
- `21` (função habilitada, `Enabled`/`Read` — todas as 6 ocorrências reais são `Read`, nenhuma `ReadWrite`, diferente do par `Read`/`ReadWrite` que a LP lista) existe 1x por módulo de linha, par com a função — o padrão de "sigla-função" (`INCLUIDO;EXCLUIDO`) descrito na LP se confirma na estrutura, mas não na direção: aqui é só leitura.

## Família ANSI 24

_7 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 24 | 24 - TRIP SOBREEXCITACAO (VOLTS HERTZ) | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 24I | 24 - INSTANTANEA SOBREEXCITACAO (VOLTS HERTZ) | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 24I1 | 24 - INSTANTANEA SOBREEXCITACAO (VOLTS HERTZ) E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 24I2 | 24 - INSTANTANEA SOBREEXCITACAO (VOLTS HERTZ) E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 24T | 24 - TEMPORIZADA SOBREEXCITACAO (VOLTS HERTZ) | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 24T1 | 24 - TEMPORIZADA SOBREEXCITACAO (VOLTS HERTZ) E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 24T2 | 24 - TEMPORIZADA SOBREEXCITACAO (VOLTS HERTZ) E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 25

_11 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 25AM | 25 - RELE 25 AUTOMATICO MANUAL | Custom | Discrete | Read | Transit;MANUAL;AUTOMATICO;Error |  |  |  |
| 25AT | 25 - TRIP DIFERENCA DE ANGULO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 25CA | 25 - FALTA VCA RELE SINCRONISMO | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| 25ER | 25 - FALHA SINCRONISMO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| 25FT | 25 - TRIP DIFERENCA FREQUENCIA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 25IE | 25 - FUNCAO SINCRONISMO | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 25IE | 25 - FUNCAO SINCRONISMO | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 25LR | 25 - CHAVE LOCAL REMOTO RELE 25 | Custom | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |
| 25OK | 25 - SINCRONISMO FONTE/CARGA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 25VT | 25 - TRIP DIFERENCA TENSAO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 25_T | 25 - TRIP SINCRONISMO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 26

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 263A | 20C 20T 63T - ALARME VALVULA OU BUCHHOLZ | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 2649 | 26 49 - FUNCAO TEMPERATURA | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 2649 | 26 49 - FUNCAO TEMPERATURA | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |

## Família ANSI 27

_16 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 27 | 27 - FUNCAO SUBTENSAO | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 27 | 27 - FUNCAO SUBTENSAO | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 2759 | 27 59 - SUBTENSAO OU SOBRETENSAO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27AB | 27 - SUBTENSAO FASE AB | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27AC | 27 - SUBTENSAO FASE AC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27BC | 27 - SUBTENSAO FASE BC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27BL | 27 - BLOQUEIO SUBTENSAO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27BR | 27 - SUBTENSAO BARRA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27CA | 27 - SUBTENSAO VCA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27CC | 27 - SUBTENSAO VCC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27CD | 27 - BLOQUEIO SUBTENSAO CDC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27E1 | 27 - SUBTENSAO E1 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27E2 | 27 - SUBTENSAO E2 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27LT | 27 - SUBTENSAO LINHA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27TP | 27 - SUBTENSAO TP | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 27_T | 27 - TRIP SUBTENSAO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (ANSI 27)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx` (`DNP3_DiscreteSignals`). `Description` vem em branco em todo o export (0/1641 linhas); a nomenclatura real observável é o `Signal Alias` + `Signal Name` padronizado + estrutura (cardinalidade/datatype/direção).

- Só 4 siglas aparecem: `27` (função, `27 FUNCAO`, 6x, **todas `ReadWrite`, nenhuma `Read`** — diferente do par `Read`/`ReadWrite` que a LP lista, mesmo padrão "sigla-função" `INCLUIDO;EXCLUIDO` da regra 6), `27CD` (`27 - BLOQUEIO SUBTENSAO CDC`), `27E1`/`27E2` (`27 - SUBTENSAO E1`/`E2`, estágios). As demais 12 siglas da LP (`27AB`, `27AC`, `27BC`, `27BL`, `27BR`, `27CA`, `27CC`, `27LT`, `27TP`, `27_T`) não aparecem nesta amostra — famílias presentes na LP sem instância real aqui.
- Aliases reais confirmam a semântica "estágio" (`E1`/`E2`) já documentada na descrição padrão — não há divergência de nomenclatura entre LP e TDT real para as siglas que aparecem.

## Família ANSI 32

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 32 | 32 - DIRECIONAL DE POTENCIA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 43

_9 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 43AM | 43 - CHAVE AUTOMATICO MANUAL | Custom | Discrete | Read | Transit;MANUAL;AUTOMATICO;Error |  |  |  |
| 43EP | 43 - CHAVE PROTECAO | Custom | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |
| 43LR | 43 - CHAVE LOCAL REMOTO | Local | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |
| 43RT | 43 - CHAVE REJEICAO POR TEMPERATURA | Custom | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |
| 43TC | 43 - CHAVE TELECOMANDO | Local | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 43TP | 43 - TRANSFERENCIA DE PROTECAO | Custom | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 43TP | 43 - TRANSFERENCIA DE PROTECAO | Custom | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 43TR | 43 - CHAVE LOCAL REMOTO TRANSFORMADOR | Custom | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |
| 43VF | 43 - CHAVE LOCAL REMOTO VENTILACAO FORCADA | Custom | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |

## Família ANSI 46

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 46 | 46 - CORRENTE DE SEQUENCIA NEGATIVA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 46E1 | 46 - CORRENTE DE SEQUENCIA NEGATIVA E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 50

_17 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 50BF | 50 - FALHA DISJUNTOR | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50CA | 50 - SOBRECORRENTE INSTANTANEA FASE C OU A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50CD | 50 - SOBRECORRENTE CDC | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50F | 50 - SOBRECORRENTE INSTANTANEA FASE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50F1 | 50 - SOBRECORRENTE INSTANTANEA FASE E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50F2 | 50 - SOBRECORRENTE INSTANTANEA FASE E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50F3 | 50 - SOBRECORRENTE INSTANTANEA FASE E3 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50FA | 50 - SOBRECORRENTE INSTANTANEA FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50FB | 50 - SOBRECORRENTE INSTANTANEA FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50FC | 50 - SOBRECORRENTE INSTANTANEA FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50FN | 50 - SOBRECORRENTE INSTANTANEA FASE NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50N | 50 - SOBRECORRENTE INSTANTANEA NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50N1 | 50 - SOBRECORRENTE INSTANTANEA NEUTRO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50N2 | 50 - SOBRECORRENTE INSTANTANEA NEUTRO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50N3 | 50 - SOBRECORRENTE INSTANTANEA NEUTRO E3 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50_1 | 50 - SOBRECORRENTE INSTANTANEA E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 50_2 | 50 - SOBRECORRENTE INSTANTANEA E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (ANSI 50)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. Das 17 siglas da LP, só 5 têm instância real, mas com volume alto (151 linhas discretas no total): `50F1`/`50F2` (`50F 1`/`50F 2`, 31 cada — estágios de fase), `50N1`/`50N2` (`50N 1`/`50N 2`, 31 cada — estágios de neutro), `50CD` (`50 - SOBRECORRENTE CDC`, 2). As variantes por fase nominal (`50FA/FB/FC/50CA/50FN/50N/50N3/50_1/50_2/50BF`) não aparecem nesta amostra.
- **Gap real, não mapeamento incorreto**: `50EF` aparece 25x no TDT real (`50EF - END FAULT`, falha de terminal de linha) mas **não existe em nenhuma linha de `docs/Pontos Padrao ADMS_v2.xlsx`** (confirmado por busca direta na sheet `DiscreteSignals`) — não é erro de mineração do Task 1, a sigla simplesmente não está na Lista Padrão. Sinal a considerar para adicionar à LP se `50EF` for recorrente em outras subestações.

## Família ANSI 51

_15 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 5161 | 51 61 - FASE NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51CA | 51 - SOBRECORRENTE TEMPORIZADA FASE C OU A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51F | 51 - SOBRECORRENTE TEMPORIZADA FASE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51F1 | 51 - SOBRECORRENTE TEMPORIZADA FASE E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51F2 | 51 - SOBRECORRENTE TEMPORIZADA FASE E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51FA | 51 - SOBRECORRENTE TEMPORIZADA FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51FB | 51 - SOBRECORRENTE TEMPORIZADA FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51FC | 51 - SOBRECORRENTE TEMPORIZADA FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51FN | 51 - SOBRECORRENTE TEMPORIZADA FASE NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51N | 51 - FUNCAO SOBRECORRENTE TEMPORIZADA NEUTRO | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 51N | 51 - FUNCAO SOBRECORRENTE TEMPORIZADA NEUTRO | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 51N1 | 51 - SOBRECORRENTE TEMPORIZADA NEUTRO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51N2 | 51 - SOBRECORRENTE TEMPORIZADA NEUTRO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51NL | 51 - SOBRECORRENTE TEMPORIZADA LOCAL | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 51V | 51 - SOBRECORRENTE TEMPORIZADA POR TENSAO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (ANSI 51)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. Só 3 das 15 siglas da LP têm instância real, mas de alto volume: `51F` (`51F`, 31 — sobrecorrente temporizada fase), `51N1` (`51N 1`, 31 — estágio 1 de neutro), `51N` (`51N`, 12, único `ReadWrite` do grupo — confirma o padrão "sigla-função" `Enabled`/`INCLUIDO;EXCLUIDO` já coberto pela regra 6, coerente com a LP que também lista `51N` como `Enabled`/`ReadWrite`).
- `51NL` (citada na regra 51NL/local do commit `7f4e732`, fix de invariante documentado) e as variantes por fase nominal não aparecem nesta amostra — LP cobre mais granularidade do que este TDT específico usa.

## Família ANSI 56

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 561F | 50 51 61 - FASE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 59

_12 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 59 | 59 - FUNCAO SOBRETENSAO | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 59 | 59 - FUNCAO SOBRETENSAO | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 59A | 59 - ALARME SOBRETENSAO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 59CD | 59 - BLOQUEIO CDC SOBRETENSAO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 59E1 | 59 - SOBRETENSAO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 59E2 | 59 - SOBRETENSAO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 59E3 | 59 - SOBRETENSAO E3 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 59E4 | 59 - SOBRETENSAO E4 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 59E5 | 59 - SOBRETENSAO E5 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 59I | 59 - SOBRETENSAO INSTANTANEA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 59N | 59 - SOBRETENSAO NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 59_T | 59 - TRIP SOBRETENSAO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (ANSI 59)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. 4 das 12 siglas da LP aparecem: `59` (função, `59 - FUNCAO SOBRETENSAO`, `ReadWrite`/`Read` — mesmo padrão-função da regra 6), `59CD` (`59 - BLOQUEIO CDC SOBRETENSAO`), `59E1`/`59E2` (`59 E1`/`E2`, estágios de fase). `59A`, `59E3-E5`, `59I`, `59N`, `59_T` não aparecem nesta amostra.
- **Gap real, mesmo padrão do ANSI 50**: `59N1`/`59N2` aparecem no TDT real (`59 NEUTRO ESTAGIO 1`/`2`, 4x cada) mas **não existem em `docs/Pontos Padrao ADMS_v2.xlsx`** (só `59N` está na LP, sem estágios numerados) — mais um sinal de que a LP às vezes generaliza onde o campo distingue por estágio.

## Família ANSI 61

_6 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 61 | 61 - DESEQUILIBRIO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 61I | 61 - DESEQUILIBRIO INSTANTANEO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 61N | 61 - DESEQUILIBRIO NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 61T | 61 - DESEQUILIBRIO TEMPORIZADO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 61_1 | 61 - DESEQUILIBRIO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 61_2 | 61 - DESEQUILIBRIO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 62

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 62BF | 62 - FALHA DISJUNTOR BLOQUEIO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 63

_8 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 63A | 63 - ALARME BUCHHOLZ | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 63C | 63 - BUCHHOLZ CDC | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  | 63CD |
| 63CA | 63 - ALARME BUCHHOLZ CDC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 63CD | 63 - TRIP BUCHHOLZ CDC | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 63T | 63 - BUCHHOLZ TRAFO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  | 63TD |
| 63TA | 63 - ALARME BUCHHOLZ TRAFO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 63TC | 63 - TRIP BUCHHOLZ CDC OU TRAFO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 63TD | 63 - TRIP BUCHHOLZ TRAFO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 67

_30 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 67 | 67 - FUNCAO DIRECIONAL SOBRECORRENTE | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 67 | 67 - FUNCAO DIRECIONAL SOBRECORRENTE | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 67F | 67 - DIRECIONAL SOBRECORRENTE FASE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67F1 | 67 - DIRECIONAL SOBRECORRENTE FASE E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67F2 | 67 - DIRECIONAL SOBRECORRENTE FASE E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67FA | 67 - DIRECIONAL SOBRECORRENTE FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67FB | 67 - DIRECIONAL SOBRECORRENTE FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67FC | 67 - DIRECIONAL SOBRECORRENTE FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67FD | 67 - DIRECIONAL SOBRECORRENTE DIRETO FASE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67FR | 67 - DIRECIONAL SOBRECORRENTE REVERSO FASE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67FT | 67 - DIRECIONAL SOBRECORRENTE FASE TEMPORIZADO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67FTD | 67 - DIRECIONAL SOBRECORRENTE DIRETO FASE TEMPORIZADA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67FTR | 67 - DIRECIONAL SOBRECORRENTE REVERSO FASE TEMPORIZADA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67N | 67 - DIRECIONAL SOBRECORRENTE NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67N1 | 67 - DIRECIONAL SOBRECORRENTE NEUTRO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67N2 | 67 - DIRECIONAL SOBRECORRENTE NEUTRO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67ND | 67 - DIRECIONAL SOBRECORRENTE DIRETO NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67NR | 67 - DIRECIONAL SOBRECORRENTE REVERSO NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67NT | 67 - DIRECIONAL SOBRECORRENTE NEUTRO TEMPORIZADO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67NT1 | 67 - DIRECIONAL SOBRECORRENTE NEUTRO TEMPORIZADO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67NT2 | 67 - DIRECIONAL SOBRECORRENTE NEUTRO TEMPORIZADO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67NTD | 67 - DIRECIONAL SOBRECORRENTE DIRETO NEUTRO TEMPORIZADA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67NTR | 67 - DIRECIONAL SOBRECORRENTE REVERSO NEUTRO TEMPORIZADA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67NX | 67 - FUNCAO DIRECIONAL SOBRECORRENTE NEUTRO | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 67NX | 67 - FUNCAO DIRECIONAL SOBRECORRENTE NEUTRO | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 67P1 | 67 - DIRECIONAL SOBRECORRENTE FASE TEMPORIZADO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67P2 | 67 - DIRECIONAL SOBRECORRENTE FASE TEMPORIZADO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67_1 | 67 - DIRECIONAL SOBRECORRENTE E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67_2 | 67 - DIRECIONAL SOBRECORRENTE E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 67_T | 67 - TRIP DIRECIONAL SOBRECORRENTE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (ANSI 67)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. Família com maior volume real do documento (163 linhas discretas, 15 siglas distintas): `67` (função, 1x por módulo de linha, `Read`), `67F1`/`67F2` (estágios de fase, 22 cada), `67FT` (fase temporizado, 22), `67N1`/`67N2` (estágios de neutro, 22 cada), `67NT` (neutro temporizado, 22), e as variantes direto/reverso `67FD/FR/FTD/FTR` + `67ND/NR/NTD/NTR` (1 cada — só 1 relé na amostra usa essa granularidade direcional).
- Nomenclatura de campo (`67 - DIRECIONAL SOBRECORRENTE FASE E1` etc.) é praticamente idêntica à descrição padrão da LP — família de proteção direcional bem coberta e sem gaps de nomenclatura nesta amostra.
- Presença de 2 relés por linha (sufixo `_P`/`_A`, principal/alternado — ver ANSI 21) se repete aqui: mesma sigla `67F1` aparece nos dois relés da mesma linha, dobrando a cardinalidade esperada por módulo.

## Família ANSI 71

_12 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 71 | 71 - NIVEL OLEO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71C | 71 - NIVEL OLEO CDC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71CH | 71 - NIVEL ALTO OLEO CDC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71CL | 71 - NIVEL BAIXO OLEO CDC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71H | 71 - NIVEL ALTO OLEO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71HI | 71 - NIVEL ALTO OLEO CDC OU TRAFO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71L | 71 - NIVEL BAIXO OLEO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71LO | 71 - NIVEL BAIXO OLEO CDC OU TRAFO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71T | 71 - NIVEL OLEO TRAFO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71TC | 71 - NIVEL OLEO CDC OU TRAFO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71TH | 71 - NIVEL ALTO OLEO TRAFO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 71TL | 71 - NIVEL BAIXO OLEO TRAFO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 78

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 78VS | 78 - SALTO VETOR ANTI-ILHAMENTO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 78_T | 78 - DESEQUILIBRIO ANGULO FASE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 79

_9 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 79 | 79 - FUNCAO RELIGAMENTO | ReclosingEnabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 79 | 79 - FUNCAO RELIGAMENTO | ReclosingEnabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 79LO | 79 - RELIGAMENTO BLOQUEADO | RecloserLockout | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 79OK | 79 - RELIGAMENTO COM SUCESSO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 79RE | 79 - RELIGAMENTO PRONTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 79TF | 79 - RELIGAMENTO TRANSFERIDO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 79_1 | 79 - PARTIDA RELIGAMENTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 79_EXC | 79 - EXCLUIR RELIGAMENTO | Custom | Discrete | Write | Transit;;;Error |  |  |  |
| 79_INC | 79 - INCLUIR RELIGAMENTO | Custom | Discrete | Write | Transit;;;Error |  |  |  |

### Nomenclaturas reais observadas (ANSI 79)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. 4 das 9 siglas da LP aparecem, com bom volume (69 linhas): `79` (função religamento, `ReadWrite`, alias `79`, 15x), `79LO` (`79 BLOQUEADO`, 18), `79OK` (`79 OK`, 18), `79RE` (`79 RESET`, 18 — atenção: no real, o alias de `79RE` é "RESET", enquanto a descrição padrão da LP para `79RE` é "79 - RELIGAMENTO PRONTO" — nomes de campo abreviados divergem do texto completo da LP, mas a sigla em si bate). `79TF`, `79_1`, `79_EXC`, `79_INC` não aparecem nesta amostra.
- Caso relevante para a regra 7 (Fusão): `79_EXC`/`79_INC` (comando incluir/excluir religamento) da LP não aparecem no real como Write órfão — sugere que, nesta amostra, a função `79` inteira já cobre o papel de habilita/desabilita via `ReadWrite` (mesmo padrão-função `INCLUIDO;EXCLUIDO` da regra 6), sem precisar dos comandos dedicados.

## Família ANSI 81

_20 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 81 | 81 - FUNCAO SUB/SOB FREQUENCIA | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 81 | 81 - FUNCAO SUB/SOB FREQUENCIA | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 81AJST | GRUPO DE AJUSTE FUNCAO 81 | Custom | Discrete | Write | Transit;;;Error |  |  |  |
| 81E1 | 81 - TRIP SUB/SOBRE FREQUENCIA E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81E2 | 81 - TRIP SUB/SOBRE FREQUENCIA E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81E3 | 81 - TRIP SUB/SOBRE FREQUENCIA E3 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81E4 | 81 - TRIP SUB/SOBRE FREQUENCIA E4 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81E5 | 81 - TRIP SUB/SOBRE FREQUENCIA E5 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81IE1 | 81 - TRIP SUB/SOBRE FREQUENCIA E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81IE2 | 81 - TRIP SUB/SOBRE FREQUENCIA E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81O1 | 81 - TRIP SOBRE FREQUENCIA E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81O2 | 81 - TRIP SOBRE FREQUENCIA E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81SO | 81 - TRIP SOBRE FREQUENCIA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81SU | 81 - TRIP SUB FREQUENCIA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 81U1 | AJUSTE PARA 81 E1 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| 81U2 | AJUSTE PARA 81 E2 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| 81U3 | AJUSTE PARA 81 E3 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| 81U4 | AJUSTE PARA 81 E4 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| 81U5 | AJUSTE PARA 81 E5 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| 81_T | 81 - TRIP SUB/SOBRE FREQUENCIA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (ANSI 81)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. Segunda maior família por volume real (208 linhas discretas): `81` (função, `ReadWrite`, 14x — mesmo TDT usado como referência na regra 1 do dc_pairer, `81U1 out=1504`), `81E1`-`81E5` (estágios, 23/23/14/14/14 — decrescente porque nem todo relé tem 5 estágios), `81BLOQ` (`81 BLOQUEIO DINAMICO`, 18), `81U1`-`81U5` (`AJUSTE PARA 81 ESTAGIO N`, `ReadWrite`, 14 cada — comandos de ajuste de estágio, coerentes com `81AJST` da LP), `81O1` (`81 - TRIP SOBRE FREQUENCIA E1`, 10), `81SO`/`81SU` (sobre/sub frequência, 4 cada).
- **Gap real**: `81IE1`/`81IE2` (na LP, "TRIP SUB/SOBRE FREQUENCIA E1/E2") e `81O2` não aparecem nesta amostra. Em contrapartida `81O1` aparece no real mas com alias diferente da contraparte esperada `81E1` — sugere que `81O1`/`81O2` (sobrefrequência) e `81E1`-`81E5` (estágios genéricos) coexistem como famílias de nomenclatura distintas dentro do próprio ANSI 81, não intercambiáveis.
- `81U1`-`81U5` no real são `ReadWrite` (ajuste é comandável), enquanto a LP os lista como `Custom`/`Read` (`Transit;DESABILITADO;HABILITADO;Error`) — divergência de `Direction` a observar se a fusão D+C (regra 1) está classificando esses ajustes corretamente.

## Família ANSI 85

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 85 | 85 - TRIP TELEPROTECAO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 86

_7 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 86 | 86 - BLOQUEIO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 86 | 86 - BLOQUEIO | Custom | Discrete | ReadWrite | Transit;NORMAL;ATUADO;Error |  |  |  |
| 86BF | 86 - BLOQUEIO DEFEITO DISJUNTOR | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 86BF | 86 - BLOQUEIO DEFEITO DISJUNTOR | Custom | Discrete | ReadWrite | Transit;NORMAL;ATUADO;Error |  |  |  |
| 86C | 86 - BLOQUEIO CDC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 86CC | FALTA VCC CIRCUITO RELE 86 | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| 86FL | 86 - FALHA CIRCUITO RELE | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

### Nomenclaturas reais observadas (ANSI 86)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. Só 2 das 7 siglas da LP aparecem, baixo volume: `86` (`86 BLOQUEIO`, 6x, split **4 `ReadWrite` + 2 `Read`** — a variante `ReadWrite` que a LP também lista é maioria no real, não ausente) e `86BF` (`86BF`, `ReadWrite`, 3x — bloqueio por falha de disjuntor, coerente com "86 - BLOQUEIO DEFEITO DISJUNTOR" da LP). `86C`, `86CC`, `86FL` não aparecem nesta amostra.
- Família de baixo volume real (9 linhas) mas coerente 1:1 com a LP nas siglas que aparecem — sem achados de divergência.

## Família ANSI 87

_29 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 87 | 87 - FUNCAO DIFERENCIAL | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 87 | 87 - FUNCAO DIFERENCIAL | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 8750 | 87 50 - FASE NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 8751 | 87 - DIFERENCIAL TEMPORIZADO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87A | 87 - DIFERENCIAL FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87B | 87 - DIFERENCIAL FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87BL | 87 - DIFERENCIAL BLOQUEIO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87C | 87 - DIFERENCIAL FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87EF | 87 - DIFERENCIAL RESTRITO FALTA A TERRA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87G | 87 - DIFERENCIAL TERRA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87LT | 87 - TRIP DIFERENCIAL LINHA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87Q | 87 - DIFERENCIAL SEQUENCIA NEGATIVA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87Q1 | 87 - DIFERENCIAL SEQUENCIA NEGATIVA E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87Q2 | 87 - DIFERENCIAL SEQUENCIA NEGATIVA E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87R | 87 - DIFERENCIAL RESTRITO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87R1 | 87 - DIFERENCIAL RESTRITO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87R2 | 87 - DIFERENCIAL RESTRITO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87RA | 87 - DIFERENCIAL RESTRITO FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87RB | 87 - DIFERENCIAL RESTRITO FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87RC | 87 - DIFERENCIAL RESTRITO FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87TA | 87 - DIFERENCIAL TEMPORIZADO FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87TB | 87 - DIFERENCIAL TEMPORIZADO FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87TC | 87 - DIFERENCIAL TEMPORIZADO FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87TT | 87 - TRIP DIFERENCIAL TRIFASICO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87U | 87 - DIFERENCIAL NAO RESTRITO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87U1 | 87 - DIFERENCIAL NAO RESTRITO E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87U2 | 87 - DIFERENCIAL NAO RESTRITO E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87_I | 87 - DIFERENCIAL INSTANTANEO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 87_T | 87 - TRIP DIFERENCIAL | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Família ANSI 90

_7 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 90DP | 90 - DISCREPANCIA DE TAP | Custom | Discrete | Read | Transit;NORMAL;DISCREPANCIA;Error |  |  |  |
| 90FU | 90 - FALHA FUSIVEL | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| 90I | 90 - BLOQUEIO SOBRECORRENTE RELE 90 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 90LR | 43 - CHAVE LOCAL REMOTO RELE 90 | Custom | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |
| 90V | 90 - BLOQUEIO TENSAO RELE 90 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 90VF | AUTOMATISMO RELE 90 E VENTILACAO FORCADA | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| 90VF | AUTOMATISMO RELE 90 E VENTILACAO FORCADA | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |

## Família ANSI 94

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 94 | 94 - RETRIP | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  | TEXT |

## Sigla AB*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| ABBN | ABERTURA PELA BOBINA DE NEUTRO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla AD*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| ADIF | 25 - DIFERENCA ANGULO | Valor Medido | Analog |  |  | Ângulo de Tensão | Grau |  |

## Sigla AJ*

_39 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| AJ1 | AJUSTE PARA AL1 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ12 | AJUSTE PARA AL12 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ13 | AJUSTE PARA AL13 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ14 | AJUSTE PARA AL14 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ15 | AJUSTE PARA AL15 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ16 | AJUSTE PARA AL16 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ17 | AJUSTE PARA AL17 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ18 | AJUSTE PARA AL18 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ2 | AJUSTE PARA AL2 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ21 | AJUSTE PARA AL21 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ25 | AJUSTE PARA AL25 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJ26 | AJUSTE PARA AL26 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ27 | AJUSTE PARA AL27 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ28 | AJUSTE PARA AL28 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ3 | AJUSTE PARA AL3 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ31 | AJUSTE PARA AL31 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ32 | AJUSTE PARA AL32 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ33 | AJUSTE PARA AL33 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ34 | AJUSTE PARA AL34 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ4 | AJUSTE PARA AL4 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ5 | AJUSTE PARA AL5 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ6 | AJUSTE PARA AL6 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ7 | AJUSTE PARA AL7 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJ8 | AJUSTE PARA AL8 | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| AJG1 | AJUSTE PARA GRUPO 1 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG1 | AJUSTE PARA GRUPO 1 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG2 | AJUSTE PARA GRUPO 2 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG2 | AJUSTE PARA GRUPO 2 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG3 | AJUSTE PARA GRUPO 3 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG3 | AJUSTE PARA GRUPO 3 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG4 | AJUSTE PARA GRUPO 4 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG4 | AJUSTE PARA GRUPO 4 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG5 | AJUSTE PARA GRUPO 5 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG5 | AJUSTE PARA GRUPO 5 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG6 | AJUSTE PARA GRUPO 6 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJG6 | AJUSTE PARA GRUPO 6 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJGP | GRUPOS DE AJUSTE | Custom | Discrete | ReadWrite | Transit;GRUPO 1;GRUPO 2;Error |  |  |  |
| AJNM | AJUSTE PARA GRUPO NORMAL | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| AJST | GRUPO DE AJUSTE | Custom | Discrete | Write | Transit;;;Error |  |  |  |

## Sigla AL*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| ALM | ALARME GERAL | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla AN*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| ANG | ANGULO | Valor Medido | Analog |  |  | Ângulo de Tensão | Grau |  |
| ANP | ANOMALIA PROTECAO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| ANR | ANOMALIA REDE | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla AU*

_5 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| AUTC | AUTOMATISMO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  | AUTO |
| AUTD | AUTOMATISMO DESLIGA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| AUTL | AUTOMATISMO LIGA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| AUTO | FUNCAO AUTOMATISMO | Custom | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| AUTO | FUNCAO AUTOMATISMO | Custom | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |

## Sigla B*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| B5M | BLOQUEIO 5 MINUTOS | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla BA*

_8 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| BAB | BLOQUEIO ABERTURA BAIXO AR COMPRIMIDO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BADC | BATERIA EM DESCARGA | Custom | Discrete | Read | Transit;CARGA;DESCARGA;Error |  |  |  |
| BAF1 | BOBINA ABERTURA FECHAMENTO 1 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BAF2 | BOBINA ABERTURA FECHAMENTO 2 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BAHI | TENSAO ALTA BATERIA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BATA | ALARME BATERIA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BATL | TENSAO BAIXA BATERIA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BAVL | CARREGAMENTO DA BATERIA | Custom | Discrete | Read | Transit;FALHA;OPERANDO;Error |  |  |  |

## Sigla BB*

_6 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| BBA1 | BOBINA ABERTURA 1 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BBA2 | BOBINA ABERTURA 2 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BBAB | BOBINA ABERTURA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BBAF | BOBINA ABERTURA OU FECHAMENTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BBFC | BOBINA FECHAMENTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BBFL | FALHA BOMBAS OLEO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla BC*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| BCDC | BLOQUEIO CDC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla BF*

_6 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| BFAT | 62 - FALHA DISJUNTOR BLOQUEIO AT | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BFBT | 62 - FALHA DISJUNTOR BLOQUEIO ALIMENTADORES | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BFC | BLOQUEIO COMANDO FECHAMENTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BFP1 | 62 - FALHA DISJUNTOR BLOQUEIO BARRA P1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BFP2 | 62 - FALHA DISJUNTOR BLOQUEIO BARRA P2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BFP3 | 62 - FALHA DISJUNTOR BLOQUEIO BARRA P3 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla BL*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| BLA | BLOQUEIO COMANDO ABERTURA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BLDJ | BLOQUEIO DISJUNTOR | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| BLV | BLOQUEIO POR TENSAO DE RETORNO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla BO*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| BOMB | ESTADO BOMBA OLEO | Custom | Discrete | Read | Transit;DESLIGADO;LIGADO;Error |  |  |  |

## Sigla BP*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| BPBR | BLOQUEIO PROTECAO DE BARRA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla BS*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| BSEC | BLOQUEIO MANOBRA SECCIONADORA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla BX*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| BXAR | BAIXA PRESSAO AR COMPRIMIDO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla C*

_4 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| C13 | CHAVE SELETORA 13 KV | Custom | Discrete | Read | Transit;DESLIGAR;; |  |  |  |
| C138 | CHAVE SELETORA 138 KV | Custom | Discrete | Read | Transit;DESLIGAR;; |  |  |  |
| C23 | CHAVE SELETORA 23 KV | Custom | Discrete | Read | Transit;DESLIGAR;; |  |  |  |
| C69 | CHAVE SELETORA 69 KV | Custom | Discrete | Read | Transit;DESLIGAR;; |  |  |  |

## Sigla CA*

_13 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| CAAL | VCA ALARME | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CAAQ | VCA AQUECIMENTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CAB | CIRCUITO ABERTURA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CAB1 | CIRCUITO ABERTURA 1 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CAB2 | CIRCUITO ABERTURA 2 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CACD | FALTA VCA COMUTADOR | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CACO | FALTA VCA COMANDO | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CAFI | VCA MOTOR DO FILTRO DO OLEO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CAFL | FALTA VCA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CAMO | FALTA VCA MOTOR | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CASA | VCA SERVICO AUXILIAR | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CASC | FALTA VCA SECCIONADORA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CAVF | FALTA VCA VENTILACAO FORCADA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |

## Sigla CC*

_17 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| CCA1 | FALTA VCC CIRCUITO ABERTURA 1 | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCA2 | FALTA VCC CIRCUITO ABERTURA 2 | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCAB | FALTA VCC CIRCUITO ABERTURA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCAL | VCC ALARME | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CCC1 | FALTA VCC COMANDO 1 | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCC2 | FALTA VCC COMANDO 2 | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCCA | FALTA VCC VCA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCCM | FALTA VCC COMANDO MOTOR | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCCO | FALTA VCC COMANDO | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCFC | FALTA VCC CIRCUITO FECHAMENTO | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCFL | FALTA VCC | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCHI | VCC ALTA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CCIC | CHAVE DE COMANDO ICCP | Custom | Discrete | ReadWrite | CMD_RGE@null___RGE@CPFLT___Custom_S_TC_SS_CPFLT |  |  |  |
| CCLO | VCC BAIXA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| CCMO | FALTA VCC MOTOR | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCPN | FALTA VCC PAINEL | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| CCSC | FALTA VCC SECCIONADORA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |

## Sigla CD*

_9 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| CDAM | CDC AUTOMATICO MANUAL | Custom | Discrete | Read | Transit;AUTOMATICO;MANUAL;Error |  |  |  |
| CDC | COMUTADOR | TapIncrement | Discrete | Write | Transit;;;Error |  |  |  |
| CDCO | CDC MODO DE OPERACAO | Parallel | Discrete | ReadWrite | MESTRE;INDIVIDUAL;COMANDADO; |  |  |  |
| CDFL | FALHA CDC | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| CDLA | CDC LOCAL AUTOMATICO | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| CDLM | CDC LOCAL MANUAL | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| CDMT | DEFEITO MOTOR CDC | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| CDRA | CDC REMOTO AUTOMATICO | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| CDRM | CDC REMOTO MANUAL | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |

## Sigla CF*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| CFC | CIRCUITO FECHAMENTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla CM*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| CMD | COMANDO | Custom | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |
| CMD | COMANDO | Custom | Discrete | ReadWrite | Transit;REMOTO;LOCAL;Error |  |  |  |
| CMDE | PROPRIEDADE DO COMANDO | Custom | Discrete | ReadWrite | Transit;CEEE;RGE;Error |  |  |  |

## Sigla CO*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| COMA | 90 - POSICAO COMANDADO | Parallel | Discrete | ReadWrite | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| COMA | 90 - POSICAO COMANDADO | Parallel | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |

## Sigla CT*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| CTPC | RETORNO DE TENSAO DA PCH | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla DC*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DCDC | DEFEITO CDC | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DCMD | DEFEITO COMANDO | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |

## Sigla DE*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DEFC | CENTRAL DE ALARME DEFEITO | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DESLIGAR | COMANDO DESLIGAR | Custom | Discrete | Read | Transit;DESLIGAR;; |  |  |  |

## Sigla DF*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DFDJ | DEFEITO DISJUNTOR | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |

## Sigla DH*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DHT | DHT - SECADOR DE SILICA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla DI*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DIAF | DIAFRAGMA TRANSFORMADOR | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla DJ*

_5 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DJA1 | DISJUNTOR NA | SwitchStatus | Discrete | Read | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| DJA1 | DISJUNTOR NA | SwitchStatus | Discrete | ReadWrite | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| DJF1 | DISJUNTOR NF (LIGADO/DESLIGADO/ABERTO/FECHADO) | SwitchStatus | Discrete | Read | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| DJF1 | DISJUNTOR NF | SwitchStatus | Discrete | ReadWrite | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| DJIE | POSICAO DISJUNTOR EXTRAIVEL | Custom | Discrete | Read | Transit;EXTRAIDO;INSERIDO;Error |  |  |  |

### Nomenclaturas reais observadas (DJ* — posição de disjuntor)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. `DJF1` tem forte presença real: 24 linhas discretas, sempre `ReadWrite`/`MultiCoord`, Message Mapping `DESLIGAR@LIGAR___DESLIGADO@LIGADO___SwitchStatus_D_TC_SE` — confirma exatamente a regra 5 (pareamento por sigla de posição) e a regra 7 (fusão em `MultiCoord`, nunca `DoubleBit`). `DJA1` **não aparece nenhuma vez** nesta amostra (0 ocorrências) — a LP modela disjuntor NA (normalmente aberto) mas esta subestação real só tem disjuntores NF (normalmente fechado); gap por ausência de equipamento na amostra, não por falha de mineração. `DJIE` também não aparece.

## Sigla DM*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DMOT | DEFEITO MOTOR | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |

## Sigla DP*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DPT1 | DEFEITO PT100 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |

## Sigla DR*

_18 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DR | DEFEITO RELE | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DR14 | DEFEITO RELE 2414 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DR21 | DEFEITO RELE 21 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DR25 | DEFEITO RELE 25 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DR67 | DEFEITO RELE 67 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DR81 | DEFEITO RELE 81 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DR87 | DEFEITO RELE 87 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DR90 | DEFEITO RELE 90 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DREL | DEFEITO RELIGADOR | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DRET | DEFEITO RETIFICADOR | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DRPL | DEFEITO RELE MONITOR DE PARALELISMO | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DRPR | DEFEITO RELE PRINCIPAL | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DRRT | DEFEITO RELE ALTERNADO | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DRT1 | DEFEITO RELE MONITORAMENTO DE TEMPERATURA 1 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DRT2 | DEFEITO RELE MONITORAMENTO DE TEMPERATURA 2 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DRT3 | DEFEITO RELE MONITORAMENTO DE TEMPERATURA 3 | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DRTM | DEFEITO RELE MONITORAMENTO DE TEMPERATURA | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DRTMAVR | DEFEITO RELE MONITORAMENTO DE TEMPERATURA E AVR | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |

## Sigla DS*

_4 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DSAB | ALARMES DESABILITADOS | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| DSEC | DEFEITO SECCIONADORA | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DSEX | DEFEITO SENSOR EXTERNO | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |
| DSIM | DEFEITO SIMULTANEO | Custom | Discrete | Read | Transit;NORMAL;DEFEITO;Error |  |  |  |

## Sigla DT*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| DTT | TRANSFERENCIA DE TRIP | Custom | Discrete | Read | Transit;OPERANDO;BLOQUEADO;Error |  |  |  |
| DTTT | TRANSFERENCIA DE TRIP TRIFASICO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla ES*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| EST | ESTADO EQUIPAMENTO | Custom | Discrete | Read | Transit;DESLIGADO;LIGADO;Error |  |  |  |

## Sigla FA*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FA | FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| FALH | FALHA GERAL | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla FB*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FB | FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla FC*

_33 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FC | FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| FC14 | FALHA COMUNICACAO RELE 2414 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FC21 | FALHA COMUNICACAO RELE 21 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FC25 | FALHA COMUNICACAO RELE 25 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FC67 | FALHA COMUNICACAO RELE 67 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FC87 | FALHA COMUNICACAO RELE 87 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FC90 | FALHA COMUNICACAO RELE 90 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCAV | FALHA COMUNICACAO AVR RELE 90 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCBN | FECHAMENTO PELA BOBINA NEUTRO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| FCCA | FALHA COMUNICACAO SERVICO AUXILIAR VCA | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCCC | FALHA COMUNICACAO SERVICO AUXILIAR VCC | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCM | FALHA COMUNICACAO TRANSDUTOR | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCMM | FALHA COMUNICACAO MULTIMEDIDOR | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCMP | FALHA COMUNICAO COMPRESSOR | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCMR | FALHA COMUNICAO TRANSDUTOR RESERVA | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCMT | FALHA COMUTADOR | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCOM | FALHA COMUNICACAO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCPL | FALHA COMUNICACAO RELE MONITORAMENTO PARALELISMO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCPR | FALHA COMUNICACAO PARALELISMO INTERNO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCRC | FALHA COMUNICACAO RELE CONTROLE | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCRE | COMANDO FECHAMENTO REMOTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| FCRP | FALHA COMUNICACAO RELE PROTECAO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCRT | FALHA COMUNICACAO RELE REGULADOR DE TENSAO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCSA | FALHA COMUNICACAO SERVICO AUXILIAR | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCSF | FECHAMENTO SOB FALTA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| FCSN | FECHAMENTO POR SINCRONISMO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| FCSP | FALHA COMUNICACAO SPS | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCT1 | FALHA COMUNICACAO RELE MONITORAMENTO DE TEMPERATURA 1 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCT2 | FALHA COMUNICACAO RELE MONITORAMENTO DE TEMPERATURA 2 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCT3 | FALHA COMUNICACAO RELE MONITORAMENTO DE TEMPERATURA 3 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCTA | FALHA COMUNICACAO SENSOR TEMPERATURA AMBIENTE E UMIDADE | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCTL | FALHA CANAL TELEPROTECAO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FCTM | FALHA COMUNICACAO RELE MONITORAMENTO DE TEMPERATURA | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla FD*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FDIF | 25 - DIFERENCA FREQUENCIA | Valor Medido | Analog |  |  | Frequência | Hz |  |

## Sigla FG*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FGTE | FUGA TERRA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla FI*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FINT | FALTA INTERMITENTE | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| FIOL | FALHA FILTRO DE OLEO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla FL*

_5 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FLAB | FALHA DE ABERTURA | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FLAF | FALHA ABERTURA OU FECHAMENTO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FLAR | FALHA FLUXO AR | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FLFC | FALHA DE FECHAMENTO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FLNR | FALHA NEUTRO RESSONANTE | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla FP*

_5 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FP | FATOR DE POTENCIA | Valor Medido | Analog |  |  | Fator de Potência | Padrão |  |
| FPAR | FALHA SINCRONISMO PARALELISMO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FPBR | FALTA POTENCIAL BARRA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| FPP1 | FALTA POTENCIAL BARRA P1 | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| FPP2 | FALTA POTENCIAL BARRA P2 | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |

## Sigla FR*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FREQ | FREQUENCIA | Valor Medido | Analog |  |  | Frequência | Hz |  |

## Sigla FS*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FSEC | FALHA SECCIONADORA | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FSIH | FALHA SINCRONISMO HORA | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FSIN | FALHA IRIG B - SINCRONISMO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla FU*

_4 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FU1 | FALHA FUSIVEL 1 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FUGA | FUGA A TERRA | Valor Medido | Analog |  |  | Corrente | A | FGTE |
| FUMA | SENSOR FUMACA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| FUTP | FALHA FUSIVEL TP | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla FV*

_6 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| FVF | FALHA VENTILACAO FORCADA | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FVF1 | FALHA VENTILACAO FORCADA 1 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FVF2 | FALHA VENTILACAO FORCADA 2 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FVF3 | FALHA VENTILACAO FORCADA 3 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FVF4 | FALHA VENTILACAO FORCADA 4 | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| FVLT | FALTA POTENCIAL LT | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |

## Sigla G*

_12 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| G1 | GRUPO DE AJUSTE 1 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G1 | GRUPO DE AJUSTE 1 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G2 | GRUPO DE AJUSTE 2 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G2 | GRUPO DE AJUSTE 2 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G3 | GRUPO DE AJUSTE 3 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G3 | GRUPO DE AJUSTE 3 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G4 | GRUPO DE AJUSTE 4 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G4 | GRUPO DE AJUSTE 4 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G5 | GRUPO DE AJUSTE 5 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G5 | GRUPO DE AJUSTE 5 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G6 | GRUPO DE AJUSTE 6 | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| G6 | GRUPO DE AJUSTE 6 | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |

## Sigla GO*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| GOOS | FALHA GOOSE | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla GR*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| GRPO | GRUPO DE AJUSTE RELIGADOR | Custom | Discrete | ReadWrite | Transit;NORMAL;ALTERNATIVO;Error |  |  |  |

## Sigla HI*

_4 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| HIF1A | FALTA DE ALTA IMPEDANCIA FASE A | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| HIF1B | FALTA DE ALTA IMPEDANCIA FASE B | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| HIF1C | FALTA DE ALTA IMPEDANCIA FASE C | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |
| HIZ | FALTA DE ALTA IMPEDANCIA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |

## Sigla HL*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| HLT | HOT LINE TAG | HotLineTag | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| HLT | HOT LINE TAG | HotLineTag | Discrete | ReadWrite | Transit;EXCLUIDO;INCLUIDO;Error |  |  |  |

## Sigla IA*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| IA | CORRENTE FASE A | Valor Medido | Analog |  |  | Corrente | A |  |
| IACC | CORRENTE CURTO CIRCUITO FASE A | Gravador de Falha | Analog |  |  | Corrente | A |  |

### Nomenclaturas reais observadas (IA/IB/IC — corrente de fase)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx` (sheet `DNP3_AnalogSignals`). `IA`, `IB`, `IC` são as siglas analógicas de maior volume real do documento: 25 ocorrências cada, sempre `Measurement Type=Current`, unidade `A` — 1:1 com a descrição padrão da LP. Confirma a regra 3 (não existe comando para sinal analógico): nenhuma das 75 linhas tem `Direction`/`Output Coordinates` preenchidos, são puramente `Read`. `IACC`/`IBCC`/`ICCC` (corrente de curto-circuito, gravador de falha) não aparecem nesta amostra.

## Sigla IB*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| IB | CORRENTE FASE B | Valor Medido | Analog |  |  | Corrente | A |  |
| IBCC | CORRENTE CURTO CIRCUITO FASE B | Gravador de Falha | Analog |  |  | Corrente | A |  |

Ver nomenclaturas reais em "Sigla IA*" acima (IA/IB/IC medidas em conjunto na mesma varredura do export).

## Sigla IC*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| IC | CORRENTE FASE C | Valor Medido | Analog |  |  | Corrente | A |  |
| ICC | RESET CORRENTE DE CURTO CIRCUITO | Custom | Discrete | Write | Transit;;;Error |  |  |  |
| ICCC | CORRENTE CURTO CIRCUITO FASE C | Gravador de Falha | Analog |  |  | Corrente | A |  |

Ver nomenclaturas reais em "Sigla IA*" acima. `ICC` (Discrete, comando write de reset) não aparece nesta amostra.

## Sigla IN*

_6 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| IN | CORRENTE NEUTRO | Valor Medido | Analog |  |  | Corrente | A |  |
| IN61 | 61 - CORRENTE DE DESEQUILIBRO | Valor Medido | Analog |  |  | Corrente | A |  |
| INCC | CORRENTE CURTO CIRCUITO NEUTRO | Gravador de Falha | Analog |  |  | Corrente | A |  |
| INDI | 90 - POSICAO INDIVIDUAL | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| INDI | 90 - POSICAO INDIVIDUAL | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| INTR | 20 63 87 - PROTECOES INTRINSECAS | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (IN*)

Cruzado com o mesmo export. `IN` (corrente de neutro "pura") **não aparece** nesta amostra (0 ocorrências) — só a variante `IN61` (corrente de desequilíbrio ligada à função 61) tem instância real, 4x, `Current`/`A`. Gap por ausência de equipamento/config específica nesta subestação, coerente com o baixo volume de ANSI 61 observado (6 siglas na LP, sem instância real do relé 61 em si nesta amostra — só o subproduto de corrente).

## Sigla IO*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| IOUT | CORRENTE CARGA | Valor Medido | Analog |  |  | Corrente | A |  |

## Sigla IT*

_4 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| ITFA | INTERTRIP FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| ITFB | INTERTRIP FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| ITFC | INTERTRIP FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| ITGE | INTERTRIP GERAL | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla KM*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| KMDF | DISTANCIA DEFEITO | Custom | Analog |  |  | Comprimento | Km |  |

## Sigla LD*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| LDF | LOCALIZADOR DE FALTA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  | MANUT |

## Sigla LI*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| LIBM | LIBERA MANOBRA | Custom | Discrete | Read | Transit;BLOQUEADA;LIBERADA;Error |  |  |  |
| LIGAR | COMANDO LIGAR | Custom | Discrete | Read | Transit;LIGAR;; |  |  |  |

## Sigla LM*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| LMAB | LIBERA MANOBRA ABERTURA | Custom | Discrete | Read | Transit;BLOQUEADA;LIBERADA;Error |  |  |  |
| LMFE | LIBERA MANOBRA FECHAMENTO | Custom | Discrete | Read | Transit;BLOQUEADA;LIBERADA;Error |  |  |  |
| LMLO | LIBERA MANOBRA LOCAL | Custom | Discrete | Read | Transit;BLOQUEADA;LIBERADA;Error |  |  |  |

## Sigla MA*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| MANI | MANIVELA COMANDO MANUAL | Custom | Discrete | Read | Transit;EXTRAIDA;INSERIDA;Error |  |  |  |

## Sigla MC*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| MCCA | FALTA VCC VCA MOLA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |

## Sigla MD*

_23 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| MD | MINI DISJUNTOR | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MD13 | MINI DISJUNTOR 13KV | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MD23 | MINI DISJUNTOR 23KV | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MD38 | MINI DISJUNTOR 138KV | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MD69 | MINI DISJUNTOR 69KV | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDBC | MINI DISJUNTOR BARRA PAINEL | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDBP | MINI DISJUNTOR BARRA PATIO | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDCA | MINI DISJUNTOR VCA | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDCC | MINI DISJUNTOR VCC | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDCD | MINI DISJUNTOR CDC | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDCM | MINI DISJUNTOR COMANDO | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDFA | MINI DISJUNTOR FASE A | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDFB | MINI DISJUNTOR FASE B | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDFC | MINI DISJUNTOR FASE C | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDLC | MINI DISJUNTOR LT PAINEL | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDLP | MINI DISJUNTOR LT PATIO | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDLT | MINI DISJUNTOR LT | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDMT | MINI DISJUNTOR TP MEDICAO CDC | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDOL | MINI DISJUNTOR OLEO | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDPM | MINI DISJUNTOR PAINEL MEDICAO | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDPN | MINI DISJUNTOR TP PAINEL | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDTM | MINI DISJUNTOR TP MEDICAO | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| MDTP | MINI DISJUNTOR TP | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |

## Sigla ME*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| MEMB | RUPTURA MEMBRANA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| MEST | 90 - POSICAO MESTRE | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| MEST | 90 - POSICAO MESTRE | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |

## Sigla ML*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| MLCC | FALTA VCC OU MOLA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| MLRE | MAL FUNCIONAMENTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla MN*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| MNAT | OPERACAO DO NEUTRO RESSONANTE | Custom | Discrete | ReadWrite | Transit;MANUAL;AUTOMATICO;Error |  |  |  |

## Sigla MO*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| MOD | MODO DE OPERAÇÃO | Custom | Discrete | ReadWrite | Transit;RELIGADOR;CHAVE;Error |  |  |  |
| MOLA | MOLA | Custom | Discrete | Read | Transit;CARREGADA;DESCARREGADA;Error |  |  |  |

## Sigla MT*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| MTRF | MODULO TRANSFERIDO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla N*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| N | NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla NE*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| NEGT | NEGATIVADO A TERRA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla OA*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| OAUT | OPERAÇÃO PELO AUTOMATISMO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla OI*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| OI | OPERACAO INDEVIDA SECCIONADORA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla OL*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| OLFL | FALHA FLUXO DE OLEO BOMBA | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| OLFL | FALHA FLUXO DE OLEO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla OP*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| OPER | CONTAGEM DE OPERACOES | Contagem de Operação | Analog |  |  | Discreto | - |  |

## Sigla P*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| P | POTENCIA ATIVA | Valor Medido | Analog |  |  | Potência Ativa | MW |  |
| P51F | PICK UP 51F | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| P51N | PICK UP 51N | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (P — potência ativa)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. `P` tem 21 ocorrências reais, `Measurement Type=ActivePower`, mas com unidade **inconsistente por equipamento**: `MW` na maioria, `kW` em pelo menos um módulo — a LP padroniza só `MW` (ver tabela acima). Vale checar se o motor normaliza a unidade na hora de casar ou se herda a que vier do input real. `P51F`/`P51N` (pickup de sobrecorrente, Discrete) não aparecem nesta amostra.

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| PALT | PERFIL DE AJUSTE ALTERNATIVO | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| PALT | PERFIL DE AJUSTE ALTERNATIVO | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |

## Sigla PB*

_10 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| PB | PROTECAO DE BARRA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PB1 | PROTECAO DE BARRA P1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PB2 | PROTECAO DE BARRA P2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PBEX | FUNCAO PROTECAO DE BARRA | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| PBF | PROTECAO DE BARRA FASE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PBF1 | PROTECAO DE BARRA FASE E1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PBF2 | PROTECAO DE BARRA FASE E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PBN | PROTECAO DE BARRA NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PBN1 | PROTECAO DE BARRA NEUTRO 1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PBN2 | PROTECAO DE BARRA NEUTRO 2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla PE*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| PERP | PERMISSAO PARALELISMO | Custom | Discrete | Read | Transit;NÃO PERMITIDO;PERMITIDO;Error |  |  |  |

## Sigla PL*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| PLLR | 43 - CHAVE LOCAL REMOTO RELE PARALELISMO | Custom | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |

## Sigla PN*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| PNOR | PERFIL DE AJUSTE NORMAL | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| PNOR | PERFIL DE AJUSTE NORMAL | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |

## Sigla PO*

_5 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| PORO | PORTAO SUBESTACAO | Custom | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| PORT | PORTA SUBESTACAO | Custom | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| PORU | PORTA UTR | Custom | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| POST | POSITIVO A TERRA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| POTT | TRIP POR TELEPROTECAO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla PP*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| PPOT | PERDA DE POTENCIAL | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla PR*

_7 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| PRES | ALARME PREDIAL | Custom | Discrete | ReadWrite | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| PRES | ALARME PREDIAL | Custom | Discrete | Read | Transit;DESATIVADO;ATIVADO;Error |  |  |  |
| PREX | ALARME PREDIAL PRESENCA EXTERNA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PRIN | ALARME PREDIAL PRESENCA INTERNA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PROL | ALARME PRESSAO DE OLEO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| PROT | PROTECAO BLOQUEADA | Custom | Discrete | Read | Transit;NORMAL;BLOQUEADA;Error |  |  |  |
| PRTF | FALHA PROTECAO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla PV*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| PVRF | PERDA DE TENSAO DE REFERENCIA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla Q*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| Q | POTENCIA REATIVA | Valor Medido | Analog |  |  | Potência Reativa | MVAR |  |

## Sigla R*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| R90 | 90 - FUNCAO REGULADOR | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| R90 | 90 - FUNCAO REGULADOR | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |

## Sigla RE*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| REFE | VARIAÇÃO DA TENSAO DE REFERÊNCIA POR MVA | Custom | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| RETA | ALARME RETIFICADOR | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla RG*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| RGBL | RELIGADOR BLOQUEADO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla RL*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| RLCD | 43 - CHAVE LOCAL REMOTO COMUTADOR | Custom | Discrete | Read | Transit;REMOTO;LOCAL;Error |  |  |  |
| RLFU | FALHA FUSIVEL | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla RV*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| RVTL | TENSAO BAIXA RELE 90 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla RX*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| RXER | FALHA RECEPCAO DADOS RX | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |
| RXTR | TRIP EXTERNO RECEBIDO | Custom | Discrete | Read | Transit;NORMAL;RECEBIDO;Error |  |  |  |

## Sigla S*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| S | POTENCIA APARENTE | Valor Medido | Analog |  |  | Potência Aparente | MVA |  |

## Sigla SC*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| SCAR | SECADOR DE AR | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla SE*

_15 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| SECB | SECCIONADORA BYPASS | SwitchStatus | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECB | SECCIONADORA BYPASS | SwitchStatus | Discrete | ReadWrite | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECC | SECCIONADORA CARGA | SwitchStatus | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECC | SECCIONADORA CARGA | SwitchStatus | Discrete | ReadWrite | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECF | SECCIONADORA FONTE | SwitchStatus | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECF | SECCIONADORA FONTE | SwitchStatus | Discrete | ReadWrite | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECG | SECCIONADORA TERRA | SwitchStatus | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECG | SECCIONADORA TERRA | SwitchStatus | Discrete | ReadWrite | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECI | SECCIONADORA INTERBARRAS | SwitchStatus | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECI | SECCIONADORA INTERBARRAS | SwitchStatus | Discrete | ReadWrite | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECL | SECCIONADORA INTERLINHAS | SwitchStatus | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECL | SECCIONADORA INTERLINHAS | SwitchStatus | Discrete | ReadWrite | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECT | SECCIONADORA TRANSFERENCIA | SwitchStatus | Discrete | Read | Transit;ABERTO;FECHADO;Error |  |  |  |
| SECT | SECCIONADORA TRANSFERENCIA | SwitchStatus | Discrete | ReadWrite | Transit;ABERTO;FECHADO;Error |  |  |  |
| SEXT | SENSOR PRESENCA EXTERNO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

### Nomenclaturas reais observadas (SEC* — seccionadora)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. Das 6 posições de seccionadora da LP, 4 aparecem: `SECF` (SECCIONADORA FONTE, 6x, `ReadWrite`/`MultiCoord`, MM `ABRIR@FECHAR___ABERTO@FECHADO`), `SECB` (BYPASS, 6x), `SECC` (CARGA, 4x, mesmo padrão `MultiCoord`), `SECG` (TERRA, 2x — mas com MM diferente: `null@null___ABERTO@FECHADO___SwitchStatus_D_TS_SO_terra`, sufixo `_terra` específico e sem par de comando `ABRIR@FECHAR`, i.e. seccionadora de terra aparenta ser só status, sem comando modelado nesta amostra). `SECI`/`SECL`/`SECT` não aparecem (0 ocorrências) — interbarras/interlinhas/transferência não existem nesta subestação real.
- Confirma a regra 7 (fusão → `MultiCoord`) e é a base direta da whitelist da regra 10: `SECF`/`SECC`/`SECB` aqui batem com as siglas de posição da whitelist `config.siglas_por_equipamento["Seccionadora"]`; `DSEC` (defeito) e `43LR` (chave local/remoto) da mesma whitelist também têm presença real forte (16 e 24 ocorrências, `SingleBit`/`Read`).

## Sigla SF*

_5 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| SF6 | BAIXA PRESSAO SF6 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| SF6A | ALARME BAIXA PRESSAO SF6 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| SF6B | BLOQUEIO BAIXA PRESSAO SF6 | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| SFAB | SF6 BLOQUEIO ABERTURA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| SFFC | SF6 BLOQUEIO FECHAMENTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla SG*

_4 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| SGF | FUNCAO SGF | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| SGF | FUNCAO SGF | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |
| SGFT | TRIP SGF | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| SGT2 | TRIP SGF E2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla SI*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| SIMD | TRIP DEFEITO SIMULTANEO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| SINT | SENSOR PRESENCA INTERNO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| SIRE | ALARME SONORO | Custom | Discrete | Read | Transit;NORMAL;DISPARADA;Error |  |  |  |

## Sigla SO*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| SOBC | SOBRECARGA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| SOTF | TRIP FECHAMENTO SOB FALTA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| SOTX | FUNCAO FECHAMENTO SOB FALTA | Enabled | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |

## Sigla ST*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| STMP | SENSOR TEMPERATURA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla TA*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| TAL | TAL - FUNCAO TRANSFERENCIA AUTOMATICA DE LINHA | Custom | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |

## Sigla TD*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| TDS | FUNCAO TRIP DEFEITO SIMULTANEO | Enabled | Discrete | ReadWrite | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |

## Sigla TE*

_4 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| TEA | 49 - ALARME TEMPERATURA ENROLAMENTO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| TED | 49 - TRIP TEMPERATURA ENROLAMENTO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| TENR | TEMPERATURA ENROLAMENTO | Valor Medido | Analog |  |  | Temperatura | C |  |
| TEXT | TRIP EXTERNO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

## Sigla TO*

_7 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| TOA | 26 - ALARME TEMPERATURA OLEO | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| TOC | 26 - ALARME TEMPERATURA OLEO CDC | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| TOD | 26 - TRIP TEMPERATURA OLEO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| TOEA | 26 49 - ALARME TEMPERATURA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| TOED | 26 49 - TRIP TEMPERATURA | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| TOL2 | TEMPERATURA OLEO 2 | Valor Medido | Analog |  |  | Temperatura | C |  |
| TOLE | TEMPERATURA OLEO | Valor Medido | Analog |  |  | Temperatura | C |  |

## Sigla TP*

_6 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| TPAM | TEMPERATURA AMBIENTE | Valor Medido | Analog |  |  | Temperatura | C |  |
| TPBT | TEMPERATURA BATERIAS | Valor Medido | Analog |  |  | Temperatura | C |  |
| TPIN | TRANSFERENCIA DE PROTECAO | Custom | Discrete | Read | Transit;COMPLETA;INCOMPLETA;Error |  |  |  |
| TPNO | PROTECAO NAO TRANSFERIDA | Custom | Discrete | Read | Transit;NORMAL;INCOMPLETA;Error |  |  |  |
| TPOK | PROTECAO TRANSFERIDA | Custom | Discrete | Read | Transit;NORMAL;COMPLETA;Error |  |  |  |
| TPPM | TPPM - FUNCAO TRANSFERENCIA COM PARALELISMO MOMENTANEO | Custom | Discrete | Read | Transit;INCLUIDO;EXCLUIDO;Error |  |  |  |

## Sigla TR*

_4 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| TRAL | TRIP PARA ALIMENTADORES | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| TRIP | TRIP | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| TRPR | TRIP RECEBIDO | Custom | Discrete | Read | Transit;NORMAL;RECEBIDO;Error |  |  |  |
| TRPT | TRIP TRANSMITIDO | Custom | Discrete | Read | Transit;NORMAL;TRANSMITIDO;Error |  |  |  |

## Sigla TS*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| TSCO | TEMPERATURA SALA DE COMANDO | Valor Medido | Analog |  |  | Temperatura | C |  |

## Sigla TX*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| TXTR | TRIP EXTERNO TRANSMITIDO | Custom | Discrete | Read | Transit;NORMAL;TRANSMITIDO;Error |  |  |  |

## Sigla UM*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| UMID | UMIDADE | Custom | Analog |  |  | Umidade | % |  |

## Sigla V*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| V | TENSAO | Valor Medido | Analog |  |  | Tensão | kV |  |
| V | TENSAO | Valor Medido | Analog |  |  | Tensão | V |  |

## Sigla VA*

_8 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| VA | TENSAO FASE A | Valor Medido | Analog |  |  | Tensão | kV |  |
| VA | TENSAO FASE A | Valor Medido | Analog |  |  | Tensão | V |  |
| VAB | TENSAO FASE AB | Valor Medido | Analog |  |  | Tensão | kV |  |
| VAB | TENSAO FASE AB | Valor Medido | Analog |  |  | Tensão | V |  |
| VABI | TENSAO FASE AB - LADO FONTE | Valor Medido | Analog |  |  | Tensão | kV |  |
| VABX | TENSAO FASE AB - LADO CARGA | Valor Medido | Analog |  |  | Tensão | kV |  |
| VA_B | TENSAO BARRA FASE A | Valor Medido | Analog |  |  | Tensão | kV |  |
| VA_L | TENSAO LINHA FASE A | Valor Medido | Analog |  |  | Tensão | kV |  |

### Nomenclaturas reais observadas (VA/VB/VC — tensão)

Cruzado com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. Achado notável: as tensões **fase-neutro** (`VA`, `VB`, `VC`) quase não aparecem — só `VB` tem 1 ocorrência real (`kV`); `VA`/`VC` têm **0**. Já as tensões **fase-fase** aparecem fortemente: `VAB` (28x, `kV` e `V` misturados), `VBC`/`VCA` (7x cada, só `kV`). Ou seja, nesta subestação a medição real é majoritariamente line-to-line, não line-to-neutral — mesmo padrão possivelmente recorrente em outras GTDs (a rede de distribuição/subtransmissão tende a medir tensão de linha). `VABI`/`VABX`/`VA_B`/`VA_L` (variantes por lado/localização) não aparecem nesta amostra.

## Sigla VB*

_9 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| VB | TENSAO FASE B | Valor Medido | Analog |  |  | Tensão | kV |  |
| VB | TENSAO FASE B | Valor Medido | Analog |  |  | Tensão | V |  |
| VBAT | TENSAO BATERIAS | Valor Medido | Analog |  |  | Tensão | V |  |
| VBC | TENSAO FASE BC | Valor Medido | Analog |  |  | Tensão | kV |  |
| VBC | TENSAO FASE BC | Valor Medido | Analog |  |  | Tensão | V |  |
| VBCI | TENSAO FASE BC - LADO FONTE | Valor Medido | Analog |  |  | Tensão | kV |  |
| VBCX | TENSAO FASE BC - LADO CARGA | Valor Medido | Analog |  |  | Tensão | kV |  |
| VB_B | TENSAO BARRA FASE B | Valor Medido | Analog |  |  | Tensão | kV |  |
| VB_L | TENSAO LINHA FASE B | Valor Medido | Analog |  |  | Tensão | kV |  |

## Sigla VC*

_13 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| VC | TENSAO FASE C | Valor Medido | Analog |  |  | Tensão | kV |  |
| VC | TENSAO FASE C | Valor Medido | Analog |  |  | Tensão | V |  |
| VCA | TENSAO FASE CA | Valor Medido | Analog |  |  | Tensão | kV |  |
| VCA | TENSAO FASE CA | Valor Medido | Analog |  |  | Tensão | V |  |
| VCAI | TENSAO FASE CA - LADO FONTE | Valor Medido | Analog |  |  | Tensão | kV |  |
| VCAM | FALTA VCA PAINEL MEDICAO | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  | 27CA |
| VCAX | TENSAO FASE CA - LADO CARGA | Valor Medido | Analog |  |  | Tensão | kV |  |
| VCC | TENSAO CORRENTE CONTINUA | Valor Medido | Analog |  |  | Tensão | V |  |
| VCC1 | TENSAO CORRENTE CONTINUA 1 | Valor Medido | Analog |  |  | Tensão | V |  |
| VCC2 | TENSAO CORRENTE CONTINUA 2 | Valor Medido | Analog |  |  | Tensão | V |  |
| VCPB | VCC PROTECAO BARRA | Custom | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| VC_B | TENSAO BARRA FASE C | Valor Medido | Analog |  |  | Tensão | kV |  |
| VC_L | TENSAO LINHA FASE C | Valor Medido | Analog |  |  | Tensão | kV |  |

## Sigla VD*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| VDIF | 25 - DIFERENCA TENSAO | Valor Medido | Analog |  |  | Tensão | kV |  |

## Sigla VF*

_17 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| VF | VENTILACAO FORCADA | Custom | Discrete | Read | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VF | VENTILACAO FORCADA | Custom | Discrete | ReadWrite | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VF1 | VENTILACAO FORCADA 1 | Custom | Discrete | Read | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VF1 | VENTILACAO FORCADA 1 | Custom | Discrete | ReadWrite | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VF2 | VENTILACAO FORCADA 2 | Custom | Discrete | Read | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VF2 | VENTILACAO FORCADA 2 | Custom | Discrete | ReadWrite | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VF3 | VENTILACAO FORCADA 3 | Custom | Discrete | Read | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VF3 | VENTILACAO FORCADA 3 | Custom | Discrete | ReadWrite | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VF4 | VENTILACAO FORCADA 4 | Custom | Discrete | Read | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VF4 | VENTILACAO FORCADA 4 | Custom | Discrete | ReadWrite | Transit;DESLIGADO;LIGADO;Error |  |  |  |
| VFAM | VENTILACAO FORCADA AUTOMATICA MANUAL | Custom | Discrete | Read | Transit;AUTOMATICO;MANUAL;Error |  |  |  |
| VFAR | VENTILACAO FORCADA AUTOMATICO REMOTO | Custom | Discrete | Read | Transit;DESABILITADO;HABILITADO;Error |  |  |  |
| VFCH | CHAVE GERAL VENTILACAO FORCADA | Custom | Discrete | Read | Transit;LIGADO;DESLIGADO;Error |  |  |  |
| VFDE | CHAVE VENTILACAO FORCADA DESLIGADA | Custom | Discrete | Read | Transit;DESABILITOU;HABILITOU;Error |  |  |  |
| VFMA | CHAVE VENTILACAO FORCADA MANUAL | Custom | Discrete | Read | Transit;DESABILITOU;HABILITOU;Error |  |  |  |
| VFRE | CHAVE VENTILACAO FORCADA REMOTO | Custom | Discrete | Read | Transit;DESABILITOU;HABILITOU;Error |  |  |  |
| VFTP | TRIP FALHA REFRIGERACAO | Custom | Discrete | Read | Transit;NORMAL;FALHA;Error |  |  |  |

## Sigla VI*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| VIN | TENSAO DE ENTRADA | Valor Medido | Analog |  |  | Tensão | V |  |

## Sigla VM*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| VMTC | FALTA VCC VCA MOTOR COMANDO | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |

## Sigla VO*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| VOUT | TENSAO DE SAIDA | Valor Medido | Analog |  |  | Tensão | V |  |

## Sigla VR*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| VREF | TENSAO DE REFERENCIA | Valor Medido | Analog |  |  | Tensão | V |  |

## Sigla ZE*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| ZERO | AUTO ZERO | Custom | Discrete | Write | Transit;;;Error |  |  |  |

## Sigla ZH*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| ZHI | FALTA ALTA IMPEDANCIA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |

## Sigla ZL*

_1 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| ZLO | FALTA BAIXA IMPEDANCIA | Custom | Discrete | Read | Transit;NORMAL;FALTA;Error |  |  |  |

## Outras / Não classificadas

_10 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| 5BKP | 50 51 - SOBRECORRENTE BACKUP | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 5F | 50 51 - SOBRECORRENTE FASE | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 5FA | 50 51 - SOBRECORRENTE FASE A | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 5FB | 50 51 - SOBRECORRENTE FASE B | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 5FC | 50 51 - SOBRECORRENTE FASE C | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 5FN | 50 51 - SOBRECORRENTE FASE NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 5FN1 | 50 51 - SOBRECORRENTE FASE NEUTRO 1 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 5FN2 | 50 51 - SOBRECORRENTE FASE NEUTRO 2 | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 5N | 50 51 - SOBRECORRENTE NEUTRO | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |
| 5NBK | 50 51 - SOBRECORRENTE NEUTRO BACKUP | RelayTrip | Discrete | Read | Transit;NORMAL;ATUADO;Error |  |  |  |

---

## Cobertura

- Total de siglas na LP (linhas válidas, Discrete + Analog): **754**
- Total de siglas cobertas neste documento: **754**
- Discrete: 692 | Analog: 62
- Famílias geradas: 151

Cobertura: OK — todas as siglas da LP aparecem em alguma família acima.
