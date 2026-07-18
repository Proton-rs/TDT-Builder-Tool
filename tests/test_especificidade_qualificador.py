"""Pós-decisão: sigla base de família (79) não engole qualificador presente
no texto (79OK/79LO/79RE/... quando o texto tem a palavra distintiva)."""

from __future__ import annotations

from dataclasses import dataclass

from tdt.config import Config
from tdt.contracts import (
    Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.especificidade_qualificador import (
    preferir_irmao_qualificado, tokens_distintivos_por_familia,
)
from tdt.motor_regras import _numero_lider
from tdt.normalizacao.normalizador import canonizar
from tdt.semantica_estados import classe_do_mm, detectar_estado, filtrar_por_estado


@dataclass(frozen=True)
class _SP:
    sigla: str
    descricao: str
    mm: str | None = None
    estados_brutos: str | None = None


class _LP:
    """Lista padrão mínima (só o que preferir_irmao_qualificado lê)."""
    def __init__(self, sinais):
        self.discretos = sinais
        self.analogicos = []

    def por_sigla(self, sigla):
        alvo = sigla.strip().upper()
        for s in (*self.discretos, *self.analogicos):
            if s.sigla.upper() == alvo:
                return s
        return None


_SINAIS = [
    _SP("79", "79 - FUNCAO RELIGAMENTO"),
    _SP("79_1", "79 - PARTIDA RELIGAMENTO"),
    _SP("79LO", "79 - RELIGAMENTO BLOQUEADO"),
    _SP("79OK", "79 - RELIGAMENTO COM SUCESSO"),
    _SP("79_EXC", "79 - EXCLUIR RELIGAMENTO"),
    _SP("79_INC", "79 - INCLUIR RELIGAMENTO"),
    _SP("79RE", "79 - RELIGAMENTO PRONTO"),
    _SP("79TF", "79 - RELIGAMENTO TRANSFERIDO"),
]


def _config() -> Config:
    return Config()


def _lp() -> _LP:
    return _LP(_SINAIS)


def _rec_decidido(bruta: str, sigla: str, cfg: Config) -> SignalRecord:
    return SignalRecord(
        id="x",
        modulo=Modulo(None, "M"),
        tipo_sinal=TipoSinal("Discrete", "DoubleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(bruta, canonizar(bruta, cfg)),
        sigla_sinal=sigla,
        candidatos=(Candidato(sigla, 0.9, "mesclado"),),
        status="decidido",
    )


def test_bem_sucedido_prefere_79ok():
    cfg = _config()
    lp = _lp()
    rec = _rec_decidido("Religamento (79) - Bem Sucedido", sigla="79", cfg=cfg)
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "79OK"
    assert out.status == "decidido"


def test_promocao_atualiza_candidatos_para_nao_ficar_obsoleto():
    # Achado 2 (revisão final de branch SP-G): candidatos[0] precisa refletir
    # a sigla DECIDIDA (79OK), não a base descartada (79) — senão a
    # auditoria mostra o score de "79" ao lado do rótulo "79OK".
    cfg = _config()
    lp = _lp()
    rec = _rec_decidido("Religamento (79) - Bem Sucedido", sigla="79", cfg=cfg)
    assert rec.candidatos[0].sigla == "79"
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "79OK"
    assert out.candidatos[0].sigla == "79OK"
    assert out.candidatos[0].score == rec.candidatos[0].score
    assert out.candidatos[0].fonte == "qualificador"
    # o candidato antigo (base) continua presente, só não é mais o topo
    assert any(c.sigla == "79" for c in out.candidatos[1:])


def test_sem_qualificador_mantem_base():
    cfg = _config()
    lp = _lp()
    rec = _rec_decidido("Religamento (79)", sigla="79", cfg=cfg)
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "79"
    assert out.status == "decidido"


def test_dois_irmaos_casando_vai_revisao():
    cfg = _config()
    lp = _lp()
    # "Bloqueado" -> 79LO, "Pronto" -> 79RE: dois irmãos distintos casam -> ambíguo
    rec = _rec_decidido("Religamento (79) Bloqueado Pronto", sigla="79", cfg=cfg)
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.status == "revisao"
    assert out.justificativa is not None and "qualificador" in out.justificativa.lower()


def test_base_ja_especifica_nao_e_relitigada():
    # Caso real (LISTA 1 GTD): decidido já é 25VT (específico, não a raiz "25").
    # "SINCRONISMO"/"FALHA" são vocabulário comum da família inteira -- não
    # devem disparar re-arbitragem contra o irmão 25ER ("FALHA SINCRONISMO").
    cfg = _config()
    lp = _LP([
        _SP("25", "25 - FUNCAO SINCRONISMO"),
        _SP("25ER", "25 - FALHA SINCRONISMO"),
        _SP("25VT", "25 - TRIP DIFERENCA TENSAO"),
        _SP("25AT", "25 - TRIP DIFERENCA DE ANGULO"),
    ])
    rec = _rec_decidido(
        "Sincronismo (25) - Falha por Diferença de Tensão", sigla="25VT", cfg=cfg
    )
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "25VT"
    assert out.status == "decidido"


def test_raiz_generica_com_vocabulario_comum_ainda_prefere_irmao_unico():
    # Se o decidido É a raiz genérica ("25") e só um irmão tem token
    # exclusivo presente no texto, a correção ainda deve valer.
    cfg = _config()
    lp = _LP([
        _SP("25", "25 - FUNCAO SINCRONISMO"),
        _SP("25ER", "25 - FALHA SINCRONISMO"),
        _SP("25VT", "25 - TRIP DIFERENCA TENSAO"),
        _SP("25AT", "25 - TRIP DIFERENCA DE ANGULO"),
    ])
    rec = _rec_decidido(
        "Sincronismo (25) - Diferença de Tensão", sigla="25", cfg=cfg
    )
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "25VT"


def test_irmao_promovido_apesar_de_filtro_estado_hard_documented():
    """Achado 1 (revisão final de branch SP-G): pinagem de comportamento
    aceito, não uma correção.

    ``preferir_irmao_qualificado`` busca o irmão qualificado em TODA a lista
    padrão (``lp.discretos``/``lp.analogicos``), não em ``rec.candidatos``
    (sobreviventes pós-filtros). Isso significa que um irmão eliminado por
    ``semantica_estados.filtrar_por_estado`` — por a classe de estado do MM
    dele conflitar com o estado detectado no texto — ainda pode ser
    promovido aqui, se tiver token exclusivo casando no texto.

    Este teste CONSTRÓI esse cenário sinteticamente (família ANSI fictícia
    "79" com um irmão "79EXC" cujo MM é classe FUNCAO, mas cujo token
    distintivo aparece num texto cuja classe detectada é EVENTO) para provar
    que o mecanismo é ALCANÇÁVEL em tese.

    Investigação na lista padrão REAL (docs/Pontos Padrao ADMS_v2.xlsx)
    encontrou DUAS exceções reais, com naturezas diferentes (ver docstring
    do módulo para o detalhamento completo):

    1. Família ANSI-51, irmão ``51NL`` ("SOBRECORRENTE TEMPORIZADA LOCAL",
       MM classe EVENTO) tem como token exclusivo "LOCAL", que
       ``semantica_estados.detectar_estado`` classifica como LOCAL_REMOTO —
       classe diferente da classe MM do próprio ``51NL``. O conflito É real,
       mas INALCANÇÁVEL hoje: a família 51 não tem nenhuma sigla igual à sua
       própria raiz bare ("51") na lista padrão, e a guarda
       ``base == numero_lider(base)`` só deixa este módulo disparar quando o
       decidido É a raiz bare da família — sem um "51" bare decidível, o
       roteador nunca decide "51" para essa família, e este módulo nunca é
       acionado para ela.

    2. Família ANSI-21, irmão ``21D`` ("DISPARO LOCALIZADOR DE FALTA", MM
       classe EVENTO) tem "LOCALIZADOR" como token exclusivo, também
       classificado como LOCAL_REMOTO por ``detectar_estado`` — mas aqui a
       família TEM raiz bare decidível ("21" existe na lista). A causa é um
       bug de léxico pré-existente em ``semantica_estados._LEXICO`` (prefixo
       "LOCAL" casa com "LOCALIZADOR" por acidente; rastreado como
       acompanhamento separado). É um risco LATENTE, não ativo hoje: contra
       o texto REAL completo do sinal, ``detectar_estado`` retorna ``None``
       (ambíguo, pois "DISPARO"/"FALTA" também casam como EVENTO e empatam
       com o falso LOCAL_REMOTO), então ``filtrar_por_estado`` não rejeita
       ``21D`` para ESSE texto específico — mas um texto real sem essas
       palavras de desambiguação reativaria o problema.

    A garantia real (ver docstring do módulo e
    ``test_scan_lp_real_sem_conflito_token_classe_mm_em_familia_com_raiz_bare``)
    é mais estreita do que "zero conflitos existem": nenhuma família COM
    raiz bare decidível, EXCETO a 21 (risco latente rastreado à parte), tem
    um irmão com esse tipo de conflito. A família 51 fica fora do escopo por
    construção (nunca é alcançada); a família 21 é excluída explicitamente,
    por nome, com a razão documentada.

    Se algum dia uma TERCEIRA família COM raiz bare decidível introduzir
    essa colisão, ou se este teste passar a falhar porque o comportamento
    mudou, isso deve forçar uma reavaliação consciente — não um "conserto
    silencioso".
    """
    cfg = _config()
    lp = _LP([
        _SP("79", "79 - FUNCAO RELIGAMENTO", mm=None),
        _SP(
            "79LO", "79 - RELIGAMENTO BLOQUEADO",
            mm="null@null___NORMAL@ATUADO___RecloserLockout_S_TS_SA",  # EVENTO
        ),
        _SP(
            "79EXC", "79 - EXCLUSAO AUTOMATICA",
            mm="INCLUIR@EXCLUIR___INCLUIDO@EXCLUIDO___Enabled_S_TS_SS",  # FUNCAO
        ),
    ])
    texto_bruto = "Religamento (79) Bloqueio por Exclusao Automatica na Falha"
    rec = _rec_decidido(texto_bruto, sigla="79", cfg=cfg)

    # Passo 1: prova que filtrar_por_estado (SP-E D2), rodando ANTES do
    # roteador no pipeline real, teria eliminado 79EXC por causa (conflito
    # de classe de estado: texto é EVENTO, MM de 79EXC é FUNCAO).
    candidatos_com_79exc = (
        Candidato("79", 0.9, "mesclado"),
        Candidato("79EXC", 0.85, "mesclado"),
    )
    mantidos, zerou = filtrar_por_estado(rec, candidatos_com_79exc, lp)
    assert [c.sigla for c in mantidos] == ["79"]
    assert zerou is False

    # Passo 2: preferir_irmao_qualificado roda DEPOIS, ignorando o que
    # filtrar_por_estado já decidiu, e promove 79EXC mesmo assim —
    # comportamento aceito (ver docstring do módulo), pinado aqui.
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "79EXC"
    assert out.status == "decidido"


# Exceções conhecidas e documentadas (docstring do módulo, "revisão final de
# branch SP-G, fix round 2") ao escopo do scan abaixo — DUAS, não mais que
# isso. Se o scan encontrar uma TERCEIRA família fora desta lista, o teste
# deve falhar (não silenciar): força reavaliação consciente em vez de
# reabrir o risco aceito silenciosamente.
_FAMILIAS_COM_EXCECAO_CONHECIDA = frozenset({
    # "21": tem raiz bare decidível ("21" existe na lista padrão), então
    # ENTRA no loop abaixo — mas seu irmão 21D ("DISPARO LOCALIZADOR DE
    # FALTA", MM classe EVENTO) tem "LOCALIZADOR" como token exclusivo, e
    # semantica_estados.detectar_estado("LOCALIZADOR") retorna LOCAL_REMOTO
    # por um bug de léxico pré-existente (prefixo "LOCAL" casa por acidente
    # com "LOCALIZADOR" = localizador de falta, nada a ver com local/
    # remoto). Risco LATENTE, não ativo hoje (o texto real completo do
    # sinal é ambíguo e não dispara o filtro duro) — rastreado como
    # acompanhamento separado do fix do léxico em semantica_estados.py.
    "21",
})


def test_scan_lp_real_sem_conflito_token_classe_mm_em_familia_com_raiz_bare(
    lista_padrao_path,
):
    """Scan comitado (achado 2, revisão final de branch SP-G) que substitui a
    varredura ad-hoc/não-comitada citada na docstring do módulo por uma
    verificação automática, re-executável sempre que a lista padrão mudar.

    Pina a garantia TRUE e ESTREITA (não "zero conflitos existem" — essa
    era falsa): para toda família ANSI que tenha uma raiz bare DECIDÍVEL
    (uma sigla igual a ``_numero_lider(sigla)`` presente na própria lista
    padrão — é essa raiz que ``preferir_irmao_qualificado`` pode decidir e
    então re-arbitrar), EXCETO as famílias em
    ``_FAMILIAS_COM_EXCECAO_CONHECIDA`` (hoje só a "21", ver comentário
    acima), nenhum irmão tem um token exclusivo cuja classe de estado
    (``semantica_estados.detectar_estado``) conflite com a classe de estado
    do MM do próprio irmão (``semantica_estados.classe_do_mm``).

    Este teste NÃO cobre a família 51 (``51NL`` etc.) — e não deveria: a 51
    não tem sigla bare "51" na lista padrão, então nunca entra no loop de
    famílias-com-raiz-bare abaixo. Essa exclusão é estrutural (consequência
    de como a família é identificada), diferente da exclusão nomeada da
    família 21 (que TEM raiz bare, mas é excluída explicitamente por um
    risco latente conhecido e rastreado à parte).
    """
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    cfg = Config()
    todos = (*lp.discretos, *lp.analogicos)

    siglas_upper = {s.sigla.upper() for s in todos}
    lideres_com_raiz_bare = {
        lider for sig in siglas_upper if (lider := _numero_lider(sig)) == sig
    }

    conflitos: list[tuple[str, str, str, str]] = []
    familias_verificadas = 0
    for lider_base in sorted(lideres_com_raiz_bare - _FAMILIAS_COM_EXCECAO_CONHECIDA):
        distintivos_por_irmao = tokens_distintivos_por_familia(
            todos, lider_base, lider_base, cfg
        )
        if not distintivos_por_irmao:
            continue
        familias_verificadas += 1
        for sig, distintivos in distintivos_por_irmao.items():
            irmao = next(s for s in todos if s.sigla.upper() == sig)
            classe_mm = classe_do_mm(irmao.mm)
            if classe_mm is None:
                continue
            for token in distintivos:
                estado_token = detectar_estado(token)
                if estado_token is not None and estado_token.classe != classe_mm:
                    conflitos.append((lider_base, sig, token, estado_token.classe))

    # Sanidade: a família 51 (sem raiz bare "51" na lista) não deve nunca
    # aparecer entre as raízes bare — prova que sua exclusão é estrutural,
    # não dependente da lista de exceções nomeadas acima.
    assert "51" not in lideres_com_raiz_bare

    # Sanidade: a família 21 (exceção nomeada) DEVE ter raiz bare decidível
    # — senão a entrada em _FAMILIAS_COM_EXCECAO_CONHECIDA está obsoleta
    # (ex.: lista padrão mudou e "21" bare sumiu) e deveria ser removida.
    assert "21" in lideres_com_raiz_bare

    assert familias_verificadas > 0, (
        "nenhuma família com raiz bare decidível encontrada — verifique se "
        "a lista padrão real carregou corretamente"
    )
    assert conflitos == [], (
        "conflito real entre token distintivo e classe MM do próprio irmão "
        f"numa família COM raiz bare decidível e SEM exceção conhecida "
        f"documentada (alcançável hoje, achado NOVO — não silenciar, "
        f"investigar e documentar): {conflitos}"
    )
