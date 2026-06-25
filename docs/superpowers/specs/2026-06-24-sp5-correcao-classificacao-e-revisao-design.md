# SP5 — Correção de Classificação Analógico/Discreto + Melhorias na Revisão

**Data:** 2026-06-24
**Status:** Aguardando revisão do usuário
**Escopo:** (1) corrigir classificação que hoje cai quase sempre em "Discrete"; (2) desempate por centroide de embeddings; (3) GPU no encoder; (4) filtros/ordenação na tela de revisão; (5) relatório de auditoria além da TDT; (6) pasta default no file picker da tela inicial.

---

## 0. Contexto

Após o SP4 implementar o dual-pass discreto/analógico (`pipeline.py:_classificar_roteado`, scorers separados por categoria), o usuário reportou em uso real que:

- Quase todos os sinais saem classificados como "Discrete", mesmo com sinais claramente analógicos.
- Sinais claramente discretos por vezes recebem siglas/candidatos analógicos (falso positivo cruzado).
- Faltam filtros/ordenação na tela de revisão, um relatório de auditoria pós-classificação, e a pasta default do projeto não é usada nos diálogos de seleção de arquivo/pasta.

Investigação no código (não em dados de produção) confirmou causas raiz concretas para os dois primeiros pontos.

---

## 1. Classificação Discreto/Analógico

### 1.1 Causa raiz: coluna "Tipo" por código curto não é reconhecida

`analise_colunas.py:_col_tipo` (linha 134-144) só aceita uma coluna como "Tipo" se ≥50% dos valores baterem com palavras completas do vocabulário (`ANALOGIC`, `COMANDO`, `DIGITAL`, etc. — `_TIPO_VOCAB`). Arquivos reais de input usam, em alguns casos, código de uma letra (`A`/`C`/`D`) na coluna Tipo — esses valores não contêm nenhuma palavra do vocabulário, então `_col_tipo` retorna `None`: a coluna nem é detectada. Sem marcador de seção no arquivo (formato comum quando o tipo já vem em coluna), `estruturador.py` cai no default `("Discrete", "Input")` com `categoria_confiavel=False` para 100% das linhas — e o dual-pass, hoje sem critério de desempate quando ambos bundles decidem, tende a favorecer o resultado discreto.

**Mudança em `analise_colunas.py`:**
```python
_CODIGOS_TIPO = {"A": ("Analog", "Input"), "C": ("Discrete", "Output"), "D": ("Discrete", "Input")}
```
- `_col_tipo`: além do match por vocabulário já existente, aceitar a coluna como "Tipo" quando o conjunto de valores distintos normalizados for subconjunto de `_CODIGOS_TIPO.keys()` (`{"A","C","D"}`), com pelo menos 2 códigos diferentes presentes, e taxa de match ≥0.9 (mais estrita que o 0.5 de hoje, já que código é disciplinado, não linguagem livre).
- **Risco aceito:** uma coluna de fase trifásica (`A`/`B`/`C`) é descartada automaticamente porque `B` não pertence ao subconjunto — essa é a salvaguarda principal contra falso positivo. Sistemas monofásicos cuja coluna de fase só tenha valor `A` poderiam colidir; não é tratado agora (`ponytail: risco aceito, exige só 1 letra em comum com código de tipo — resolver se aparecer caso real`).

**Mudança em `estruturador.py`:** mesmo dicionário `_CODIGOS_TIPO`, usado em `_classificar(texto)`: após o match por substring de palavra completa, checar igualdade exata (`n in _CODIGOS_TIPO`) e retornar o par correspondente. Igualdade exata — não substring — para não colidir com nenhum outro texto livre.

`_ANALOG`/`_COMANDO`/`_DISCRETO` já são duplicados hoje entre `estruturador.py` e `analise_colunas.py` (mesmo conteúdo, duas cópias). `_CODIGOS_TIPO` é nova e entra nos dois lugares do mesmo jeito — pra não criar uma terceira fonte de drift, mover as quatro constantes (`_ANALOG`, `_COMANDO`, `_DISCRETO`, `_CODIGOS_TIPO`) para um módulo único (ex. `tdt/vocabulario_tipo.py`) importado pelos dois, já que essa duplicação preexistente é exatamente o tipo de coisa que diverge silenciosamente quando alguém edita um lado e esquece o outro.

### 1.2 Thresholds analógicos calibrados separadamente

`config.py:47-48` hoje usa os mesmos valores (`threshold_pct=0.45`, `threshold_gap=0.08`) para discreto e analógico, apesar da lista padrão analógica ser ~10x menor (scores naturalmente mais baixos por escassez de corpus).

- Ajustar defaults: `threshold_pct_analog=0.35`, `threshold_gap_analog=0.05`.
- Calibração inicial "no chute"; usuário valida na prática depois de rodar contra dados reais e re-ajusta se necessário (não há dataset rotulado disponível agora para calibrar com precisão).

### 1.3 Desempate no dual-pass quando ambos bundles decidem

Hoje, quando `categoria_confiavel=False` e os dois bundles (discreto e analógico) decidem, o registro vai para revisão (`motivo="categoria_ambigua"`) sem tentar desempatar — correto como fallback seguro, mas gera revisão manual evitável quando há sinal suficiente pra decidir automaticamente.

**Novo critério de desempate, em ordem:**
1. **Maior gap relativo** entre os dois resultados — o bundle cujo candidato decidido tem maior `(score_top1 - score_top2)` normalizado vence (mais "confiante" na própria decisão).
2. **Se os gaps forem próximos** (dentro de uma margem pequena, ex. 0.03): usar o **centroide de embeddings** (seção 1.4) como critério adicional — qual centroide (discreto/analógico) o embedding do sinal está mais próximo.
3. **Se ainda inconclusivo:** mantém o comportamento atual (vai para revisão com candidatos das duas análises).

Isso substitui a politica implícita "ambos decidem → sempre revisão" por "ambos decidem → tenta desempatar com sinal mais forte; só vai pra revisão se a tentativa também for ambígua".

### 1.4 Centroide de embeddings como sinal adicional (sem índice novo)

Em vez de construir um terceiro índice FAISS combinado ("lista completa"), que duplicaria o que o dual-pass já faz (comparar contra os dois mundos), adiciona-se um sinal mais barato: o **vetor médio** das descrições de cada categoria.

**Mudança em `IndiceVetorial` (`dados/indice_vetorial.py`):**
- No `construir()`, calcular `centroide = _normalizar(vecs.mean(axis=0, keepdims=True))` e guardar como atributo (`self.centroide`).
- Persistir/carregar junto com o índice (`meta.json` ganha o vetor do centroide serializado, ou recalculado no load a partir do índice salvo — decisão de implementação, sem impacto de design).
- Novo método `afinidade_centroide(texto: str) -> float`: codifica a query (reaproveitando o mesmo encoder/vetor já calculado durante o scoring vetorial — não há encode duplicado) e retorna o produto escalar com `self.centroide`.

**Uso:** no critério de desempate (1.3, passo 2), comparar `indice_discreto.afinidade_centroide(desc)` vs `indice_analogico.afinidade_centroide(desc)` — o maior vence. Custo: dois produtos escalares, zero re-encoding.

### 1.5 Testes

- `tests/test_analise_colunas.py`: coluna Tipo com códigos `A/C/D` é detectada; coluna de fase `A/B/C` continua sendo rejeitada (regressão do risco aceito).
- `tests/test_estruturador.py`: `_classificar("A")`, `_classificar("C")`, `_classificar("D")` retornam os pares esperados; `_classificar("ALARME")` (palavra livre, não é código) não colide.
- `tests/test_pipeline.py`: casos de dual-pass com gap distante (desempate por gap), gap próximo (desempate por centroide), e caso ainda ambíguo (cai em revisão, comportamento preservado).
- `tests/test_indice_vetorial.py` (ou onde já existem testes do índice): `afinidade_centroide` retorna maior valor pro centroide mais próximo, com fake encoder determinístico.

---

## 2. GPU no Encoder

`dados/encoder.py:16-19` instancia `SentenceTransformer(nome)` sem `device`. O gargalo real de performance é a inferência do modelo (vetorizar descrições novas), não a busca FAISS (corpus padrão é pequeno — busca já é da ordem de microssegundos em CPU).

**Mudança:**
```python
def criar_encoder(modelo: str, prefixo: str = "", device: str | None = None):
    ...
@lru_cache(maxsize=2)
def _modelo(nome: str, device: str | None):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(nome, device=device)
```
- `device=None` deixa o `sentence-transformers` autodetectar (usa CUDA se disponível, senão CPU) — comportamento sem regressão em máquinas sem GPU.
- Opcionalmente expor um knob em `Config` (ex. `device_encoder: str | None = None`) caso o usuário queira forçar `"cpu"` mesmo tendo GPU (depuração) — incluído porque é uma linha e evita um knob faltante depois.
- Sem mudança de arquitetura, sem dependência nova (torch+CUDA já é dependência transitiva de `sentence-transformers` quando há GPU disponível no ambiente).

### 2.1 Testes
- Sem teste de GPU em si (ambiente de CI não tem GPU) — `tests/test_encoder.py` (se existir) cobre que `device=None` não quebra a assinatura e que passar `device="cpu"` explicitamente funciona com o fake/stub usado hoje.

---

## 3. Filtros e Ordenação na Tela de Revisão

### 3.1 Problema

`tela_revisao.py` usa `QTableView` direto sobre `ModeloSinais` (`QAbstractTableModel`), sem ordenação por clique de cabeçalho nem filtro. Usuário quer: esconder sinais já aprovados/decididos da visão, ordenar por status pra agrupar visualmente, e (idealmente) filtro de texto por coluna como numa planilha.

### 3.2 Design

Inserir um `QSortFilterProxyModel` entre o modelo e a view — padrão nativo do Qt, sem biblioteca nova.

**Novo arquivo `src/tdt/ui/proxy_revisao.py`:**
```python
class ProxyRevisao(QSortFilterProxyModel):
    def setEsconderDecididos(self, ativo: bool) -> None: ...
    def setFiltroTexto(self, coluna: int, termo: str) -> None: ...
    def filterAcceptsRow(self, source_row, source_parent) -> bool: ...
```

**Em `tela_revisao.py`:**
- Ao montar a tabela: `self._proxy = ProxyRevisao(); self._proxy.setSourceModel(self._modelo); self.tabela.setModel(self._proxy); self.tabela.setSortingEnabled(True)`.
- Barra acima da tabela: checkbox "Mostrar apenas revisão" (chama `setEsconderDecididos`) + campo de texto de filtro (chama `setFiltroTexto` na coluna selecionada, ou um filtro simples na coluna "Descr. bruta"/"Sigla" pra começar — filtro por coluna individual fica de fase 2 se o filtro único não for suficiente).
- Ordenação por clique de cabeçalho funciona automaticamente com `setSortingEnabled(True)` — sem código adicional.

**Cuidado obrigatório:** qualquer lugar que hoje usa `self.tabela.currentIndex().row()` pra mapear a linha selecionada pro registro (ex. ao editar a sigla via `DelegateSinal`, duplo-clique) precisa trocar para `self._proxy.mapToSource(self.tabela.currentIndex()).row()` — senão, depois de filtrar/ordenar, a edição cai no sinal errado. Esse é o risco principal apontado pela investigação e é o ponto a testar manualmente antes de fechar.

### 3.3 Testes
- `tests/test_ui_modelo_tabela.py` (já existe pra `ModeloSinais`): novo teste cobrindo `ProxyRevisao` — filtro de "esconder decididos" oculta as linhas certas; ordenação por coluna não desalinha dados; `mapToSource` aponta pro registro correto após filtrar+ordenar.

---

## 4. Relatório de Auditoria (TDT + Candidatos)

### 4.1 Problema

Hoje só existe `pipeline.gerar_tdt()` (gera `TDT.xlsx`, só sinais decididos, sem metadados de revisão). Não há export da tabela de revisão nem dos candidatos descartados — usuário quer auditar cruzando TDT + uma tabela completa com os candidatos de pontuação baixa por sinal.

### 4.2 Design

Novo arquivo `src/tdt/relatorio_revisao.py`, reusando o padrão de escrita openpyxl já usado em `engine_tdt.py`.

```python
def gerar_relatorio_revisao(
    registros: list[SignalRecord],
    revisao: list[ItemRevisao],
    destino: str | Path,
) -> None:
    """Gera Auditoria_Revisao.xlsx: uma linha por sinal, com status, sigla
    decidida, score final e os top-3 candidatos lado a lado (sigla + score
    por método: tfidf/vetorial/fuzzy)."""
```

- **Sheet única "Auditoria"** (não sheets separadas) — uma linha por sinal facilita ler tudo sem pular abas; ID na primeira coluna permite cruzar com a TDT.
- Colunas: ID Sinal, Descrição Bruta, Tipo, Endereço, Status, Sigla Decidida, Score Final, Justificativa/Motivo Revisão, e 3x (Candidato N, Score tfidf, Score vetorial, Score fuzzy) usando os dados já existentes em `SignalRecord.candidatos`, `Diagnostico.scores_por_metodo` e `ItemRevisao.candidatos_sugeridos`.
- Disparo: mesmo botão "Gerar TDT" em `tela_revisao.py`, chamando `relatorio_revisao.gerar_relatorio_revisao(...)` depois de `pipeline.gerar_tdt(...)`, salvando no mesmo diretório de output.

### 4.3 Testes
- `tests/test_relatorio_revisao.py` (novo): gera o Excel a partir de registros/revisão fake, confirma colunas e linhas esperadas, confirma que sinais sem 3 candidatos não quebram (células vazias).

---

## 5. Pasta Default no File Picker (Tela Inicial)

### 5.1 Causa raiz

`tela_inicial.py` (linhas ~108-123): `QFileDialog.getOpenFileName/getExistingDirectory` usa `self._estado.paths.get("input"/"output", "")` como diretório inicial. No primeiro uso, esse valor está vazio (`AppState.paths` inicializa como `{"input": "", "output": "", ...}`) e o `or ""` não aplica nenhum fallback — o diálogo abre em local arbitrário do Windows. As constantes de default (`_DEFAULT_LISTA`, `_DEFAULT_OUTPUT`) já existem mas estão presas em `tela_config.py`, usadas só pra labels, nunca passadas ao diálogo.

### 5.2 Design

- Mover `_DEFAULT_TEMPLATE`, `_DEFAULT_LISTA`, `_DEFAULT_OUTPUT` de `tela_config.py` para um local compartilhado (ex. `config.py` ou um novo `defaults.py` em `src/tdt/`), já que agora são usadas por duas telas.
- Em `tela_inicial.py`, nos handlers de abrir diálogo:
  ```python
  atual = self._estado.paths.get("input", "") or DEFAULT_LISTA
  atual = self._estado.paths.get("output", "") or DEFAULT_OUTPUT
  ```
- Depois da primeira seleção manual, o valor persistido em `paths` passa a vencer o default — comportamento já existente, sem mudança.

### 5.3 Testes
- `tests/test_ui_estado.py` ou `test_ui_smoke.py`: diálogo recebe o diretório default quando `paths` está vazio; recebe o valor persistido quando já há seleção anterior.

---

## 6. Critérios de Aceite

1. Arquivo com coluna "Tipo" em código curto (`A`/`C`/`D`) classifica sinais analógicos corretamente, sem regressão em colunas de fase (`A`/`B`/`C`).
2. Sinais com categoria ambígua só vão pra revisão manual quando o desempate (gap + centroide) também for inconclusivo — taxa de revisão automática cai sem introduzir falso positivo cruzado óbvio (validar com dados reais após implementar).
3. Encoder usa GPU automaticamente quando disponível, sem regressão em ambiente sem GPU.
4. Tela de revisão permite esconder sinais decididos e ordenar por qualquer coluna clicando no cabeçalho, sem desalinhar edição de sigla após filtrar/ordenar.
5. Botão "Gerar TDT" também gera `Auditoria_Revisao.xlsx` com status, scores e candidatos descartados de cada sinal.
6. Diálogos de seleção de input/output na tela inicial abrem na pasta padrão do projeto quando nada foi selecionado ainda.
7. Testes existentes continuam verdes; cada item acima ganha cobertura nova conforme as seções 1.5, 2.1, 3.3, 4.3, 5.3.
