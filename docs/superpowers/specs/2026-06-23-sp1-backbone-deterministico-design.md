# SP1 — Backbone Determinístico + Embeddings (DNP3)

**Data:** 2026-06-23
**Status:** Aprovado para implementação
**Escopo:** Primeiro sub-projeto do Projeto TDT v2.

---

## 1. Objetivo

Transformar uma planilha Excel de entrada (lista de pontos de subestação) em um
arquivo **TDT** DNP3 válido, de forma **determinística + busca vetorial local**,
**sem agentes LLM**. É o backbone: SP2 (agentes LLM) e SP4 (UI) plugam em
interfaces previstas aqui.

### Em escopo
- Protocolo **DNP3** apenas.
- Entrada homogênea **e** não-homogênea (`.xlsx`).
- Embeddings locais (sentence-transformers) + FAISS para busca vetorial.
- Geração da **lista homogênea** intermediária e do **TDT.xlsx** final.
- Fila de revisão (estrutura de dados) para sinais não decididos.

### Fora de escopo (YAGNI por enquanto)
- Agentes LLM (avaliador de linhas, revisão) → **SP2, em espera**. Existem como
  hooks determinísticos.
- UI desktop → **SP4**.
- IEC 104 / IEC 101 / ICCP → extensão futura.
- Catálogos AlarmCatalog/AlarmLimits/DOM além do mínimo p/ DiscreteSignals.

---

## 2. Fluxo

```
                              ┌─ homogêneo ──→ MapeamentoLeve ──────────────┐
input.xlsx → Identificador ──┤                                              ├→ ListaHomogenea → EngineTDT → TDT.xlsx
                              └─ não-homogêneo → [pipeline classificação] ───┘            │
                                                                                          └→ (opcional) writer .xlsx homogêneo limpo

[pipeline classificação]:
  Normalizador → AnalisadorColunas → EstruturadorJSON → Tokenizer
   → ScorerTFIDF ⊕ ScorerVetorial → MesclaScores → MotorRegras
   → Roteador → NormalizadorEstrutural → CriadorListaHomogenea
                          │
                          └→ FilaRevisao (sinais não decididos / erros sem fix)
```

A **ListaHomogenea** é a representação intermediária única. Ambas as rotas
produzem-na; a `EngineTDT` só conhece ela.

---

## 3. Contrato de dados

Todos os módulos trocam estes tipos (dataclasses imutáveis em `contracts.py`).
Nenhum módulo conhece o interior de outro — só o contrato.

### 3.1 `SignalRecord`
Espelha o JSON do diagrama, estendido com campos de classificação.

```python
@dataclass(frozen=True)
class Modulo:
    nome: str | None            # "FWB12"
    origem_contexto: str        # "sheet_name" | "linha" | "coluna:<x>"

@dataclass(frozen=True)
class TipoSinal:
    categoria: str              # "Discrete" | "Analog" | "DiscreteAnalog"
    is_double_bit: bool
    direcao: str                # "Input" | "Output" | "InputOutput"

@dataclass(frozen=True)
class Enderecamento:
    protocolo: str              # "DNP3"
    indices: list[int]          # [100, 101] (double-bit) | [17] | [] (sem endereço)

@dataclass(frozen=True)
class Descricoes:
    bruta: str
    normalizada: str

@dataclass(frozen=True)
class Eletrico:
    fase: str | None            # "ABC", "A", "N", ...
    nivel_tensao: str | None    # "AT" | "BT"
    equipamento_alvo: str | None
    nome_equipamento: str | None  # "52-10"

@dataclass(frozen=True)
class GrandezasAnalogicas:
    unidade_medida: str | None
    escala_transmissao: float | None
    tipo_medicao: str | None

@dataclass(frozen=True)
class MapeamentoEstados:
    estados_brutos: str | None  # "Transit;LIGADO;DESLIGADO;Error"
    valores_scada: list[int]    # [0,1,2,3]

@dataclass(frozen=True)
class Candidato:
    sigla: str                  # candidato da lista padrão, ex "DJ"
    score: float                # 0..1 após mescla
    fonte: str                  # "tfidf" | "vetorial" | "mesclado"

@dataclass(frozen=True)
class SignalRecord:
    id: str                     # estável: f"{sheet}:{linha}"
    sigla_sinal: str | None     # None até decidir; preenchido pelo Roteador
    modulo: Modulo
    tipo_sinal: TipoSinal
    enderecamento: Enderecamento
    descricoes: Descricoes
    eletrico: Eletrico
    grandezas_analogicas: GrandezasAnalogicas
    mapeamento_estados: MapeamentoEstados
    candidatos: tuple[Candidato, ...] = ()
    status: str = "pendente"    # "pendente"|"decidido"|"revisao"
    justificativa: str | None = None  # por que foi decidido/enviado p/ revisão
```

Enriquecimento é **funcional**: cada módulo recebe `SignalRecord` e devolve um
novo com `replace(...)`. Sem mutação in-place.

### 3.2 `ListaHomogenea`
```python
@dataclass(frozen=True)
class ListaHomogenea:
    subestacao: str | None
    protocolo: str              # "DNP3"
    registros: tuple[SignalRecord, ...]   # todos com status="decidido"
```

### 3.3 `ItemRevisao`
```python
@dataclass(frozen=True)
class ItemRevisao:
    registro: SignalRecord
    motivo: str                 # "score_baixo"|"endereco_duplicado"|"sem_endereco"|"sem_fix"
    candidatos_sugeridos: tuple[Candidato, ...]
```

### 3.4 Resultado do pipeline
```python
@dataclass(frozen=True)
class ResultadoPipeline:
    lista: ListaHomogenea
    revisao: tuple[ItemRevisao, ...]
```

---

## 4. Módulos (SRP — um arquivo, uma responsabilidade)

Cada módulo expõe **uma função pura** (ou classe com um método público).
Entrada/saída são tipos do contrato. Sem efeitos colaterais exceto os serviços
de dados (que leem disco/cache explicitamente).

| Módulo | Arquivo | Assinatura | Responsabilidade |
|---|---|---|---|
| Identificador | `identificador.py` | `classificar(workbook, override) -> Rota` | homogêneo vs não-homogêneo; lista sheets de dados |
| Normalizador | `normalizador.py` | `normalizar(texto) -> str` | maiúsculas, acentos, espaços, `/-.`→espaço, abreviações, stopwords, stemming (tudo calibrável; **não** quebrar siglas) |
| AnalisadorColunas | `analise_colunas.py` | `mapear(sheet, indice_vetorial) -> MapaColunas` | embeddings p/ achar colunas semânticas + detector de índices sequenciais por tipo (A/C/D) |
| EstruturadorJSON | `estruturador.py` | `estruturar(sheet, mapa, ctx) -> list[SignalRecord]` | monta `SignalRecord`s a partir da sheet + contexto |
| Tokenizer | `tokenizer.py` | `tokenizar(desc) -> list[str]` | regras regex (`67 N`→`67N`, `67 N 1`→`67N1`), separa siglas do texto |
| ScorerTFIDF | `scoring/tfidf.py` | `pontuar(rec, corpora) -> list[Candidato]` | TF-IDF global + sheet + lista padrão |
| ScorerVetorial | `scoring/vetorial.py` | `pontuar(rec, indice) -> list[Candidato]` | similaridade FAISS contra lista padrão |
| MesclaScores | `scoring/mescla.py` | `mesclar(tfidf, vet, pesos) -> list[Candidato]` | funde as duas listas (pesos calibráveis) |
| MotorRegras | `motor_regras.py` | `aplicar(rec, candidatos, regras) -> list[Candidato]` | incrementa/decrementa por regras de domínio (E1→estágio, Neutro→67N, etc.) |
| Roteador | `roteador.py` | `rotear(rec, candidatos, thresholds) -> SignalRecord` | quadrantes gap×% → `decidido` ou `revisao`, grava `sigla_sinal`+`justificativa` |
| NormalizadorEstrutural | `normalizador_estrutural.py` | `corrigir(registros) -> (corrigidos, erros)` | merge double-bit (`100;101`), detecta dup/sem-endereço; sem fix → revisão |
| CriadorListaHomogenea | `criador_lista_homogenea.py` | `montar(registros, ctx) -> ListaHomogenea` | agrupa classificados no formato homogêneo (enriquecimento determinístico: AT/BT, proteção, AOR via regras) |
| EngineTDT | `engine_tdt.py` | `gerar(lista, template_path) -> Workbook` | escreve sheets DNP3 localizando colunas pelo **field name (row 3)** do template |
| Auditoria | `auditoria.py` | `Auditoria.evento(modulo, msg, nivel, dados)` / `.salvar(path)` | registra o que cada etapa fez, decisões (decidido/revisão+justificativa) e erros, para **revisão humana** |

### Auditoria (log para revisão humana)
`Auditoria` é um coletor passado pelo `pipeline.py` a cada módulo (injeção
simples). Cada módulo chama `aud.evento(...)` para registrar o que fez. Não tem
lógica de negócio — só acumula e serializa.

- **Saída humana**: `OUT.log.txt` — linha por evento, legível
  (`[INFO] roteador: DJF1 decidido (gap=0.31, %=0.91)`; `[ERRO] engine_tdt: coluna MEASUREMENT_TYPE ausente`).
- **Saída estruturada**: `OUT.auditoria.json` — eventos com `modulo`, `nivel`
  (`INFO`/`AVISO`/`ERRO`), `msg`, `dados`, `timestamp` e `signal_id` quando
  aplicável — consumível pelo SP4 e pelo `Aprendiz` (SP2).
- Níveis: `INFO` (o que foi feito), `AVISO` (enviado p/ revisão, fix aplicado),
  `ERRO` (o que deu errado). Espelha no console via `logging` stdlib.
- `# ponytail: usa logging stdlib + lista de eventos; sem framework de log.`

### Regras críticas herdadas do domínio (ver skill `especialista-ADMS-TDT`)
- **Localizar coluna pelo field name (row 3)**, nunca por índice fixo.
- `DNP3_DiscreteSignals` = **43 colunas**; validar contra o template real.
- Double-bit: `indices=[1100,1101]` → `INCOORDS="1100;1101"`, `Input Data Type=DoubleBit`. Segundo índice **nunca** pode ser perdido.
- Pareamento D+C por **`nome_completo`** (não `modulo_sigla`).
- Dedup com chave `f"{nome_completo}_{tipo_input}"` (C e D coexistem).
- `is_command()` **com parênteses** ao decidir output coordinate.

---

## 5. Serviços de dados

### 5.1 `ListaPadraoADMS` (`dados/lista_padrao.py`)
Lê `docs/Pontos Padrao ADMS_v1.xlsx`, sheets `DiscreteSignals`/`AnalogSignals`.
Expõe os sinais padrão (SINAL, DESCRIÇÃO NOVA, SIGNAL TYPE, MM, etc.) como o
"gabarito de respostas". Carregada uma vez por execução.

### 5.2 `IndiceVetorial` (`dados/indice_vetorial.py`)
sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, configurável) +
FAISS sobre as descrições da lista padrão. **Gerado uma vez e persistido em
disco** (`.faiss` + metadados); rebuild só quando a lista padrão muda (hash do
arquivo). Expõe `buscar(texto, k) -> list[(sigla, score)]`.

---

## 6. Configuração calibrável (`config.py`)

O mundo real precisa de tuning. Knobs num único dataclass, com defaults
sensatos. `# ponytail: knobs existem porque calibração é física, não over-eng`.

```python
@dataclass(frozen=True)
class Config:
    # Normalizador
    abreviacoes: dict[str, str]          # {"DISJ":"DISJUNTOR","DJ":"DISJUNTOR",...}
    stopwords: frozenset[str]
    # Mescla de scores
    peso_tfidf: float = 0.5
    peso_vetorial: float = 0.5
    # Roteador — quadrantes gap × percentual
    threshold_pct: float = 0.70          # % mínima p/ ser candidato forte
    threshold_gap: float = 0.15          # gap mínimo entre 1º e 2º p/ decidir
    top_n_pct: float = 0.80              # corte do Top N% candidatos
    # Embeddings
    modelo_embedding: str = "paraphrase-multilingual-MiniLM-L12-v2"
    k_vizinhos: int = 5
```

### Roteamento (quadrantes)
| gap | % | resultado |
|---|---|---|
| alto | alta | **decidido** |
| baixo | alta | revisão (ambíguo) |
| alto | baixa | revisão (incerto) |
| baixo | baixa | **revisão** |

---

## 7. Pontos de extensão (para SP2 / SP4)

- `FilaRevisao` — `ResultadoPipeline.revisao` é a fila que a **UI (SP4)** consome.
- `Avaliador` — protocolo com `avaliar(rec, candidatos) -> Candidato | None`.
  Impl. determinística (`AvaliadorRegras`) no SP1; **SP2** fornece
  `AvaliadorLLM`. Injetado no `MotorRegras`/`NormalizadorEstrutural`.
- `Aprendiz` — protocolo no-op no SP1; **SP2** documenta erros corrigidos/não
  resolvidos para aprender com a revisão humana.

Tudo via injeção de dependência simples (parâmetro de função / construtor),
sem framework. `# ponytail: protocolo só vira interface quando SP2 existir`.

---

## 8. CLI (`cli.py`)

```
tdt gerar INPUT.xlsx --output OUT.xlsx [--template docs/dnp3_template.xlsx]
        [--modo auto|homogeneo|nao-homogeneo] [--subestacao AUTO|<sigla>]
        [--salvar-lista-homogenea LISTA.xlsx] [--config config.toml]
```
Imprime log do pipeline e um resumo: N decididos / N em revisão. Saída de
revisão também em `OUT.revisao.json` para o SP4 consumir.

---

## 9. Abordagem TDD

**Test-first, um arquivo de teste por módulo.** Sem frameworks pesados —
`pytest` + asserts. Fixtures = os arquivos reais em `docs/`.

| Teste | Garante |
|---|---|
| `test_identificador.py` | homogêneo (`input_homogeneo.xlsx`) vs não-homogêneo (`input_nao_homogeneo_1.xlsx`) classificados certo; override respeitado |
| `test_normalizador.py` | acentos/espaços/abreviações; **siglas preservadas** (`67N` não vira `67 N`) |
| `test_analise_colunas.py` | acha coluna de descrição por embedding; detecta coluna de índices sequenciais |
| `test_tokenizer.py` | `"67 N 1"`→`["67N1"]`; siglas separadas do texto |
| `test_scoring.py` | TF-IDF e vetorial rankeiam o candidato certo p/ casos conhecidos; mescla respeita pesos |
| `test_motor_regras.py` | E1→estágio 1; Neutro presente desconsidera candidatos de fase |
| `test_roteador.py` | os 4 quadrantes gap×% roteiam certo |
| `test_normalizador_estrutural.py` | `[100,101]`→double-bit `"100;101"`; endereço duplicado/ausente→revisão |
| `test_engine_tdt.py` | sheet `DNP3_DiscreteSignals` tem **43 colunas**; colunas achadas por field name; double-bit não perde 2º índice |
| `test_auditoria.py` | acumula eventos por nível; serializa `.log.txt` legível e `.auditoria.json` com signal_id |
| `test_pipeline.py` | E2E: `input_homogeneo.xlsx` → TDT importável (estrutura válida); contagem decididos/revisão coerente |

Cada módulo deixa **pelo menos um teste runnable** que falha se a lógica
quebrar (TDD). Casos de borda do domínio (double-bit, D+C, dedup) têm teste
dedicado porque já causaram bug antes.

---

## 10. Layout do projeto

```
projetoTDT/
  pyproject.toml            # deps: openpyxl, sentence-transformers, faiss-cpu, numpy, scikit-learn, pytest
  src/tdt/
    contracts.py
    config.py
    pipeline.py             # orquestra os módulos (a única coisa que conhece todos)
    cli.py
    identificador.py
    normalizador.py
    analise_colunas.py
    estruturador.py
    tokenizer.py
    motor_regras.py
    roteador.py
    normalizador_estrutural.py
    criador_lista_homogenea.py
    engine_tdt.py
    auditoria.py
    scoring/{tfidf.py, vetorial.py, mescla.py}
    dados/{lista_padrao.py, indice_vetorial.py}
    extensao.py             # protocolos Avaliador/Aprendiz + impls determinísticas
  tests/                    # um test_*.py por módulo (ver §9)
  .cache/                   # índice FAISS persistido
```

`pipeline.py` é o **único** módulo que importa todos os outros (orquestrador).
Os módulos não se importam entre si — só `contracts.py`.

---

## 11. Tratamento de erros

- **Coluna obrigatória ausente** (engine): lista as ausências e aborta com erro
  claro; nunca inventa mapeamento.
- **Sinal sem candidato / score baixo / endereço dup/ausente**: vai para
  `revisao`, não derruba o pipeline.
- **Template desatualizado** (nº de colunas ≠ esperado): erro explícito antes
  de gerar (evita shift silencioso de colunas).
- **Lista padrão / índice vetorial ausente**: erro na inicialização do serviço.

---

## 12. Critérios de sucesso

1. `input_homogeneo.xlsx` → `TDT.xlsx` com `DNP3_DiscreteSignals` estruturada
   (43 colunas, field names corretos) — validável abrindo o arquivo.
2. `input_nao_homogeneo_1.xlsx` → maioria dos sinais `decidido`; ambíguos na
   fila de revisão com candidatos sugeridos.
3. Double-bit, pareamento D+C e dedup corretos (testes dedicados verdes).
4. Pipeline roda **sem nenhum LLM** (só embeddings locais + regras).
5. Todos os `test_*.py` verdes.
