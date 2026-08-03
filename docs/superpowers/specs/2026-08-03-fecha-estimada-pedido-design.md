# Fecha estimada de pedido — diseño

**Fecha:** 2026-08-03
**Proyecto:** Reporte Semanal de Stock — Hair Biolabs

## Problema

El reporte dice *cuántas* unidades faltan pero no *cuándo* hay que pedirlas. El semáforo
a 30 días puede decir `OK` mientras el stock real se agota en 8 semanas, y con un lead
time de proveedor de 2-3 semanas eso significa llegar tarde sin haber visto ninguna
alerta. Esta semana es el caso exacto: serum en `OK` a 30 días y en `URGENTE` a 3 meses.

## Objetivo

Añadir al reporte una **fecha límite estimada de pedido** por producto (serum y champú).
Solo responde *cuándo*; el *cuánto* ya está en `RECOMENDACION DE REPOSICION`.

## Método de cálculo

**Burn-down sobre la curva de demanda de Katching**, no tasa plana.

Katching da demanda acumulada a 7d / 30d / 3m / 12m. De ahí salen cuatro tramos con su
consumo diario propio, y se quema el stock tramo a tramo:

| Tramo | Días | Tasa diaria |
|---|---|---|
| 1 | 0-7 | `D25 / 7` |
| 2 | 7-30 | `(D26-D25) / 23` |
| 3 | 30-90 | `(D27-D26) / 60` |
| 4 | 90-365 | `(D28-D27) / 275` |

Se eligió frente a una tasa plana a 30 días porque el consumo **no es plano**: el serum
va a ~62 uds/día esta semana pero a ~82 uds/día en el tramo 30-90. Una tasa plana da la
fecha de pedido con ~1 semana de retraso justo cuando la demanda acelera.

Encadenado:

```
día_agotamiento = inversa de la curva acumulada evaluada en el stock actual
día_llegada     = día_agotamiento − colchón
día_pedido      = día_llegada − lead_time
fecha_pedido    = fecha_base + día_pedido
```

El colchón se resta como días sobre la línea temporal (no se convierte a unidades). Es
equivalente a "que llegue cuando aún queden N días de venta" y evita la circularidad de
que el colchón en unidades dependa de la tasa del día de llegada.

## Parámetros

| Parámetro | Valor | Celda | Editable |
|---|---|---|---|
| Fecha base del cálculo | fecha de generación del reporte | `B44` | no (la escribe el script) |
| Lead time proveedor | 21 días | `B45` | sí (amarilla) |
| Colchón al recibir | 7 días de cobertura | `B46` | sí (amarilla) |

Lead time 21 = extremo malo de la horquilla real del proveedor (2-3 semanas).

Las fechas proyectadas se anclan a `B44` (los datos de demanda son de ese día). Los
"días restantes" usan `TODAY()`, para que el contador de urgencia siga vivo entre
ejecuciones semanales.

## Alcance del stock

Solo **stock físico disponible** (`B6` serum, `B8` champú). No se cuenta stock entrante
ni reservado. Confirmado contra beeping: Disponible 3.868 · Reservado 185 · Entrante 10.

## Layout en el Sheet

Sección nueva `CUANDO PEDIR (ESTIMADO)` justo debajo de `RECOMENDACION DE REPOSICION`
(fila 40). El bloque `NOTAS Y SUPUESTOS` baja de la fila 42 a la 54.

```
42  CUANDO PEDIR (ESTIMADO)
43  Parámetro                  | Valor      | Detalle
44  Fecha base del cálculo     | 2026-08-03 | Fecha de generación del reporte
45  Lead time proveedor (días) | 21         | AMARILLA
46  Colchón al recibir (días)  | 7          | AMARILLA
47
48  Producto | Consumo/día  | Stock se  | Pedido debe | FECHA LIMITE | Días      | Aviso
             | (al agotarse)| agota el  | llegar el   | DE PEDIDO    | restantes |
49  SERUM
50  CHAMPU
51
52  Fechas estimadas con la demanda proyectada de Katching.
    No descuentan pedidos ya en camino.
53
54  NOTAS Y SUPUESTOS
55  Champús y Packs - que suscripcion tienen?
```

Implementado con **fórmulas, no valores fijos**, igual que el resto del Sheet: cambiar
el lead time a 14 recalcula las fechas sin volver a correr el script.

### Fórmulas (fila 49 = SERUM; fila 50 = CHAMPU con `E32` y `D32:D35`)

```
B49  =IFERROR(IF(E25>D28,"-",IF(E25<=D25,D25/7,IF(E25<=D26,(D26-D25)/23,
      IF(E25<=D27,(D27-D26)/60,(D28-D27)/275)))),"-")

C49  =IFERROR(IF(E25>D28,">12 meses",
      $B$44+IF(E25<=D25, E25*7/D25,
             IF(E25<=D26, 7+(E25-D25)*23/(D26-D25),
             IF(E25<=D27, 30+(E25-D26)*60/(D27-D26),
                          90+(E25-D27)*275/(D28-D27))))),"sin datos")

D49  =IF(ISNUMBER(C49), C49-$B$46, "-")
E49  =IF(ISNUMBER(D49), D49-$B$45, "-")
F49  =IF(ISNUMBER(E49), INT(E49)-TODAY(), "-")
G49  =IF(NOT(ISNUMBER(E49)),"Sin riesgo a 12 meses",
      IF(F49<=0,"PEDIR HOY - YA VAS TARDE",
      IF(F49<=14,"PEDIR ESTA SEMANA","OK")))
```

**Redondeo:** el día de agotamiento sale fraccionario (53,69 para serum). Se trunca hacia
abajo — el último día completo con stock — que es lo conservador y coincide con lo que
Sheets muestra al formatear un serial fraccionario como fecha. `INT()` en `F49` para que
los días restantes salgan enteros.

`C49:E50` en formato fecha. `B45:B46` con fondo amarillo, como el resto de inputs.

## Casos borde

| Caso | Comportamiento |
|---|---|
| Stock > demanda a 12 meses | `>12 meses`, aviso `Sin riesgo a 12 meses`. Sin extrapolar más allá del horizonte de Katching. |
| Fecha límite ya pasada | `PEDIR HOY - YA VAS TARDE` en vez de fecha negativa. |
| Tramo con demanda incremental 0 | `IFERROR` → `-`. Evita división por cero. |
| Champú (0 suscripciones) | Funciona igual; sus cuatro tramos son casi planos. |

## Cambios en `weekly/update_sheet.py`

1. Flags nuevos opcionales `--lead-time` y `--colchon`. Solo escriben `B45`/`B46` si se
   pasan explícitamente; si no, se respeta lo que haya en la celda (son editables).
2. Escribir siempre `B44` con la fecha base como **valor de fecha real**, no texto.
3. Ampliar el escaneo de errores de `A1:H45` a `A1:H60`. Sin esto, un `#REF!` en la
   sección nueva pasaría desapercibido.
4. Leer `A49:G50` tras escribir y añadir el bloque al reporte impreso.

Las fechas no se calculan en Python: se leen del Sheet ya calculadas, siguiendo el patrón
existente. Única fuente de verdad = las fórmulas.

## Setup de una sola vez: `weekly/setup_cuando_pedir.py`

Script aparte, idempotente, que se ejecuta una vez:

1. Vaciar `B7` (dato muerto: `1632` congelado desde que se montó el Sheet, sin ninguna
   fórmula que lo referencie y nunca actualizado por el script).
2. Mover `NOTAS Y SUPUESTOS` de las filas 42-43 a las 54-55.
3. Escribir la sección `CUANDO PEDIR` (filas 42-52) con sus fórmulas.
4. Aplicar formato: fechas en `C49:E50`, amarillo en `B45:B46`, negrita en cabeceras.

**No se elimina la fila 7.** Borrarla desplazaría todo hacia arriba y rompería el script,
que escribe `B6`/`B8`/`B9`/`B10`/`B25:B28` por posición fija.

## Formato en el reporte del chat

Bloque nuevo entre `RECOMENDACION DE COMPRA` y las notas:

```
CUANDO PEDIR (lead time 21d, colchon 7d)
- SERUM:  pedir antes del 2026-08-28 (quedan 25 dias) - stock se agota ~2026-09-25
- CHAMPU: pedir antes del 2026-11-27 (quedan 116 dias) - stock se agota ~2026-12-25
No descuenta pedidos ya en camino.
```

## Resultado esperado con los datos de 2026-08-03

Stock serum 3.868 · demanda 433 / 1.932 / 6.836 / 27.651

- Día de agotamiento = `30 + (3868-1932)*60/(6836-1932)` = 53,687 → día 53 → **2026-09-25**
- Llegada objetivo día 46 → 2026-09-18
- **Fecha límite de pedido: 2026-08-28** (25 días de margen)
- Consumo/día al agotarse: 81,7

Stock champú 1.078 · demanda 52 / 225 / 676 / 2.704

- Día de agotamiento = `90 + (1078-676)*275/(2704-676)` = 144,512 → día 144 → **2026-12-25**
- Llegada objetivo día 137 → 2026-12-18
- **Fecha límite de pedido: 2026-11-27** (116 días de margen)
- Consumo/día al agotarse: 7,4

## Verificación

1. `--no-write` para confirmar que el script arranca sin romper nada.
2. Tras el setup, comprobar que `ERRORES DE FORMULA: NINGUNO` sigue saliendo.
3. Contrastar las fechas del Sheet con el cálculo manual de arriba (día 54 serum,
   día 145 champú).
4. Editar `B45` a 14 en el Sheet y comprobar que la fecha límite de serum se mueve
   7 días adelante, sin volver a correr el script.

## Fuera de alcance

- Cuántas unidades pedir (ya cubierto por `RECOMENDACION DE REPOSICION`).
- Descontar stock entrante o reservado.
- Histórico de fechas de pedido o seguimiento de pedidos abiertos.
