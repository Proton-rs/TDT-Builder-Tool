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
— o mecanismo É alcançável em tese. Porém uma varredura exaustiva da lista
padrão real (``docs/Pontos Padrao ADMS_v2.xlsx``, 26 famílias ANSI, 12 delas
com classes de MM mistas entre irmãos) não encontrou NENHUM caso onde o
token distintivo de um irmão conflite com a própria classe de estado do MM
desse irmão — testado tanto com a descrição completa do irmão quanto com só
os tokens distintivos como texto. Isso não é coincidência: o vocabulário que
distingue um irmão (ex. "BLOQUEADO", "FALTA", "BLOQUEIO") tende a SER o
mesmo vocabulário que evidencia a classe de estado do MM dele (EVENTO) —
ambos vêm da mesma fonte (a descrição padrão do próprio irmão). Dado isso,
o risco é aceito como estreito na prática (guarda bare-root + exclusividade
de token já é apertada) e não justifica complicar a busca com uma
interseção que arriscaria reintroduzir o bug original do Task 5. Se a lista
padrão mudar e uma família introduzir essa colisão, o teste de regressão
falha e força reavaliação consciente.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

from tdt.config import Config
from tdt.contracts import Candidato, SignalRecord
from tdt.motor_regras import _numero_lider
from tdt.normalizacao.normalizador import canonizar


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

    casando: list[str] = []
    for sig, toks in irmaos:
        distintivos = frozenset(t for t in (toks - tokens_base) if contagem[t] == 1)
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
