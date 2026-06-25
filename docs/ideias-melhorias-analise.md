# Ideias para melhorar além de 79%

Vou organizar em **3 camadas**: ajustes rápidos, reorganização dos métodos, e inovações.

---

## 🔧 **Camada 1: Ajustes no ensemble atual**

### **1.1 Threshold adaptativo por tipo de match**

Você treinou com **28 pares**, mas nem todos são igualmente difíceis. Alguns patterns repetem:

```python
def mescla_adaptativa(tfidf, vetorial, fuzzy, par_texto):
    """
    Adjust threshold based on signal pattern
    """
    # Padrão 1: fuzzy muito alto = variação de grafia
    # → confia em fuzzy, exige menos dos outros
    if fuzzy >= 0.85:
        threshold = 0.35  # mais permissivo
        return (tfidf*0.2 + vetorial*0.3 + fuzzy*0.5) >= threshold
    
    # Padrão 2: vetorial muito alto = semântica forte
    # → fuzzy pode ser baixo
    if vetorial >= 0.80:
        threshold = 0.40
        return (tfidf*0.3 + vetorial*0.5 + fuzzy*0.2) >= threshold
    
    # Padrão 3: todos moderados = precisa de consenso
    # → threshold mais alto
    threshold = 0.50
    return (tfidf*0.33 + vetorial*0.33 + fuzzy*0.33) >= threshold
```

**Ganho esperado**: +3-5% (explorar patterns no seu dataset)

---

### **1.2 Votação por maioria + confiança (em vez de média)**

Atual: `(a+b+c)/3 >= 0.45`

Melhor: **voto categórico + desempate por confiança**

```python
def voto_decisivo(tfidf, vetorial, fuzzy, threshold=0.45):
    """
    Cada método vota SIM/NÃO (acima/abaixo de threshold)
    Maioria decide
    Em caso de empate 1-2, usa score máximo
    """
    votos = [
        tfidf >= threshold,
        vetorial >= threshold,
        fuzzy >= threshold
    ]
    
    # Maioria clara: 2 ou 3 votam igual
    if sum(votos) >= 2:
        return sum(votos) >= 2  # True = MATCH
    
    # Empate 1-2: usa o score mais alto
    if sum(votos) == 1:
        return max(tfidf, vetorial, fuzzy) >= (threshold + 0.1)
    
    return False
```

**Por quê?** Evita que um score mediano em um método "puxe" dois baixos para cima. Força consenso.

**Ganho esperado**: +2-3%

---

### **1.3 Gap dinâmico (em vez de fixo 0.08)**

Atual: você descarta pares onde `max - 2º = < 0.08`

Melhor: **aprender o gap ótimo por cluster de dificuldade**

```python
# Análise pós-benchmark:
# Pares fáceis (todos 3 métodos altos): gap=0.05 já é suficiente
# Pares difíceis (1-2 métodos altos): precisa gap=0.15+

gaps_por_dificuldade = {
    'facil': 0.05,    # todos concordam
    'medio': 0.08,    # 2 concordam
    'dificil': 0.15   # 1 só tem score alto
}
```

**Ganho esperado**: +1-2% (marginal, mas zero overhead)

---

## 🔄 **Camada 2: Reorganizar a sequência de métodos**

### **2.1 Fuzzy PRIMEIRO (pipeline invertida)**

Intuição: Fuzzy é barato computacionalmente e **elimina ruído de entrada** antes dos métodos pesados.

```python
# Atual (menos eficiente):
# 1. TF-IDF (bag-of-words)
# 2. Vetorial (embedding)
# 3. Fuzzy (ortografia)

# Proposta:
# 1. Fuzzy (ortografia) → normaliza texto
#    - "pneuomia" → "pneumonia"
#    - "covid 19" → "covid-19"
# 2. TF-IDF (no texto normalizado)
# 3. Vetorial (no texto normalizado)
```

**Vantagem**: TF-IDF e Vetorial trabalham com input **limpo**

**Risco**: Fuzzy agressivo pode perder informação

**Ganho esperado**: +1-2% + 30% mais rápido

---

### **2.2 Camadas de fallback (em vez de paralelo)**

```python
def mescla_hierarquica(tfidf, vetorial, fuzzy, par_texto):
    """
    Decide em cascata, não em paralelo
    """
    # Nível 1: Fuzzy muito alto = certeza, return
    if fuzzy >= 0.90:
        return True, 0.90, "fuzzy"  # (match, score, método)
    
    # Nível 2: TF-IDF + Vetorial (ambos altos)
    if tfidf >= 0.70 and vetorial >= 0.70:
        return True, (tfidf+vetorial)/2, "tfidf+vetorial"
    
    # Nível 3: Vetorial sozinho (semântica forte)
    if vetorial >= 0.85:
        return True, vetorial, "vetorial"
    
    # Nível 4: Voto ponderado (fallback)
    score = 0.35*tfidf + 0.35*vetorial + 0.30*fuzzy
    if score >= 0.45:
        return True, score, "ensemble"
    
    # Rejected
    return False, score, "none"
```

**Vantagem**: Cada nível usa o sinal MAIS CONFIÁVEL primeiro
**Ganho esperado**: +2-4% (+ rastreabilidade = quando cada método decidiram)

---

## 🚀 **Camada 3: Inovações novas**

### **3.1 Análise de frequência de termos (TF-IDF turbo)**

Atual: TF-IDF vanilla (frequência + logaritmo)

Melhor: **TF-IDF + IDF reverso** (termos únicos ganham peso)

```python
def tfidf_melhorado(texto1, texto2, corpus):
    """
    Penalizar termos muito comuns (para diferenciar "de", "e", "a")
    Premiar termos raros e específicos (para exatidão médica)
    """
    # TF-IDF vanilla
    score_base = tfidf_vectorizer.similarity(texto1, texto2)
    
    # Bônus: termos únicos/raros que aparecem em ambos
    termos_1 = set(texto1.lower().split())
    termos_2 = set(texto2.lower().split())
    overlap_raro = termos_1 & termos_2
    
    # Se overlap é composto por termos raros (baixa IDF)
    # → match é mais significativo
    idf_medio_overlap = mean([idf[t] for t in overlap_raro])
    bonus = idf_medio_overlap * 0.1  # +10% se termos são raros
    
    return min(score_base + bonus, 1.0)
```

**Por quê?** No domínio médico, "inflamação" é comum, "pericardite" é raro. Overlap em "pericardite" ≠ overlap em "inflamação".

**Ganho esperado**: +2-3%

---

### **3.2 Contexto local (bigrams/trigrams)**

Atual: TF-IDF ignora ordem das palavras

Melhor: **Adicione n-grams**

```python
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(
    ngram_range=(1, 3),  # unigrams + bigrams + trigrams
    max_features=500
)

# Agora captura:
# - "diabetes tipo 2" ≠ "tipo 2 diabetes" (mesmas palavras, ordem importa)
# - "pressão sanguínea alta" ≠ "pressão alta de sangue"
```

**Ganho esperado**: +1-2%

---

### **3.3 Similaridade semântica com distância euclidiana inversa**

Atual: Vetorial usa similaridade de cosseno (padrão)

Melhor: **Combinar cosseno + distância euclidiana**

```python
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
import numpy as np

def vetorial_hibrido(emb1, emb2):
    """
    Cosseno: bom para ângulo (semântica)
    Euclidiano: bom para proximidade absoluta (magnitudes)
    """
    cos_sim = cosine_similarity([emb1], [emb2])[0][0]
    
    # Euclidiano invertido: quanto menor, melhor
    eucl_dist = euclidean_distances([emb1], [emb2])[0][0]
    eucl_sim = 1 / (1 + eucl_dist)  # normaliza pra [0,1]
    
    # Combine: cóseno captura direção, euclidiano captura proximidade
    return 0.6 * cos_sim + 0.4 * eucl_sim
```

**Ganho esperado**: +1-2%

---

### **3.4 Meta-features: características do par**

Pra cada par, extraia features que indicam confiança:

```python
def meta_features(texto1, texto2):
    """
    Features adicionais que indicam confiança do match
    """
    return {
        'comprimento_similar': abs(len(texto1) - len(texto2)) < 5,
        'num_palavras_similar': abs(len(texto1.split()) - len(texto2.split())) < 2,
        'capitalizacao_similar': texto1[0].isupper() == texto2[0].isupper(),
        'ambos_maiusculos': texto1.isupper() and texto2.isupper(),  # siglas
        'compartilham_numero': any(c.isdigit() for c in texto1) and any(c.isdigit() for c in texto2),
    }

# Depois, use com regressão logística ou XGBoost para pesar
# A decisão final depende não só dos 3 scores, mas dessas features
```

**Por quê?** "HTN" vs "HAS" são curtos, ambos maiúsculos, compartilham padrão → match provável.

**Ganho esperado**: +3-5%

---

### **3.5 Boosting com hard negatives**

Você testou com 28 pares. Mas qual é o "espaço" de pares impossíveis?

```python
# Gere pares NEGATIVOS deliberadamente difíceis:
hard_negatives = [
    ("diabetes", "hipertensão"),        # semântica próxima, SEM relação
    ("hepatite", "hepatocele"),          # mesmo prefixo, SEM relação
    ("covid-19", "gripe"),               # doenças infecciosas, SEM relação
]

# Rebalance seu dataset
# Antes: 28 pares (provavelmente balanceado)
# Depois: 28 positivos + 28 hard negatives

# Retrain/recalibrate thresholds
# Isso força os métodos a aprender DIFERENÇAS, não só SIMILARIDADES
```

**Ganho esperado**: +5-10% (mas precisa de curadoria manual)

---

## 📊 **Comparação de impacto (estimado)**

| Técnica | Esforço | Ganho | Complexidade |
|---------|---------|-------|---|
| 1.1 Threshold adaptativo | 2h | +3-5% | Baixa |
| 1.2 Votação decisiva | 1h | +2-3% | Muito baixa |
| 1.3 Gap dinâmico | 1h | +1-2% | Baixa |
| 2.1 Fuzzy primeiro | 3h | +1-2% + 30% speed | Média |
| 2.2 Cascata hierárquica | 2h | +2-4% | Média |
| 3.1 TF-IDF turbo | 2h | +2-3% | Média |
| 3.2 N-grams | 1h | +1-2% | Baixa |
| 3.3 Vetorial híbrido | 2h | +1-2% | Média |
| 3.4 Meta-features | 4h | +3-5% | Alta |
| 3.5 Hard negatives | 8h | +5-10% | Alta |

---

## 🎯 **Meu roteiro recomendado (Quick wins)**

Pra ganhar +10-15% com mínimo esforço:

```
1. Implementar 1.2 (votação decisiva) — 1h, +2-3%
2. Adicionar 3.2 (n-grams) — 1h, +1-2%
3. Tentar 2.2 (cascata) — 2h, +2-4%
4. Se ainda tiver tempo: 3.4 (meta-features) — 4h, +3-5%

Total: 8h de work, potencial +8-14% de ganho
```

---

Vou procurar por estratégias recentes e artigos sobre ensemble de métodos para matching/similaridade.Boas descobertas. Agora vou procurar por abordagens específicas de stacking e metalearning:Ótimo. Agora vou buscar por contrastive learning e hard negatives:Agora vou procurar por active learning e query strategies:Agora vou procurar por data augmentation e synthetic data generation para datasets pequenos:Agora vou procurar por domain-specific embeddings e fine-tuning:Perfeito! Agora vou procurar por abordagens de calibração e threshold tuning:Agora vou procurar especificamente sobre ROC AUC e otimização de thresholds:Excelente! Agora vou consolidar tudo isso em um relatório estruturado para você. Deixa eu fazer um resumo bem organizado:Pronto! Criei um relatório bem completo baseado em pesquisa. Aqui está o **sumário executivo:**

## 📊 **Principais Descobertas da Pesquisa**

### **11 Estratégias Research-Backed para ganhar +10-15%:**

#### 🏆 **Top 3 (Maior ROI):**

1. **Stacking com Meta-Learner** (+5-8%) ⭐
   - Ao invés de pesar os 3 métodos com pesos fixos, treina uma rede neural que *aprende* os pesos ótimos
   - Stacking treina um meta-learner para combinar otimamente as saídas, permitindo composições não-lineares

2. **Temperature Scaling** (+2-3%)
   - Calibra a confiança de cada método individualmente
   - Método pós-processamento simples mas efetivo: multiplica os logits por um parâmetro T otimizado

3. **Hard Negatives + Contrastive Learning** (+5-10%)
   - Treina com pares que parecem similares mas NÃO são (ex: "hipertensão" vs "hipotensão")
   - SupMPN aceita múltiplas sentenças hard-positive e hard-negative simultaneamente

#### 🔄 **Data & Workflow:**

- **Data Augmentation** (+3-5%): Gerar variações dos 28 pares via paráfrases/back-translation
- **Active Learning** (+1-2% por novo rótulo): Saber quais pares rotular próximo

#### 🧠 **Inovações:**

- **Meta-Features** (+3-5%): Extrair propriedades do par (comprimento similar?, maiúsculo?, números?) como features adicionais
- **Threshold Adaptativo** (+1-2%): Usar Youden's J ou F1-score ao invés de threshold fixo
- **Fuzzy como Pré-processamento** (+1-2%, + 30% speed): Normalizar texto ANTES dos métodos pesados

---

## 🚀 **Roadmap Prático:**

**Fase 1 (Quick wins, 8h):** Temperature Scaling + Threshold Opt + Fuzzy Fix = **+4-7%** → 83-86%

**Fase 2 (Meta-learning, 16h):** Stacking + Meta-Features = **+8-13%** → 87-92%

**Fase 3 (Domain-specific, 12h):** Hard Negatives OU BioMedical Embeddings OU Data Augmentation = **+5-10%**

**Expectativa final: 79% → 87-92%**

---
É excelente ver esse salto no benchmark! Chegar a 79% de acurácia com 88% de precisão na decisão demonstra que a sua premissa central estava certíssima: os métodos são complementares.

Abaixo, explico por que essa tríade funciona tão bem e trago as estratégias mais criativas para extrair ainda mais precisão do seu ensemble.

### **Por que essa tríade é tão poderosa?**

Pense nestes três algoritmos como uma junta médica, onde cada especialista avalia o problema sob uma lente completamente diferente. Quando um falha, o outro cobre o ponto cego:

* **Fuzzy (O Especialista em Forma/Ortografia):** Sozinho, ele é fraco (36% de acurácia no seu benchmark), pois é muito literal. Porém, ele é o único que "salva" a pipeline contra erros de digitação humanos. Se um médico escreve "pneuomia" e o outro "pneumonia", a semântica e o TF-IDF podem se perder, mas o Fuzzy percebe que é a mesma palavra.
* **TF-IDF (O Especialista em Frequência/Jargão):** Ele procura por correspondências exatas e dá peso às palavras. Ele é excelente para garantir que termos médicos muito específicos (que ocorrem em ambos os textos) sejam um forte indicativo de *match*.
* **Vetorial (O Especialista em Semântica):** Ele entende o contexto invisível. É ele quem vai olhar para "pressão alta" e "hipertensão" e dizer: *os textos não compartilham nenhuma letra, mas significam exatamente a mesma coisa*.

Para entender melhor como diferentes regras matemáticas alteram a forma como esses "três especialistas" chegam a um consenso, experimente o simulador abaixo:

---

### **Estratégias Criativas para Aumentar a Precisão e Assertividade**

Para sair dos 79% e buscar a faixa dos 85%+, a chave não é necessariamente adicionar um quarto método, mas sim **mudar a forma como eles conversam entre si**. Aqui estão as formas mais inteligentes de fazer isso:

#### **1. Abandone a Média, Adote a Votação Categórica**

Fazer a média simples `(a+b+c)/3` é perigoso porque um método com pontuação incrivelmente baixa pode "puxar" para baixo dois métodos que estão super confiantes.

* **A Solução:** Use a estratégia de *Maioria decide*. Cada método dá um voto (SIM/NÃO) se ultrapassar o *threshold*. Se 2 de 3 disserem "Match", é Match. Isso força um consenso real e evita o efeito âncora.

#### **2. Implemente o "TF-IDF Turbo" (Foque no Raro)**

No vocabulário médico, "dor" ou "inflamação" são palavras comuns. "Pericardite" é rara.

* **A Solução:** Ajuste o seu algoritmo para dar um bônus de similaridade (+10% no score, por exemplo) se a interseção entre os dois textos for composta por palavras raras (com IDF alto). Isso aumenta drasticamente a confiança quando um jargão médico complexo dá *match*.

#### **3. Crie um "Gap Dinâmico" por Confiança**

Atualmente, você descarta pares se a diferença (gap) do primeiro para o segundo colocado for menor que `0.08`.

* **A Solução:** O gap exigido não deve ser fixo. Se os três métodos (Fuzzy, TF-IDF e Vetorial) deram scores altíssimos (ex: todos acima de 0.85), a sua confiança já é tão alta que um gap de apenas `0.05` é suficiente para decidir. Se a situação for nebulosa e apenas um método apontar um match, exija um gap maior (`0.15+`) para não correr o risco de um Falso Positivo.

#### **4. Treine com "Hard Negatives" (O Teste de Fogo)**

Se o seu modelo só viu pares que são claramente diferentes ou claramente iguais, ele fica preguiçoso.

* **A Solução:** Injete pares como "hepatite" vs "hepatocele" ou "diabetes" vs "hipertensão" no seu dataset de calibração. São doenças sem relação semântica, mas que compartilham prefixos, co-ocorrências médicas ou contextos. Forçar o modelo a dizer "Não" para esses casos obriga os *thresholds* a ficarem incrivelmente precisos.

---

Seu plano de ação de 8 horas no documento estima um ganho de até +14% focando nas *quick wins*.

**Qual dessas lógicas — a Votação Categórica, os gaps dinâmicos ou os N-grams no TF-IDF — você gostaria de começar implementando na nossa pipeline via TDD agora?**