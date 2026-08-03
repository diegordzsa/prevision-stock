# -*- coding: utf-8 -*-
"""
Actualiza el Google Sheet semanal de stock de Hair Biolabs (modo sobrescribir).

USO (desde la carpeta del proyecto):
  python weekly/update_sheet.py --stock-serum 4740 --stock-champu 1173 --ventas-serum 92
  # opcionales: --ventas-champu 65   (por defecto = unidades SHAMPOO de Shopify)
  #             --date 2026-07-27     (por defecto = hoy)
  #             --no-write            (dry-run: calcula e imprime sin escribir)

ENTRADAS (en esta misma carpeta weekly/):
  shopify.csv   -> export crudo de Shopify "Ventas totales por variante - 7 dias"
                   (usa las columnas de producto, variante y articulos netos vendidos)
  katching.csv  -> transcripcion de las capturas de Katching Prevision de Inventario.
                   Cabecera: producto,variante,renov_7d,renov_30d,renov_3m,renov_12m
"""
import argparse, csv, re, os, sys, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SID = '1wNXOy6dIjQqfgsSmnqvdEVFmCv-ibj0kgy4BuyYQvZ8'
KEY = r'C:\Users\diego\Downloads\prevision-stock-5264cd38736b.json'
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- reglas de clasificacion ----------
def multiplicador(variante):
    v = (variante or '').lower()
    if 'default' in v:
        return 1
    m = re.search(r'\d+', v)
    return int(m.group()) if m else 1

def categoria(producto, variante):
    t = (producto or '').lower() + ' ' + (variante or '').lower()
    if 'prueba' in t:
        return 'EXCLUIR'
    if 'regalo misterioso' in t or 'guia' in t or 'guía' in t:
        return 'EXCLUIR'
    if 'pack completo' in t:
        return 'PACK'
    has_serum = ('serum' in t) or ('sérum' in t)
    has_champu = ('champu' in t) or ('champú' in t)
    if has_champu and not has_serum:
        return 'SHAMPOO'
    if has_serum:
        return 'SERUM'
    return 'REVISAR'   # no deberia pasar; se marca para revisar a mano

# ---------- lectura robusta de CSV ----------
def read_csv(path):
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            with open(path, newline='', encoding=enc) as f:
                return list(csv.reader(f))
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise SystemExit(f"No pude leer {path}")

def col_idx(header, *keywords):
    for i, h in enumerate(header):
        hl = h.lower()
        if all(k in hl for k in keywords):
            return i
    return None

def load_shopify():
    rows = read_csv(os.path.join(HERE, 'shopify.csv'))
    if not rows:
        raise SystemExit("shopify.csv vacio")
    header = rows[0]
    i_prod = col_idx(header, 'producto') if col_idx(header, 't', 'producto') is None else col_idx(header, 'producto')
    # mas robusto: por nombre estandar de Shopify
    i_prod = col_idx(header, 'título del producto') or col_idx(header, 'titulo del producto') or 0
    i_var  = col_idx(header, 'variante') if col_idx(header, 'variante') is not None else 1
    i_ped  = col_idx(header, 'artículos netos') or col_idx(header, 'articulos netos') or col_idx(header, 'net items') or 3
    out = []
    for r in rows[1:]:
        if not r or len(r) <= max(i_prod, i_var, i_ped):
            continue
        prod = r[i_prod].strip()
        var  = r[i_var].strip()
        if not prod:
            continue
        try:
            ped = int(float(r[i_ped]))
        except ValueError:
            ped = 0
        out.append((prod, var, ped, multiplicador(var), categoria(prod, var)))
    return out

def load_katching():
    rows = read_csv(os.path.join(HERE, 'katching.csv'))
    header = [h.lower() for h in rows[0]]
    def ci(*k):
        for i,h in enumerate(header):
            if all(x in h for x in k): return i
        return None
    ip, iv = ci('producto') or 0, ci('variante') or 1
    i7, i30 = ci('7'), ci('30')
    i3, i12 = ci('3m') if ci('3m') is not None else ci('3','m'), ci('12')
    out = []
    for r in rows[1:]:
        if not r or not r[ip].strip():
            continue
        prod, var = r[ip].strip(), r[iv].strip()
        if 'prueba' in (prod+var).lower():
            continue   # excluir producto de test
        def num(i):
            try: return int(float(r[i]))
            except (ValueError, TypeError, IndexError): return 0
        out.append((prod, var, multiplicador(var), num(i7), num(i30), num(i3), num(i12)))
    return out

# ---------- Sheets ----------
def svc():
    creds = service_account.Credentials.from_service_account_file(
        KEY, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return build('sheets', 'v4', credentials=creds).spreadsheets()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stock-serum', type=int, required=True)
    ap.add_argument('--stock-champu', type=int, required=True)
    ap.add_argument('--ventas-serum', type=int, required=True, help='ventas serum NO-suscripcion 7d')
    ap.add_argument('--ventas-champu', type=int, default=None, help='def = unidades SHAMPOO Shopify')
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--no-write', action='store_true')
    ap.add_argument('--lead-time', type=int, default=None,
                    help='dias de lead time del proveedor (def = lo que haya en B45)')
    ap.add_argument('--colchon', type=int, default=None,
                    help='dias de cobertura al recibir (def = lo que haya en B46)')
    a = ap.parse_args()

    shop = load_shopify()
    kat  = load_katching()

    revisar = [s for s in shop if s[4] == 'REVISAR']
    if revisar:
        print("[AVISO] filas Shopify sin categoria clara (revisar):")
        for s in revisar: print("   ", s[0], '|', s[1])

    shampoo_units = sum(p*m for _,_,p,m,c in shop if c == 'SHAMPOO')
    ventas_champu = a.ventas_champu if a.ventas_champu is not None else shampoo_units

    # filas para escribir
    shop_rows = [[p, v, ped, m, f"=C{4+i}*D{4+i}", c] for i,(p,v,ped,m,c) in enumerate(shop)]
    kat_rows = []
    for i,(p,v,m,r7,r30,r3,r12) in enumerate(kat):
        r = 4+i
        kat_rows.append([p, v, m, r7, r30, r3, r12,
                         f"=C{r}*D{r}", f"=C{r}*E{r}", f"=C{r}*F{r}", f"=C{r}*G{r}"])
    total_row = 4 + len(kat_rows)          # fila TOTAL SERUM (dinamica)
    last = total_row - 1
    kat_rows.append(["TOTAL SERUM","","","","","","",
                     f"=SUM(H4:H{last})", f"=SUM(I4:I{last})", f"=SUM(J4:J{last})", f"=SUM(K4:K{last})"])

    print(f"\nShopify: {len(shop)} filas | Katching: {len(kat)} productos (TOTAL en fila {total_row})")
    print(f"Inputs -> stock serum {a.stock_serum}, stock champu {a.stock_champu}, "
          f"ventas serum {a.ventas_serum}, ventas champu {ventas_champu}")

    if a.no_write:
        print("\n[DRY-RUN] no se escribio nada.")
        return

    s = svc()
    s.values().clear(spreadsheetId=SID, range="'Shopify 7d'!A4:F1000").execute()
    s.values().clear(spreadsheetId=SID, range="'Katching Suscripciones'!A4:K1000").execute()
    data = [
        {"range":"'Shopify 7d'!A4","values":shop_rows},
        {"range":"'Katching Suscripciones'!A4","values":kat_rows},
        {"range":"'Reporte Consolidado'!A2","values":[[f"Fecha de generación: {a.date}"]]},
        {"range":"'Reporte Consolidado'!B6","values":[[a.stock_serum]]},
        {"range":"'Reporte Consolidado'!B8","values":[[a.stock_champu]]},
        {"range":"'Reporte Consolidado'!B9","values":[[a.ventas_serum]]},
        {"range":"'Reporte Consolidado'!B10","values":[[ventas_champu]]},
        {"range":"'Reporte Consolidado'!B25","values":[[f"='Katching Suscripciones'!H{total_row}"]]},
        {"range":"'Reporte Consolidado'!B26","values":[[f"='Katching Suscripciones'!I{total_row}"]]},
        {"range":"'Reporte Consolidado'!B27","values":[[f"='Katching Suscripciones'!J{total_row}"]]},
        {"range":"'Reporte Consolidado'!B28","values":[[f"='Katching Suscripciones'!K{total_row}"]]},
        {"range":"'Reporte Consolidado'!B44","values":[[a.date]]},
    ]
    # B45/B46 solo se pisan si se pasan los flags: son celdas editables a mano
    if a.lead_time is not None:
        data.append({"range":"'Reporte Consolidado'!B45","values":[[a.lead_time]]})
    if a.colchon is not None:
        data.append({"range":"'Reporte Consolidado'!B46","values":[[a.colchon]]})
    res = s.values().batchUpdate(spreadsheetId=SID,
            body={"valueInputOption":"USER_ENTERED","data":data}).execute()
    print(f"Celdas escritas: {res.get('totalUpdatedCells')}")

    # ---- leer de vuelta y armar reporte + escaneo de errores ----
    def g(rng):
        return s.values().get(spreadsheetId=SID, range=rng,
                              valueRenderOption='FORMATTED_VALUE').execute().get('values',[])
    errs = []
    for rng in ["'Reporte Consolidado'!A1:H60","'Shopify 7d'!A1:F200","'Katching Suscripciones'!A1:K200"]:
        for row in g(rng):
            for c in row:
                if isinstance(c,str) and c.startswith('#'): errs.append(c)
    serum = g("'Reporte Consolidado'!A25:G28")
    champu = g("'Reporte Consolidado'!A32:G35")
    reco = g("'Reporte Consolidado'!B39:D40")

    def line(row):
        # A=timeframe B=susc C=nosusc D=demanda E=stock F=dif G=estado
        tf, dem, dif, est = row[0], row[3], row[5], row[6]
        signo = "falta" if str(dif).startswith('-') else "sobra"
        return f"- {tf}: necesitas {dem}, {signo} {str(dif).lstrip('-')}. {est}"

    print("\n" + "="*54)
    print(f"REPORTE SEMANAL {a.date}\n")
    print(f"Serum (stock: {a.stock_serum} unidades)")
    for row in serum: print(line(row))
    print(f"\nChampu (stock: {a.stock_champu} unidades)")
    for row in champu: print(line(row))
    urg = [row[0] for row in serum+champu if 'URGENTE' in row[6]]
    if reco:
        print("\nRECOMENDACION DE COMPRA INMEDIATA (30 dias):")
        print(f"- SERUM:  {reco[0][0]}")
        print(f"- CHAMPU: {reco[1][0]}")
    pedir = g("'Reporte Consolidado'!A49:G50")
    param = g("'Reporte Consolidado'!B45:B46")
    param_ok = (len(param) >= 2
                and param[0] and str(param[0][0]).strip() != ''
                and param[1] and str(param[1][0]).strip() != '')
    if pedir and param_ok:
        lead, colchon = param[0][0], param[1][0]
        print(f"\nCUANDO PEDIR (lead time {lead}d, colchon {colchon}d)")
        for row in pedir:
            # A=producto B=cons/dia C=agota D=llega E=limite F=dias G=aviso
            r = row + [''] * (7 - len(row))
            if r[6] == 'Sin riesgo a 12 meses':
                print(f"- {r[0]}: sin riesgo, el stock cubre mas de 12 meses")
            else:
                print(f"- {r[0]}: pedir antes del {r[4]} (quedan {r[5]} dias) "
                      f"- stock se agota ~{r[2]} [{r[6]}]")
        print("  (no descuenta pedidos ya en camino)")
        for row in pedir:
            if len(row) > 6 and 'PEDIR HOY' in row[6]:
                urg.append(f"{row[0]} - pedido fuera de plazo")
    elif pedir and not param_ok:
        print("\n[AVISO] B45 (lead time) o B46 (colchon) esta vacia - la FECHA "
              "LIMITE DE PEDIDO seria incorrecta, no calculo CUANDO PEDIR. "
              "Rellena B45/B46 o re-ejecuta weekly/setup_cuando_pedir.py")
    else:
        print("\n[AVISO] no encontre la seccion CUANDO PEDIR en A49:G50 - "
              "re-ejecuta weekly/setup_cuando_pedir.py")
    print("\nALERTAS URGENTES:", ", ".join(urg) if urg else "ninguna")
    print("\nERRORES DE FORMULA:", errs if errs else "NINGUNO")
    print("="*54)

if __name__ == '__main__':
    main()
