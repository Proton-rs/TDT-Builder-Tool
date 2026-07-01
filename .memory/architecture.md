# Arquitetura

Projeto TDT v2: transforma planilha Excel de pontos de subestação em arquivo TDT (EcoStruxure ADMS). Pipeline em `docs/Pipeline-projetoTDT v2.svg`.

**Decomposição em sub-projetos** (cada um spec→plano→impl próprio):
- **SP1**: backbone determinístico + embeddings, DNP3. input→lista homogênea→TDT. Sem agentes LLM.
- **SP2** (em espera): agentes LLM (avaliador de linhas, revisão). Pluga via hooks `Avaliador`/`Aprendiz`.
- **SP3**: absorvido no SP1 — lista homogênea é a representação intermediária única antes da EngineTDT.
- **SP4**: UI desktop (`docs/interface_inicial.svg`, `interface_revisão.svg`). Consome `ResultadoPipeline.revisao`.

**Decisões fechadas:** Python núcleo + UI desktop. sentence-transformers + FAISS para busca vetorial local. DNP3 primeiro (IEC104/101/ICCP depois). Embeddings fazem parte do backbone (não opcionais); só agentes LLM são opcionais.

**Stack:** Python 3.14, pytest 9, openpyxl 3.1. Risco conhecido: faiss-cpu/sentence-transformers podem não ter wheels p/ 3.14.

**Domínio TDT** (ver skill `especialista-ADMS-TDT`): coluna localizada por field name (row 3); DNP3_DiscreteSignals=43 colunas; double-bit nunca perde 2º índice; pareamento D+C por nome_completo; `is_command()` por parênteses.

**Regras de domínio da fusão D+C** (confirmadas pelo usuário): comando=Output, status=Input, mesmo sinal físico, fundem em ponto `ReadWrite`. Sigla que persiste = a da Lista Padrão ADMS (a do status), nunca o verbo de comando. Não existe comando para analógicos. Double-bit dividido em 2 linhas é pareamento de POLARIDADE (`pareamento_polaridade.py`), distinto da fusão D+C (`dc_pairer.py`).
