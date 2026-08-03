# Reporte Semanal de Stock — Hair Biolabs

**Cada conversación en este proyecto es para lo mismo:** el usuario da los inputs de la
semana y tú **sobrescribes** el Google Sheet y le devuelves el reporte. Rápido, sin
re-explicar. No preguntes cosas ya resueltas aquí; solo actúa.

## Qué te da el usuario cada semana
1. **CSV de Shopify** ("Ventas totales por variante de producto - 7 días").
2. **Capturas de Katching** (Previsión de Inventario).
3. **Stock actual SERUM** (viene de beeping).
4. **Stock actual CHAMPU** (viene de beeping).
5. **Ventas SERUM no-suscripción 7d** (número manual).
   - Champú NO hace falta: el 100% del champú es no-suscripción → se toma solo de Shopify.

## Flujo de ejecución (haz esto)
1. Guarda el CSV que te pasa el usuario en `weekly/shopify.csv` (tal cual, sin editar).
2. Transcribe las capturas de Katching a `weekly/katching.csv` con cabecera exacta:
   `producto,variante,renov_7d,renov_30d,renov_3m,renov_12m` (una fila por producto/variante).
3. Corre:
   ```
   python weekly/update_sheet.py --stock-serum <N> --stock-champu <N> --ventas-serum <N>
   ```
   Opcionales: `--ventas-champu <N>` (def = unidades SHAMPOO de Shopify), `--date YYYY-MM-DD`
   (def = hoy), `--no-write` (dry-run), `--lead-time <N>` (def = lo que haya en B45),
   `--colchon <N>` (def = lo que haya en B46).
4. El script sobrescribe las 3 hojas, verifica que no haya errores y **imprime el reporte**.
   Pásale ese reporte al usuario en el chat con el formato de abajo.

Antes de escribir en firme, un `--no-write` rápido es buena práctica para revisar conteos y
avisos de categoría `REVISAR` (producto que el script no supo clasificar → míralo a mano).

## Reglas fijas (ya implementadas en el script — no reinventar)
- **Multiplicador** desde la variante: número que aparezca (`1 mes`→1, `2 meses`→2,
  `3 meses`→3, `2 sérum`→2, `1 sérum`→1, `Default Title`→1).
- **Categoría** (precedencia): `prueba`→EXCLUIR · `regalo misterioso`/`guia`/`guía`→EXCLUIR ·
  `pack completo`→PACK · champú sin serum→SHAMPOO · serum/sérum→SERUM.
- **Katching:** se excluye cualquier producto con `prueba`. Unidades = renovaciones × mult.
  Fila TOTAL SERUM al final (posición dinámica).
- **Champú = 100% no-suscripción** (Katching nunca tiene renovaciones de champú).
- **Consolidado:** solo se tocan celdas amarillas (B6 stock serum, B8 stock champú,
  B9 ventas serum, B10 ventas champú) + las referencias Susc del serum (B25:B28) que
  enlazan a la fila TOTAL SERUM de Katching. **No tocar** las fórmulas de Estado/Recomendación.
- **Fecha de pedido (sección CUANDO PEDIR, filas 42-52 del Consolidado):** burn-down
  sobre los 4 tramos de Katching (0-7 / 7-30 / 30-90 / 90-365). `fecha_pedido =
  agotamiento − colchón − lead time`. Lead time (B45) y colchón (B46) son **amarillas
  editables**: el script solo las pisa si pasas `--lead-time` / `--colchon`.
- **B7 está vacía a propósito** (dato muerto, ninguna fórmula la usa). No la rellenes y
  **no borres la fila 7**: desplazaría todo y rompería las referencias fijas del script.
- Solo cuenta stock físico disponible; no descuenta entrante ni reservado.

## Formato del reporte para el chat
```
REPORTE SEMANAL <fecha>

Serum (stock: X unidades)
- 7 dias / 30 dias / 3 meses / 12 meses: necesitas X, sobra/falta X. [ESTADO]

Champu (stock: X unidades)
- (mismo formato)

RECOMENDACION DE COMPRA INMEDIATA (30 dias): SERUM X · CHAMPU X

CUANDO PEDIR (lead time Xd, colchon Xd)
- SERUM:  pedir antes del <fecha> (quedan X dias) - stock se agota ~<fecha> [aviso]
- CHAMPU: pedir antes del <fecha> (quedan X dias) - stock se agota ~<fecha> [aviso]
  (no descuenta pedidos ya en camino)

ALERTAS URGENTES: [solo estados URGENTE, con cuántas faltan]

ERRORES DE FORMULA: [lista de celdas con error, o NINGUNO]

Notas semana a semana: [productos nuevos/que desaparecen, cambios grandes]
```

## Infra
- Google Sheet: **"Reporte Stock HairBiolabs - Semanal"**, id `1wNXOy6dIjQqfgsSmnqvdEVFmCv-ibj0kgy4BuyYQvZ8`.
- Escritura: cuenta de servicio `claude-sheets@prevision-stock.iam.gserviceaccount.com`
  (Editor del Sheet). Llave en `C:\Users\diego\Downloads\prevision-stock-5264cd38736b.json`
  (fuera del proyecto, no la muevas a OneDrive). El script usa esa llave vía Sheets API.
- MCP `google-sheets` también registrado en Claude Code (carga al reiniciar); el script no
  depende del MCP, escribe directo por API.
- Python: `C:\Python314\python`. Deps ya instaladas (`google-api-python-client`, `openpyxl`).
- `weekly/setup_cuando_pedir.py` ya se ejecutó (2026-08-03). Solo hay que volver a
  correrlo si se rompe la sección CUANDO PEDIR. Es idempotente.
- `weekly/verificar_fechas.py` contrasta las fechas del Sheet con `weekly/burndown.py`.
  Útil si alguna fecha parece rara.
- Backup/restore del Sheet: `C:\Python314\python backups/backup_sheet.py` (guarda
  `backups/sheet-<fecha>.json`) y `C:\Python314\python backups/backup_sheet.py --restore
  backups/sheet-<fecha>.json` para revertir (reescribe fórmulas tal cual estaban).
