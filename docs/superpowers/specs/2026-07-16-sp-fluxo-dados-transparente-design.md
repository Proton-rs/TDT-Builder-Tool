# SP Fluxo de Dados Transparente — Conservação de Informação no Pipeline

**Data:** 2026-07-16
**Status:** Proposto
**Origem:** Regressão LVA AL21 — a coluna SIGLA era detectada por `analise_colunas._col_sigla()` mas o estruturador ignorava a informação quando a coluna MÓDULO também era reivindicada (`elif` tornava as duas resoluções mutuamente exclusivas; commit b9b0118). Sintoma percebido: "o programa parou de identificar a coluna das siglas". A informação existia, foi detectada e foi descartada no caminho. Corrigida pontualmente em 16/07; esta spec generaliza a proteção.
**Escopo:** Estabelecer invariantes de conservação de informação em todo o pipeline (estruturador → identidade → inferência → scoring → dc_pairer → normalizador_estrutural → engine_tdt) e os testes que os garantem.
**Relacionada:** regra universal "Não-regressão e fluxo de dados" no `CLAUDE.md`; testes de conservação existentes (`test_conservacao`: invariante total TDT+revisão, cadeia até `particionar_endereco_duplicado`).

---

## Diagnóstico

### Problema

O pipeline adquire informação em várias etapas (coluna detectada, equipamento extraído, módulo resolvido, endereço lido) mas nem toda informação adquirida chega às etapas que precisam dela:

1. **Perda por exclusividade indevida** (caso LVA AL21): duas fontes de identidade independentes (módulo-por-coluna, sigla-por-coluna) resolvidas em ramos `if/elif` — reivindicar uma desligava a outra para a sheet inteira. Uma única célula divergente (81×`AL21` + 1×`AL22`) mudou o comportamento de 83 sinais.
2. **Perda por consumo local:** valor extraído usado numa decisão intermediária e não gravado no `SignalRecord` — etapas posteriores que releiam a planilha ou o registro não encontram mais o dado (ex. citado pelo usuário: equipamento identificado numa análise e indisponível para a próxima).
3. **Perda por sobrescrita:** etapa posterior sobrescreve campo já preenchido sem registrar em auditoria (ex. `dc_pairer` reatribui `indices` a partir de `indices_saida` — hoje mitigado capturando `endereco_bruto` no diagnóstico ANTES do pairer; o padrão deve ser regra, não exceção).

### Exceção reconhecida

**Pré-processamento e normalização** (N0..N5 do `normalizador`, `tokenizer`) removem ruído por design e PODEM descartar dado bruto. Enquanto o usuário não apontar que um dado relevante está sendo destruído nessas duas etapas, o descarte é aceitável. `descricoes.bruta` permanece sempre preservada no registro como fonte de verdade.

---

## Proposta

### Invariantes (I1–I4)

- **I1 — Aquisição vira campo estruturado.** Toda informação extraída de planilha ou inferida (sigla, módulo, equipamento, fase, barra, endereço, tipo) é gravada em campo do `SignalRecord` (ou no diagnóstico/auditoria) no momento da aquisição — nunca apenas consumida numa decisão local e perdida.
- **I2 — Identidades independentes, resoluções independentes.** Módulo, sigla, equipamento, endereço e tipo são identidades ortogonais. A resolução de uma nunca desliga a resolução de outra (proibido `if/elif` entre fontes distintas). Precedência só existe DENTRO da mesma identidade (ex.: coluna explícita > extração do NOME > nome da sheet).
- **I3 — Nenhuma etapa reduz informação silenciosamente.** Pós-estruturador, etapa que sobrescreva ou descarte valor de campo de identidade preenchido (sigla_sinal, modulo.nome, eletrico.nome_equipamento, enderecamento.indices) registra evento de auditoria com valor anterior e motivo. O valor bruto original permanece recuperável (diagnóstico `endereco_bruto` é o padrão a seguir).
- **I4 — Contagem conservada.** Nenhum sinal some: todo registro lido termina em TDT, revisão ou descarte auditado (já coberto por `test_conservacao`; manter).

### Arquitetura

```
Planilha → estruturador (I1, I2)
             │  SignalRecord com TODOS os campos adquiridos
             ▼
   identidade / inferência / scoring / dc_pairer / normalizador_estrutural (I3)
             │  só ENRIQUECEM ou marcam p/ revisão; sobrescrita = evento de auditoria
             ▼
   engine_tdt (I4)  →  TDT + revisão + auditoria (nada some)
```

### Tarefas (alto nível — detalhar em plano)

1. **Auditoria de fluxo:** mapear etapa a etapa quais campos cada função lê/escreve/sobrescreve (tabela em `docs/`); identificar violações de I1–I3 remanescentes (candidatos: consumo local em `inferencia_topologia`, sobrescritas em `dc_pairer`/`normalizador_estrutural`).
2. **Teste de conservação de identidade:** estender `test_conservacao` para afirmar que campos de identidade preenchidos no estruturador chegam ao fim do pipeline (ou têm evento de auditoria justificando a mudança) — não só a contagem de sinais.
3. **Teste de independência:** para cada par de fontes de identidade (módulo×sigla já coberto), fixture com as duas presentes deve resolver as duas (guarda contra novos `elif`).
4. **Auditoria de sobrescrita (I3):** helper único (ex. `aud.sobrescrita(id, campo, antes, depois, motivo)`) e adoção nas etapas que alteram campos preenchidos.
5. **Gate de closeout:** incorporar à verificação de fim de spec a comparação com listas reais (SAN2, CVA, LVA, GAU, GTD) além do `gate_tdt_real`.

### Fora de escopo

- Refatorar pré-processamento/normalização (exceção reconhecida).
- Mudar contratos públicos do `SignalRecord` (só adições, nunca remoções).

### Critério de sucesso

- Fixture com módulo+sigla+equipamento simultâneos resolve as três identidades.
- Nenhuma violação de I1–I3 sem evento de auditoria na execução das listas reais de referência.
- Regressão tipo LVA AL21 passa a ser capturada por teste antes de chegar ao usuário.
