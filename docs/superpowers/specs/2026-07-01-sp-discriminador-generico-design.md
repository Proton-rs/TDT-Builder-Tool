# Spec: classificação e pareamento genéricos por discriminador + gate anti-regressão

Data: 2026-07-01

## Contexto

Dois sintomas reportados na revisão da LISTA 1 - GTD (`output/LISTA 1 - GTD/Auditoria_Revisao3.xlsx`):

1. **Sub-sinais caem no prefixo genérico.** "Religamento (79) - Bem Sucedido"
   decide `79` (genérico "FUNÇÃO RELIGAMENTO") em vez de `79OK`
   ("RELIGAMENTO COM SUCESSO"), que existe na Lista Padrão.
2. **Sinais catch-all não pareiam.** No módulo `GTD_11` há 1 Output ("Excluir")
   + 2 Inputs ("Excluída", "Atuado"), todos sigla `SGF` → `dc_pairer` agrupa por
   `(módulo, equipamento, sigla)` = `(GTD_11, None, SGF)` → 1 output + 2 inputs
   com chave idêntica → `pareamento_ambiguo` pra todos.

### Investigação (evidência, não suposição)

Comparação dos 3 audits salvos (Jun 24 GTA, Jun 26 v2, Jul 1 v3):

- "Bem Sucedido" → `79` em **todos os três**. `79OK` **nunca** foi atribuído em
  nenhum artefato salvo.
- SGF → `pareamento_ambiguo` em **todos os três**.
- `dc_pairer`, `filtro_preciso`, `expansao_candidatos` **não** mudaram no batch
  de 30-jun (git log confirma).

**Conclusão honesta:** os dois sintomas citados **não são regressões de
código** — são limitação persistente. Mas o batch de 30-jun (identidade de
módulo + coluna de sigla + SP-B/C/D2, tudo junto) **regrediu de fato outros
sinais** (337 classificações mudaram; `Desligar/Ligar` comando `DJA1→None`,
`Mola Descarregada` `DJA1→None`), misturado com melhorias, **sem nenhum gate
por-sinal pegar** — porque o benchmark tem só 28 pares sintéticos.

### Causa-raiz única (dois sintomas, um problema)

Uma **sigla genérica/catch-all** é atribuída a vários sinais distintos que só
diferem pelo **discriminador** (o "- ‹estado›" no fim da descrição: "Bem
Sucedido", "Bloqueado", "Excluir", "Atuado"). A sigla é grossa demais; o
discriminador carrega a distinção real. Isso quebra:
- **classificação** (o filho específico existe mas o pai-nu ganha no score bruto);
- **pareamento** (N sinais com a mesma sigla no módulo → o pairer não sabe
  qual Input casa com qual Output).

Por que o scorer não pega `79OK`: o texto tem o literal "(79)" + "RELIGAMENTO",
casando o genérico "79 FUNCAO RELIGAMENTO" (score 1.02). O discriminador
"SUCEDIDO" não casa lexicalmente "SUCESSO", e o embedding MiniLM também não
conecta (no repro `79OK` ficou fora do top-6, score < 0.42). `filtrar_especi-
ficidade` não resgata: `79` e `79OK` empatam em 1 token discriminador
("RELIGAMENTO") e o genérico vence no score.

## Auditoria de raciocínio (falhas encontradas na proposta inicial e correções)

Registrado por pedido explícito do usuário — para que a lógica fique documentada.

| # | Falha na proposta inicial | Correção |
|---|---|---|
| 1 | "Vocabulário de sinônimos sucedido↔sucesso" resolve 79OK | Não é genérico — vira lista infinita ("atacar sempre os mesmos pontos"). Mecanismo primário = **semântico** (embedding enriquecido / e5) + regra **estrutural** pai-vs-filho. Sinônimo curado só como último recurso medido. |
| 2 | "Expandir e pegar o filho de maior confiança" | O maior score entre filhos é o **errado** (repro: 79RE/79_INC > 79OK). Correção: **despriorizar o pai-nu** quando o texto tem discriminador, melhorar sensibilidade semântica do filho; se nenhum filho vence com folga → **revisão**, nunca genérico silencioso. Decidir errado é pior que revisar. |
| 3 | "Adicionar discriminador à chave do `dc_pairer`" | **Quebraria** o pareamento D+C: comando "Desligar" e status "Desligado" têm discriminadores diferentes de propósito. Correção: parear Output↔Input por **similaridade** de discriminador (rapidfuzz), não igualdade; Input sem par vira **Input standalone decidido**, não revisão. |
| 4 | "Lista de casos travados escrita à mão" mede "funciona pra todos" | Não escala nem é genérica. Correção: ground-truth extraído do **TDT real** (`docs/TDT/exportTDT_UTR_{GTD,FWB}_*.xlsx`, que nomeiam cada ponto `{SE}_{MODULO}_{EQUIP}_{SIGLA}` — a sigla verdadeira). Genérico, real, e serve de gate. |
| 5 | Validar em `SignalRecord` sintético (o repro) | Pula a estruturação/normalização real de uma planilha. Correção: gate e fixes validam **end-to-end** nos inputs não-homogêneos reais (`docs/input_nao_homogeneo_{1_GTD,2_FWB,3_GPR,4_GAU}.xlsx`) via `pipeline.executar`. |
| 6 | Tratar 79OK/SGF como "regressão a reverter" | Evidência: nunca funcionaram nos artefatos salvos. Correção: separar **capacidade nova** (79OK, SGF) de **recuperação de regressão** (DJA1/comando — funcionava e quebrou). Ambos no escopo, mas honestamente rotulados. |
| 7 | "Família = prefixo de 2 dígitos" cobre o problema | Catch-all alfabético (SGF/PRTF/MTRF/FCMR) **não** tem prefixo numérico. O conceito unificador é o **discriminador**: qualquer sigla atribuída a >1 descrição distinta no mesmo contexto é catch-all. O mecanismo genérico opera sobre discriminador, cobrindo numérico (79→79OK) e alfabético (SGF→SGFT). |

## Goal

Um mecanismo **genérico** (sem hardcode por sinal) que, para todo sinal:
1. quando existe variante mais específica que o casamento genérico, e o texto
   carrega o discriminador dela, **escolhe a variante** — ou manda pra revisão
   se a evidência não for clara (nunca genérico silencioso);
2. quando sinais catch-all no mesmo módulo formam pares comando↔status,
   **pareia por similaridade** de discriminador e mantém os sem-par como
   Inputs standalone decididos;
3. tudo medido contra **ground-truth do TDT real** e travado num **gate de
   regressão** que roda no closeout de qualquer mudança de matching/estrutura —
   a countermeasure que impede regredir o que já foi corrigido.

## Não-goals (escopo desta spec)

- Resolver a colisão de nomeação do catch-all (2 pontos `SGF` no mesmo módulo
  geram nome duplicado no TDT mesmo pareados corretamente) — isso é
  enriquecimento por-sigla (v6/SP-GT), fora daqui. Esta spec para de mandar SGF
  pra revisão errada e classifica "Atuado"→`SGFT` quando cabível, mas não
  inventa siglas novas.
- Trocar o modelo de embedding como decisão fechada — a Fase 1 **mede** se
  corpus enriquecido / e5 fecham o gap semântico; a troca (se houver) é
  consequência da medição, não premissa.

## Arquitetura (faseada)

### Fase 0 — Gate por endereço (nosso TDT × TDT real) + casos travados

**É o pré-requisito de tudo: o measuring stick.** Sem ele, qualquer fix é
"chutar e torcer", e regressões passam (foi o que aconteceu no batch 30-jun).

**Método PROVADO em dado real (2026-07-01):** o TDT real
(`exportTDT_UTR_{GTD,FWB}`) e o nosso TDT gerado têm o mesmo formato (sheets
`DNP3_DiscreteSignals`/`DNP3_AnalogSignals`), ambos com `Signal Name` (col 0,
`{SE}_{MODULO}_{EQUIP}_{SIGLA}` — sigla = último token após `_`) e endereço
`Input Coordinates`/INCOORDS (col 31). **A descrição bruta NÃO está no TDT real
(col Description vazia)** — por isso o join é por **endereço**, não por texto.
Protótipo rodado: 563 endereços em comum (GTD), **61.8% de concordância de
sigla** (348/563) — este é o baseline. As divergências já expõem bugs
sistêmicos reais (viram alvos das Fases 1-3):
- verbo de comando vazando como sigla (`LIGAR` onde real quer `BBFC`);
- sigla truncada ao dígito de estágio (`1`/`2` onde real quer `50F1`/`50F2`);
- seccionadora mal classificada (`43LR` onde real quer `DSEC`);
- estágio perdido (`51N` onde real quer `51N1`).

- **`bench/gate_tdt_real.py`**: dado (nosso_tdt.xlsx, tdt_real.xlsx), casa por
  INCOORDS nas sheets Discrete+Analog, extrai a sigla (último token do Signal
  Name) de cada lado, e reporta: nº de endereços em comum, % concordância,
  lista de divergências `addr, real, nosso, nome_real`. Função pura sobre 2
  workbooks — testável com fixtures pequenas.
- **`bench/casos_travados.csv`**: subconjunto **curado** de casos que já
  corrigimos ou que importam. Cada linha: `subestacao, endereco(INCOORDS),
  sigla_esperada, origem(data+motivo), nota`. Endereço é a chave (estável e
  presente no TDT real). **É a documentação viva do que foi corrigido** —
  quando um fix futuro quebra um caso travado, o gate acusa. Começa semeado das
  divergências conhecidas que formos corrigindo (79*/SGF/DJA1/comando/estágio).
- **`bench/regressao.py`**: orquestra — gera o nosso TDT do input real
  (`input_nao_homogeneo_1_GTD` → `exportTDT_UTR_GTD`; `_2_FWB` → `_FWB`) via
  `pipeline.executar`, chama `gate_tdt_real`, e cruza com `casos_travados.csv`.
  Imprime agregado (% vs real, antes/depois) + PASS/FAIL de cada caso travado.
  **Exit ≠ 0 se qualquer caso travado falha** (gate de closeout).
- Rodar no closeout de toda mudança de matching/estrutura, ao lado do `pytest`.
  Documentar no `AGENTS.md` raiz (Verification).

**Entregável da Fase 0:** baseline medido (61.8% GTD hoje) + os casos travados
semeados — a régua contra a qual as Fases 1-3 provam ganho **sem regredir os
348 que já batem**.

### Fase 1 — Seleção genérica filho-vs-pai (investigação → mecanismo → fix)

**Investigação primeiro (medir antes de wirar — princípio do projeto):**
- Medir, no GT real, com que frequência o pipeline hoje escolhe o pai genérico
  onde o TDT real quer um filho específico (quantifica o problema além do 79).
- Medir se **corpus enriquecido** (sigla+desc+metadados, já existe em
  `_corpus_enriquecido`) e/ou **e5** (dormant em `encoder`/`indice_vetorial`)
  rankeiam o filho certo (ex. 79OK) acima do pai — isto é, se o gap é semântico
  e um embedding melhor o fecha **genericamente**.

**Mecanismo (escolhido pela medição, não pré-fixado):** regra estrutural
genérica — quando o casamento top é um "pai-nu" (descrição-padrão sem
discriminador além do nome de função) **e** o texto tem tokens discriminadores
**e** existe filho na mesma família, **despriorizar o pai** e deixar os scorers
(com a melhor configuração medida) escolher o filho; se nenhum filho passa o
gap → revisão. Só se a medição mostrar que nenhum embedding fecha um gap
semântico específico é que entra um mapa de sinônimos **mínimo e medido**.

**Gate:** benchmark (28 pares) sem regressão **E** GT real melhora **E** casos
travados 79* passam a PASS. Método novo entra como candidato sem apagar o
original (princípio do projeto).

### Fase 2 — Pareamento genérico de catch-all (mecanismo concreto)

No `dc_pairer.parear`, o ramo "ambíguo" (N inputs + M outputs no mesmo grupo)
deixa de mandar tudo pra revisão. Em vez disso:
- Para cada Output, escolhe o Input de **maior similaridade de descrição**
  (rapidfuzz sobre a descrição normalizada, já é dependência), acima de um
  limiar calibrável (`config`). Funde os pares escolhidos (greedy, maior
  similaridade primeiro; cada Input/Output usado uma vez).
- Inputs sem par → **saída como Input standalone decidido** (não revisão).
- Outputs sem par → revisão (`pareamento_ambiguo`) — comando órfão é
  genuinamente ambíguo.
- Grupo com 1 input + 1 output continua fundindo direto (comportamento atual
  intacto).

**Gate:** casos travados SGF passam (Excluir↔Excluída pareado, Atuado
standalone) **E** nenhum pareamento correto pré-existente (1:1) regride, medido
no GT real.

### Fase 3 — Varredura das regressões reais do batch 30-jun

- Usar o gate (Fase 0) pra listar todos os sinais onde o TDT real quer sigla X
  e o pipeline hoje dá `None`/errado (ex. `Desligar/Ligar`→`DJA1`,
  `Mola Descarregada`). Priorizar por frequência.
- Rastrear a causa por sinal (identidade de módulo? pareamento? scoring?) e
  corrigir a causa-raiz, travando cada um nos casos.
- **Gate:** casos travados DJA1/comando passam; agregado GT real não regride.

## Validação com dados reais (requisito do usuário, vale para todas as fases)

Nenhuma fase fecha sem rodar `bench/regressao.py` sobre pelo menos
`input_nao_homogeneo_1_GTD` (par com `exportTDT_UTR_GTD`) e reportar: agregado
vs GT real (antes/depois) + PASS/FAIL de todos os casos travados. Validação em
`SignalRecord` sintético é só para desenvolvimento rápido, nunca como prova de
fechamento.

## Riscos

- **Cobertura parcial do join** (563 de 1641 endereços reais; nosso pipeline só
  emite ~630 discretos porque o resto vai pra revisão). Mitigação: o gate mede
  só sobre os endereços em comum; subir cobertura é consequência das Fases 1-3,
  não pré-requisito. Endereços sem par (só num lado) são reportados, não contam
  como erro.
- **INCOORDS como chave assume que o endereço do nosso input == o do TDT real.**
  Provado no protótipo (563 casam), mas nem todos: alguns divergem por o
  pipeline agrupar/subdividir módulo diferente. Mitigação: reportar taxa de
  casamento; divergência de endereço ≠ divergência de sigla (as duas são
  medidas separadas).
- **Despriorizar o pai pode regredir sinais que SÃO o pai-nu** (ex. "Função
  Religamento" puro). Mitigação: só despriorizar quando o texto tem token
  discriminador ausente da descrição do pai; o gate mede a regressão.
- **Pareamento por similaridade pode casar errado** em módulos com muitos
  catch-all. Mitigação: limiar calibrável + greedy maior-primeiro; o gate mede.
