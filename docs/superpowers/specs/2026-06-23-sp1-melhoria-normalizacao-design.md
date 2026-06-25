# SP1 — Melhoria da Normalização

**Data:** 2026-06-23
**Status:** Spec aprovada para implementação
**Parte crítica:** a normalização define o texto que TODOS os scorers consomem.
Lixo entra → lixo sai. Hoje: maiúsculas, acentos, espaços, abreviações,
stopwords, rejunção de siglas (tokenizer).

## Problemas observados nos dados reais
- Descrições com **boilerplate de equipamento**: "Disj. 52-1 (01Q0) - Baixa
  Pressão SF6 - Bloqueio" — o prefixo "Disj. 52-1 (01Q0)" dilui o match; o
  sinal está no rabo ("Baixa Pressão SF6 Bloqueio").
- **IDs de equipamento** (52-1, 01Q0, 89-16) viram ruído lexical e podem colidir
  com números de proteção (52 disjuntor × 52 função). Precisam ser separados/tagueados.
- **Erros de digitação** reais ("Corretnte" → "Corrente").
- Dicionário de abreviações ainda pequeno.

## Componentes (transforms SRP, TDD; cada um isolável e testável)

### N1. Dicionário de abreviações de domínio (expandido)
Curar a partir da skill `especialista-ADMS-TDT` (DISJ→DISJUNTOR, SECC→SECCIONADORA,
TRAFO→TRANSFORMADOR, CDC, REL→RELE, etc.). Whole-token (não quebra siglas).

### N2. Separação de IDs de equipamento × códigos de sinal
Regex para IDs de equipamento (`\d+-\d+`, `\d+Q\d+`) → remover/tagvear como
contexto (não entram no texto de matching), preservando números de **função**
(67, 87, 50N...). Evita colisão 52(disjuntor)×52(função). `# ponytail: regex
calibrada; ID de equipamento é contexto, não sinal.`

### N3. Remoção de boilerplate
Remover prefixos de equipamento repetidos ("DISJUNTOR 52-1" no início) quando há
descrição substantiva após o separador, mantendo o núcleo semântico.

### N4. Correção de typos (fuzzy contra vocabulário de domínio)
Vocabulário = termos das descrições da lista padrão. Corrige tokens com 1 edição
para um termo de domínio conhecido (rapidfuzz, threshold alto p/ não estragar
siglas). "CORRETNTE"→"CORRENTE".

### N5. Normalização de unidades (opcional)
kV/KV/Kv→KV, A/Amp→A, MW/Mw→MW — só onde ajuda o matching analógico.

## Ordem do pipeline de normalização
`bruto → N1(abrev) → N2(separa IDs) → N3(boilerplate) → N4(typos) → tokenizer(siglas) → canônico`
A função `canonizar` (já existe) passa a orquestrar esses transforms. Cada
transform é função pura `str -> str` (ou `str -> (str, contexto)` para N2).

## Config
`abreviacoes`, `corrigir_typos: bool`, `remover_ids_equipamento: bool` —
calibráveis; defaults seguros para não estragar siglas.

## Critérios de sucesso
- Siglas nunca são quebradas (teste dedicado: 67N, DJF1, SF6 preservados).
- "Corretnte de Desbalanço" → casa IN61 após N4.
- Boilerplate removido melhora acc@1 no harness sem novos FP.
- Cada transform tem teste isolado; `canonizar` tem teste de ponta a ponta.
