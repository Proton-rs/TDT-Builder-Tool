# spD3 — Achados: filho-vs-pai (investigação Fase 1)

**Status:** investigação concluída, não implementa fix. Entrada para o plano de implementação da Fase 1.

**Script:** `bench/diag_filho_vs_pai.py` (`PYTHONPATH=src python -m bench.diag_filho_vs_pai`)

## O problema em uma frase

Uma sigla genérica ("pai") que existe standalone na lista padrão (ex. `79` =
"FUNÇÃO RELIGAMENTO", `51N` = "FUNÇÃO SOBRECORRENTE TEMPORIZADA NEUTRO") às
vezes vence a classificação sobre uma sigla "filha" mais específica da mesma
família (ex. `79OK` = "RELIGAMENTO COM SUCESSO", `51N1` = "SOBRECORRENTE
TEMPORIZADA NEUTRO E1"), mesmo quando o texto de entrada tem um discriminador
claro que aponta para a filha ("Bem Sucedido", "E1"/estágio).

## Step 1 — frequência no GT real (GTD)

Comparação `bench/gate_tdt_real.comparar` entre `bench/_tdt_gerado_GTD.xlsx`
(nosso) e `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx` (real), por endereço
DNP3, para a subestação GTD:

- **664 pontos em comum**, 358 iguais (53.9%), **306 divergências**.
- **18 dessas 306 divergências (5.9%) são o padrão filho-vs-pai** — a nossa
  sigla é uma sigla genérica que existe standalone na lista padrão E a sigla
  real começa com essa sigla (é uma variante mais específica da mesma
  família).
- As outras 288 divergências (94%) são **outros padrões, fora de escopo desta
  investigação**: truncamento numérico (`50F1`→`1`, `67F1`→`1`, já rastreado
  em `bench/casos_travados.csv`), equipamento/verbo errado (`BBFC`→`LIGAR`,
  `MOLA`→`MLCC`), sigla totalmente diferente sem relação de prefixo (`81`→
  `PRTF`, `67`→`RGBL`), etc.

### Distribuição por família (18 casos)

| nossa sigla (pai) | n | variante real (filho) | endereços |
|---|---|---|---|
| `51N` | 12 | `51N1` | 67, 267, 459, 709, 730, 1009, 1030, 2135, 2235, 2332, 3035, 3135 |
| `63T` | 2 | `63TD` | 667, 967 |
| `20T` | 2 | `20TD` | 670, 970 |
| `67N` | 1 | `67ND` | 2335 |
| `SGF` | 1 | `SGFT` | 2341 |

**`51N`→`51N1` domina (12/18 = 67% dos casos filho-vs-pai)**: é um único
padrão textual repetido em muitos módulos ("Proteção 51 N - Atuado" sem
menção explícita de estágio/elemento — o texto de entrada não diferencia
`51N` genérico de `51N1` estágio 1; a distinção correta viria de contexto de
posição/estágio que hoje não está sendo usado para desambiguar).

Nota: `51N1` já aparecia em `bench/casos_travados.csv` (linha addr=67,
"Dígito de estágio perdido") — a investigação aqui confirma que a causa raiz
desse caso travado *é* filho-vs-pai (o pai `51N` venceu porque existe como
sigla própria com score competitivo), não um truncamento isolado.

## Step 2 — um embedding melhor fecha o gap?

Testado em 5 descrições (o repro motivador sintético "Religamento (79) - Bem
Sucedido" + 4 casos reais extraídos do GT do Step 1, com a descrição bruta
recuperada via `pipeline.executar` sobre `docs/input_nao_homogeneo_1_GTD.xlsx`):

Comparação feita em duas camadas, porque são reveladoras de coisas diferentes:

1. **Scorer vetorial isolado** (só o embedding, sem tfidf/fuzzy/regras) — mede
   o que o *embedding em si* consegue diferenciar.
2. **Pipeline completo** (`pipeline._classificar_sinal` com tfidf 0.70 +
   vetorial 0.25 + fuzzy 0.05, F1 expansão de candidatos, filtro de
   especificidade, motor de regras) — mede o resultado real que chegaria ao
   roteador hoje.

Testado com **MiniLM** (`paraphrase-multilingual-MiniLM-L12-v2`, modelo
atual em produção, `config.modelo_embedding` default) e **e5**
(`intfloat/multilingual-e5-base` com prefixos `query:`/`passage:`, dormente
atrás de `config.e5_prefixos=False`, mesmo modelo já testado e descartado num
benchmark anterior de propósito geral — ver `.memory/decisions.md`).

Confirmado antes de medir: **não existem dois "paths" de corpus concorrendo em
produção.** `pipeline._construir_scorers` (e sua variante cacheada) já
constrói o índice vetorial com `_corpus_enriquecido` (sigla + descrição +
metadados) por padrão — não há um path "corpus simples" alternativo
esperando para ser ligado. A pergunta do brief "(b) MiniLM usando
`_corpus_enriquecido` se não for já o usado" tem resposta: **já é o usado
hoje**, então (i) e (ii) do brief colapsam no mesmo resultado. O script testa
essa premissa lendo `pipeline._construir_scorers` diretamente (fonte da
verdade), não assume.

### Resultado — filho ranqueia acima do pai?

| descrição | vet. isolado MiniLM | pipeline completo MiniLM | vet. isolado e5 | pipeline completo e5 |
|---|---|---|---|---|
| Religamento (79) - Bem Sucedido → `79OK` vs `79` | não (pos 6 vs 2) | não (pos 7 vs 1) | **sim** (pos 1 vs 5) | não (pos 5 vs 1) |
| Proteção 51 N - Atuado → `51N1` vs `51N` | não (fora top10 vs 2) | não (pos 7 vs 3) | não (fora top10 vs 3) | **sim** (pos 6 vs fora top6) |
| Relé Buchholz (63T) - Desligamento → `63TD` vs `63T` | não (pos 9 vs 1) | não (pos 8 vs 4) | não (pos 3 vs 1) | não (fora top6 vs 4) |
| Válvula de Alivio de Pressão (20T) - Atuada → `20TD` vs `20T` | não (fora top10 vs fora) | não (ambos fora top6) | não (pos 5 vs 1) | não (ambos fora top6) |
| Proteção 67N FOWARD - Atuado → `67ND` vs `67N` | não (ambos fora top10) | não (ambos fora top6) | não (ambos fora top6) | não (ambos fora top6) |

**Nenhum dos dois embeddings fecha o gap de forma consistente e genérica.**
e5 vence em 1/5 casos no scorer vetorial isolado e em 1/5 (um caso
*diferente*) no pipeline completo — não é o mesmo caso nas duas camadas, o
que indica ruído/coincidência, não um efeito sistemático.

**Achado qualitativo relevante, mesmo sem "vitória":** olhando o *scorer
vetorial isolado*, e5 consistentemente aproxima mais o filho do topo do que
MiniLM (79OK sobe de pos 6→1; 63TD de pos 9→3; 20TD de fora do top10→pos 5).
Ou seja, e5 melhora a ordenação vetorial pura, mas **isso não se propaga ao
resultado final** porque o peso do scorer vetorial na mescla é baixo
(`peso_tfidf=0.70`, `peso_vetorial=0.25`, `peso_fuzzy=0.05` —
`src/tdt/config.py`) e o tfidf/fuzzy (que casam a palavra "religamento"/"51
N" literal, presente tanto no pai quanto no filho) dominam o score
combinado. O pai vence não porque o embedding é ruim — vence porque
qualquer scorer léxico vê a mesma palavra-chave nos dois textos (pai e
filho) e o pai, sendo mais curto/genérico, tende a normalizar/casar melhor
ou empatar, e a mescla favorece o candidato que já estava na frente.

### Por que nenhum embedding resolve isso estruturalmente

O padrão filho-vs-pai não é (só) um problema de "os dois embeddings estão
distantes" — é estrutural: **a descrição do pai é quase sempre um
subconjunto textual da descrição do filho** ("79 - FUNÇÃO RELIGAMENTO" vs
"79 - RELIGAMENTO COM SUCESSO"; "51 - FUNÇÃO SOBRECORRENTE TEMPORIZADA
NEUTRO" vs "51 - SOBRECORRENTE TEMPORIZADA NEUTRO E1"). Um texto de entrada
que menciona só a função base, sem o discriminador específico ("Bem
Sucedido", "E1"), é *genuinamente* mais parecido com o pai — não é um
problema do embedding, é uma característica do domínio (a sigla genérica
"nua" existe justamente para casos sem informação suficiente para
especializar). O embedding só ajudaria nos casos em que o texto de entrada
**tem** o discriminador (como "Bem Sucedido" no repro motivador) — e mesmo
nesses, o baixo peso do scorer vetorial na mescla apaga o ganho.

## Recomendação

**Não trocar o embedding.** Nem MiniLM→e5 nem MiniLM-corpus-simples→
MiniLM-corpus-enriquecido (já é o caso hoje) resolvem o padrão de forma
genérica — e5 tem ganho parcial e inconsistente, ao custo de +1GB de modelo,
o que já havia sido descartado numa rodada de benchmark anterior por motivo
geral (`.memory/decisions.md`) e esta investigação **não encontra motivo
para reabrir essa decisão**.

**Mecanismo recomendado: regra estrutural "pai-nu não vence quando existe
filho competitivo", aplicada no pipeline de classificação — não no
embedding.** Concretamente, algo como: quando o candidato top1 é uma sigla
que é *prefixo exato* de outro(s) candidato(s) no mesmo top-k (a "família"),
e o(s) candidato(s) mais específico(s) estão dentro de uma margem de score
pequena do top1, desempatar a favor do filho ou, no mínimo, empurrar o caso
para revisão manual em vez de decidir automaticamente pelo pai. Isso ataca a
causa raiz medida aqui — o problema é de *desambiguação estrutural entre
sigla curta e suas variantes*, não de proximidade semântica de embedding.

Escopo sugerido para a próxima fase de implementação, com base no que foi
medido:
- Cobre pelo menos as famílias medidas: `51N`/`51N1` (12 ocorrências reais —
  maior prioridade), `63T`/`63TD`, `20T`/`20TD`, `67N`/`67ND`, `SGF`/`SGFT`,
  e o caso `79`/`79OK` que motivou a investigação original (não presente no
  GT real do GTD testado, mas plausível em outras subestações/listas —
  mesma estrutura sigla-prefixo).
- Gate de fechamento: os 18 casos filho-vs-pai medidos aqui deveriam virar
  PASS (ou ir para revisão explicitamente, nunca decidir errado
  silenciosamente) sem regressão no benchmark sintético de 28 pares
  (`bench/benchmark.py`) nem no restante do gate real (`bench/regressao.py`).
- **Fora de escopo dessa regra:** os outros 288 casos de divergência não são
  filho-vs-pai (truncamento, verbo/comando, equipamento errado) — já têm (ou
  precisam de) mecanismos próprios, tratados em planos separados (ver Fase 3
  no plano mestre).

Se, ao implementar, a regra estrutural revelar casos onde o discriminador
textual (ex. "Bem Sucedido") deveria bastar para decidir automaticamente sem
precisar de revisão, um **mapa de sinônimos pequeno e curado** (não um
embedding novo) é a alternativa de baixo risco: ele resolveria especificamente
o subconjunto de casos com discriminador textual claro (como `79`/`79OK`),
sem o custo/risco de trocar o modelo de embedding do sistema inteiro.

## Evidência bruta

Ver saída completa do script em `bench/diag_filho_vs_pai.py`
(`PYTHONPATH=src python -m bench.diag_filho_vs_pai`) — reproduzível a
qualquer momento; não há estado não determinístico (embeddings de modelos
fixos, corpus fixo da lista padrão `docs/Pontos Padrao ADMS_v2.xlsx`).
