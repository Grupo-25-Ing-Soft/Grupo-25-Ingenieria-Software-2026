"""Levanta la app con el Supabase simulado para probarla en el navegador
sin tocar la base real. Los datos viven en memoria y se pierden al cerrar.

    python tests/servidor_prueba.py        ->  http://127.0.0.1:5050

Trae productos 412/414/415/425, colores Blanco/Negro/Beige y tallas S/M/L
(la L sin código EAN).
"""
import os
import sys

os.environ['SUPABASE_URL'] = 'http://127.0.0.1:9'
os.environ['SUPABASE_PUBLISHABLE_KEY'] = 'sb_publishable_pruebas'
os.environ['FLASK_SECRET_KEY'] = 'servidor-de-prueba'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import realFlask  # noqa: E402
from tests.supabase_falso import con_datos_de_ejemplo  # noqa: E402

realFlask.supabase = con_datos_de_ejemplo()
# Los cambios en las plantillas se ven al recargar, sin reiniciar el servidor.
realFlask.app.config['TEMPLATES_AUTO_RELOAD'] = True

if __name__ == '__main__':
    realFlask.app.run(host='127.0.0.1', port=int(os.environ.get('PORT', 5050)), debug=False)
