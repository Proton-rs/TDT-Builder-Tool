# Padrões

- **Princípios de código:** SRP (1 módulo = 1 responsabilidade, função pura, contrato `SignalRecord`) e TDD.
- **Candidatos sem apagar original:** novos métodos de scoring/matching entram como candidatos lado a lado com os existentes; troca só acontece após benchmark provar ganho (ver [decisions.md](decisions.md)).
- **Gate real de mudança estrutural é a suíte pytest completa**, não o benchmark de scoring (`bench/benchmark.py` só cobre a camada de matching).
