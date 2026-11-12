"""Lanzador de escritorio del sistema Comercial D Nix.

Levanta la aplicación Flask (realFlask.py) en este equipo y la muestra en una
ventana propia (Microsoft Edge en modo aplicación). Al cerrar la ventana, el
programa termina. Va en la raíz del repositorio, junto a realFlask.py.
"""
import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser

from dotenv import load_dotenv

HOST = "127.0.0.1"
PUERTO = 5000
URL = f"http://{HOST}:{PUERTO}"

# Carpeta del .exe una vez instalado; carpeta del repositorio en desarrollo.
CARPETA = os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                          else os.path.abspath(__file__))
# Carpeta con permiso de escritura para el registro de errores y el perfil de Edge.
DATOS = os.path.join(os.environ.get("LOCALAPPDATA", CARPETA), "ComercialDNix")


def puerto_ocupado():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, PUERTO)) == 0


def buscar_edge():
    rutas = [os.path.join(os.environ.get(var, ""), "Microsoft", "Edge", "Application", "msedge.exe")
             for var in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
    return next((r for r in rutas if os.path.isfile(r)), None) or shutil.which("msedge")


def abrir_ventana():
    """Abre la ventana y espera a que se cierre. Devuelve False si no hay Edge."""
    edge = buscar_edge()
    if not edge:
        webbrowser.open(URL)
        return False
    subprocess.run([edge, f"--app={URL}", "--no-first-run", "--window-size=1366,820",
                    f"--user-data-dir={os.path.join(DATOS, 'edge')}"])
    return True


def main():
    os.makedirs(DATOS, exist_ok=True)
    logging.basicConfig(filename=os.path.join(DATOS, "errores.log"), level=logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Si el sistema ya está abierto, solo se muestra otra ventana.
    if puerto_ocupado():
        abrir_ventana()
        return

    try:
        # El .env se lee desde la carpeta del .exe ANTES de importar realFlask,
        # que crea el cliente de Supabase al importarse.
        load_dotenv(os.path.join(CARPETA, ".env"))
        os.environ.pop("FLASK_DEBUG", None)
        from waitress import serve
        from realFlask import app
    except Exception:
        logging.exception("No se pudo iniciar el sistema")
        raise

    threading.Thread(target=serve, args=(app,),
                     kwargs={"host": HOST, "port": PUERTO, "threads": 8},
                     daemon=True).start()
    for _ in range(50):
        if puerto_ocupado():
            break
        time.sleep(0.1)

    if not abrir_ventana():
        # Sin Edge se usa el navegador predeterminado y el servidor queda activo.
        threading.Event().wait()


if __name__ == "__main__":
    main()
