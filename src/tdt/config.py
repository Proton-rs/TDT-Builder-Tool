"""Knobs calibráveis do SP1, com defaults sensatos.

ponytail: knobs existem porque calibração é física, não over-engineering.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Expansão whole-token (só quando o token == chave), para não quebrar siglas.
ABREVIACOES_PADRAO: dict[str, str] = {
    "DISJ": "DISJUNTOR",
    "DJ": "DISJUNTOR",
    "SECC": "SECCIONADORA",
    "SEC": "SECCIONADORA",
    "TR": "TRANSFORMADOR",
    "TRAFO": "TRANSFORMADOR",
    "LT": "LINHA TRANSMISSAO",
    "AL": "ALIMENTADOR",
    "BC": "BANCO CAPACITORES",
    "PROT": "PROTECAO",
}

STOPWORDS_PADRAO: frozenset[str] = frozenset(
    {"DE", "DA", "DO", "DOS", "DAS", "E", "O", "A", "OS", "AS", "EM", "NO", "NA"}
)


@dataclass(frozen=True)
class Config:
    abreviacoes: dict[str, str] = field(
        default_factory=lambda: dict(ABREVIACOES_PADRAO)
    )
    stopwords: frozenset[str] = STOPWORDS_PADRAO
    # Mescla de scores (calibrado: tfidf+vet+0.05 fuzzy — calibrar.py E2)
    peso_tfidf: float = 0.70
    peso_vetorial: float = 0.25
    peso_fuzzy: float = 0.05
    # Roteador — quadrantes gap × percentual (calibrado no ground-truth)
    threshold_pct: float = 0.45
    threshold_gap: float = 0.08
    top_n_pct: float = 0.80
    # Analógicos — mesmos defaults dos discretos até calibrar separadamente
    peso_tfidf_analog: float = 0.70
    peso_vetorial_analog: float = 0.25
    peso_fuzzy_analog: float = 0.05
    threshold_pct_analog: float = 0.35
    threshold_gap_analog: float = 0.05
    # Embeddings
    modelo_embedding: str = "paraphrase-multilingual-MiniLM-L12-v2"
    k_vizinhos: int = 5
    # Normalização (transforms novos — defaults seguros p/ não estragar siglas)
    corrigir_typos: bool = True
    remover_ids_equipamento: bool = True
    # N6 stemming superficial (spF §3). Default OFF: o stemmer atual gera
    # colisões (RELIGADOR/RELIGAMENTO -> RELIGA) e stems inconsistentes
    # singular/plural (POTENCIA->POTENT, POTENCIAS->POTENNT), o que reduz a
    # discriminação. Ligar só depois de corrigir as regras e validar no bench.
    stemming: bool = False
    # Pareamento de polaridade (SP10) — rede de segurança quando a descrição
    # padrão da sigla de posição é genérica demais pro scorer de texto.
    parear_polaridade_equipamento: bool = True
    # Motor de regras — delta base por regra (calibrável; defaults conservadores)
    pesos_regras: dict[str, float] = field(
        default_factory=lambda: {
            "numero_protecao": 0.10,
            "opostos": 0.15,
            "fase": 0.10,
            "estagio": 0.10,
            "comando_status": 0.08,
            "equipamento": 0.12,
            "lado_tensao": 0.08,
        }
    )
    # Análise — e5 assimétrico + consenso + gap dinâmico + calibração
    e5_prefixos: bool = False
    calibracao_metodo: str = "minmax"  # "minmax" | "temperature" | "isotonic" | "platt"
    # Parâmetros de calibração por método de scoring, treinados offline.
    # Ex: {"tfidf": {"metodo": "minmax"}, "vetorial": {"metodo": "temperature", "params": {"T": 0.1}}, ...}
    calibracao_por_metodo: dict[str, dict] = field(
        default_factory=lambda: {
            "tfidf": {"metodo": "minmax"},
            "vetorial": {"metodo": "minmax"},
            "fuzzy": {"metodo": "minmax"},
        }
    )
    # Calibrador de confiança pós-mescla (E4) — treinado offline, aplicado no runtime.
    confianca_calibrador: dict[str, Any] = field(
        default_factory=lambda: {"metodo": "platt", "params": {"coef_": 2.0403, "intercept_": -0.9391}}
    )
    min_consenso: int = 2  # nº mínimo de métodos que concordam no top-1
    gaps_por_confianca: dict[str, float] = field(
        default_factory=lambda: {"alta": 0.05, "media": 0.10, "baixa": 0.15}
    )
    # Identidade do módulo (C1) — sementes calibráveis; confirmar nos inputs.
    mapa_prefixo_modulo: dict[str, str] = field(
        default_factory=lambda: {
            "AL": "AL", "GTD": "AL", "FWB": "AL",
            "LT": "LT", "BC": "BC", "TR": "TR",
        }
    )
    tipo_por_prefixo: dict[str, str] = field(
        default_factory=lambda: {
            "AL": "Alimentador",
            "LT": "Linha de Transmissão",
            "BC": "Banco de Capacitores",
            "TR": "Transformador",
        }
    )
    palavras_chave_tipo: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "Banco de Capacitores": ("CAPACITOR", "BANCO"),
            "Linha de Transmissão": ("LINHA",),
            "Transformador": ("TRANSFORMADOR", "TRAFO"),
            "Barra": ("BARRA",),
            "Transferência": ("TRANSFERENCIA",),
        }
    )
