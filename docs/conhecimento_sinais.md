# Base de conhecimento de sinais — Lista Padrão ADMS

Documento gerado automaticamente por `bench/minerar_lp_conhecimento.py` a partir de `docs/Pontos Padrao ADMS_v2.xlsx` (sheets `DiscreteSignals`, `AnalogSignals`, `DE->PARA`, `Message Mapping`).

Agrupamento por família reusa `tdt.motor_regras._numero_lider` (prefixo ANSI de 2 dígitos, ex.: `67N` -> `67`). Siglas sem prefixo ANSI numérico são agrupadas por prefixo alfabético de 2 letras (`ALPHA_xx`); o restante cai em **Outras / Não classificadas** — nenhuma sigla é descartada.

Este é o **esqueleto** (Task 1 do plano SP-L): dados minerados diretamente da LP, sem curadoria de conteúdo além de formatação. Tasks 2/3 adicionam semântica de domínio, exemplos e cross-references.

---

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

## Sigla IB*

_2 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| IB | CORRENTE FASE B | Valor Medido | Analog |  |  | Corrente | A |  |
| IBCC | CORRENTE CURTO CIRCUITO FASE B | Gravador de Falha | Analog |  |  | Corrente | A |  |

## Sigla IC*

_3 sigla(s)._

| Sigla | Descrição padrão | Tipo ADMS | Categoria | Direção | Estados / MM | Tipo medição | Unidade | DE->PARA |
|---|---|---|---|---|---|---|---|---|
| IC | CORRENTE FASE C | Valor Medido | Analog |  |  | Corrente | A |  |
| ICC | RESET CORRENTE DE CURTO CIRCUITO | Custom | Discrete | Write | Transit;;;Error |  |  |  |
| ICCC | CORRENTE CURTO CIRCUITO FASE C | Gravador de Falha | Analog |  |  | Corrente | A |  |

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

## Sigla PA*

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
