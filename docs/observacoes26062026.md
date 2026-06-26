Organizei as observações agrupando itens relacionados e conectando problemas que se complementam. Isso deve facilitar tanto a priorização quanto a implementação.

---

# Observações e Melhorias Propostas

## 1. Interface de Revisão

### 1.1 Operações em múltiplas linhas

Atualmente as alterações precisam ser feitas individualmente.

**Sugestão:**

* Permitir selecionar múltiplas linhas.
* Executar ações em lote para todos os campos editáveis.

**Exemplos:**

* Alterar o sinal padrão de várias linhas simultaneamente.
* Alterar equipamento.
* Alterar módulo.
* Alterar tipo de módulo.
* Confirmar/rejeitar múltiplas sugestões.

---

### 1.2 Reordenação de colunas

Não é possível reorganizar a tabela.

**Sugestão:**

* Permitir arrastar e soltar colunas horizontalmente.
* Manter a ordem escolhida pelo usuário durante a sessão.

---

### 1.3 Desfazer e refazer alterações

Não existem mecanismos para desfazer ações realizadas durante a revisão.

**Sugestão:**

* Implementar botões:

  * Desfazer (Undo).
  * Refazer (Redo).

---

### 1.4 Seguir sinais pareados

Quando um sinal é pareado, ele pode ser reposicionado na tabela, fazendo o usuário perder o contexto.

**Sugestão:**

* travar a visão no sinal

---

## 2. Estrutura e Visualização da Tabela

### 2.1 Colunas específicas para endereçamento

Hoje existe apenas o tipo do sinal, que indica implicitamente se é entrada ou saída.

**Sugestão:**
Adicionar colunas específicas:

| Campo                  |
| ---------------------- |
| Endereço Input         |
| Endereço Output        |
| Possui Comando Pareado |

O campo **Tipo** pode permanecer como está.

Isso facilita:

* Identificação rápida de telemetrias e comandos.
* Análise de pareamentos.
* Auditoria manual.

---

### 2.2 Informações de confiança

Foram observados alguns problemas:

* Existem sinais sem nível de confiança (ex.: DJF1).
* Alguns sinais apresentam confiança maior que 1.

**Pontos a investigar:**

#### Ausência de confiança

Sinais provenientes exclusivamente do motor de regras podem não estar recebendo score.

#### Valores maiores que 1

É necessário esclarecer:

* O valor representa probabilidade?
* Similaridade?
* Score acumulado?

Caso represente probabilidade, valores maiores que 1 não deveriam ocorrer.

---

### 2.3 Exibição dos scores em sinais ambíguos

Atualmente sinais ambíguos não exibem os scores utilizados na decisão.

**Sugestão:**
exibir todos os scores
Isso permitirá avaliar:

* Comportamento do modelo.
* Qualidade dos embeddings.
* Eficiência das regras.

---

## 3. Pareamento de Sinais

### 3.1 Problemas no DCpairer

Foi observado:

* O **DCpairer** aparentemente não está funcionando corretamente durante a revisão.
* Exemplo encontrado:

  * DJF1 do equipamento **24-1** da lista não homogênea 1 sem pareamento Input/Output.

---

### 3.2 Falha na fusão de sinais duplicados

Foi identificado:

* Dois sinais DJF1 do mesmo equipamento.
* Endereços sequenciais (900 e 901).
* Não foram mesclados.

**Sugestão:**
Criar regras adicionais para fusão considerando:

* Mesmo equipamento(pode apresentar gargalo se o equipamento não estiver especificado e não for possível decidir o equipamento por lógica).
* Mesmo sinal padrão.
* Endereços consecutivos.
* Compatibilidade Input/Output.

---

## 4. Contexto de Equipamentos e Módulos

Grande parte dos erros ocorre porque muitas planilhas não informam explicitamente o equipamento.

---

### 4.1 Inferência de equipamento usando conhecimento do domínio

Exemplo observado:

* Módulos de alimentador normalmente possuem:

  * 1 disjuntor.
  * 2 ou 3 seccionadoras telecontroladas.

Assim:

> Todo sinal não explicitamente associado a uma seccionadora provavelmente pertence ao disjuntor principal.

Para isso é necessário:

1. Descobrir qual é o módulo.
2. Descobrir a topologia típica do módulo.
3. Aplicar regras de inferência.

---

### 4.2 Identificação correta do módulo

Atualmente o nome da sheet é utilizado para identificar o módulo.

Problema:

| Nome da Sheet | Módulo Real |
| ------------- | ----------- |
| AL FWB15      | AL15        |
| GTD_11        | AL11        |

Além disso, existem casos em que:

* Um módulo possui sinais distribuídos em múltiplas sheets.
* Existem sheets do tipo **slot** contendo sinais de vários módulos.

Exemplo:

* Lista não homogênea 3.

Conclusão:

> O nome da sheet não pode ser utilizado como identificador definitivo do módulo.

---

### 4.3 Classificação automática do tipo de módulo

Para aplicar regras de domínio é necessário identificar se o módulo é:

* Alimentador.
* Linha de transmissão.
* Banco de capacitores.
* Alta do transformador.
* Baixa do transformador.
* Transformador.
* Barra.
* Transferência.
* Outros.

---

### 4.4 Edição manual do módulo na revisão

Sugestões:

* Permitir alterar manualmente o nome do módulo.
* Permitir alterar manualmente o tipo do módulo.
* Disponibilizar uma lista de tipos conhecidos.
* Quando possível, preencher automaticamente a partir das planilhas.

Exemplo:

```
Módulo: GTD11
Tipo: Alimentador
```

---

## 5. Evolução do Motor de Regras

### 5.1 Expandir conhecimento a partir da Full Base

Analisar a **Export Full Base** para descobrir:

* Quais sinais seguem o padrão oficial.
* Quais sinais podem existir em cada tipo de módulo.
* Quais sinais podem existir em cada tipo de equipamento.

Objetivo:

> Utilizar esse conhecimento para enriquecer o motor de regras.

---

### 5.2 Adquirir mais contexto das planilhas

Além do conteúdo das linhas, explorar:

* Cabeçalhos.
* Títulos.
* Observações.
* Células superiores.
* Estruturas da sheet.

Essas informações podem beneficiar:

* Análise de sinais.
* Motor de regras.
* Processo de revisão.
* Auditoria.

---

### 5.3 Measurement Type

Consultar a Full Base para identificar como o **KMDF** referencia o **Measurement Type**.

---

## 6. Qualidade e Testes

### 6.1 Testes para identificação de falsos positivos

Criar um conjunto de testes para:

* Encontrar falsos positivos.
* Identificar padrões de erro.
* Corrigir regras e heurísticas.

---

### 6.2 Testes adversariais

Criar cenários deliberadamente difíceis para a análise.

Objetivos:

* Descobrir fragilidades do sistema.
* Melhorar robustez.
* Garantir que melhorias não aumentem falsos positivos.

---

## 7. Geração de Arquivos

### 7.1 Evitar sobrescrita de arquivos

Ao gerar arquivos de saída:

* Verificar se já existe um arquivo com o mesmo nome.
* Caso exista, adicionar sufixo numérico.

Exemplo:

```text
resultado.xlsx
resultado_1.xlsx
resultado_2.xlsx
```

Isso evita perda acidental de arquivos anteriores.
