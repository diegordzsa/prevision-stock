# Reporte Semanal de Stock — Hair Biolabs

Scripts que convierten los inputs semanales (export de Shopify, capturas de Katching,
stock actual) en el reporte de previsión de stock, sobrescribiendo el Google Sheet
*"Reporte Stock HairBiolabs - Semanal"* y devolviendo el reporte en texto.

**El manual de operación es [CLAUDE.md](CLAUDE.md)**: flujo semanal paso a paso, reglas
de clasificación, sección CUANDO PEDIR y formato del reporte. Este README solo cubre
cómo dejar el proyecto funcionando en un ordenador nuevo.

## Puesta en marcha en un ordenador nuevo

```bash
git clone <url-del-repo>
cd prevision-stock
pip install -r requirements.txt
```

Después hay que darle la llave de la cuenta de servicio de Google. **La llave no está en
el repo** (la ignora `.gitignore`): cópiala del ordenador original o descárgala de Google
Cloud — cuenta `claude-sheets@prevision-stock.iam.gserviceaccount.com`, que debe ser
Editor del Sheet.

Ponla en cualquiera de estos sitios; [credenciales.py](credenciales.py) los busca en este
orden:

1. La ruta que indique la variable de entorno `PREVISION_STOCK_KEY`.
2. `credentials/service-account.json` dentro del repo. **Es la opción recomendada**: esa
   carpeta ya está ignorada por git.
3. `C:\Users\diego\Downloads\prevision-stock-5264cd38736b.json`, la ubicación histórica
   del ordenador original (por eso allí no hay que mover nada).

Si no la encuentra, los scripts fallan con un mensaje que repite estas tres opciones.

### Comprobar que funciona

```bash
# Tests del burn-down: no tocan la red ni necesitan llave
python weekly/test_burndown.py

# Dry-run del reporte: lee los CSV, calcula e imprime, NO escribe en el Sheet
python weekly/update_sheet.py --stock-serum 0 --stock-champu 0 --ventas-serum 0 --no-write
```

El dry-run tampoco necesita llave (sale antes de llamar a la API). El primer comando que
sí la pide es un `update_sheet.py` sin `--no-write`, o `weekly/verificar_fechas.py`.

## Sobre el intérprete de Python

Los comandos de `CLAUDE.md` están escritos como `C:\Python314\python ...` porque ese es el
intérprete del ordenador original. En otra máquina usa el `python` que tengas (3.9+);
la ruta absoluta no tiene nada de especial.

## Estructura

| Ruta | Qué es |
|---|---|
| `weekly/update_sheet.py` | Script principal: lee los CSV, sobrescribe las 3 hojas e imprime el reporte |
| `weekly/burndown.py` | Cálculo de agotamiento de stock sobre los 4 tramos de Katching |
| `weekly/verificar_fechas.py` | Contrasta las fechas de CUANDO PEDIR del Sheet contra el oráculo de `burndown.py` |
| `weekly/setup_cuando_pedir.py` | Crea/repara la sección CUANDO PEDIR del Sheet (idempotente, ya ejecutado) |
| `weekly/shopify.csv`, `weekly/katching.csv` | Inputs de la semana; sirven de ejemplo del formato exacto |
| `weekly/test_*.py` | Tests de `burndown.py` y prueba de mutación del verificador |
| `backups/backup_sheet.py` | Backup y restore del Sheet completo (fórmulas incluidas) |
| `credenciales.py` | Único sitio donde se decide dónde está la llave |
| `docs/` | Spec y plan de la feature CUANDO PEDIR |

## Qué no se versiona

La llave de servicio, `credentials/`, `__pycache__/` y `AGENTS.md` (guía paralela para
Codex, específica de la máquina original). Los CSV semanales **sí** se versionan, pero no
hace falta hacer commit cada semana: sobrescríbelos y ya.
