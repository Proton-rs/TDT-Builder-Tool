# SP10 — DJF1 e Pareamento de Polaridade (Ligado/Desligado)

**Data:** 2026-06-24
**Status:** Aguardando revisão do usuário
**Escopo:** Item "DJF1" de `docs/ObservacoesProgramaTDT.txt`. Dois fixes independentes, conforme decisão do usuário: (1) dado — segunda versão da Lista Padrão com descrição enriquecida; (2) código — regra de pareamento configurável on/off como rede de segurança.

---

## 0. Causa Raiz Confirmada

Lista Padrão ADMS (`docs/Pontos Padrao ADMS_v1.xlsx`, `DiscreteSignals`): `DJF1` → descrição **"DISJUNTOR NF"**, `SIGNAL TYPE = "SwitchStatus"`. Nenhuma palavra de polaridade ("Ligado"/"Desligado"/"Aberto"/"Fechado") na descrição padrão.

Input não-homogêneo real (`docs/input_nao_homogeneo_1.xlsx`): o disjuntor aparece em duas linhas separadas — `"Disj. 52-2 (06Q0) - Desligado"` e `"Disj. 52-2 (06Q0) - Ligado"`. O scorer de texto compara essas descrições contra "DISJUNTOR NF" (sem termo de estado) e prefere outro candidato — `motor_regras.r2_opostos` (regra de pares opostos ligado/desligado, `motor_regras.py:158`) não resolve porque é uma regra de **desambiguação entre candidatos já concorrentes com marca de polaridade na sigla** (ex. LIG/DESLIG), e `DJF1` não tem marca de polaridade na própria sigla — ela fica neutra para esse caso, não promove DJF1 contra a concorrência.

---

## 1. Lista Padrão v2 (dado)

Cópia `docs/Pontos Padrao ADMS_v2.xlsx` de `Pontos Padrao ADMS_v1.xlsx`, com a única mudança: descrição de `DJF1` em `DiscreteSignals` enriquecida com sinônimos de estado, ex. `"DISJUNTOR NF (LIGADO/DESLIGADO/ABERTO/FECHADO)"` — mantém "DISJUNTOR NF" no texto (não quebra nada que já casa por ele) e adiciona os termos que faltavam pro scorer reconhecer as duas linhas do input.

`src/tdt/defaults.py`: `DEFAULT_LISTA` passa a apontar pra `Pontos Padrao ADMS_v2.xlsx` (v2 é estritamente melhor — mesma estrutura/colunas, descrição mais rica; v1 fica no repo como histórico, usuário pode trocar manualmente pelo seletor de arquivo se precisar).

`v1.xlsx` não é editado (princípio de não tocar a lista oficial compartilhada sem processo de governança — fica registrado aqui que outras siglas com descrição igualmente genérica podem precisar do mesmo tratamento depois, fora de escopo deste corte).

---

## 2. Regra de pareamento por polaridade (código, configurável)

### 2.1 `Config` ganha o knob

```python
parear_polaridade_equipamento: bool = True
```

Em `config.py`, junto dos outros booleanos de gate (`corrigir_typos`, `remover_ids_equipamento`).

### 2.2 N0 passa a guardar o ID bruto do equipamento

`Eletrico.nome_equipamento` (`contracts.py:44`) já existe no contrato e já é **lido** por `engine_tdt._nome_hierarquico` — mas nunca é **escrito** em lugar nenhum hoje. `ContextoEstrutural` (`normalizador.py`) ganha o campo, populado no mesmo lugar onde `equipamento_alvo` já é resolvido:

```python
@dataclass(frozen=True)
class ContextoEstrutural:
    equipamento_alvo: str | None = None
    nome_equipamento: str | None = None  # "52-2" — ID bruto, pro pareamento e pro Signal Name
    barra: str | None = None
    fase: str | None = None


def extrair_contexto_estrutural(texto: str) -> tuple[str, ContextoEstrutural]:
    ...
    m = _ID_EQUIPAMENTO.search(base)
    nome_equipamento = None
    if m:
        equipamento_alvo = _EQUIPAMENTO_ANSI.get(m.group(1))
        nome_equipamento = f"{m.group(1)}-{m.group(2)}"  # "52-2"
        ...
    ...
    return base, ContextoEstrutural(
        equipamento_alvo=equipamento_alvo, nome_equipamento=nome_equipamento, barra=barra, fase=fase,
    )
```

`estruturador.py` (já chama `extrair_contexto_estrutural` e monta `Eletrico(...)`) passa a incluir `nome_equipamento=ctx_estrutural.nome_equipamento`.

### 2.3 Nova etapa: forçar convergência de pares ligado/desligado

Novo módulo `src/tdt/pareamento_polaridade.py` (SRP: só essa responsabilidade, testável isolado):

```python
_SIGLA_POSICAO: dict[str, str] = {"Disjuntor": "DJF1"}
_LIGADO = frozenset({"LIGADO", "FECHADO"})
_DESLIGADO = frozenset({"DESLIGADO", "ABERTO"})


def _chave(rec: SignalRecord) -> tuple | None:
    eq = rec.eletrico.equipamento_alvo
    if eq not in _SIGLA_POSICAO or not rec.eletrico.nome_equipamento:
        return None
    return (rec.modulo.nome, eq, rec.eletrico.nome_equipamento)


def forcar_polaridade_equipamento(
    registros: list[SignalRecord], config: Config,
) -> list[SignalRecord]:
    """Antes do scoring: duas linhas do mesmo equipamento com polaridade oposta
    (ligado/desligado, aberto/fechado) convergem direto pra sigla de posição do
    equipamento (ex. DJF1), sem depender do scorer de texto. Rede de segurança
    pro caso de a descrição padrão ser genérica demais (ver SP10)."""
    if not config.parear_polaridade_equipamento:
        return registros

    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        chave = _chave(rec)
        if chave is not None:
            grupos[chave].append(rec)

    forcados: dict[str, str] = {}  # rec.id -> sigla forçada
    for chave, grupo in grupos.items():
        ligado = [r for r in grupo if _LIGADO & set(r.descricoes.normalizada.split())]
        desligado = [r for r in grupo if _DESLIGADO & set(r.descricoes.normalizada.split())]
        if len(ligado) == 1 and len(desligado) == 1 and ligado[0] is not desligado[0]:
            sigla = _SIGLA_POSICAO[chave[1]]
            forcados[ligado[0].id] = sigla
            forcados[desligado[0].id] = sigla

    if not forcados:
        return registros
    return [
        replace(rec, sigla_sinal=forcados[rec.id], status="decidido") if rec.id in forcados else rec
        for rec in registros
    ]
```

### 2.4 Onde entra no pipeline

`pipeline.executar()`, logo depois de `sinais = list(estruturar(...))` por sheet, antes do loop de classificação:

```python
sinais = list(estruturar(rows, mapa, sheet_name=sn, config=config, vocab=vocab))
sinais = forcar_polaridade_equipamento(sinais, config)
for j, rec in enumerate(sinais, 1):
    if rec.status == "decidido":  # já resolvido pelo pareamento de polaridade
        decididos.append(rec)
        continue
    ...  # caminho de scoring de hoje, inalterado
```

Os dois registros forçados (mesmo `modulo.nome` + mesma `sigla_sinal="DJF1"`) chegam ao `normalizador_estrutural.corrigir()` (já roda hoje sobre `decididos`, sem mudança nenhuma ali) com endereços consecutivos — o merge double-bit existente já junta os dois numa linha só, exatamente como o formato homogêneo descreve. **Nenhuma mudança em `corrigir()` ou `dc_pairer.py`** — o ganho é só forçar a sigla certa cedo, o resto da estrutura já resolve.

### 2.5 Por que não generalizar pra Seccionadora agora

Só `Disjuntor`→`DJF1` está confirmado (descrição real da Lista Padrão + exemplo real de input). Não há evidência ainda de um sinal de posição genérico equivalente pra Seccionadora (`SECF` na lista padrão é "Seccionadora Fonte", não um sinal de posição) — `_SIGLA_POSICAO` fica pequena de propósito, mesmo padrão do SP6 (tabela de equipamento ANSI), expandir quando aparecer outro caso real confirmado.

---

## Testes

- `tests/test_normalizador.py`: `extrair_contexto_estrutural("DISJUNTOR 52-2 DESLIGADO")` preenche `ctx.nome_equipamento == "52-2"`.
- `tests/test_pareamento_polaridade.py` (novo): duas linhas mesmo módulo/equipamento, uma "LIGADO" outra "DESLIGADO" → ambas saem com `sigla_sinal="DJF1"`, `status="decidido"`; só uma das duas presente (sem par) → nenhuma é forçada (fica pro scoring normal); `config.parear_polaridade_equipamento=False` → no-op, registros voltam inalterados; equipamento fora de `_SIGLA_POSICAO` (ex. Seccionadora) → no-op.
- `tests/test_pipeline.py`: ponta a ponta com as duas linhas reais do fixture de input não-homogêneo — saem como um único registro double-bit com sigla `DJF1` na lista final (depois de `corrigir()`).
- `tests/test_lista_padrao.py` ou um teste de smoke: `ListaPadraoADMS.carregar(DEFAULT_LISTA)` (agora v2) encontra `DJF1` com a descrição enriquecida.

## Critérios de Aceite

1. `docs/Pontos Padrao ADMS_v2.xlsx` existe, idêntico ao v1 exceto a descrição de DJF1; `DEFAULT_LISTA` aponta pra ele.
2. Com `parear_polaridade_equipamento=True` (default), as duas linhas reais do input não-homogêneo 1 (disjuntor ligado/desligado) saem na TDT final como um único sinal double-bit `DJF1`.
3. Com a flag `False`, comportamento idêntico ao de hoje (regressão zero).
4. Pareamento nunca dispara fora do par exato (1 ligado + 1 desligado do mesmo módulo+equipamento) — ambiguidade (0, ou >1 de cada lado) cai no caminho de scoring normal.
5. Testes existentes continuam verdes.
