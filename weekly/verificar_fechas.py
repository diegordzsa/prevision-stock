# -*- coding: utf-8 -*-
"""Compara las fechas calculadas por el Sheet con el oraculo de burndown.py.

Ejecutar tras update_sheet.py:
    C:\\Python314\\python weekly/verificar_fechas.py
"""
import os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from burndown import dia_agotamiento
from google.oauth2 import service_account
from googleapiclient.discovery import build

SID = '1wNXOy6dIjQqfgsSmnqvdEVFmCv-ibj0kgy4BuyYQvZ8'
KEY = r'C:\Users\diego\Downloads\prevision-stock-5264cd38736b.json'
HOJA = 'Reporte Consolidado'

creds = service_account.Credentials.from_service_account_file(
    KEY, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
s = build('sheets', 'v4', credentials=creds).spreadsheets()


def val(rng):
    r = s.values().get(spreadsheetId=SID, range=f"'{HOJA}'!{rng}",
                       valueRenderOption='UNFORMATTED_VALUE').execute().get('values', [])
    return r


def num(x):
    return float(str(x).replace(',', ''))


base = datetime.date.fromisoformat(str(val('B44')[0][0])[:10]) \
    if isinstance(val('B44')[0][0], str) else None
if base is None:
    # B44 llega como serial de Sheets (dias desde 1899-12-30)
    base = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(val('B44')[0][0]))
lead = int(num(val('B45')[0][0]))
colchon = int(num(val('B46')[0][0]))
print(f"Fecha base {base} | lead {lead}d | colchon {colchon}d\n")

CASOS = [
    ("SERUM", 49, 'E25', ('D25', 'D26', 'D27', 'D28')),
    ("CHAMPU", 50, 'E32', ('D32', 'D33', 'D34', 'D35')),
]

fallos = []
for nombre, fila, cstock, cdem in CASOS:
    stock = num(val(cstock)[0][0])
    dem = tuple(num(val(c)[0][0]) for c in cdem)
    dia = dia_agotamiento(stock, dem)
    esperado_agota = base + datetime.timedelta(days=int(dia))
    esperado_pedido = base + datetime.timedelta(days=int(dia) - colchon - lead)

    fila_sheet = val(f'A{fila}:G{fila}')[0]
    got_agota = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(fila_sheet[2]))
    got_pedido = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(fila_sheet[4]))

    for etiqueta, got, esp in (("agotamiento", got_agota, esperado_agota),
                               ("fecha pedido", got_pedido, esperado_pedido)):
        ok = got == esp
        print(("  OK   " if ok else "  FALLO") +
              f" {nombre} {etiqueta}: Sheet={got} oraculo={esp}")
        if not ok:
            fallos.append(f"{nombre}/{etiqueta}")
    print(f"         (stock {stock:.0f}, dia de agotamiento {dia:.2f})")

print()
if fallos:
    print(f"DISCREPANCIAS: {', '.join(fallos)}")
    sys.exit(1)
print("Sheet y oraculo coinciden.")
