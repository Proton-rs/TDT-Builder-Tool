# SP-L — Base de conhecimento de sinais + atualização das skills — Design

**Data:** 2026-07-02

## Problema

O motor de regras e as decisões de matching dependem de conhecimento de
domínio (o que cada sinal é, como funciona numa subestação real, o que pode e
o que não pode coexistir). Esse conhecimento hoje está espalhado (specs,
memória, skills desatualizadas) e incompleto. As skills `especialista-ADMS` e
`especialista-ADMS-TDT` contêm informação já provada errada/obsoleta durante
o desenvolvimento.

## Design

### 1. Compilado por sinal — `docs/conhecimento_sinais.md`

Para cada sigla/família da lista padrão (agrupar por família ANSI quando
fizer sentido: 79*, 25*, 27/59, 50/51/67, 86/94, 43, SEC*, DJ*, SGF*, CDC,
MOLA, SF6, GOOSE, VF, MCB/mini-disjuntor…):

- **Nome e função real** na subestação (1-3 frases);
- **Nomenclaturas alternativas** vistas em listas reais (secc., seccionadora,
  chave; religamento, 79, recl.; bem sucedido, com sucesso…);
- **Estados possíveis** e semântica (NORMAL@ATUADO, INCLUIDO@EXCLUIDO,
  LIGADO@DESLIGADO…) — extraído da própria LP (Message Mapping);
- **Regras e exceções** (o que pode/não pode): cardinalidade por equipamento,
  coexistência (ex. disjuntor tem 1 posição, seccionadora 2-3), direção
  (Read/Write/ReadWrite), pares comando↔estado;
- **Fontes**: LP real, TDTs reais analisadas, pesquisa web (nomenclatura ANSI
  /IEEE C37.2, práticas de concessionárias BR), descobertas do projeto
  (referenciar specs).

Método: primeiro minerar o que a LP e as TDTs reais já dizem (determinístico,
maior autoridade); pesquisa web complementa nomenclaturas e funcionamento.
Conflito entre web e arquivo real → arquivo real vence, exceção anotada.

### 2. Atualização das skills

`especialista-ADMS` e `especialista-ADMS-TDT` (em `.claude/skills/`):
- remover afirmações provadas erradas/obsoletas durante o projeto;
- incorporar as regras descobertas (semântica de estados, fusão D+C, sigla
  persistente = lista padrão, sem comando analógico, DJF1/DJA1, etc.);
- referenciar `docs/conhecimento_sinais.md` como fonte canônica em vez de
  duplicar conteúdo.

### 3. Consumo pelo motor de regras

O compilado é insumo humano+agente; regras novas dele derivadas entram em SPs
próprias (não nesta). Esta SP só cria o conhecimento e aponta candidatos a
regra (seção "Candidatos a regra" no fim do doc).

## Critérios de aceite

1. `docs/conhecimento_sinais.md` cobre 100% das famílias da LP discreta +
   analógicas principais, com fontes.
2. Skills atualizadas sem contradição com o compilado; conteúdo obsoleto
   removido.
3. Lista "Candidatos a regra" com ≥ 5 itens acionáveis para SPs futuras.

## Fora de escopo

- Implementar regras novas no motor (SPs futuras).
- Traduzir o compilado para config/código.
