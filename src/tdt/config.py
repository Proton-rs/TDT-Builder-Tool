"""Knobs calibráveis do SP1, com defaults sensatos.

ponytail: knobs existem porque calibração é física, não over-engineering.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tdt.contracts import Topologia

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
    # Piso absoluto de confiança calibrada (SP-CVA E2): abaixo dele, nunca
    # decide mesmo com gap grande (top-1 fraco não deve vencer por W.O.).
    # 0.0 desliga (retrocompat).
    piso_decisao: float = 0.20
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
    # Pareamento D+C de catch-all: similaridade mínima (rapidfuzz token_sort_ratio,
    # 0-100) para casar 1 Output com 1 Input quando N inputs/M outputs compartilham
    # a mesma sigla no módulo. Abaixo disso, output órfão vai pra revisão.
    limiar_pareamento_similaridade: float = 60.0
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
            "estado": 0.15,
            "direcao": 0.10,
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
    # Rota de consenso (passo 3 da cascata do roteador) — benchmark mostrou
    # precisão de 42% (contra 95% dos outros métodos da cascata). Default OFF;
    # liga só para quem quiser testar/calibrar (spec SP-Cleanup item 2).
    usar_consenso: bool = False
    gaps_por_confianca: dict[str, float] = field(
        default_factory=lambda: {"alta": 0.05, "media": 0.10, "baixa": 0.15}
    )
    # Ancoragem por sigla explícita (SP ancoragem-sigla)
    ancora_sigla_ativa: bool = True
    # Score injetado para âncoras exatas/junção — alto o bastante para vencer
    # candidatos textuais genéricos com gap; abaixo de 1.0 para que filhos
    # (expansao_candidatos) e filtro_especificidade selecionem a variante certa.
    ancora_sigla_score: float = 0.85
    # Identidade do módulo (C1) — sementes calibráveis; confirmar nos inputs.
    # TRF é módulo de Transferência, distinto de TR (Transformador) — confirmado
    # no ground-truth real (exportTDT_UTR_{GTD,FWB}): TRF1/TRF2/TRF03 coexistem
    # com TR1/TR2/TR1AT/TR2BT no mesmo TDT. NÃO fundir TRF com TR (spC1 28/jun).
    mapa_prefixo_modulo: dict[str, str] = field(
        default_factory=lambda: {
            "AL": "AL", "GTD": "AL", "FWB": "AL",
            "LT": "LT", "BC": "BC", "TR": "TR",
            "TRF": "TRF", "IB": "IB",
        }
    )
    tipo_por_prefixo: dict[str, str] = field(
        default_factory=lambda: {
            "AL": "Alimentador",
            "LT": "Linha de Transmissão",
            "BC": "Banco de Capacitores",
            "TR": "Transformador",
            "TRF": "Transferência",
            "IB": "Barra",
            # "87B*" não tokeniza num prefixo alfabético isolado (87 fica
            # junto de "B"+sufixo) -- classificar_tipo também aceita o nome
            # completo do módulo como chave; daí os 3 nomes literais abaixo.
            "87BAT": "Barra",
            "87BMT1": "Barra",
            "87BMT2": "Barra",
            "PSACA": "Outros",
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
    # Alias direto sheet_name (tokens concatenados, sem separadores/espaços,
    # upper-case — mesma normalização de identidade_modulo._tokens) -> nome do
    # módulo real, p/ casos onde o sheet_name não decompõe em prefixo+número
    # (medição real em input_nao_homogeneo_1/GTA, 28-jun): bay/vão com sufixo
    # textual (LT_GTA/LT_KGC), proteção de barra (87B_*) e siglas próprias (IB,
    # PSACA) cujo número embutido não é o número do módulo — ex.: "23" em
    # IB_23kV é a tensão (23kV), não o módulo; confirmado no TDT real
    # (exportTDT_UTR_GTD/FWB): o módulo de interbarras lá é "IB", sem número.
    mapa_sheet_modulo: dict[str, str] = field(
        default_factory=lambda: {
            "01F1GTAP": "LTGTA", "01F1GTAA": "LTGTA",
            "01F1KGCP": "LTKGC", "01F1KGCA": "LTKGC",
            "87BAT": "87BAT",
            "87BMT1": "87BMT1",
            "87BMT2": "87BMT2",
            "IB23KV": "IB",
            "PSACACC": "PSACA",
            "TRF3P": "TRF03", "TRF3A": "TRF03",
        }
    )
    # Sheets que não são de dados DNP3 (capa, índice, consolidação cross-
    # módulo) — entram hoje como sheets_dados e geram só sinais-lixo de
    # revisão (medição real 28-jun: Consistidos mistura LT_GTA/87B-AT/TR1_MT
    # na mesma sheet por ser um índice, não dados de um módulo). Nome exato,
    # comparação normalizada (upper, sem acentos) em identificador.classificar.
    sheets_excluidas: frozenset[str] = frozenset(
        {"CAPA", "CONSISTIDOS", "CTR", "UCCD1"}
    )
    # Topologia por tipo de módulo (C2.1) — composição esperada e equipamento
    # "default" pra inferência (C2.2). Sementes mínimas: Alimentador tem
    # principal não-ambíguo (1 disjuntor); Barra/Transferência/Outros não têm
    # default claro (vários elementos possíveis) -- ficam None de propósito,
    # sinal sem equipamento explícito nesses tipos vai pra revisão
    # (equipamento_ambiguo) mantendo a sigla decidida como sugestão, não
    # chuta o equipamento. Minerar a Full Base pra refinar fica pra C3 (fora
    # de escopo aqui).
    topologia_por_tipo: dict[str, Topologia] = field(
        default_factory=lambda: {
            "Alimentador": Topologia(
                equipamentos=("Disjuntor", "Seccionadora"),
                default="Disjuntor",
                cardinalidade={"Disjuntor": 1, "Seccionadora": (2, 3)},
            ),
            "Linha de Transmissão": Topologia(
                equipamentos=("Disjuntor", "Seccionadora"),
                default="Disjuntor",
                cardinalidade={"Disjuntor": 1, "Seccionadora": (2, 3)},
            ),
            "Banco de Capacitores": Topologia(
                equipamentos=("Disjuntor", "Seccionadora"),
                default="Disjuntor",
                cardinalidade={"Disjuntor": 1, "Seccionadora": (1, 2)},
            ),
            "Transformador": Topologia(
                equipamentos=("Disjuntor", "Seccionadora"),
                default=None,  # AT e BT cada um tem seu disjuntor -- ambíguo
                # sem o lado (ver C2.4); inferência de equipamento roda só
                # depois da subdivisão AT/BT decidir o módulo.
                cardinalidade={"Disjuntor": (1, 2), "Seccionadora": (1, 4)},
            ),
            "Barra": Topologia(
                equipamentos=("Seccionadora",),
                default=None,  # vários elementos possíveis, sem principal único
            ),
            "Transferência": Topologia(
                equipamentos=("Disjuntor", "Seccionadora"),
                default=None,
            ),
            "Outros": Topologia(equipamentos=(), default=None),
        }
    )
    # --- SP-E: semântica de estados e políticas por projeto ------------------
    # D2: filtro duro estado-detectado × par de estados do MM da lista padrão.
    filtro_semantica_estados: bool = True
    # Sigla decidida que cada projeto escolhe incluir ou não (real GTD
    # descartou LIBM; base full tem 36) -> rebaixa para revisão.
    siglas_revisao_projeto: frozenset[str] = frozenset({"LIBM"})
    # D5: comandos que são Write legítimo (sem discreto de status).
    # AUTC/PB/CMD: SP-I Task 2, casos reais PSACA_CC:20/21/22 (LISTA 1 - GTD)
    # — "Comando Iluminação Pátio", "Seleção de Barra Preferencial", "Rearme
    # 86 Automatismo". Nenhum tem status correspondente em lugar nenhum do
    # input (confirmado por reprocessamento + varredura). Seguro whitelistar
    # globalmente por sigla porque a whitelist só morde dentro de um grupo
    # dc_pairer._chave = (módulo, equipamento, sigla) que já não tem NENHUM
    # Input — confirmado que, embora CMD/AUTC apareçam como Input legítimo em
    # dezenas de outros módulos (ex. "Falha Comando de Desligar/Ligar",
    # "Automatismo - Atuado"), em NENHUM desses outros módulos existe um
    # grupo (módulo, equipamento, CMD/AUTC) com Output e zero Input — logo
    # esses grupos nunca passam pelo ramo `elif not inputs` e não são
    # afetados por esta whitelist.
    siglas_write_legitimo: frozenset[str] = frozenset({"CDC", "AUTC", "PB", "CMD"})
    # D3: siglas fundíveis além das SwitchStatus da lista padrão.
    siglas_fundiveis_extra: frozenset[str] = frozenset()
    # Resgate por regras na zona cinzenta (SP-H Task 3): quando pct_ok mas
    # gap insuficiente, e o motor de regras de domínio já apontou
    # exclusivamente para o candidato topo (ajuste positivo no topo, zero
    # ou negativo no segundo), decide em vez de mandar para revisão -- ver
    # ``roteador._resolver_resgate_por_regras``. Default ligado; permite
    # desligar para comparar taxa de decisão/corretude sem o mecanismo.
    resgate_por_regras: bool = True
    # D6: whitelist de siglas por equipamento_alvo (semente = medição no
    # Export Base Full 27fev2026, sinais com equip 89-*/29-* no nome; 2103
    # sinais). Estender por medição quando aparecer sigla nova real.
    siglas_por_equipamento: dict[str, frozenset[str]] = field(
        default_factory=lambda: {
            "Seccionadora": frozenset({
                "SECF", "DSEC", "SECC", "43LR", "SECG", "SECB", "SECT",
                "CCCO", "CCFL", "CCMO", "FSEC", "OI", "LIBM", "CCCM",
                "CCAL", "BSEC", "MANI", "MDCM", "FLFC", "BBFC", "BBAB",
                "FLAB", "FALH", "PROT", "CCLO", "VMTC", "BBA2", "SOBC",
                "BATA", "MINC",
            }),
        }
    )
    # Siglas da lista de entrada que NÃO viram ponto no ADMS (base real:
    # comando de TAP não é sinal; 0/1629 DiscreteAnalog com output).
    siglas_sem_ponto: frozenset[str] = frozenset({"COMTAP"})
