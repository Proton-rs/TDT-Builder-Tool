# SP1 — Melhoria do Motor de Regras

**Data:** 2026-06-23
**Status:** Spec aprovada para implementação
**Parte crítica:** o motor de regras corrige o que a similaridade erra, usando
conhecimento de domínio. Hoje só trata neutro e estágio.

## Princípio de design
Cada regra é uma **função pura** `regra(rec, candidato, contexto) -> AjusteRegra`
onde `AjusteRegra(delta: float, motivo: str)`. Um registro (lista) de regras é
aplicado; os deltas somam ao score e os `motivo` alimentam a `justificativa`
(rastreabilidade — alinhado à cascata da spec de análise). Regras novas = novas
funções, sem reescrever. SRP + TDD: um teste por regra, com caso real do domínio.

## Regras (catálogo, ver skill `especialista-ADMS-TDT`)

### R1. Número de proteção compartilhado (boost) / divergente (penalidade)
Extrai o número de função do texto (50,51,67,87,27,59,81,86,25,79,21,...). Se
bate com o número líder da sigla candidata → boost; se o texto tem um número e a
sigla tem outro → penalidade. (É o "shares number" das meta-features, como regra.)

### R2. Desambiguação de pares opostos (hard/soft negatives)
Catálogo de pares confusáveis e seu token discriminador:
| par | discriminador | efeito |
|---|---|---|
| sobrecorrente × subcorrente | SOBRE/SUB | penaliza polaridade errada |
| 59 (sobretensão) × 27 (subtensão) | SOBRE/SUB, 59/27 | idem |
| TAP máximo × mínimo | MAX/MIN | idem |
| ligado × desligado | LIGADO/DESLIGADO | idem |
| barra × linha (VAB_B × VAB_L) | BARRA/LINHA | idem |
Quando o discriminador está presente, penaliza o candidato de polaridade
contrária. Reduz FP nos casos mais perigosos.

### R3. Fase (A/B/C/N/AB/BC/CA/ABC)
Detecta a fase no texto e favorece candidatos da mesma fase; penaliza fase
divergente. Cobre o caso já existente de neutro (vira caso de R3).

### R4. Estágio (E1–E4) — já existe, migra para o registro.

### R5. Comando × status
LIGAR/DESLIGAR/COMANDO/CONTROLE → favorece candidato com direção de comando;
caso contrário, status.

### R6. Lado / nível de tensão (primário/secundário/barra; AT/BT)
Quando presente no texto/contexto, favorece candidato correspondente.

## Config
`pesos_regras: dict[str, float]` (delta base por regra, calibrável). Defaults
conservadores; calibrar via `bench/benchmark.py`.

## Contrato
```python
@dataclass(frozen=True)
class AjusteRegra:
    delta: float
    motivo: str

def aplicar(rec, candidatos, config) -> list[Candidato]   # soma deltas, reordena
def aplicar_rastreado(rec, candidatos, config) -> tuple[list[Candidato], list[AjusteRegra]]
```

## Critérios de sucesso
- Cada regra tem teste com caso real (ex.: "Sobrecorrente" não decide subcorrente).
- acc@1 e prec@decididos no harness ≥ baseline.
- `justificativa` lista as regras que atuaram.
