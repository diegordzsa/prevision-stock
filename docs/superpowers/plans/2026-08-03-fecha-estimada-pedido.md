# Fecha estimada de pedido — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir al reporte semanal una fecha límite estimada de pedido por producto (serum y champú), calculada por burn-down sobre la curva de demanda de Katching.

**Architecture:** Las fechas viven en el Google Sheet como fórmulas (única fuente de verdad), en una sección nueva `CUANDO PEDIR (ESTIMADO)` en las filas 42-52 del `Reporte Consolidado`. Un script de setup de una sola vez crea esa sección; el script semanal solo refresca la fecha base y lee las fechas ya calculadas para imprimirlas en el chat. Un módulo Python puro replica el cálculo y sirve de oráculo para verificar que las fórmulas del Sheet no tienen erratas.

**Tech Stack:** Python 3.14 (`C:\Python314\python`), `google-api-python-client`, Google Sheets API v4. Sin framework de tests — los tests son asserts en un script ejecutable directamente.

## Global Constraints

- Google Sheet id: `1wNXOy6dIjQqfgsSmnqvdEVFmCv-ibj0kgy4BuyYQvZ8`
- Hoja destino: `Reporte Consolidado`
- Llave de servicio: `C:\Users\diego\Downloads\prevision-stock-5264cd38736b.json` (fuera del proyecto, no moverla)
- Python: `C:\Python314\python`
- Lead time por defecto: **21** días. Colchón por defecto: **7** días.
- Tramos de la curva: 0-7 / 7-30 / 30-90 / 90-365 días.
- **Nunca eliminar la fila 7 del Consolidado.** Desplazaría todo hacia arriba y rompería `update_sheet.py`, que escribe `B6`/`B8`/`B9`/`B10`/`B25:B28` por posición fija.
- **No tocar** las fórmulas de Estado (`G25:G28`, `G32:G35`) ni de Recomendación (`B39:D40`).
- Redondeo: el día de agotamiento se trunca hacia abajo (último día completo con stock).
- Todos los ficheros Python llevan `# -*- coding: utf-8 -*-` en la primera línea (hay acentos en literales).

---

### Task 0: Inicializar git (opcional)

El proyecto no es un repo git, así que no hay histórico ni forma de revertir. Este plan
incluye pasos de commit. Si el usuario prefiere no usar git, **saltar esta tarea y omitir
todos los pasos "Commit" del resto del plan**; todo lo demás funciona igual.

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Inicializar el repo**

```bash
git init
git branch -M main
```

- [ ] **Step 2: Crear .gitignore**

```
__pycache__/
*.pyc
```

Nota: `weekly/shopify.csv` y `weekly/katching.csv` SÍ se versionan — son el input crudo de
cada semana y tener su histórico es útil para comparar semana a semana.

- [ ] **Step 3: Commit inicial**

```bash
git add -A
git commit -m "chore: inicializar repo del reporte semanal de stock"
```

---

### Task 1: Módulo de cálculo `burndown.py` + tests

Módulo puro, sin dependencias ni red. Replica exactamente las fórmulas que irán al Sheet.
Su valor es ser el oráculo de la Task 4: si el Sheet y este módulo discrepan, una de las
dos está mal.

**Files:**
- Create: `weekly/burndown.py`
- Test: `weekly/test_burndown.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `dia_agotamiento(stock: float, demandas: tuple[float,float,float,float]) -> float | None`
    Devuelve el día (float) en que el stock llega a cero, o `None` si aguanta más de 12 meses.
  - `tasa_al_agotarse(stock: float, demandas: tuple) -> float | None`
    Consumo diario del tramo en el que el stock llega a cero.
  - `TRAMOS: tuple` — los cuatro tramos como `((0,7),(7,30),(30,90),(90,365))`.

- [ ] **Step 1: Escribir el test que falla**

Crear `weekly/test_burndown.py`:

```python
# -*- coding: utf-8 -*-
"""Tests de weekly/burndown.py. Ejecutar: C:\\Python314\\python weekly/test_burndown.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from burndown import dia_agotamiento, tasa_al_agotarse

SERUM = (433, 1932, 6836, 27651)
CHAMPU = (52, 225, 676, 2704)

fallos = []

def check(nombre, obtenido, esperado, tol=0.01):
    ok = (obtenido is None and esperado is None) or (
        obtenido is not None and esperado is not None and abs(obtenido - esperado) < tol)
    print(("  OK   " if ok else "  FALLO") + f" {nombre}: {obtenido} (esperado {esperado})")
    if not ok:
        fallos.append(nombre)

print("dia_agotamiento")
# serum: cae en el tramo 30-90 -> 30 + (3868-1932)*60/(6836-1932)
check("serum 3868", dia_agotamiento(3868, SERUM), 53.6867)
# champu: cae en el tramo 90-365 -> 90 + (1078-676)*275/(2704-676)
check("champu 1078", dia_agotamiento(1078, CHAMPU), 144.5118)
# primer tramo
check("serum 100", dia_agotamiento(100, SERUM), 100 * 7 / 433)
# segundo tramo
check("serum 1000", dia_agotamiento(1000, SERUM), 7 + (1000 - 433) * 23 / (1932 - 433))
# frontera exacta: stock == demanda a 30 dias
check("serum 1932 (frontera)", dia_agotamiento(1932, SERUM), 30.0)
# aguanta mas de 12 meses
check("serum 99999", dia_agotamiento(99999, SERUM), None)
# stock cero o negativo
check("stock 0", dia_agotamiento(0, SERUM), 0.0)
check("stock -5", dia_agotamiento(-5, SERUM), 0.0)
# tramo con demanda incremental cero no revienta
check("tramo plano", dia_agotamiento(50, (0, 0, 100, 200)), 30 + 50 * 60 / 100)

print("tasa_al_agotarse")
check("serum 3868", tasa_al_agotarse(3868, SERUM), (6836 - 1932) / 60)
check("champu 1078", tasa_al_agotarse(1078, CHAMPU), (2704 - 676) / 275)
check("serum 99999", tasa_al_agotarse(99999, SERUM), None)

print()
if fallos:
    print(f"FALLARON {len(fallos)}: {', '.join(fallos)}")
    sys.exit(1)
print("TODOS OK")
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `C:\Python314\python weekly/test_burndown.py`
Expected: FAIL con `ModuleNotFoundError: No module named 'burndown'`

- [ ] **Step 3: Escribir la implementación mínima**

Crear `weekly/burndown.py`:

```python
# -*- coding: utf-8 -*-
"""Burn-down del stock sobre la curva de demanda acumulada de Katching.

Espeja las formulas de la seccion CUANDO PEDIR del Sheet. Es el oraculo para
verificar esas formulas: si el Sheet y este modulo discrepan, una esta mal.

demandas = (d7, d30, d90, d365) demanda ACUMULADA a 7 dias, 30 dias, 3 meses
y 12 meses. Los tramos y sus longitudes en dias: 0-7 (7), 7-30 (23),
30-90 (60), 90-365 (275).
"""

TRAMOS = ((0, 7), (7, 30), (30, 90), (90, 365))


def _tramo(stock, demandas):
    """Devuelve (inicio_dia, largo_dias, dem_inicio, dem_incremental) del tramo
    donde el stock llega a cero, o None si aguanta mas de 12 meses."""
    d7, d30, d90, d365 = demandas
    if stock > d365:
        return None
    if stock <= d7:
        return (0, 7, 0, d7)
    if stock <= d30:
        return (7, 23, d7, d30 - d7)
    if stock <= d90:
        return (30, 60, d30, d90 - d30)
    return (90, 275, d90, d365 - d90)


def dia_agotamiento(stock, demandas):
    """Dia (float) en que el stock llega a cero. None si aguanta > 12 meses."""
    if stock <= 0:
        return 0.0
    t = _tramo(stock, demandas)
    if t is None:
        return None
    inicio, largo, dem_inicio, dem_incr = t
    if dem_incr <= 0:
        return None
    return inicio + (stock - dem_inicio) * largo / dem_incr


def tasa_al_agotarse(stock, demandas):
    """Consumo diario (uds/dia) del tramo en el que el stock llega a cero."""
    t = _tramo(stock, demandas)
    if t is None:
        return None
    _, largo, _, dem_incr = t
    return dem_incr / largo
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `C:\Python314\python weekly/test_burndown.py`
Expected: PASS — `TODOS OK`, exit code 0.

Si falla `tramo plano`: `dia_agotamiento(50, (0,0,100,200))` con `d7=0` y `d30=0` debe
caer al tramo 30-90 porque `50 > 0`. Comprobar que las comparaciones son `<=` y no `<`.

- [ ] **Step 5: Commit**

```bash
git add weekly/burndown.py weekly/test_burndown.py
git commit -m "feat: modulo de burn-down de stock con tests"
```

---

### Task 2: Script de setup `setup_cuando_pedir.py`

Crea la sección en el Sheet. Se ejecuta **una sola vez**, pero es idempotente.

**Files:**
- Create: `weekly/setup_cuando_pedir.py`

**Interfaces:**
- Consumes: nada de Task 1 (el Sheet calcula por su cuenta).
- Produces: la sección `CUANDO PEDIR` en `Reporte Consolidado!A42:G52`, con
  `B44` = fecha base, `B45` = lead time, `B46` = colchón, fila 49 = SERUM, fila 50 = CHAMPU.
  `NOTAS Y SUPUESTOS` reubicado en `A54:A55`. `B7` vacía.

- [ ] **Step 1: Escribir el script**

Crear `weekly/setup_cuando_pedir.py`:

```python
# -*- coding: utf-8 -*-
"""Setup de una sola vez de la seccion CUANDO PEDIR (ESTIMADO).

Ejecutar UNA vez:
    C:\\Python314\\python weekly/setup_cuando_pedir.py
    C:\\Python314\\python weekly/setup_cuando_pedir.py --no-write   (dry-run)

Es idempotente: volver a ejecutarlo deja el Sheet igual.

  1. Vacia B7 (dato muerto congelado, ninguna formula lo referencia).
  2. Escribe la seccion CUANDO PEDIR en las filas 42-52 (pisa las NOTAS viejas).
  3. Reescribe NOTAS Y SUPUESTOS en las filas 54-55.
  4. Aplica formatos copiando los que ya usa el Sheet + formato de fecha.

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


def seccion(fecha_base):
    return [
        ["CUANDO PEDIR (ESTIMADO)"],                                       # 42
        ["Parámetro", "Valor", "Detalle"],                                 # 43
        ["Fecha base del cálculo", fecha_base,
         "Fecha de generación del reporte (la escribe el script)"],        # 44
        ["Lead time proveedor (días)", LEAD_TIME_DEF,
         "Desde que pides hasta que está disponible para vender"],         # 45
        ["Colchón al recibir (días)", COLCHON_DEF,
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
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--no-write', action='store_true')
    a = ap.parse_args()

    filas = seccion(a.date)
    print(f"Seccion CUANDO PEDIR: {len(filas)} filas (42-{41+len(filas)})")
    print(f"Fecha base: {a.date} | lead time {LEAD_TIME_DEF}d | colchon {COLCHON_DEF}d")
    if a.no_write:
        print("\n[DRY-RUN] no se escribio nada.")
        return

    api = svc()
    s = api.spreadsheets()
    gid = gid_de(api)

    # 1. limpiar la zona (idempotencia) sin tocar la fila 40
    s.values().clear(spreadsheetId=SID, range=f"'{HOJA}'!A41:H60").execute()
    # 2. vaciar B7 (dato muerto)
    s.values().clear(spreadsheetId=SID, range=f"'{HOJA}'!B7").execute()
    # 3. escribir seccion + notas
    res = s.values().batchUpdate(spreadsheetId=SID, body={
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": f"'{HOJA}'!A42", "values": filas},
            {"range": f"'{HOJA}'!A54", "values": NOTAS},
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
```

- [ ] **Step 2: Dry-run**

Run: `C:\Python314\python weekly/setup_cuando_pedir.py --no-write`
Expected: imprime `Seccion CUANDO PEDIR: 11 filas (42-52)` y no escribe nada.

- [ ] **Step 3: Ejecutar de verdad**

Run: `C:\Python314\python weekly/setup_cuando_pedir.py --date 2026-08-03`
Expected:
- `Celdas escritas:` un número > 0
- `Formatos aplicados.`
- `ERRORES DE FORMULA: NINGUNO`
- `B7 vacia: SI`
- Dos líneas con SERUM y CHAMPU y fechas con formato `yyyy-mm-dd`

Si sale `#REF!` en C49: comprobar que `E25`/`D25:D28` existen y no se movieron.
Si sale `#VALUE!`: casi seguro que `$B$44` no es una fecha real — comprobar que se
escribió con `USER_ENTERED` y que el formato DATE se aplicó.

- [ ] **Step 4: Verificar idempotencia**

Run: `C:\Python314\python weekly/setup_cuando_pedir.py --date 2026-08-03`
Expected: mismo output, `ERRORES DE FORMULA: NINGUNO`, y las notas siguen **solo** en
las filas 54-55 (no duplicadas).

- [ ] **Step 5: Commit**

```bash
git add weekly/setup_cuando_pedir.py
git commit -m "feat: script de setup de la seccion CUANDO PEDIR"
```

---

### Task 3: Integrar en `update_sheet.py`

**Files:**
- Modify: `weekly/update_sheet.py`

**Interfaces:**
- Consumes: la sección creada en Task 2 (`B44`, `B45`, `B46`, `A49:G50`).
- Produces: nada que consuman otras tareas.

- [ ] **Step 1: Añadir los flags nuevos**

En `main()`, tras la línea `ap.add_argument('--no-write', action='store_true')`, añadir:

```python
    ap.add_argument('--lead-time', type=int, default=None,
                    help='dias de lead time del proveedor (def = lo que haya en B45)')
    ap.add_argument('--colchon', type=int, default=None,
                    help='dias de cobertura al recibir (def = lo que haya en B46)')
```

- [ ] **Step 2: Escribir la fecha base y, si se piden, lead time y colchón**

En la lista `data`, después de la entrada de `'Reporte Consolidado'!B10`, añadir:

```python
        {"range":"'Reporte Consolidado'!B44","values":[[a.date]]},
```

Y justo después de construir `data` (antes de `res = s.values().batchUpdate(...)`), añadir:

```python
    # B45/B46 solo se pisan si se pasan los flags: son celdas editables a mano
    if a.lead_time is not None:
        data.append({"range":"'Reporte Consolidado'!B45","values":[[a.lead_time]]})
    if a.colchon is not None:
        data.append({"range":"'Reporte Consolidado'!B46","values":[[a.colchon]]})
```

- [ ] **Step 3: Ampliar el escaneo de errores**

Localizar esta línea:

```python
    for rng in ["'Reporte Consolidado'!A1:H45","'Shopify 7d'!A1:F200","'Katching Suscripciones'!A1:K200"]:
```

Sustituir `A1:H45` por `A1:H60`:

```python
    for rng in ["'Reporte Consolidado'!A1:H60","'Shopify 7d'!A1:F200","'Katching Suscripciones'!A1:K200"]:
```

Sin este cambio, un `#REF!` en las filas 46-60 saldría como `ERRORES: NINGUNO`.

- [ ] **Step 4: Imprimir el bloque nuevo en el reporte**

Localizar el bloque final:

```python
    if reco:
        print("\nRECOMENDACION DE COMPRA INMEDIATA (30 dias):")
        print(f"- SERUM:  {reco[0][0]}")
        print(f"- CHAMPU: {reco[1][0]}")
```

Insertar justo **después** de ese `if reco:` y **antes** de `print("\nERRORES DE FORMULA:"...)`:

```python
    pedir = g("'Reporte Consolidado'!A49:G50")
    param = g("'Reporte Consolidado'!B45:B46")
    if pedir and param:
        lead, colchon = param[0][0], param[1][0]
        print(f"\nCUANDO PEDIR (lead time {lead}d, colchon {colchon}d)")
        for row in pedir:
            # A=producto B=cons/dia C=agota D=llega E=limite F=dias G=aviso
            r = row + [''] * (7 - len(row))
            print(f"- {r[0]}: pedir antes del {r[4]} (quedan {r[5]} dias) "
                  f"- stock se agota ~{r[2]} [{r[6]}]")
        print("  (no descuenta pedidos ya en camino)")
        for row in pedir:
            if len(row) > 6 and 'PEDIR HOY' in row[6]:
                urg.append(f"{row[0]} - pedido fuera de plazo")
```

Nota: `urg` se define más arriba (`urg = [row[0] for row in serum+champu if 'URGENTE' in row[6]]`)
pero se imprime **antes** de este bloque. Para que los avisos de pedido entren en las
alertas, mover la línea `print("\nALERTAS URGENTES:", ...)` a después de este bloque
nuevo. Es decir, el orden final del reporte queda:

1. Serum por timeframe
2. Champu por timeframe
3. `RECOMENDACION DE COMPRA INMEDIATA`
4. `CUANDO PEDIR`
5. `ALERTAS URGENTES` (ya incluye los avisos de pedido fuera de plazo)
6. `ERRORES DE FORMULA`

- [ ] **Step 5: Dry-run**

Run: `C:\Python314\python weekly/update_sheet.py --stock-serum 3868 --stock-champu 1078 --ventas-serum 138 --no-write`
Expected: mismo output que antes del cambio (`Shopify: 22 filas | Katching: 27 productos`),
sin excepciones. El dry-run sale antes de escribir, así que no imprime el bloque nuevo.

- [ ] **Step 6: Ejecución real**

Run: `C:\Python314\python weekly/update_sheet.py --stock-serum 3868 --stock-champu 1078 --ventas-serum 138 --date 2026-08-03`
Expected: el reporte completo con el bloque `CUANDO PEDIR` y `ERRORES DE FORMULA: NINGUNO`.

- [ ] **Step 7: Commit**

```bash
git add weekly/update_sheet.py
git commit -m "feat: bloque CUANDO PEDIR en el reporte semanal"
```

---

### Task 4: Verificación cruzada Sheet ↔ oráculo

Confirma que las fórmulas del Sheet dan lo mismo que el módulo Python. Esta es la tarea
que caza una errata en un `23` o un `275` dentro de las fórmulas.

**Files:**
- Create: `weekly/verificar_fechas.py`

**Interfaces:**
- Consumes: `burndown.dia_agotamiento` (Task 1), la sección del Sheet (Task 2).
- Produces: nada.

- [ ] **Step 1: Escribir el verificador**

Crear `weekly/verificar_fechas.py`:

```python
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
```

- [ ] **Step 2: Ejecutar la verificación**

Run: `C:\Python314\python weekly/verificar_fechas.py`
Expected: `Sheet y oraculo coinciden.` y, con los datos del 2026-08-03:

```
  OK    SERUM agotamiento: Sheet=2026-09-25 oraculo=2026-09-25
  OK    SERUM fecha pedido: Sheet=2026-08-28 oraculo=2026-08-28
         (stock 3868, dia de agotamiento 53.69)
  OK    CHAMPU agotamiento: Sheet=2026-12-25 oraculo=2026-12-25
  OK    CHAMPU fecha pedido: Sheet=2026-11-27 oraculo=2026-11-27
         (stock 1078, dia de agotamiento 144.51)
```

Si hay discrepancia de exactamente 1 día: es el redondeo. El Sheet trunca al formatear;
el oráculo usa `int(dia)`. Ambos deben truncar — revisar que no se coló un `round()`.

- [ ] **Step 3: Verificar que el lead time editable funciona**

Editar `B45` en el Sheet a mano: cambiar `21` por `14`.
Run: `C:\Python314\python weekly/verificar_fechas.py`
Expected: `SERUM fecha pedido` pasa de `2026-08-28` a `2026-09-04` (7 días más tarde),
y sigue diciendo `Sheet y oraculo coinciden` (el oráculo lee `B45` del Sheet).

Devolver `B45` a `21` al terminar.

- [ ] **Step 4: Verificar que el script semanal no pisa B45**

Run: `C:\Python314\python weekly/update_sheet.py --stock-serum 3868 --stock-champu 1078 --ventas-serum 138 --date 2026-08-03`
Luego comprobar que `B45` sigue valiendo `21` (no se ha reseteado).
Expected: sigue en `21`.

- [ ] **Step 5: Commit**

```bash
git add weekly/verificar_fechas.py
git commit -m "test: verificacion cruzada Sheet vs oraculo de burndown"
```

---

### Task 5: Actualizar `CLAUDE.md`

Sin esto, la próxima sesión no sabrá que existe la sección nueva ni el formato del reporte.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Añadir el bloque al formato del reporte**

En la sección `## Formato del reporte para el chat`, dentro del bloque de código, insertar
entre la línea `RECOMENDACION DE COMPRA INMEDIATA...` y `Notas semana a semana:`:

```
CUANDO PEDIR (lead time Xd, colchon Xd)
- SERUM:  pedir antes del <fecha> (quedan X dias) - stock se agota ~<fecha>
- CHAMPU: pedir antes del <fecha> (quedan X dias) - stock se agota ~<fecha>
```

- [ ] **Step 2: Documentar las reglas nuevas**

En `## Reglas fijas`, añadir al final:

```markdown
- **Fecha de pedido (sección CUANDO PEDIR, filas 42-52 del Consolidado):** burn-down
  sobre los 4 tramos de Katching (0-7 / 7-30 / 30-90 / 90-365). `fecha_pedido =
  agotamiento − colchón − lead time`. Lead time (B45) y colchón (B46) son **amarillas
  editables**: el script solo las pisa si pasas `--lead-time` / `--colchon`.
- **B7 está vacía a propósito** (dato muerto). No la rellenes y **no borres la fila 7**:
  desplazaría todo y rompería las referencias fijas del script.
- Solo cuenta stock físico disponible; no descuenta entrante ni reservado.
```

- [ ] **Step 3: Documentar el setup en Infra**

En `## Infra`, añadir:

```markdown
- `weekly/setup_cuando_pedir.py` ya se ejecutó (2026-08-03). Solo hay que volver a
  correrlo si se rompe la sección CUANDO PEDIR. Es idempotente.
- `weekly/verificar_fechas.py` contrasta las fechas del Sheet con `weekly/burndown.py`.
  Útil si alguna fecha parece rara.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: documentar la seccion CUANDO PEDIR en CLAUDE.md"
```

---

## Self-Review

**Cobertura del spec:**

| Requisito del spec | Tarea |
|---|---|
| Método burn-down por tramos | Task 1 (oráculo) + Task 2 (fórmulas) |
| Parámetros B44/B45/B46 | Task 2 Step 1, Task 3 Steps 1-2 |
| Solo stock físico | Task 2 (fórmulas usan `E25`/`E32` = `B6`/`B8`) |
| Layout filas 42-52, notas a 54 | Task 2 Step 1 (`seccion()`, `NOTAS`) |
| Fórmulas exactas | Task 2 Step 1 (`fila_producto()`) |
| Formato fecha + amarillo | Task 2 Step 1 (`formatos()`) |
| Casos borde (>12m, tarde, div/0, champú) | Task 1 Step 1 (tests), Task 2 (`IFERROR`) |
| Vaciar B7 | Task 2 Step 1 + verificación en Step 3 |
| No eliminar fila 7 | Global Constraints + docstring Task 2 |
| Flags `--lead-time`/`--colchon` | Task 3 Steps 1-2 |
| Escaneo de errores a `A1:H60` | Task 3 Step 3 |
| Bloque en el reporte del chat | Task 3 Step 4 |
| Verificación (4 puntos del spec) | Task 4 Steps 2-4 |
| Fuera de alcance respetado | No hay tarea de "cuánto pedir" ni de stock entrante |

**Consistencia de nombres:** `dia_agotamiento` y `tasa_al_agotarse` se definen en Task 1
y se consumen en Task 4 con esos mismos nombres. `fila_producto`, `seccion`, `formatos`,
`gid_de`, `rango` son internos de Task 2. Celdas `B44`/`B45`/`B46` y filas `49`/`50`
coinciden entre Tasks 2, 3 y 4.

**Hueco detectado y cubierto:** el spec no mencionaba actualizar `CLAUDE.md`. Sin eso la
próxima sesión semanal no sabría imprimir el bloque nuevo ni que B7 debe seguir vacía.
Añadido como Task 5.
