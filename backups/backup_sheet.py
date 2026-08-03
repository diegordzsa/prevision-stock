# -*- coding: utf-8 -*-
"""Copia de seguridad del Google Sheet: valores Y formulas de las 3 hojas.

    C:\\Python314\\python backups/backup_sheet.py            -> guarda backups/sheet-<fecha>.json
    C:\\Python314\\python backups/backup_sheet.py --restore backups/sheet-2026-08-03.json

El restore reescribe las formulas tal cual estaban (USER_ENTERED), no los
valores calculados.
"""
import argparse, datetime, json, os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SID = '1wNXOy6dIjQqfgsSmnqvdEVFmCv-ibj0kgy4BuyYQvZ8'
KEY = r'C:\Users\diego\Downloads\prevision-stock-5264cd38736b.json'
HERE = os.path.dirname(os.path.abspath(__file__))

RANGOS = {
    'Reporte Consolidado': 'A1:H80',
    'Shopify 7d': 'A1:F200',
    'Katching Suscripciones': 'A1:K200',
}


def svc():
    creds = service_account.Credentials.from_service_account_file(
        KEY, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return build('sheets', 'v4', credentials=creds).spreadsheets()


def guardar(s, destino):
    dump = {}
    for hoja, rng in RANGOS.items():
        r = f"'{hoja}'!{rng}"
        formulas = s.values().get(spreadsheetId=SID, range=r,
                                  valueRenderOption='FORMULA').execute().get('values', [])
        valores = s.values().get(spreadsheetId=SID, range=r,
                                 valueRenderOption='FORMATTED_VALUE').execute().get('values', [])
        dump[hoja] = {'rango': rng, 'formulas': formulas, 'valores': valores}
        print(f"  {hoja}: {len(formulas)} filas")
    with open(destino, 'w', encoding='utf-8') as f:
        json.dump(dump, f, ensure_ascii=False, indent=1)
    print(f"Backup guardado en {destino}")


def restaurar(s, origen):
    with open(origen, encoding='utf-8') as f:
        dump = json.load(f)
    data = []
    for hoja, d in dump.items():
        s.values().clear(spreadsheetId=SID, range=f"'{hoja}'!{d['rango']}").execute()
        data.append({"range": f"'{hoja}'!A1", "values": d['formulas']})
        print(f"  {hoja}: {len(d['formulas'])} filas")
    res = s.values().batchUpdate(spreadsheetId=SID, body={
        "valueInputOption": "USER_ENTERED", "data": data}).execute()
    print(f"Restaurado. Celdas escritas: {res.get('totalUpdatedCells')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--restore', metavar='FICHERO')
    a = ap.parse_args()
    s = svc()
    if a.restore:
        restaurar(s, a.restore)
    else:
        destino = os.path.join(HERE, f"sheet-{datetime.date.today().isoformat()}.json")
        guardar(s, destino)


if __name__ == '__main__':
    main()
