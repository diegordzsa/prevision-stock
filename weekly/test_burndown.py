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
