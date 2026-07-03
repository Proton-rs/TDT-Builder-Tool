"""Pós-decisão: sigla base de família não engole qualificador presente no texto.

Contexto (SP-G, Task 4): ``motor_regras.aplicar_rastreado`` soma um delta não
limitado APÓS a calibração Platt, então uma sigla genérica (``79``) pode
pontuar mais que uma irmã mais específica (``79OK``, ``79LO``, ``79RE``...)
mesmo quando o texto do sinal contém a palavra que qualifica a irmã (ex.:
"Bem Sucedido" -> deveria ser ``79OK``, não ``79``). Esse módulo não mexe na
calibração/regras (fora de escopo aqui) — atua como camada de correção
PÓS-decisão: se o decidido é a sigla RAIZ (bare) de uma família ANSI — ou seja
``sigla == numero_lider(sigla)`` (ex.: ``79``, ``25``, ``21``; NÃO ``25VT``,
``20T``, ``81E1``, que já são específicas) — e a descrição-padrão de
exatamente UM irmão tem token distintivo presente no texto canônico do sinal,
o irmão vence. Vários irmãos casando ao mesmo tempo -> ambíguo, vai para
revisão (motivo ``qualificador_ambiguo``).

Guarda ``sigla == numero_lider(sigla)`` é essencial: só re-arbitra quando o
decidido é o rótulo genérico puro da família (o cenário do bug — calibração
deixa o genérico vencer por score). Sem essa guarda, o módulo re-litigaria
decisões que JÁ elegeram um irmão específico (ex.: base ``25VT`` "TRIP
DIFERENCA TENSAO" vs irmão ``25ER`` "FALHA SINCRONISMO") — nesses casos a
palavra "SINCRONISMO"/"FALHA" é vocabulário comum da família ANSI-25 inteira,
não um qualificador discriminante, e sinalizaria falso-positivo de
ambiguidade (visto em dados reais: ``docs/input_nao_homogeneo_1_GTD.xlsx``,
casos "Sincronismo (25) - Falha por Diferença de Tensão/Ângulo").

Família de irmãos identificada via ``motor_regras._numero_lider`` (mesmo
critério usado por ``filtro_preciso.filtrar_especificidade``), não por
``sigla.startswith(base)`` ingênuo: siglas "combo" como ``2759`` (27+59) ou
``8750`` (87+50) compartilham prefixo textual com bases de 2 dígitos mas são
de família ANSI diferente (``_numero_lider("2759") == "27"``, não ``"75"`` ou
``"59"``) — usar apenas startswith geraria falso-positivo nesses casos.

Token distintivo de um irmão = presente na descrição do irmão, ausente da
descrição da base E exclusivo desse irmão dentro da família (não repetido em
nenhuma outra descrição do grupo) — evita que vocabulário compartilhado por
vários irmãos (ex.: "SINCRONISMO" na família 25) seja tratado como
qualificador de um único irmão.

Risco avaliado e aceito (revisão final de branch SP-G, achado 1): a busca de
irmão roda sobre ``(*lp.discretos, *lp.analogicos)`` — a lista padrão
INTEIRA — não sobre ``rec.candidatos`` (sobreviventes pós-``filtro_preciso``/
``filtro_especificidade``/``semantica_estados.filtrar_por_estado``/whitelist
de equipamento). Isso é proposital: a correção existe justamente porque o
irmão certo (ex. ``79OK``) pode não entrar no top-K por score bruto de texto
— exigir presença prévia em ``rec.candidatos`` reintroduziria o bug que este
módulo corrige. Consequência teórica: um irmão eliminado por
``filtrar_por_estado`` por CAUSA (conflito de classe de estado do MM) ainda
pode ser promovido aqui se tiver token exclusivo casando no texto.

Investigado e construído um cenário sintético que reproduz exatamente isso
(``tests/test_especificidade_qualificador.py::test_irmao_promovido_apesar_de_filtro_estado_hard_documented``)
— o mecanismo É alcançável em tese, e uma varredura contra a lista padrão
REAL (``docs/Pontos Padrao ADMS_v2.xlsx``) confirma que a hipótese de que
"vocabulário distintivo tende a coincidir com a classe do MM" NÃO é uma
garantia geral: existem DUAS exceções conhecidas, com naturezas diferentes.

1. Família ANSI-51, irmão ``51NL`` ("SOBRECORRENTE TEMPORIZADA LOCAL", MM
   classe EVENTO) tem como token exclusivo "LOCAL", que
   ``semantica_estados.detectar_estado`` classifica como LOCAL_REMOTO — uma
   classe DIFERENTE da classe MM do próprio ``51NL``. O conflito é real, mas
   INALCANÇÁVEL hoje por um motivo estrutural, não por sorte: a família 51
   não tem nenhuma sigla igual à sua própria raiz bare ("51") na lista
   padrão — só existem irmãos qualificados (``51NL`` e outros). A guarda
   ``base == numero_lider(base)`` (linha ~92 acima) só deixa este módulo
   disparar quando o decidido É a raiz bare da família; sem um "51" bare
   decidível, o roteador nunca decide "51" para a família 51, então este
   módulo nunca é acionado para ela.

2. Família ANSI-21, irmão ``21D`` ("DISPARO LOCALIZADOR DE FALTA", MM classe
   EVENTO) tem "LOCALIZADOR" como um dos tokens exclusivos, e
   ``semantica_estados.detectar_estado("LOCALIZADOR")`` também retorna
   LOCAL_REMOTO — só que aqui, ao contrário da 51, a família TEM raiz bare
   decidível (``"21" — FUNCAO DISTANCIA`` existe na lista padrão), então
   este é um caso que uma garantia baseada só em "tem raiz bare?" NÃO
   excluiria estruturalmente. A causa raiz é diferente da família 51: é um
   bug de léxico pré-existente em ``semantica_estados._LEXICO`` — o prefixo
   ``"LOCAL"`` casa acidentalmente com "LOCALIZADOR" (localizador de FALTA,
   nada a ver com local/remoto), tratado como acompanhamento em separado
   (achado da revisão final de branch SP-G, fix round 2). Hoje isso é
   um risco LATENTE, não ativo: contra o texto REAL do sinal ("DISPARO
   LOCALIZADOR DE FALTA" completo), ``detectar_estado`` retorna ``None``
   (ambíguo — "DISPARO"/"FALTA" também casam como EVENTO, empatando com o
   falso LOCAL_REMOTO de "LOCALIZADOR"), e texto ambíguo é tratado como
   "sem evidência" por ``compativel``/``filtrar_por_estado`` — ou seja,
   ``21D`` NÃO é hoje rejeitado por ``filtrar_por_estado`` para esse texto
   específico. Mas uma variação de texto real sem as palavras que
   desambiguam (ex. "21 - Funcao Localizador", sem "DISPARO"/"FALTA")
   reativaria o falso LOCAL_REMOTO isolado e causaria uma rejeição
   incorreta de ``21D`` por ``filtrar_por_estado`` — esse risco só fecha de
   verdade com o fix do léxico em ``semantica_estados.py`` (fora de escopo
   deste módulo).

A garantia que de fato vale — e que é verificada automaticamente por
``tests/test_especificidade_qualificador.py::test_scan_lp_real_sem_conflito_token_classe_mm_em_familia_com_raiz_bare``
contra a lista padrão real — é mais estreita do que "zero conflitos
existem": *nenhuma família ANSI com raiz bare DECIDÍVEL, EXCETO a 21 (achado
2, risco latente rastreado separadamente), tem um irmão cujo token exclusivo
conflite com a classe de estado do MM desse próprio irmão*. A família 51
fica fora do escopo por construção (nunca é alcançada, não por exclusão
manual); a família 21 é excluída explicitamente, por nome, com a razão
documentada acima. Se a lista padrão mudar e uma TERCEIRA família COM raiz
bare decidível introduzir essa colisão, o teste de regressão falha e força
reavaliação consciente — o escopo aceito hoje é exatamente estas duas
exceções, não mais que isso.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

from tdt.config import Config
from tdt.contracts import Candidato, SignalRecord
from tdt.motor_regras import _numero_lider
from tdt.normalizacao.normalizador import canonizar


def tokens_distintivos_por_familia(
    todos, base: str, lider_base: str, config: Config
) -> dict[str, frozenset[str]]:
    """Para cada irmão da família de ``base`` (mesmo ``_numero_lider``, exceto
    a própria ``base``), calcula seu conjunto de tokens distintivos: presentes
    na descrição do irmão, ausentes da descrição da base E exclusivos desse
    irmão dentro da família (não repetidos em nenhum outro irmão do grupo).

    Extraído de ``preferir_irmao_qualificado`` para ser reutilizado pelo teste
    de varredura da lista padrão real (``tests/test_especificidade_qualificador.py``)
    sem duplicar a lógica de exclusividade de token.
    """
    desc_base = next(
        (s.descricao for s in todos if s.sigla.upper() == base), ""
    )
    tokens_base = frozenset(canonizar(desc_base, config).split()) if desc_base else frozenset()

    irmaos: list[tuple[str, frozenset[str]]] = []
    for s in todos:
        sig = s.sigla.upper()
        if sig == base or _numero_lider(sig) != lider_base or not s.descricao:
            continue
        irmaos.append((s.sigla, frozenset(canonizar(s.descricao, config).split())))

    # Token só conta como qualificador se for exclusivo de UM irmão dentro da
    # família (não aparece na base nem em outro irmão) — vocabulário comum a
    # vários irmãos (ex. "SINCRONISMO" na família 25) não decide nada.
    contagem: Counter[str] = Counter()
    for _, toks in irmaos:
        for t in toks - tokens_base:
            contagem[t] += 1

    return {
        sig: frozenset(t for t in (toks - tokens_base) if contagem[t] == 1)
        for sig, toks in irmaos
    }


def preferir_irmao_qualificado(
    rec: SignalRecord, lp, config: Config | None = None
) -> SignalRecord:
    """Troca a sigla decidida por um irmão mais específico quando o texto do
    sinal contém a palavra que o distingue da base. Múltiplos irmãos casando
    -> ``status="revisao"``, motivo ``qualificador_ambiguo``.
    """
    if rec.status != "decidido" or not rec.sigla_sinal or lp is None:
        return rec
    if config is None:
        config = Config()

    base = rec.sigla_sinal.upper()
    lider_base = _numero_lider(base)
    if lider_base is None or base != lider_base:
        # Só re-arbitra quando o decidido é a raiz genérica da família (ex.
        # "79", "25"); sigla já específica (25VT, 81E1, 20T...) não é
        # re-litigada por este módulo (ver docstring).
        return rec

    texto = frozenset(rec.descricoes.normalizada.upper().split())

    # Busca na lista padrão INTEIRA, não em rec.candidatos (proposital — ver
    # "Risco avaliado e aceito" na docstring do módulo: exigir presença
    # prévia em candidatos reintroduziria o bug que este módulo corrige).
    todos = (*lp.discretos, *lp.analogicos)
    distintivos_por_irmao = tokens_distintivos_por_familia(todos, base, lider_base, config)

    casando: list[str] = []
    for sig, distintivos in distintivos_por_irmao.items():
        if distintivos and (distintivos & texto):
            casando.append(sig)

    if len(casando) == 1:
        irmao = casando[0]
        justificativa = f"{irmao} por qualificador (base {rec.sigla_sinal})"
        if rec.justificativa:
            justificativa = f"{rec.justificativa} | {justificativa}"
        # candidatos[0] deve refletir a sigla DECIDIDA, não a base descartada
        # — senão a auditoria mostra o score de "79" ao lado do rótulo
        # "79OK", confundindo quem revisa o relatório. Preserva o score do
        # antigo topo (a confiança da decisão não mudou, só a sigla) e marca
        # a origem como "qualificador" para rastreabilidade.
        score_antigo = rec.candidatos[0].score if rec.candidatos else 0.0
        candidato_promovido = Candidato(irmao, score_antigo, "qualificador")
        novos_candidatos = (candidato_promovido, *rec.candidatos)
        return replace(
            rec, sigla_sinal=irmao, justificativa=justificativa,
            candidatos=novos_candidatos,
        )

    if len(casando) > 1:
        # justificativa é o motivo literal ("qualificador_ambiguo"), no mesmo
        # padrão de "estado_sem_candidato"/"fora_whitelist_equipamento" —
        # pipeline._classificar_roteado (linhas 341-343) faz match exato de
        # d.justificativa contra a lista de motivos conhecidos para propagar
        # ao ItemRevisao; texto livre aqui seria silenciosamente reclassificado
        # como "score_baixo"/"sigla_multipla".
        return replace(rec, status="revisao", justificativa="qualificador_ambiguo")

    return rec
