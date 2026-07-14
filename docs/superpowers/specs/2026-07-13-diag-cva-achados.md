# Diagnóstico CVA — Achados (SP-CVA Fase 1, Task 1)

**Data:** 2026-07-13
**Script:** `bench/diag_cva.py` (`PYTHONPATH=src python bench/diag_cva.py`, log completo em `bench/resultados/diag_cva.log`)
**Input:** `C:\Users\vinic\Documents\docs importantes\RGE\CVA\CVA - Pontos Por Equipamentos DNP_V03 - COS - resumida.xlsx` (sheets BC1/BC2/BC5_6/CVA11 dentro do escopo)
**Lista padrão:** `docs/Pontos Padrao ADMS_v8.xlsx` (default do projeto)
**Template:** `docs/dnp3_template.xlsx`

Não altera produção — só instrumenta e documenta. Números abaixo são do rodar real do script, não estimados.

---

## Achado-chave: nenhuma perda silenciosa nas sheets/casos investigados

O script rastreou os 7 comandos (direção Output) detectados na entrada das sheets BC1/BC2/BC5_6/CVA11 e comparou contra a saída (TDT final ∪ revisão). Resultado: **`AUSENTE (perda silenciosa): 0`** — todo comando termina em `TDT ReadWrite` (fundido) ou em algum item de revisão com motivo rastreável. O que o usuário percebe como "sumiço" (itens 1b/3/5/10) é **visibilidade**, não perda de dado: os comandos caem em revisão com motivos que hoje renderizam `"—"` na UI (E6, Task 2 — não mapeados em `_MOTIVO_LABEL`) e/ou são consequência direta da colisão de módulo do item 11.

Nota de método: a 1ª rodada do script tinha um bug de instrumentação (comparava a chave de agrupamento do `dc_pairer` usando o registro capturado ANTES da classificação, cujo `sigla_sinal` ainda é `None` — todo comando fundido aparecia como falso "AUSENTE"). Corrigido re-resolvendo a chave a partir do registro em `decididos` (pós-classificação, pré-`dc_pairer.parear`) antes de comparar. Ver `bench/diag_cva.py:_destino_comando`.

---

## Item 1b — BC1: comando faltando "endereço 80 dos comandos"

**Evidência (`bench/diag_cva.py`, seção 1, sheet BC1):**
```
linha=14  texto='Disjuntor 52-08 (18Q0) - Abrir/Fechar'  endereco=80  destino=revisão: comando_sem_discreto
  -> sigla do comando (se decidido): 'DJA1'
  -> registros decididos no mesmo equipamento ('52-08'): BC1:21:DJF1:Input, BC1:22:DJF1:Input, BC1:32:MOLA:Input, ...
```

**Interpretação confirmada:** o endereço 80 (comando de Abrir/Fechar do Disjuntor 52-08) **não desaparece** — chega a `decididos` com sigla `DJA1`, mas o par de status do mesmo equipamento (linhas 21/22, texto "Fechado"/"Aberto") foi resolvido para `DJF1` por `pareamento_polaridade.forcar_polaridade_equipamento` (`src/tdt/pareamento_polaridade.py:91-151`). `dc_pairer.parear` agrupa por `(módulo, equipamento, sigla)` (`src/tdt/dc_pairer.py:21-25`) — como o comando ficou com sigla `DJA1` e o status com `DJF1`, caem em grupos **diferentes**: o grupo do comando não tem input → `motivo="comando_sem_discreto"` (`src/tdt/dc_pairer.py:97-102`).

**Causa raiz:** `forcar_polaridade_equipamento` só reconhece pares de status com prefixos `LIGAD/FECHAD` × `DESLIGAD/ABERT` (`src/tdt/pareamento_polaridade.py:16-17`) — o texto do comando ("Abrir/Fechar", verbo infinitivo, uma linha só) não bate em nenhum dos dois prefixos, então o comando **não** passa pela heurística de polaridade e vai para o scorer semântico normal, que escolhe `DJA1` em vez de `DJF1` (ambiguidade real entre as duas siglas na lista padrão para descrições genéricas de comando de disjuntor — mesma causa-raiz do item 1a do mapa da spec, `docs/superpowers/specs/2026-07-13-sp-correcoes-tdt-cva-design.md:20`, só que aqui do lado do COMANDO, não do status).

**Escopo:** E3 (pareamento) + E5 (visibilidade — motivo `comando_sem_discreto` não está em `_MOTIVO_LABEL` hoje, Task 2 já cobre).

---

## Item 3 e 5 — BC2: DJF1 classificado sem comando / comando do DJF1 não pareado

**Evidência (`bench/diag_cva.py`, seção 1, sheet BC2):**
```
linha=14  texto='Disjuntor 52-06 (28QO) - Abrir/Fechar'  endereco=90  destino=revisão: estado_sem_candidato
```

**Interpretação confirmada:** mecanismo **diferente** do item 1b/10 — este comando nem chega a `decididos`. `estado_sem_candidato` é emitido dentro de `_classificar_sinal` quando `semantica_estados.filtrar_por_estado` (gate SP-E D2, `src/tdt/pipeline.py:284-293`) zera **todos** os candidatos antes mesmo do roteador rodar — o comando nunca ganha sigla, então nunca chega ao `dc_pairer` (não é o gate `compatibilidade_texto`/D5 do `dc_pairer`, que é outro módulo). Precisa de diagnóstico adicional em `src/tdt/semantica_estados.py` (fora do escopo desta Task 1 — motivo já isolado, mas o predicado exato que zera precisa de leitura própria antes de propor fix).

**Escopo:** E3 (classificação/estado).

---

## Item 10 — BC5_6: comando DJF1 desaparecido

**Evidência (`bench/diag_cva.py`, seção 1, sheet BC5_6):**
```
linha=8   texto='Disjuntor 52-15 (19Q0) - Abrir/Fechar'   endereco=100  destino=revisão: comando_sem_discreto
linha=9   texto='Proteção 27 - Excluir/Incluir'           endereco=101  destino=TDT ReadWrite (fundido com id do status=BC5_6:34)
linha=10  texto='Disjuntor 52-14 (30Q0) - Abrir/Fechar'   endereco=102  destino=revisão: comando_sem_discreto
```

**Interpretação confirmada:** mesmíssimo mecanismo do item 1b (`DJA1` no comando × `DJF1` forçado no status, `dc_pairer` agrupa por sigla e separa). Note que o 3º comando da sheet (endereço 101, "Proteção 27") **funde corretamente** — BC5_6 não tem colisão de módulo com outra sheet (ver item 11 abaixo: só BC1↔BC2 colidem), então esse par sobrevive até o TDT final. Confirma que o "desaparecimento" percebido pelo usuário é: (a) motivo de revisão não rotulado na UI (renderiza `"—"`, Task 2 já cobre) e (b) nos casos BC1/BC2 (não BC5_6), a colisão de Custom ID do item 11 remove até os pares que fundiram corretamente.

**Escopo:** mesmo de 1b — E3 + E5.

---

## Item 8 — CVA11: VAB com tipo=Input (classificação errada)

**Evidência (`bench/diag_cva.py`, seção 2, sheet CVA11):**
```
MapaColunas CVA11: header_row=3 colunas={'descricao': 4, 'indice': 9}
coluna TIPO escolhida por _col_tipo: None

linha=5  texto='Tensão Barra AB'  categoria(estruturação)=Discrete  direcao(estruturação)=Input  confiavel=False
         cel_tipo=None  veio_de=default (sem evidência -- nem coluna TIPO nem marcador bateram)
         destino=revisão: categoria_ambigua
linha=6  texto='Tensão Barra BC'  ... destino=revisão: categoria_ambigua
linha=7  texto='Tensão Barra CA'  ... destino=revisão: categoria_incompativel
```

**Interpretação confirmada:** a hipótese "tipo na linha numa sheet, na coluna em outra" (anot.txt item 8) é a causa. Em `CVA11`, `analise_colunas._col_tipo` (`src/tdt/analise/analise_colunas.py:218-237`) **não encontra** nenhuma coluna cujos valores casem o vocabulário de tipo (score < 0.5 em todas) — devolve `None`. Também não há marcador de seção de linha (`estruturador._eh_marcador`, `src/tdt/normalizacao/estruturador.py:34-39`) antes das linhas de VAB/VBC/VCA. Sem nenhuma das duas evidências, `estruturador.estruturar` cai no default hard-coded `secao = ("Discrete", "Input")` (`src/tdt/normalizacao/estruturador.py:67`, `categoria, direcao = cat_dir or secao` em `:89`) — VAB/VBC/VCA (sinais analógicos de tensão) nascem classificados como **Discrete/Input**, com `categoria_confiavel=False` (`:90`). O dual-pass subsequente (dois bundles, Discrete e Analog) não resolve o conflito de forma limpa: VAB/VBC caem em `categoria_ambigua`, VCA em `categoria_incompativel` — nenhum chega ao TDT como Analog.

O layout real do CVA11 tem o TIPO em algum outro formato (bloco/linha não capturado pelos dois heurísticos atuais) — precisa de leitura direta do layout da sheet para a Task 9 (não incluída aqui; Task 9 do plano já aponta os sites certos).

**Escopo:** E1→fix VAB, Task 9 (bloqueada por dado — agora desbloqueada pelo achado acima).

---

## Item 11 — BC1/BC2: módulo incorretamente nomeado (colisão)

**Evidência (`bench/diag_cva.py`, seção 4):** **21 grupos** de Custom ID colidido, **todos** entre `BC1` e `BC2`, e em **todos** os 21 grupos o Custom ID final carrega o prefixo de módulo `BC1` (isto é: os pontos da sheet `BC2` foram resolvidos internamente como módulo "BC1" também) — confirma exatamente a descrição do usuário ("os pontos da BC2 estavam como se fossem do módulo da BC1"). Amostra:
```
Custom ID=CVA_BC1_BC1_VAB_UTR_CVA_1     id=BC1:5 / BC2:5   sigla=VAB   sheets=['BC1','BC2']
Custom ID=CVA_BC1_BC1_27_UTR_CVA_1      id=BC1:38 / BC2:38 sigla=27    sheets=['BC1','BC2']  <- é o status que fundiu com os comandos dos itens 1b/10 (endereços 81/91)
... (21 grupos, lista completa em bench/resultados/diag_cva.log)
```

**Interpretação confirmada:** `engine_tdt.particionar_custom_id_duplicado` (`src/tdt/engine_tdt.py:321-344`) já detecta a colisão e manda **todos** os registros do grupo para revisão com `motivo="custom_id_duplicado"` — nenhum sai calado do TDT. Mas hoje o motivo é genérico (não diferencia "colidiu dentro da mesma sheet" de "colidiu entre sheets distintas, é o dado de origem com módulo errado"), e o comando fundido dos itens 1b/10 (endereços 81/91, `BC1:38`/`BC2:38`) é vítima colateral: mesmo tendo pareado corretamente com o status, sai do TDT porque o Custom ID colide. Confirma a "hipótese H4" do plano (`docs/superpowers/plans/2026-07-13-sp-correcoes-tdt-cva.md:464`).

**Escopo:** E4 (Task 6, já planejada — motivo específico `modulo_duplicado_entre_sheets`; correção do dado de origem é fora de alcance).

---

## Item 14 (verificação) — tensões entre fases fora do domínio PhaseCode

Nenhum registro com `eletrico.fase == "CA"` (ou fora do domínio interno `FASES`) apareceu no TDT final desta lista CVA — a causa já está confirmada no template (ver spec `2026-07-13-sp-correcoes-tdt-cva-design.md:34`), só não há caso concreto NESTE dataset para servir de evidência adicional. Task 4b segue como planejada (a fixture sintética do Step 6 já cobre a regressão).

---

## Proposta de sub-tasks — Task 8 (pareamento CVA, pós-diagnóstico)

Uma causa confirmada = uma sub-task, TDD + gate individual, formato das Tasks 4-5 do plano.

### Task 8.1 — Comando de disjuntor (Abrir/Fechar) não converge para a sigla do status pareado (DJA1×DJF1)
- **Causa:** confirmada acima (itens 1b, 10). `forcar_polaridade_equipamento` não reconhece comandos de uma linha só ("Abrir/Fechar"); o scorer normal desempata para a sigla errada.
- **Site:** `src/tdt/pareamento_polaridade.py` (estender reconhecimento de comando) OU `src/tdt/dc_pairer.py` (resolver mismatch de sigla dentro do mesmo equipamento antes de decidir "sem discreto").
- **Correção candidata a validar com o usuário:** quando um grupo `(módulo, equipamento)` tem exatamente 1 status de posição decidido (DJF1/DJA1/SEC\*) e 1 comando Output sem par na MESMA sigla, mas texto do comando bate no mesmo equipamento — re-chave o comando para a sigla do status antes do `dc_pairer` agrupar (ou dar um passo de reconciliação pós-scoring, análogo ao `forcar_polaridade_equipamento`, mas para comandos).
- **Teste-que-falha:** fixture com 1 comando "Abrir/Fechar" + par status Ligado/Desligado do mesmo equipamento, sigla do comando decidida diferente da sigla forçada do status → hoje cai em `comando_sem_discreto`; depois da correção, funde.

### Task 8.2 — `semantica_estados.filtrar_por_estado` zera candidatos de comando "Abrir/Fechar" (estado_sem_candidato)
- **Causa:** confirmada acima (itens 3, 5). Mecanismo isolado (`src/tdt/pipeline.py:284-293` → `src/tdt/semantica_estados.py`), mas o predicado exato que zera ainda não foi lido a fundo — abrir com leitura do módulo antes de propor a correção.
- **Site:** `src/tdt/semantica_estados.py` (`filtrar_por_estado`).
- **Teste-que-falha:** fixture com o texto exato "Disjuntor 52-06 (28QO) - Abrir/Fechar" (ou reduzido) contra candidatos DJF1/DJA1 da lista padrão → hoje zera; entender por quê antes de decidir se é afrouxar o gate ou é falta de vocabulário "Abrir/Fechar" no reconhecedor de estado.

### Task 8.3 — Par fundido corretamente ainda sai do TDT por colisão de Custom ID (consequência do item 11)
- **Já mitigada por Task 6** (visibilidade — motivo `modulo_duplicado_entre_sheets`). Não propor nova lógica de pareamento aqui: o par (`BC1:38`/`BC2:38`, sigla `27`, endereços 81/91) está correto: sai do TDT porque o Custom ID colide de verdade (é o mesmo módulo, dado de origem errado). Corrigir a *causa* é fora de alcance (dado do cliente); o caminho do operador para resolver na UI (renomear módulo em lote — Task 11, ou aviso explícito — Task 6) já cobre.
- **Ação:** nenhuma sub-task de pareamento nova; confirmar com o usuário que Task 6 + Task 11 (já planejadas) fecham este caso.

## Task 9 (CVA11 VAB) — confirmação dos sites, sem mudança na proposta do plano

O achado do item 8 acima confirma exatamente os dois sites já apontados no plano (`docs/superpowers/plans/2026-07-13-sp-correcoes-tdt-cva.md:470-477`): `analise_colunas.py:218-237` (`_col_tipo` retorna `None` para CVA11) e `estruturador.py:67,88-90` (default hard-coded quando nem coluna nem marcador batem). Task 9 pode ser instanciada como está no plano — o Step 1 (fixture sintética reproduzindo o layout CVA11) usa a evidência acima diretamente (linhas 5/6/7 da sheet, `header_row=3`, sem coluna tipo detectável).

---

## Resumo para aprovação do usuário (Task 1, Step 6 — parar e reportar)

| Item | Causa confirmada | Perda silenciosa? | Sub-task proposta |
|---|---|---|---|
| 1b | scorer DJA1×DJF1 do comando não converge com status forçado | Não — vai pra revisão (`comando_sem_discreto`), mas UI mostra "—" | Task 8.1 |
| 3, 5 | `semantica_estados` zera candidatos do comando (`estado_sem_candidato`) | Não — vai pra revisão, mas UI mostra "—" | Task 8.2 |
| 8 | CVA11 sem coluna TIPO nem marcador de seção → default Discrete/Input | Não — vai pra revisão (`categoria_ambigua`/`categoria_incompativel`) | Task 9 (já planejada) |
| 10 | mesma causa de 1b; 1 de 3 comandos da sheet funde OK (sem colisão) | Não | Task 8.1 |
| 11 | módulo BC2 nomeado como BC1 na origem — 21 grupos colididos | Não — vai pra revisão (`custom_id_duplicado`), inclui pares já fundidos (1b/10) | Task 6 (já planejada) + Task 8.3 (sem ação nova) |

Nenhum caso do anot.txt investigado aqui é bug de perda silenciosa de dado — é bug de **classificação/pareamento** (rastreável, corrigível com as sub-tasks acima) somado a bug de **visibilidade na UI** (Task 2, já planejada). Aguardando aprovação do usuário para instanciar Tasks 8.1/8.2 antes de implementar (Task 8, Step 2 do plano).
