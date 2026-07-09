"""Gera docs/Pontos Padrao ADMS_v7.xlsx = v2 + aba DiscreteAnalog (TAP).

Base = v2 (default atual do app) para NAO mudar o matching de nenhum sinal
existente — v7 so acrescenta a categoria nova. Valores da linha TAP vem do
TDT real (exportTDT_UTR_GTD_1_20260626.xlsx, aba DNP3_DiscreteAnalog):
SignalType=TapPosition, MeasType=Discrete, Phases=ABC, Direction=Read,
NormalValue=9, RemotePointType=Analog, deadband Float, DeviceMapping->COMTAP.
So em transformadores.
"""
import shutil

import openpyxl

ORIGEM = "docs/Pontos Padrao ADMS_v2.xlsx"
DESTINO = "docs/Pontos Padrao ADMS_v7.xlsx"

HEADER = ("SINAL", "DESCRIÇÃO NOVA", "SIGNAL TYPE", "MEASUREMENT TYPE", "FASES",
          "DIRECTION", "NORMAL VALUE", "REMOTE POINT TYPE", "OUTPUT DATA TYPE",
          "DEVICE MAPPING REF", "APLICABILIDADE")
TAP = ("TAP", "POSICAO DO TAP", "TapPosition", "Discrete", "ABC",
       "Read", 9, "Analog", "Float", "COMTAP", "TRANSFORMADOR")

shutil.copyfile(ORIGEM, DESTINO)
wb = openpyxl.load_workbook(DESTINO)
ws = wb.create_sheet("DiscreteAnalog", index=2)  # ao lado de Discrete/Analog
ws.append(HEADER)
ws.append(TAP)
wb.save(DESTINO)
print(f"gerado: {DESTINO}")
