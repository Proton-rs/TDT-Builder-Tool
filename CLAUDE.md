# CLAUDE.md — Diretrizes internas da empresa

## 🎯 Objetivo
Este documento define como o Claude deve gerar código, revisar PRs e interagir com este repositório.

---

## 🧱 Padrões de código
- Use nomes de variáveis claros e descritivos.
- Siga o estilo da linguagem:
  - JavaScript/TypeScript: ESLint + Prettier
  - Python: PEP8
  - Go: gofmt
- Sempre incluir testes automatizados para novas funções.
- Evitar duplicação de código (DRY).
- Priorizar funções puras e componentes desacoplados.

---

## 🧪 Testes
- Criar testes unitários para cada função pública.
- Cobertura mínima: 80%.
- Usar mocks para dependências externas.
- Testes devem ser rápidos e determinísticos.

---

## 📁 Estrutura de pastas
- `src/` — código-fonte
- `tests/` — testes
- `docs/` — documentação
- `infra/` — IaC, pipelines, configs
- `scripts/` — utilitários internos

---

## 🔐 Segurança
- Nunca incluir chaves, tokens ou segredos no código.
- Validar entradas do usuário.
- Evitar dependências desatualizadas.
- Sugerir mitigação para vulnerabilidades encontradas.

---

## 🔍 Revisão de PRs
Ao revisar PRs, Claude deve:
1. Verificar clareza e legibilidade
2. Checar segurança
3. Garantir que testes foram adicionados
4. Sugerir melhorias quando necessário
5. Manter tom profissional e construtivo

---

## 🔒 Não-regressão e fluxo de dados (regra universal — 2026-07-16)
Toda spec/plano/alteração DEVE preservar as funcionalidades existentes:

1. **Não quebrar o que já funciona.** Se a funcionalidade existente atrapalha a spec nova, a solução é redesenhar para as duas coexistirem de forma coerente — nunca desligar ou degradar a antiga silenciosamente. Conflito irreconciliável → decisão explícita do usuário, registrada na spec.
2. **Fluxo de dados transparente.** Informação adquirida em qualquer etapa (equipamento, sigla, módulo, endereço, fase...) não pode ser apagada nem tornada inacessível para as etapas seguintes. Identidades independentes nunca se resolvem em ramos mutuamente exclusivos (ex.: `elif` que fazia módulo-por-coluna desligar sigla-por-coluna — regressão LVA AL21, corrigida 16/07).
3. **Exceção: pré-processamento e normalização.** Essas duas etapas removem ruído por design e PODEM descartar dado bruto — enquanto o usuário não apontar que um dado relevante está sendo destruído nelas; a partir daí vira bug de fluxo (regra 2).
4. **Verificação obrigatória antes do closeout de spec:** suíte completa + testes de conservação/`gate_tdt_real` + comparação de comportamento com as listas reais já suportadas (SAN2, CVA, LVA, GAU, GTD...). Fixture limpa não substitui dado real.

---

## 🚀 Implementação de features
Quando solicitado a implementar algo:
- Criar branches `feature/nome-da-feature`
- Criar PR com descrição clara
- Adicionar commits pequenos e bem descritos
- Incluir testes e documentação

---

## 🗣️ Estilo de comunicação
- Ser direto, educado e técnico
- Evitar jargões desnecessários
- Explicar decisões quando relevante

---

## 🧩 Skills internas
Claude pode usar skills em `.claude/skills/` quando mencionadas via:
