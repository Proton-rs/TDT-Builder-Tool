"""Diagnóstico (SP-CVA, Fase 1, Task 1): rastreio de comandos, tipo VAB e
colisões de módulo na lista CVA. Padrão dos `bench/diag_*.py` existentes
(ver `diag_direcao_comando.py`, `diag_outputs_sem_par.py`, `diag_colunas.py`).

NÃO altera produção. Só instrumenta (monkeypatch local de captura, restaurado
ao final) e documenta achados em
`docs/superpowers/specs/2026-07-13-diag-cva-achados.md`.

Caminho do input real é PESSOAL do usuário (fora do repo) -- passe por
argv[1] se rodar em outra máquina; o default abaixo é só conveniência local.

Uso: PYTHONPATH=src python bench/diag_cva.py [input.xlsx]
Saída: bench/resultados/diag_cva.log (+ print no stdout)
"""
from __future__ import annotations

import sys
import warnings
import logging
from collections import defaultdict
from pathlib import Path

warnings.simplefilter("ignore")
logging.disable(logging.CRITICAL)

import openpyxl

import tdt.dc_pairer as dc_pairer_mod
import tdt.pipeline as pipeline_mod
from tdt.analise.analise_colunas import analisar, normalizar_emb
from tdt.analise.identificador import ler_rows
from tdt.config import Config
from tdt.contracts import SignalRecord
from tdt.dados.encoder import criar_encoder
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.engine_tdt import _nome_hierarquico, _remote_unit
from tdt.normalizacao.estruturador import estruturar
from tdt.normalizacao.normalizador import canonizar
from tdt.normalizacao.vocabulario_tipo import classificar as classificar_tipo
from tdt.pipeline import executar

# caminho pessoal do usuário -- caminho da máquina em que este diag foi
# rodado (13jul); sobrescreva via argv[1] em outra máquina.
_INPUT_DEFAULT = (
    r"C:\Users\vinic\Documents\docs importantes\RGE\CVA"
    r"\CVA - Pontos Por Equipamentos DNP_V03 - COS - resumida.xlsx"
)
_TEMPLATE = "docs/dnp3_template.xlsx"
_LISTA = "docs/Pontos Padrao ADMS_v8.xlsx"
_SUBESTACAO = "CVA"
_SHEETS_COMANDO = ("BC1", "BC2", "BC5_6", "CVA11")
_OUT = Path("bench/resultados/diag_cva.log")


def _sheet_de(rec_id: str) -> str:
    return rec_id.rsplit(":", 1)[0] if ":" in rec_id else ""


def _chave(rec: SignalRecord) -> tuple:
    return (rec.modulo.nome, rec.eletrico.nome_equipamento, rec.sigla_sinal)


# ---------------------------------------------------------------------------
# Captura via monkeypatch: pipeline.executar não expõe estágios intermediários
# (sinais pós-estruturação, decididos pré-dc_pairer) no seu contrato público
# -- capturamos localmente e restauramos os nomes originais no `finally`.
# ---------------------------------------------------------------------------

def _rodar_com_captura(cfg: Config, enc):
    entrada: dict[str, list[SignalRecord]] = defaultdict(list)  # sheet -> sinais pós-estruturação
    decididos_capturados: list[SignalRecord] = []

    orig_aplicar_identidade = pipeline_mod.aplicar_identidade
    orig_parear = dc_pairer_mod.parear

    def _aplicar_identidade_captura(sinais, sn, rows, config):
        if sn in _SHEETS_COMANDO:
            entrada[sn].extend(sinais)
        return orig_aplicar_identidade(sinais, sn, rows, config)

    def _parear_captura(registros, config=None):
        decididos_capturados.extend(registros)
        return orig_parear(registros, config)

    pipeline_mod.aplicar_identidade = _aplicar_identidade_captura
    dc_pairer_mod.parear = _parear_captura
    try:
        resultado, _wb = executar(
            _INPUT, _TEMPLATE, _LISTA,
            config=cfg, encoder=enc, subestacao=_SUBESTACAO, diagnostico=True,
        )
    finally:
        pipeline_mod.aplicar_identidade = orig_aplicar_identidade
        dc_pairer_mod.parear = orig_parear
    return resultado, entrada, decididos_capturados


def _destino_comando(
    comando: SignalRecord, decididos: list, lista_final: tuple, revisao: tuple,
) -> str:
    # `comando` é capturado na ENTRADA (pós-estruturação, pré-classificação):
    # `sigla_sinal` ainda é None ali. Se o mesmo id chegou a `decididos`
    # (pré dc_pairer), usa a versão JÁ CLASSIFICADA para a chave de
    # agrupamento do dc_pairer (módulo, equipamento, sigla) -- senão a
    # comparação por chave nunca bate (sigla None != sigla decidida) e todo
    # comando fundido apareceria como falso AUSENTE.
    comando_decidido = next((d for d in decididos if d.id == comando.id), comando)
    chave = _chave(comando_decidido)
    indices_cmd = comando_decidido.enderecamento.indices

    # 1) sobrevive fundido no TDT final (par D+C completo).
    for r in lista_final:
        if (_chave(r) == chave and r.tipo_sinal.direcao == "InputOutput"
                and r.enderecamento.indices_saida == indices_cmd):
            return f"TDT ReadWrite (fundido com id do status={r.id})"

    # 2) sobrevive solto (Write órfão / write_legitimo).
    for r in lista_final:
        if r.id == comando.id and r.tipo_sinal.direcao == "Output":
            return "TDT Write órfão"

    # 3) revisão direta (mesmo id do comando).
    for it in revisao:
        if it.registro.id == comando.id:
            return f"revisão: {it.motivo}"

    # 4) revisão como par fundido (ex. custom_id_duplicado pegou o par depois
    #    de fundido -- carrega o id do status, não do comando original).
    for it in revisao:
        r = it.registro
        if (_chave(r) == chave and r.enderecamento.indices_saida == indices_cmd):
            return f"revisão: {it.motivo} (fundido com id do status={r.id})"

    # 5) nunca chegou a `decididos` (pré dc_pairer) -- perdido antes do
    #    pareamento, na classificação ou antes dela.
    if comando.id not in {d.id for d in decididos}:
        return "AUSENTE (perda silenciosa) -- não chegou a `decididos`"

    return "AUSENTE (perda silenciosa)"


def diagnosticar_comandos(entrada: dict, decididos, lista_final, revisao, linhas: list[str]) -> None:
    linhas.append("## 1) Rastreio de comandos (direção Output) — BC1/BC2/BC5_6/CVA11\n")
    total = 0
    ausentes = 0
    for sn in _SHEETS_COMANDO:
        sinais_sheet = entrada.get(sn, [])
        comandos = [r for r in sinais_sheet if r.tipo_sinal.direcao == "Output"]
        linhas.append(f"### {sn}: {len(comandos)} comando(s) detectado(s) na entrada")
        for c in sorted(comandos, key=lambda r: _sheet_de(r.id)):
            total += 1
            destino = _destino_comando(c, decididos, lista_final, revisao)
            if destino.startswith("AUSENTE"):
                ausentes += 1
            linha_id = c.id.rsplit(":", 1)[-1] if ":" in c.id else c.id
            endereco = ";".join(str(i) for i in c.enderecamento.indices) or "(vazio)"
            linhas.append(
                f"  linha={linha_id:<6} texto={c.descricoes.bruta!r:<60} "
                f"endereco={endereco:<12} destino={destino}"
            )
            if "comando_sem_discreto" in destino or "estado_sem_candidato" in destino:
                cd = next((d for d in decididos if d.id == c.id), None)
                equip = cd.eletrico.nome_equipamento if cd else None
                sigla_cmd = cd.sigla_sinal if cd else None
                irmaos = [
                    d for d in decididos
                    if d.id != c.id and d.eletrico.nome_equipamento == equip
                    and _sheet_de(d.id) == sn
                ]
                linhas.append(
                    f"    -> sigla do comando (se decidido): {sigla_cmd!r}; "
                    f"registros decididos no mesmo equipamento ({equip!r}) na sheet: "
                    + ", ".join(f"{d.id}:{d.sigla_sinal}:{d.tipo_sinal.direcao}" for d in irmaos)
                )
        linhas.append("")
    linhas.append(f"total comandos detectados: {total} | AUSENTE (perda silenciosa): {ausentes}\n")


def diagnosticar_vab_cva11(
    cfg: Config, enc, lista_final: tuple, revisao: tuple, linhas: list[str],
) -> None:
    linhas.append("## 2) CVA11 (VAB) — coluna TIPO x marcador de seção\n")
    lp = ListaPadraoADMS.carregar(_LISTA)
    corpus = [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.discretos if s.descricao]
    ref = normalizar_emb(enc([d for _, d in corpus]))

    wb = openpyxl.load_workbook(_INPUT, read_only=True, data_only=True)
    if "CVA11" not in wb.sheetnames:
        linhas.append("!! sheet CVA11 não encontrada no input\n")
        wb.close()
        return
    rows = ler_rows(wb["CVA11"])
    mapa = analisar(rows, enc, ref, siglas_set=lp.siglas, config=cfg)
    c_tipo = mapa.colunas.get("tipo")
    linhas.append(f"MapaColunas CVA11: header_row={mapa.header_row} colunas={mapa.colunas}")
    linhas.append(f"coluna TIPO escolhida por _col_tipo: {c_tipo!r}\n")

    sinais = list(estruturar(rows, mapa, sheet_name="CVA11", config=cfg, vocab=None, siglas_set=lp.siglas))
    sinais_por_id = {r.id: r for r in sinais}

    # ids da sheet CVA11 cuja sigla DECIDIDA (final, pós-classificação) é uma
    # tensão de fase -- a busca por substring "VAB"/"VBC"/"VCA" no texto BRUTO
    # falha quando o texto é "Tensão Barra AB" (sem a sigla literal), então
    # cruza com o resultado final (lista + revisão) em vez de só o texto.
    candidatos = [r for r in lista_final if _sheet_de(r.id) == "CVA11"]
    candidatos += [it.registro for it in revisao if _sheet_de(it.registro.id) == "CVA11"]
    alvo = {
        r.id: r for r in candidatos
        if (r.sigla_sinal or "").upper() in ("VAB", "VBC", "VCA")
    }
    # também mantém a busca textual (achados por texto cru, sem sigla decidida
    # ainda -- ex. sinal foi p/ revisão antes de chegar a ter sigla).
    for rec in sinais:
        bruta = rec.descricoes.bruta.upper()
        if any(k in bruta for k in ("VAB", "VBC", "VCA", "TENS")):
            alvo.setdefault(rec.id, rec)

    if not alvo:
        linhas.append("  nenhum sinal VAB/VBC/VCA (por sigla decidida ou texto) encontrado na sheet CVA11")
        linhas.append("")
        wb.close()
        return

    revisao_por_id = {it.registro.id: it.motivo for it in revisao}
    final_por_id = {r.id: r for r in lista_final}
    for rid, decidido_ou_bruto in sorted(alvo.items()):
        rec = sinais_por_id.get(rid)
        if rec is None:
            linhas.append(f"  linha={rid}: não encontrado em `sinais` (estruturado) -- id só existe pós-classificação?")
            continue
        linha_id = rid.rsplit(":", 1)[-1]
        idx0 = int(linha_id) - 1 if linha_id.isdigit() else None
        cel_tipo = None
        if c_tipo is not None and idx0 is not None and 0 <= idx0 < len(rows) and c_tipo < len(rows[idx0]):
            cel_tipo = rows[idx0][c_tipo]
        veio_de = (
            "coluna TIPO" if (cel_tipo is not None and classificar_tipo(cel_tipo) is not None)
            else "marcador de seção (secao_explicita)" if rec.tipo_sinal.categoria_confiavel
            else "default (sem evidência -- nem coluna TIPO nem marcador bateram)"
        )
        if rid in final_por_id:
            destino = f"decidido sigla={final_por_id[rid].sigla_sinal!r} categoria_final={final_por_id[rid].tipo_sinal.categoria!r}"
        elif rid in revisao_por_id:
            destino = f"revisão: {revisao_por_id[rid]}"
        else:
            destino = "AUSENTE (não encontrado em decididos nem revisão)"
        linhas.append(
            f"  linha={linha_id:<6} texto={rec.descricoes.bruta!r:<40} "
            f"categoria(estruturação)={rec.tipo_sinal.categoria:<10} direcao(estruturação)={rec.tipo_sinal.direcao:<8} "
            f"confiavel={rec.tipo_sinal.categoria_confiavel} cel_tipo={cel_tipo!r} veio_de={veio_de} destino={destino}"
        )
    linhas.append("")
    wb.close()


_DOMINIO_PHASECODE = frozenset({"N", "A", "B", "C", "AB", "BC", "AC", "ABC"})


def diagnosticar_fases(lista_final: tuple, linhas: list[str]) -> None:
    linhas.append("## 3) Item 14 — tensões entre fases fora do domínio PhaseCode\n")
    achados = [
        r for r in lista_final
        if r.eletrico.fase is not None and r.eletrico.fase not in _DOMINIO_PHASECODE
    ]
    if not achados:
        linhas.append("  nenhuma fase interna fora do domínio PhaseCode ADMS encontrada (verificar CA explicitamente abaixo)\n")
    for r in achados:
        linhas.append(f"  id={r.id} sigla={r.sigla_sinal} fase_interna={r.eletrico.fase!r} texto={r.descricoes.bruta!r}")
    # CA é um caso especial: está DENTRO do domínio interno (`FASES`), mas
    # FORA do domínio PhaseCode do ADMS (que usa AC) -- não pega no filtro
    # acima. Reporta à parte, é a causa já confirmada (item 14).
    cas = [r for r in lista_final if r.eletrico.fase == "CA"]
    linhas.append(f"\n  registros com fase interna 'CA' (domínio interno OK, PhaseCode ADMS exige 'AC'): {len(cas)}")
    for r in cas:
        linhas.append(f"    id={r.id} sigla={r.sigla_sinal} texto={r.descricoes.bruta!r}")
    linhas.append("")


def diagnosticar_modulo_bc(subestacao: str, revisao: tuple, linhas: list[str]) -> None:
    linhas.append("## 4) BC1/BC2 — grupos removidos por Custom ID duplicado\n")
    remote_unit = _remote_unit(subestacao)
    grupos: dict[str, list] = defaultdict(list)
    for it in revisao:
        if it.motivo != "custom_id_duplicado":
            continue
        r = it.registro
        nome = _nome_hierarquico(
            subestacao, r.modulo.nome, r.eletrico.nome_equipamento, r.eletrico.barra,
            r.sigla_sinal or "?",
        )
        cid = f"{nome}_{remote_unit}" if remote_unit else nome
        grupos[cid].append(r)
    if not grupos:
        linhas.append("  nenhum grupo custom_id_duplicado encontrado\n")
        return
    for cid, regs in grupos.items():
        sheets = sorted({_sheet_de(r.id) for r in regs})
        linhas.append(f"  Custom ID={cid}")
        for r in regs:
            linhas.append(f"    id={r.id} sheet={_sheet_de(r.id)} sigla={r.sigla_sinal} texto={r.descricoes.bruta!r}")
        marca = " <<< sheets distintas (colisão de módulo)" if len(sheets) > 1 else ""
        linhas.append(f"    sheets de origem: {sheets}{marca}")
    linhas.append("")


def main() -> None:
    global _INPUT
    _INPUT = sys.argv[1] if len(sys.argv) > 1 else _INPUT_DEFAULT
    if not Path(_INPUT).exists():
        print(f"BLOCKED: input não encontrado em {_INPUT}")
        sys.exit(1)
    if not Path(_LISTA).exists():
        print(f"BLOCKED: lista padrão não encontrada em {_LISTA}")
        sys.exit(1)
    if not Path(_TEMPLATE).exists():
        print(f"BLOCKED: template não encontrado em {_TEMPLATE}")
        sys.exit(1)

    cfg = Config()
    enc = criar_encoder(cfg.modelo_embedding)

    resultado, entrada, decididos = _rodar_com_captura(cfg, enc)
    lista_final = resultado.lista.registros
    revisao = resultado.revisao

    linhas: list[str] = [f"# diag_cva — SP-CVA Fase 1 Task 1 (2026-07-13) | input={_INPUT}\n"]
    diagnosticar_comandos(entrada, decididos, lista_final, revisao, linhas)
    diagnosticar_vab_cva11(cfg, enc, lista_final, revisao, linhas)
    diagnosticar_fases(lista_final, linhas)
    diagnosticar_modulo_bc(_SUBESTACAO, revisao, linhas)

    texto = "\n".join(linhas) + "\n"
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"log em {_OUT}")


if __name__ == "__main__":
    main()
