# -*- coding: utf-8 -*-
"""Compara las fechas calculadas por el Sheet con el oraculo de burndown.py.

Ejecutar tras update_sheet.py:
    C:\\Python314\\python weekly/verificar_fechas.py

Estados de negocio validos (modelados por la formula del Sheet con IFERROR):
- Si el stock aguanta mas de 12 meses, la columna "se agota" (C) trae el texto
  ">12 meses" en vez de un serial de fecha, y dia_agotamiento() devuelve None.
- Si el tramo tiene demanda incremental <=0 (division por cero evitada), C trae
  "sin datos".
- En ambos casos, la columna D ("debe llegar") y E ("fecha limite") no son
  ISNUMBER en el Sheet, asi que caen en cascada a "-".
Este script reconoce esos tres textos como coincidencia valida cuando el
oraculo tambien dice None; cualquier otra cosa (texto inesperado, o texto en
un lado y fecha en el otro) es una discrepancia real.
"""
import os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from burndown import dia_agotamiento
from google.oauth2 import service_account
from googleapiclient.discovery import build

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from credenciales import ruta_llave

SID = '1wNXOy6dIjQqfgsSmnqvdEVFmCv-ibj0kgy4BuyYQvZ8'
HOJA = 'Reporte Consolidado'

EPOCA = datetime.date(1899, 12, 30)


def svc():
    creds = service_account.Credentials.from_service_account_file(
        ruta_llave(), scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    return build('sheets', 'v4', credentials=creds).spreadsheets()


def val(s, rng):
    r = s.values().get(spreadsheetId=SID, range=f"'{HOJA}'!{rng}",
                       valueRenderOption='UNFORMATTED_VALUE').execute().get('values', [])
    return r


def num(x):
    return float(str(x).replace(',', ''))


def celda_a_fecha_o_texto(x):
    """Interpreta una celda del Sheet: si es texto (">12 meses", "sin datos",
    "-", o cualquier otra cosa inesperada) devuelve (False, texto). Si es un
    serial de fecha valido, devuelve (True, date)."""
    if isinstance(x, str):
        return False, x
    try:
        return True, EPOCA + datetime.timedelta(days=int(x))
    except (TypeError, ValueError):
        return False, f"<valor inesperado: {x!r}>"


def comparar(nombre, fila, cstock, cdem, s, base, lead, colchon):
    """Compara agotamiento y fecha de pedido de un producto. Devuelve la
    lista de etiquetas que fallaron (vacia si todo coincide)."""
    stock = num(val(s, cstock)[0][0])
    dem = tuple(num(val(s, c)[0][0]) for c in cdem)
    dia = dia_agotamiento(stock, dem)

    if dia is None:
        # estado valido: el stock aguanta > 12 meses (o tramo sin demanda
        # incremental). El oraculo no da fecha; el Sheet tampoco deberia.
        d365 = dem[3]
        esperado_agota = ">12 meses" if stock > d365 else "sin datos"
        esperado_pedido = "-"  # D y E caen en cascada a "-" cuando C no es ISNUMBER
    else:
        esperado_agota = base + datetime.timedelta(days=int(dia))
        esperado_pedido = base + datetime.timedelta(days=int(dia) - colchon - lead)

    fila_sheet = val(s, f'A{fila}:G{fila}')[0]
    fila_sheet = fila_sheet + [''] * (7 - len(fila_sheet))  # padding defensivo
    es_fecha_agota, got_agota = celda_a_fecha_o_texto(fila_sheet[2])
    es_fecha_pedido, got_pedido = celda_a_fecha_o_texto(fila_sheet[4])

    fallos_local = []
    for etiqueta, es_fecha, got, esp in (
            ("agotamiento", es_fecha_agota, got_agota, esperado_agota),
            ("fecha pedido", es_fecha_pedido, got_pedido, esperado_pedido)):
        if isinstance(esp, str):
            # el oraculo espera un estado de texto (">12 meses" / "sin datos" / "-")
            ok = (not es_fecha) and got == esp
        else:
            # el oraculo espera una fecha real
            ok = es_fecha and got == esp
        print(("  OK   " if ok else "  FALLO") +
              f" {nombre} {etiqueta}: Sheet={got} oraculo={esp}")
        if not ok:
            fallos_local.append(f"{nombre}/{etiqueta}")

    dia_str = f"{dia:.2f}" if dia is not None else "None"
    print(f"         (stock {stock:.0f}, dia de agotamiento {dia_str})")
    return fallos_local


def main():
    s = svc()

    b44 = val(s, 'B44')[0][0]
    base = datetime.date.fromisoformat(str(b44)[:10]) if isinstance(b44, str) else None
    if base is None:
        # B44 llega como serial de Sheets (dias desde 1899-12-30)
        base = EPOCA + datetime.timedelta(days=int(b44))
    b45 = val(s, 'B45')
    b46 = val(s, 'B46')
    b45_ok = b45 and b45[0] and str(b45[0][0]).strip() != ''
    b46_ok = b46 and b46[0] and str(b46[0][0]).strip() != ''
    if not (b45_ok and b46_ok):
        print("[AVISO] B45 (lead time) o B46 (colchon) esta vacia - no puedo "
              "verificar fechas. Rellena esas celdas o re-ejecuta "
              "weekly/setup_cuando_pedir.py")
        sys.exit(1)
    lead = int(num(b45[0][0]))
    colchon = int(num(b46[0][0]))
    print(f"Fecha base {base} | lead {lead}d | colchon {colchon}d\n")

    CASOS = [
        ("SERUM", 49, 'E25', ('D25', 'D26', 'D27', 'D28')),
        ("CHAMPU", 50, 'E32', ('D32', 'D33', 'D34', 'D35')),
    ]

    fallos = []
    for nombre, fila, cstock, cdem in CASOS:
        fallos += comparar(nombre, fila, cstock, cdem, s, base, lead, colchon)

    print()
    if fallos:
        print(f"DISCREPANCIAS: {', '.join(fallos)}")
        sys.exit(1)
    print("Sheet y oraculo coinciden.")


if __name__ == '__main__':
    main()
