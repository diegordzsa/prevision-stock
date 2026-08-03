# -*- coding: utf-8 -*-
"""Burn-down del stock sobre la curva de demanda acumulada de Katching.

Espeja las formulas de la seccion CUANDO PEDIR del Sheet. Es el oraculo para
verificar esas formulas: si el Sheet y este modulo discrepan, una esta mal.

demandas = (d7, d30, d90, d365) demanda ACUMULADA a 7 dias, 30 dias, 3 meses
y 12 meses. Los tramos y sus longitudes en dias: 0-7 (7), 7-30 (23),
30-90 (60), 90-365 (275).
"""


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
    if dem_incr <= 0:
        return None
    return dem_incr / largo
