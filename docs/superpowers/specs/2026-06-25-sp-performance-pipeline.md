# SP-PERF: Performance do Pipeline

## 1. Gargalo #1 — Per-Signal Encoding

### Problema
`pipeline.py:86` chama `pontuar_vetorial(rec, ...)` para cada sinal individualmente. Cada chamada codifica **1 descrição** pelo SentenceTransformer. O modelo é otimizado para **batches** — codificar 200 descrições de uma vez é ~10-50x mais rápido que 200 chamadas individuais.

### Solução
Antes do loop de classificação, coletar todas as descrições e codificá-las **em lote**:

```python
descricoes = [r.descricoes.normalizada for r in sinais]
embeddings_lote = encoder(descricoes)
lote = {rec.id: emb for rec, emb in zip(sinais, embeddings_lote)}
```

`pontuar_vetorial` recebe o embedding pré-codificado em vez de chamar o encoder.

### Mudanças
- `scoring/vetorial.py`: nova função `pontuar_com_embedding(embedding, indice, k)` — recebe `ndarray` pronto
- `pipeline._classificar_sinal`: parâmetro opcional `embedding_vet`
- `pipeline.executar`: batch encode antes de cada sheet loop

### Ganho estimado
200 sinais: ~20s → ~1s. 237K sinais: ~6h → ~10min.

---

## 2. Gargalo #2 — Scorers Reconstruídos Toda Execução

### Problema
`_construir_scorers()` recria TF-IDF, FAISS index e FuzzyMatcher do zero a cada `executar()`. A lista padrão ADMS raramente muda (~900 discretos, ~700 analógicos).

### Solução
Cache em disco com hash de conteúdo. `IndiceVetorial` já tem `salvar()`/`carregar()` — só conectar.

```python
class CacheScorers:
    _CAMINHO = Path("cache/scorers/")

    @classmethod
    def carregar_ou_construir(cls, lp, config, encoder, categoria) -> _Scorers:
        h = _hash_corpus(lp, categoria)
        if (cls._CAMINHO / h).exists():
            return cls._carregar(h, encoder)
        scorers = _construir_scorers(lp, config, encoder, categoria)
        cls._salvar(scorers, h)
        return scorers
```

### Mudanças
- `scoring/tfidf.py`: serializar/deserializar matriz TF-IDF + vetorizador
- `tdt/matchers/fuzzy_match.py`: serializar caches de string
- `IndiceVetorial`: já implementado — só conectar no pipeline

### Ganho estimado
Setup de ~10-20s → ~0.1s na 2ª execução.

---

## 3. Gargalo #3 — Encoder Carregado Antes de Validar

### Problema
`worker.py:47` carrega o encoder (120MB-1GB) **antes** de validar se os arquivos de input existem. Se o path for inválido, o modelo foi carregado à toa.

### Solução
1. Lazy load: adiar `criar_encoder` para depois de validar paths
2. Keep-alive: manter encoder em `AppState.encoder` entre execuções na mesma sessão

### Mudanças
- `worker.py.run()`: validar paths primeiro, carregar encoder depois
- `estado.py`: campo `encoder: object | None = None`

### Ganho
Evita carga desnecessária quando o input não existe. Mantém modelo quente entre runs na mesma sessão.

---

## 4. Gargalo #4 — Progresso Opaco na UI

### Problema
Usuário vê log a cada 50 sinais — sem barra de progresso, ETA, ou noção se travou.

### Solução
`PipelineWorker` emite novo sinal:
```python
progresso = Signal(int, int)  # (atual, total)
status_msg = Signal(str)       # "Sheet GTA: 150/200..."
```

Na UI: `QProgressBar` + `QLabel` de status. Log text append vira secundário.

### Mudanças
- `worker.py`: sinais `progresso` e `status_msg`
- `pipeline.executar`: emitir evento a cada sinal (não só a cada 50)
- `tela_inicial.py`: `QProgressBar` + label de status

---

## 5. Profiling (Timeline + Memória)

### Pipeline Timeline
Timer por etapa via `contextmanager`:

```python
@contextmanager
def _timer(nome, aud):
    t0 = time.perf_counter()
    yield
    dt = time.perf_counter() - t0
    aud.evento("perf", f"{nome}: {dt:.2f}s")
```

Etapas medidas: `scorers (disc)`, `scorers (ana)`, `classificação`, `dc_pairer`, `engine_tdt`.

### Memória
`psutil.Process().memory_info().rss` antes/depois do encoder e ao final. Logado via auditoria.

---

## 6. Prioridade

| Item | Ganho | Esforço | Prio |
|------|-------|---------|------|
| Batch encoding | 10-50x | médio | **1** |
| UI progresso | UX | baixo | **2** |
| Scorer cache | setup ~20s | médio | **3** |
| Lazy encoder | baixo | baixo | **4** |
| Profiling | diagnóstico | baixo | **5** |

## 7. Não Fazer

- **Paralelismo nos scorers**: 3 scorers rodam ~5ms cada — encoding é o gargalo real, não o scoring
- **GPU auto-detection**: SentenceTransformer já autodeteta `cuda` se disponível
- **Pipeline streaming**: só faz sentido para 237K+ sinais; adiar até demanda real
