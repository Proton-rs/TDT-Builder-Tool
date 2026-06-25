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
