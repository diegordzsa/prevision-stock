# -*- coding: utf-8 -*-
"""
Localiza la llave de la cuenta de servicio de Google que usan los scripts.

La llave NO esta en el repo (la ignora .gitignore), asi que cada ordenador la
tiene en un sitio distinto. Este modulo es el unico lugar donde se decide cual.

Orden de busqueda:
  1. Variable de entorno PREVISION_STOCK_KEY (ruta completa al .json).
  2. credentials/service-account.json dentro del repo.
  3. La ruta historica en Downloads del ordenador original.

Si PREVISION_STOCK_KEY esta definida pero apunta a un archivo que no existe,
falla ahi mismo en vez de caer en silencio a las otras opciones: si alguien se
molesto en definirla, un error tipografico debe verse, no taparse.
"""
import os

RAIZ = os.path.dirname(os.path.abspath(__file__))

# Ubicacion recomendada al clonar el repo en un ordenador nuevo.
EN_REPO = os.path.join(RAIZ, 'credentials', 'service-account.json')

# Ordenador original: la llave sigue donde estaba, no hace falta moverla.
HISTORICA = r'C:\Users\diego\Downloads\prevision-stock-5264cd38736b.json'

CUENTA = 'claude-sheets@prevision-stock.iam.gserviceaccount.com'

_AYUDA = """No encuentro la llave de la cuenta de servicio de Google.

La llave nunca se sube a GitHub, hay que ponerla a mano en cada ordenador.
Copiala del ordenador original o descargala de Google Cloud (cuenta de
servicio {cuenta}, que debe ser Editor del Sheet).

Ponla en una de estas tres ubicaciones:

  1. Donde diga la variable de entorno PREVISION_STOCK_KEY
  2. {en_repo}
  3. {historica}

La opcion 2 es la recomendada: esa carpeta ya esta en .gitignore."""


def ruta_llave():
    """Devuelve la ruta al .json de la cuenta de servicio.

    Lanza SystemExit con instrucciones si no la encuentra en ningun sitio.
    """
    del_entorno = os.environ.get('PREVISION_STOCK_KEY')
    if del_entorno:
        if os.path.isfile(del_entorno):
            return del_entorno
        raise SystemExit(
            'PREVISION_STOCK_KEY apunta a un archivo que no existe:\n'
            '  {}\n'
            'Corrige la variable o borrala para usar las otras ubicaciones.'
            .format(del_entorno))

    for candidata in (EN_REPO, HISTORICA):
        if os.path.isfile(candidata):
            return candidata

    raise SystemExit(_AYUDA.format(cuenta=CUENTA, en_repo=EN_REPO,
                                   historica=HISTORICA))
