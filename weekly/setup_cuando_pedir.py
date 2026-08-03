# -*- coding: utf-8 -*-
"""Setup / reparacion de la seccion CUANDO PEDIR (ESTIMADO).

Ejecutar cuando la seccion se rompa o falte:
    C:\\Python314\\python weekly/setup_cuando_pedir.py
    C:\\Python314\\python weekly/setup_cuando_pedir.py --no-write   (dry-run)

Es idempotente y NO destructivo con lo que el usuario haya editado a mano:
  1. Vacia B7 (dato muerto congelado, ninguna formula lo referencia).
  2. Lee B45 (lead time) y B46 (colchon) ANTES de tocar nada. Si tienen valor,
     los CONSERVA tal cual; solo usa los defaults (21 / 7 dias) si estan vacias.
  3. Lee A54:H60 (NOTAS Y SUPUESTOS) ANTES de tocar nada. Si hay contenido, lo
     CONSERVA tal cual; solo usa el texto por defecto si esta vacio.
  4. Reescribe la seccion CUANDO PEDIR en las filas 41-52 (formulas + los
     valores de B45/B46 conservados o los defaults) y las notas en A54 en
     adelante (conservadas o el default).
  5. Aplica formatos copiando los que ya usa el Sheet + formato de fecha.

NO borra la fila 7: eso desplazaria todo hacia arriba y romperia update_sheet.py,
que escribe B6/B8/B9/B10/B25:B28 por posicion fija.
"""
import argparse, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SID = '1wNXOy6dIjQqfgsSmnqvdEVFmCv-ibj0kgy4BuyYQvZ8'
KEY = r'C:\Users\diego\Downloads\prevision-stock-5264cd38736b.json'
HOJA = 'Reporte Consolidado'

LEAD_TIME_DEF = 21
COLCHON_DEF = 7

NOTAS = [["NOTAS Y SUPUESTOS"],
         ["Champús y Packs - que suscripcion tienen?"]]


def fila_producto(nombre, fila, stock, dem):
    """Construye la fila de un producto (columnas A..G).

    fila:  49 (serum) o 50 (champu)
    stock: celda con el stock actual, p.ej. 'E25'
    dem:   ('D25','D26','D27','D28') demanda acumulada 7d/30d/3m/12m
    """
    d7, d30, d90, d365 = dem
    r = fila
    return [
        nombre,
        # B: consumo/dia del tramo en el que se agota
        f'=IFERROR(IF({stock}>{d365},"-",'
        f'IF({stock}<={d7},{d7}/7,'
        f'IF({stock}<={d30},({d30}-{d7})/23,'
        f'IF({stock}<={d90},({d90}-{d30})/60,({d365}-{d90})/275)))),"-")',
        # C: fecha de agotamiento
        f'=IFERROR(IF({stock}>{d365},">12 meses",'
        f'$B$44+IF({stock}<={d7},{stock}*7/{d7},'
        f'IF({stock}<={d30},7+({stock}-{d7})*23/({d30}-{d7}),'
        f'IF({stock}<={d90},30+({stock}-{d30})*60/({d90}-{d30}),'
        f'90+({stock}-{d90})*275/({d365}-{d90}))))),"sin datos")',
        # D: el pedido debe llegar el...
        f'=IF(ISNUMBER(C{r}),C{r}-$B$46,"-")',
        # E: fecha limite de pedido
        f'=IF(ISNUMBER(D{r}),D{r}-$B$45,"-")',
        # F: dias restantes (vivo, contra TODAY)
        f'=IF(ISNUMBER(E{r}),INT(E{r})-TODAY(),"-")',
        # G: aviso
        f'=IF(NOT(ISNUMBER(E{r})),"Sin riesgo a 12 meses",'
        f'IF(F{r}<=0,"PEDIR HOY - YA VAS TARDE",'
        f'IF(F{r}<=14,"PEDIR ESTA SEMANA","OK")))',
    ]


def seccion(fecha_base, lead_time, colchon):
    return [
        ["CUANDO PEDIR (ESTIMADO)"],                                       # 42
        ["Parámetro", "Valor", "Detalle"],                                 # 43
        ["Fecha base del cálculo", fecha_base,
         "Fecha de generación del reporte (la escribe el script)"],        # 44
        ["Lead time proveedor (días)", lead_time,
         "Desde que pides hasta que está disponible para vender"],         # 45
        ["Colchón al recibir (días)", colchon,
         "Días de cobertura que aún quedan cuando llega el pedido"],       # 46
        [],                                                                # 47
        ["Producto", "Consumo/día (al agotarse)", "Stock se agota el",
         "Pedido debe llegar el", "FECHA LIMITE DE PEDIDO",
         "Días restantes", "Aviso"],                                       # 48
        fila_producto("SERUM", 49, "E25", ("D25", "D26", "D27", "D28")),   # 49
        fila_producto("CHAMPU", 50, "E32", ("D32", "D33", "D34", "D35")),  # 50
        [],                                                                # 51
        ["Fechas estimadas con la demanda proyectada de Katching. "
         "No descuentan pedidos ya en camino."],                           # 52
    ]


def svc():
    creds = service_account.Credentials.from_service_account_file(
        KEY, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return build('sheets', 'v4', credentials=creds)


def gid_de(api):
    meta = api.spreadsheets().get(
        spreadsheetId=SID, fields='sheets(properties(sheetId,title))').execute()
    for sh in meta['sheets']:
        if sh['properties']['title'] == HOJA:
            return sh['properties']['sheetId']
    raise SystemExit(f"No encontre la hoja '{HOJA}'")


def rango(gid, r0, r1, c0, c1):
    """GridRange 0-indexed, fin exclusivo. r0/r1 son numeros de fila 1-indexed."""
    return {"sheetId": gid, "startRowIndex": r0 - 1, "endRowIndex": r1,
            "startColumnIndex": c0, "endColumnIndex": c1}


def formatos(gid):
    def copia(src, dst):
        return {"copyPaste": {"source": src, "destination": dst,
                              "pasteType": "PASTE_FORMAT"}}
    def numfmt(rng, patron, tipo):
        return {"repeatCell": {
            "range": rng,
            "cell": {"userEnteredFormat": {
                "numberFormat": {"type": tipo, "pattern": patron}}},
            "fields": "userEnteredFormat.numberFormat"}}
    return [
        # titulo de seccion: copiar el de "RECOMENDACION DE REPOSICION" (A37)
        copia(rango(gid, 37, 37, 0, 1), rango(gid, 42, 42, 0, 1)),
        # cabeceras: copiar la fila de cabecera existente (A38:G38)
        copia(rango(gid, 38, 38, 0, 7), rango(gid, 43, 43, 0, 7)),
        copia(rango(gid, 38, 38, 0, 7), rango(gid, 48, 48, 0, 7)),
        # inputs amarillos: copiar el formato de B6 (stock serum)
        copia(rango(gid, 6, 6, 1, 2), rango(gid, 45, 46, 1, 2)),
        # fechas C49:E50
        numfmt(rango(gid, 49, 50, 2, 5), "yyyy-mm-dd", "DATE"),
        # fecha base B44
        numfmt(rango(gid, 44, 44, 1, 2), "yyyy-mm-dd", "DATE"),
        # consumo/dia con un decimal
        numfmt(rango(gid, 49, 50, 1, 2), "0.0", "NUMBER"),
        # dias restantes enteros
        numfmt(rango(gid, 49, 50, 5, 6), "0", "NUMBER"),
        # fusionar la fila de titulo (igual que el resto de titulos de seccion:
        # filas 1,4,15,23,30,37 estan fusionadas A:G). Va AL FINAL: el copyPaste
        # de formato de A37->A42 (arriba) deshace el merge si va despues.
        {"mergeCells": {"range": rango(gid, 42, 42, 0, 7), "mergeType": "MERGE_ALL"}},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--no-write', action='store_true')
    a = ap.parse_args()

    api = svc()
    s = api.spreadsheets()
    gid = gid_de(api)

    # 0. leer B45:B46 y las notas ANTES de tocar nada, para poder conservarlos.
    param_actual = s.values().get(spreadsheetId=SID,
                                  range=f"'{HOJA}'!B45:B46").execute().get('values', [])
    notas_actuales = s.values().get(spreadsheetId=SID,
                                    range=f"'{HOJA}'!A54:H60").execute().get('values', [])

    def tiene_valor(fila):
        return bool(fila) and str(fila[0]).strip() != ''

    if len(param_actual) >= 1 and tiene_valor(param_actual[0]):
        lead_time = param_actual[0][0]
        print(f"Conservado lead time existente: {lead_time}")
    else:
        lead_time = LEAD_TIME_DEF
        print(f"B45 vacia -> usando lead time por defecto: {lead_time}")

    if len(param_actual) >= 2 and tiene_valor(param_actual[1]):
        colchon = param_actual[1][0]
        print(f"Conservado colchon existente: {colchon}")
    else:
        colchon = COLCHON_DEF
        print(f"B46 vacia -> usando colchon por defecto: {colchon}")

    if notas_actuales and any(any(str(c).strip() for c in fila) for fila in notas_actuales):
        notas = notas_actuales
        print(f"Conservadas notas existentes ({len(notas_actuales)} filas).")
    else:
        notas = NOTAS
        print("Notas vacias -> usando texto por defecto.")

    filas = seccion(a.date, lead_time, colchon)
    print(f"Seccion CUANDO PEDIR: {len(filas)} filas (42-{41+len(filas)})")
    print(f"Fecha base: {a.date} | lead time {lead_time}d | colchon {colchon}d")
    if a.no_write:
        print("\n[DRY-RUN] no se escribio nada.")
        return

    # 1. limpiar solo la zona de la seccion (41-52); NO tocar 53-60 (notas):
    #    ya las leimos arriba y las vamos a reinstalar tal cual.
    s.values().clear(spreadsheetId=SID, range=f"'{HOJA}'!A41:H52").execute()
    # 1b. desfusionar celdas heredadas en la zona 41-60 (filas 43-50 llegaban
    #     fusionadas A:G de un estado previo; escribir valores en B..G de una
    #     fila fusionada los descarta en silencio, asi que hay que desfusionar
    #     ANTES de escribir valores, no solo antes de aplicar formatos). Se
    #     desfusiona hasta la fila 60 tambien por si las notas quedaron
    #     fusionadas de un estado antiguo; no borra nada, ya las leimos.
    s.batchUpdate(spreadsheetId=SID, body={"requests": [
        {"unmergeCells": {"range": rango(gid, 41, 60, 0, 8)}}]}).execute()
    # 2. vaciar B7 (dato muerto)
    s.values().clear(spreadsheetId=SID, range=f"'{HOJA}'!B7").execute()
    # 3. escribir seccion + notas (conservadas o default)
    res = s.values().batchUpdate(spreadsheetId=SID, body={
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": f"'{HOJA}'!A42", "values": filas},
            {"range": f"'{HOJA}'!A54", "values": notas},
        ]}).execute()
    print(f"Celdas escritas: {res.get('totalUpdatedCells')}")
    # 4. formatos
    s.batchUpdate(spreadsheetId=SID, body={"requests": formatos(gid)}).execute()
    print("Formatos aplicados.")

    # verificacion
    vals = s.values().get(spreadsheetId=SID, range=f"'{HOJA}'!A42:G55",
                          valueRenderOption='FORMATTED_VALUE').execute().get('values', [])
    errs = [c for row in vals for c in row if isinstance(c, str) and c.startswith('#')]
    print("ERRORES DE FORMULA:", errs if errs else "NINGUNO")
    for row in vals:
        if row and row[0] in ('SERUM', 'CHAMPU'):
            print("  ", " | ".join(str(c) for c in row))
    b7 = s.values().get(spreadsheetId=SID, range=f"'{HOJA}'!B7").execute().get('values', [])
    print("B7 vacia:", "SI" if not b7 else f"NO -> {b7}")


if __name__ == '__main__':
    main()
