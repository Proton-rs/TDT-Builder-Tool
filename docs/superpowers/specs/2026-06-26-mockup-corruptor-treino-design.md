# Gerador de Mockup — corruptor determinístico p/ treino (pré-requisito da spec E) — Design

**Data:** 2026-06-26
**Status:** aprovado (brainstorming) — pronto p/ plano
**Origem:** spec E precisa de dados de treino/validação rotulados além dos 28 pares de `bench/rotulos.py`. Este é o "gerador de mockup (corruptor determinístico de 5 níveis)" que a spec E e a spec D deixaram pendente.

## Objetivo

Gerar, de forma **determinística**, pares rotulados `(descrição_corrompida → sigla)` a partir da Lista Padrão **V2**, em **5 níveis cumulativos** de dificuldade (trivial→adversarial), modelando como descrições reais degradam vs. a descrição padrão. Cobre todos os sinais e dá um eixo de dificuldade controlado p/ calibrar pesos (E2) e o calibrador de confiança (E4).

## Fonte e fundamentação

- Fonte: `docs/Pontos Padrao ADMS_v2.xlsx` (`DiscreteSignals`+`AnalogSignals`, coluna `DESCRIÇÃO NOVA` = corpus de matching atual).
- Padrões de corrupção confirmados nos 28 pares reais (`bench/rotulos.py`): abreviação (`Disj.`), ruído de ID de equipamento (`52-1 (01Q0)`, `IED 01F1`), código ANSI entre parênteses (`Diferencial (87)`), sinônimos (`Desbalanço`↔`Desequilíbrio`), reordenação, descrição parcial, sufixo de estado (`Bloqueio`).
- Reusa assets existentes (não reinventar): `config.ABREVIACOES_PADRAO`, `scripts/enriquecer_v5/ansi_ref.py::ANSI_C37_2`, e uma pequena tabela de sinônimos + pool de IDs de equipamento.

## Níveis (cumulativos — nível N = transforms de N-1 + uma classe nova)

Aplicados com RNG semeado por `(sigla, nível, variante)`:

1. **Trivial** — title-case + normalização de acento + espaços. (≈ identidade.)
2. **Leve** — + abreviar alguns tokens (reverso de `ABREVIACOES_PADRAO`) + troca por sinônimo.
3. **Médio** — + reordenar palavras + inserir 1 ID de equipamento + anexar 1 sufixo de estado.
4. **Difícil** — + remover 1-2 tokens não-chave + substituir a frase-função por código ANSI `(NN)` + 1 typo determinístico.
5. **Adversarial** — combinação agressiva: manter só tokens mínimos + ruído máximo (= corpus nível-5 compartilhado c/ spec D).

## Arquitetura

- Módulo offline `scripts/treino/mockup.py` (tooling, fora de `src/`).
- API: `gerar_dataset(lp, niveis=(1,2,3,4,5), n_variantes=3, seed=0) -> list[tuple[str, str, int]]` → `(texto_corrompido, sigla, nivel)`. Puro/determinístico.
- Transforms como funções puras pequenas, uma por classe (`_abreviar`, `_sinonimo`, `_reordenar`, `_ruido_equip`, `_sufixo_estado`, `_remover_tokens`, `_ansi_parens`, `_typo`), cada uma recebendo um `random.Random(seed)`.
- Determinismo: mesmo `seed` ⇒ mesma saída byte-a-byte (semente derivada de `hash((sigla, nivel, variante, seed))`).

## Integração (spec E)

- Consumido **offline** pela calibração (reescrita de `scripts/calibrar.py` na spec E): treina pesos/calibradores contra esses rótulos. **Sem acesso a disco em runtime** (runtime só carrega parâmetros calibrados).
- **Sempre combinar com `bench/rotulos.py`** (real) e reportar métricas por fonte (sintético vs real) — não calibrar só no sintético.
- Split treino/validação **estável por seed** (sem vazamento). Gate final de regressão continua no benchmark real.

## Testes (TDD)

| Item | Asserção mínima |
|---|---|
| Determinismo | mesmo seed ⇒ saída idêntica; seeds diferentes ⇒ diferente |
| Rótulo | toda variante mantém a sigla verdadeira; toda sigla da V2 aparece |
| Monotonicidade | sobreposição-de-tokens com o padrão decresce de nível 1→5 (nível 5 < nível 1) |
| Cada nível | aplica a classe nova (ex. nível 4 contém `(NN)` ou token removido; nível 2 contém abreviação/sinônimo) |
| Pureza | nenhuma escrita em disco; função pura |

## Não-objetivos

- Não é a calibração em si (spec E) nem a mineração da Full Base (C3).
- Sem fine-tuning. Sem acesso a runtime. Não materializa dataset obrigatoriamente (gera em memória; dump a arquivo é opcional p/ inspeção).
- V2 é a fonte (decisão do usuário); v4/v5 não entram.

## Decomposição (p/ o plano)

1. Tabelas de corrupção (sinônimos + pool de IDs de equipamento + sufixos de estado) reusando `ABREVIACOES_PADRAO`/`ansi_ref`.
2. Transforms puros (um por classe) + testes de cada um.
3. `gerar_dataset` compondo os níveis cumulativos + testes (determinismo, rótulo, monotonicidade).
4. Dump opcional p/ CSV de inspeção + amostra revisada por humano.
