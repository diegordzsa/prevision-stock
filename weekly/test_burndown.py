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
# tramo(s) previos con incremento cero (d7=d30=0) no rompen la busqueda: el
# stock cae en el tramo 30-90, cuyo dem_incr (100) es positivo. (Nota: esto
# NO ejercita la guarda "if dem_incr <= 0" de dia_agotamiento -- ver mas
# abajo por que esa rama es inalcanzable via la API publica.)
check("tramo plano (segmentos previos)", dia_agotamiento(50, (0, 0, 100, 200)), 30 + 50 * 60 / 100)
# lo mismo con TRES tramos previos planos (d7=d30=d90=0): el stock cae en el
# ultimo tramo (90-365), cuyo dem_incr (500) tambien es positivo.
check("tramo plano (3 segmentos previos)", dia_agotamiento(250, (0, 0, 0, 500)), 90 + 250 * 275 / 500)

# La guarda "if dem_incr <= 0: return None" dentro de dia_agotamiento es
# INALCANZABLE via la API publica para cualquier (stock, demandas): elegir
# el tramo k (k=1,2,3) exige demandas[k-1] < stock <= demandas[k], lo que
# fuerza demandas[k] > demandas[k-1] (dem_incr > 0) por pura logica de las
# comparaciones encadenadas -- sin importar si la curva de demanda es
# monotona o no. La unica forma de obtener dem_incr <= 0 es en el tramo0
# con d7 <= 0 y stock <= d7 (i.e. stock <= 0), y ese caso ya lo intercepta
# el atajo "if stock <= 0: return 0.0" ANTES de llegar a _tramo. Verificado
# ademas por busqueda aleatoria (2M combinaciones, incluyendo demandas
# negativas/decrecientes): ningun caso alcanza esa rama. Por eso la
# cobertura real de "dem_incr <= 0" se hace abajo sobre tasa_al_agotarse,
# que SI puede alcanzar ese tramo (no tiene el atajo de stock <= 0).
check("dia_agotamiento stock 0, d7=0 (atajo, no la guarda interna)", dia_agotamiento(0, (0, 100, 200, 300)), 0.0)

print("tasa_al_agotarse")
check("serum 3868", tasa_al_agotarse(3868, SERUM), (6836 - 1932) / 60)
check("champu 1078", tasa_al_agotarse(1078, CHAMPU), (2704 - 676) / 275)
check("serum 99999", tasa_al_agotarse(99999, SERUM), None)
# guarda dem_incr <= 0: tasa_al_agotarse no tiene el atajo de stock <= 0 de
# dia_agotamiento, asi que SI puede caer en el tramo0 con dem_incr = d7 = 0
# cuando stock <= 0 y d7 <= 0. Debe devolver None (no 0.0 ni negativo) para
# que ambas funciones coincidan en cuando dicen "no puedo calcularlo".
check("tasa stock 0, d7=0", tasa_al_agotarse(0, (0, 100, 200, 300)), None)
check("tasa stock -5, d7=0", tasa_al_agotarse(-5, (0, 100, 200, 300)), None)

print()
if fallos:
    print(f"FALLARON {len(fallos)}: {', '.join(fallos)}")
    sys.exit(1)
print("TODOS OK")
