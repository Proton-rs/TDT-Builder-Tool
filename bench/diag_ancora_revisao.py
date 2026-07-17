"""Diagnóstico P5 (SP-OBS-17JUL): âncora de sigla detectada que terminou em
revisão/sem decisão + generalização do caso 81U1 (partição por classe de MM).
Uso: PYTHONPATH=src python bench/diag_ancora_revisao.py

Diagnóstico puro -- não altera matching/scoring. Três saídas:

1. Casos: para cada lista real, roda o pipeline e, para cada registro em
   ``resultado.revisao`` (status != "decidido") onde ``ancoragem_sigla.detectar``
   acha >=1 âncora, classifica H1 (irmãos da mesma família da âncora no
   top-3 sugerido) / H2 (roteador rejeitou por `confiança calibrada < piso`,
   ver ``roteador._quadrante``) / H3 (nenhuma sigla-âncora sobrevive no
   top-3 sugerido) / outra.
2. Partição LP: agrupa siglas da lista padrão por família ANSI
   (``ancoragem_sigla._familia``), tabula ``classe_do_mm(sp.mm)`` -> variantes
   (raiz nua da família excluída -- é sempre FUNCAO/trivial, não é o caso de
   ambiguidade que o C4 mira) e marca famílias onde alguma classe isola
   exatamente 1 variante, e famílias onde a classe_do_mm produz >=2 grupos
   não-triviais (discrimina, mesmo sem isolar a 1 variante -- caso 81/ATIVACAO).
3. FP do léxico: roda ``semantica_estados.detectar_estado`` sobre cada token
   distinto das descrições normalizadas (já processadas pelo pipeline) das
   listas reais, e lista, por prefixo do léxico, quais tokens casaram (para
   inspeção manual do padrão "LOCALIZADOR"->LOCAL_REMOTO).
"""
from __future__ import annotations

import warnings
import logging
from collections import Counter, defaultdict
from pathlib import Path

warnings.simplefilter("ignore")
logging.disable(logging.CRITICAL)

from tdt import ancoragem_sigla, semantica_estados
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.pipeline import executar

_TEMPLATE = "docs/dnp3_template.xlsx"
_LISTA_PADRAO = "docs/Pontos Padrao ADMS_v8.xlsx"  # única garantida com aba DE->PARA

_LISTAS_REAIS = [
    ("GTD", "docs/input_nao_homogeneo_1_GTA.xlsx"),
    ("IMA", "docs/input_homogeneo_IMA.xlsx"),
    ("FWB", "docs/input_nao_homogeneo_2_FWB.xlsx"),
    ("GPR", "docs/input_nao_homogeneo_3_GPR.xlsx"),
    ("GAU", "docs/input_nao_homogeneo_4_GAU.xlsx"),
]

_OUT = Path("bench/resultados/diag_ancora_revisao.log")


def _detectar_ancoras(rec, lp: ListaPadraoADMS) -> list[ancoragem_sigla.Ancora]:
    """Mesma escolha de domínio que ``pipeline._classificar_roteado``: só a
    categoria confiável quando ``categoria_confiavel``, os dois domínios
    (Discrete+Analog) quando incerta."""
    if rec.tipo_sinal.categoria_confiavel:
        cat = "Discrete" if rec.tipo_sinal.categoria == "Discrete" else "Analog"
        return ancoragem_sigla.detectar(rec, lp, cat)
    return (
        ancoragem_sigla.detectar(rec, lp, "Discrete")
        + ancoragem_sigla.detectar(rec, lp, "Analog")
    )


def _exata_ou_juncao(rec, sigla_upper: str) -> str:
    tokens = rec.descricoes.normalizada.upper().split()
    if sigla_upper in tokens:
        return "exata"
    for i in range(len(tokens) - 1):
        if tokens[i] + tokens[i + 1] == sigla_upper:
            return "juncao"
    return "?"


# Únicos motivos de ItemRevisao cujo ``candidatos_sugeridos`` é populado pelo
# funil de scoring (ver pipeline._classificar_roteado, linhas 447-508). Os
# demais (custom_id_duplicado, nome_sigla_inconsistente, modulo_indefinido,
# modulo_duplicado_entre_sheets, endereco_duplicado, ...) são gates
# estruturais anteriores/paralelos ao scoring -- ItemRevisao é construído sem
# candidatos_sugeridos (default ``()``), então H1/H2/H3 (que dependem do
# top-3 sugerido) seriam vacuamente "confirmados" ali por ausência de dado,
# não por evidência real. Classificados à parte, como "estrutural".
_MOTIVOS_FUNIL = {
    "score_baixo", "sigla_multipla", "categoria_ambigua", "categoria_incompativel",
    "estado_sem_candidato", "fora_whitelist_equipamento", "qualificador_ambiguo",
}


def _classificar_caso(rec, ancoras: list[ancoragem_sigla.Ancora], top: list, motivo: str) -> list[str]:
    """Devolve as hipóteses que casam (lista, pode ser vazia -> "outra")."""
    if motivo not in _MOTIVOS_FUNIL:
        return ["estrutural"]

    tags: list[str] = []
    justificativa = rec.justificativa or ""
    if "< piso" in justificativa:
        tags.append("H2")

    siglas_top = {c.sigla.upper() for c in top}
    ancora_siglas = {a.sigla.upper() for a in ancoras}
    if not (ancora_siglas & siglas_top):
        tags.append("H3")

    familias_ancora = {ancoragem_sigla._familia(s) for s in ancora_siglas}
    siglas_familia_no_top = {
        c.sigla.upper() for c in top if ancoragem_sigla._familia(c.sigla) in familias_ancora
    }
    if len(siglas_familia_no_top) >= 2:
        tags.append("H1")

    return tags or ["outra"]


def analisar_casos(lp: ListaPadraoADMS) -> list[dict]:
    """Parte 1: âncora detectada + status != decidido, por lista real."""
    cfg = Config()
    enc = criar_encoder(cfg.modelo_embedding)
    casos: list[dict] = []
    corpus_textos: list[str] = []

    for nome, path in _LISTAS_REAIS:
        try:
            resultado, _wb = executar(
                path, _TEMPLATE, _LISTA_PADRAO,
                config=cfg, encoder=enc, subestacao=nome,
            )
        except Exception as e:
            print(f"!! {nome} ({path}): pipeline falhou: {e!r}")
            continue

        for rec in resultado.lista.registros:
            corpus_textos.append(rec.descricoes.normalizada)
        for item in resultado.revisao:
            corpus_textos.append(item.registro.descricoes.normalizada)

        for item in resultado.revisao:
            rec = item.registro
            if rec.status == "decidido":
                continue
            ancoras = _detectar_ancoras(rec, lp)
            if not ancoras:
                continue
            top = sorted(item.candidatos_sugeridos, key=lambda c: c.score, reverse=True)[:3]
            tags = _classificar_caso(rec, ancoras, top, item.motivo)
            casos.append({
                "lista": nome,
                "id": rec.id,
                "descricao": rec.descricoes.bruta,
                "ancoras": [
                    (a.sigla, _exata_ou_juncao(rec, a.sigla.upper())) for a in ancoras
                ],
                "familia": sorted({ancoragem_sigla._familia(a.sigla) for a in ancoras}),
                "top3": [(c.sigla, round(c.score, 3), c.fonte) for c in top],
                "gap": round(top[0].score - top[1].score, 3) if len(top) >= 2 else None,
                "motivo": item.motivo,
                "justificativa": rec.justificativa,
                "tags": tags,
            })

    return casos, corpus_textos


def analisar_particao_lp(lp: ListaPadraoADMS) -> dict:
    """Parte 2: partição por família ANSI x classe_do_mm (generalização 81U1)."""
    sinais = list(lp.discretos) + list(lp.analogicos)
    fam: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for s in sinais:
        f = ancoragem_sigla._familia(s.sigla)
        if s.sigla.upper() == f:
            continue  # raiz nua da familia -- trivial (sempre FUNCAO isolado), fora do escopo
        c = semantica_estados.classe_do_mm(s.mm)
        fam[f][str(c)].add(s.sigla)

    familias_multi = {}  # familia -> {classe: [variantes...]}, so as com >=2 variantes
    isola_1 = []  # (familia, classe, variante)
    discrimina_multi_classe = []  # familia -> {classe: [...]} com >=2 classes nao-None
    for f, classes in sorted(fam.items()):
        total = set()
        for v in classes.values():
            total |= v
        if len(total) < 2:
            continue
        familias_multi[f] = {c: sorted(v) for c, v in classes.items()}
        classes_nonone = {c: v for c, v in classes.items() if c != "None"}
        if len(classes_nonone) >= 2:
            discrimina_multi_classe.append(f)
        for c, v in classes.items():
            if c != "None" and len(v) == 1:
                isola_1.append((f, c, next(iter(v))))

    return {
        "familias_multi": familias_multi,
        "isola_1": isola_1,
        "discrimina_multi_classe": discrimina_multi_classe,
    }


def analisar_fp_lexico(corpus_textos: list[str]) -> dict[str, Counter]:
    """Parte 3: tokens do corpus real que casam por prefixo em cada entrada
    do léxico (para inspeção manual do padrão LOCALIZADOR->LOCAL_REMOTO)."""
    tokens: Counter[str] = Counter()
    for texto in corpus_textos:
        for tok in texto.upper().split():
            tokens[tok] += 1

    por_prefixo: dict[str, Counter] = defaultdict(Counter)
    for tok, n in tokens.items():
        if tok in semantica_estados._TOKENS_EXATOS:
            por_prefixo[f"[exato] {tok}"][tok] = n
            continue
        for prefixo, _classe, _pol in semantica_estados._LEXICO:
            if tok.startswith(prefixo):
                por_prefixo[prefixo][tok] += n
                break  # mesma prioridade de _classificar_token (primeiro match)

    return por_prefixo


def main() -> None:
    lp = ListaPadraoADMS.carregar(_LISTA_PADRAO)
    linhas: list[str] = []
    linhas.append("# diag_ancora_revisao -- SP-OBS-17JUL P5 Fase-0 (2026-07-17)\n")

    # --- Parte 1 ---
    casos, corpus_textos = analisar_casos(lp)
    linhas.append("## Parte 1 -- casos ancora->revisao\n")
    linhas.append(f"total de casos (ancora detectada + status != decidido): {len(casos)}\n")
    contagem_tags: Counter[str] = Counter()
    for c in casos:
        for t in c["tags"]:
            contagem_tags[t] += 1
    linhas.append(f"contagem por hipotese (nao mutuamente exclusivas): {dict(contagem_tags)}\n")
    for c in casos:
        linhas.append(
            f"[{c['lista']}] id={c['id']} tags={c['tags']} motivo={c['motivo']}\n"
            f"  desc={c['descricao']!r}\n"
            f"  ancoras={c['ancoras']} familia={c['familia']}\n"
            f"  top3={c['top3']} gap={c['gap']}\n"
            f"  justificativa={c['justificativa']!r}\n"
        )

    # --- Parte 2 ---
    particao = analisar_particao_lp(lp)
    linhas.append("## Parte 2 -- particao LP por familia x classe_do_mm\n")
    linhas.append(f"familias com >=2 variantes (raiz nua excluida): {len(particao['familias_multi'])}\n")
    for f, classes in particao["familias_multi"].items():
        linhas.append(f"  familia {f}: {classes}")
    linhas.append("")
    linhas.append(
        f"familias onde alguma classe isola exatamente 1 variante ({len(particao['isola_1'])}):"
    )
    for f, c, v in particao["isola_1"]:
        linhas.append(f"  {f} -> {c} isola {v}")
    linhas.append("")
    linhas.append(
        "familias onde classe_do_mm produz >=2 grupos nao-triviais "
        f"(discrimina, mesmo sem isolar a 1) ({len(particao['discrimina_multi_classe'])}): "
        f"{particao['discrimina_multi_classe']}\n"
    )

    # --- Parte 3 ---
    por_prefixo = analisar_fp_lexico(corpus_textos)
    linhas.append("## Parte 3 -- FP do lexico (semantica_estados) no corpus real\n")
    for prefixo, tokens in sorted(por_prefixo.items()):
        linhas.append(f"  prefixo {prefixo!r}: {dict(tokens)}")

    texto = "\n".join(linhas) + "\n"
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"log em {_OUT}")


if __name__ == "__main__":
    main()
