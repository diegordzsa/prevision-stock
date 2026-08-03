# -*- coding: utf-8 -*-
"""Prueba de mutacion de weekly/verificar_fechas.py.

Objetivo: demostrar que el verificador SI detecta una discrepancia real (no
solo que siempre dice OK). No escribe nada en el Sheet: solo lee los datos de
produccion (igual que verificar_fechas.py) y parchea en memoria el resultado
de burndown.dia_agotamiento() para forzar un desajuste con lo que hay en el
Sheet. Es de solo lectura sobre Google Sheets.

Ejecutar (no forma parte del flujo semanal, es solo un test manual):
    C:\\Python314\\python weekly/test_verificar_fechas_mutacion.py
"""
import os, sys, runpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import burndown

_original = burndown.dia_agotamiento


def _mutado(stock, demandas):
    """Igual que el original pero desplazado +999 dias: fuerza que la fecha
    que calcula el 'oraculo' no coincida con la que ya esta escrita en el
    Sheet, sin tocar el Sheet para nada."""
    dia = _original(stock, demandas)
    return dia if dia is None else dia + 999


burndown.dia_agotamiento = _mutado

print("=== Prueba de mutacion: dia_agotamiento() parcheado (+999 dias) ===\n")
exit_code = 0
try:
    # verificar_fechas.py hace "from burndown import dia_agotamiento" al
    # ejecutarse: como burndown ya esta en sys.modules con el atributo
    # parcheado, coge la version mutada, no la original.
    runpy.run_path(os.path.join(HERE, 'verificar_fechas.py'), run_name='__main__')
except SystemExit as e:
    exit_code = e.code if isinstance(e.code, int) else 1

print(f"\nEXIT CODE observado: {exit_code}")
if exit_code == 1:
    print("OK: la mutacion SI produjo FALLO + exit 1 (el verificador detecta discrepancias).")
    sys.exit(0)
else:
    print("FALLO DE LA PRUEBA: se esperaba exit code 1 y no se obtuvo.")
    sys.exit(1)
