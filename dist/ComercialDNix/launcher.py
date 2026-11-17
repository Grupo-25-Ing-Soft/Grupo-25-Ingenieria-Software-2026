"""Lanzador de escritorio del sistema Comercial D Nix.

Levanta la aplicación Flask (realFlask.py) en este equipo y la muestra en una
ventana propia (Microsoft Edge en modo aplicación). Al cerrar la ventana, el
programa termina. Va en la raíz del repositorio, junto a realFlask.py.

Si algo impide iniciar, muestra un mensaje con la causa y deja el detalle en
%LOCALAPPDATA%\\ComercialDNix\\errores.log.
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
TITULO = "Comercial D Nix"

# Carpeta del .exe una vez instalado; carpeta del repositorio en desarrollo.
CARPETA = os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                          else os.path.abspath(__file__))
# Carpeta con permiso de escritura para el registro y el perfil de Edge.
DATOS = os.path.join(os.environ.get("LOCALAPPDATA", CARPETA), "ComercialDNix")
REGISTRO = os.path.join(DATOS, "errores.log")

log = logging.getLogger("launcher")


def avisar(mensaje):
    """Muestra el error en una ventana (el .exe no tiene consola)."""
    log.error(mensaje)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, f"{mensaje}\n\nDetalle: {REGISTRO}", TITULO, 0x10)
    else:
        print(mensaje, file=sys.stderr)


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
        log.info("Edge no encontrado: se usa el navegador predeterminado")
        webbrowser.open(URL)
        return False
    subprocess.run([edge, f"--app={URL}", "--no-first-run", "--window-size=1366,820",
                    f"--user-data-dir={os.path.join(DATOS, 'edge')}"])
    return True


def main():
    os.makedirs(DATOS, exist_ok=True)
    logging.basicConfig(filename=REGISTRO, level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Los errores de los hilos (el servidor corre en uno) también van al registro.
    threading.excepthook = lambda a: log.error(
        "Error en el hilo %s", a.thread.name if a.thread else "?",
        exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
    log.info("Inicio. Carpeta del programa: %s", CARPETA)

    # Si el sistema ya está abierto, solo se muestra otra ventana.
    if puerto_ocupado():
        log.info("El puerto %s ya está en uso: se abre una ventana sobre ese servidor", PUERTO)
        abrir_ventana()
        return 0

    # El .env se lee desde la carpeta del .exe ANTES de importar realFlask,
    # que crea el cliente de Supabase al importarse.
    ruta_env = os.path.join(CARPETA, ".env")
    load_dotenv(ruta_env)
    os.environ.pop("FLASK_DEBUG", None)
    faltan = [v for v in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY") if not os.environ.get(v)]
    if faltan:
        motivo = "no existe" if not os.path.isfile(ruta_env) else "no define " + " ni ".join(faltan)
        avisar(f"No se puede iniciar: el archivo de configuración\n{ruta_env}\n{motivo}.")
        return 1

    try:
        from waitress import serve
        from realFlask import app
    except Exception as error:
        log.exception("No se pudo cargar el sistema")
        avisar(f"No se pudo cargar el sistema:\n{type(error).__name__}: {error}")
        return 1

    servidor = threading.Thread(target=serve, args=(app,), name="servidor",
                                kwargs={"host": HOST, "port": PUERTO, "threads": 8},
                                daemon=True)
    servidor.start()
    limite = time.monotonic() + 30
    while not puerto_ocupado():
        if not servidor.is_alive() or time.monotonic() > limite:
            avisar(f"El servidor local no respondió en {URL}.")
            return 1
        time.sleep(0.2)
    log.info("Servidor escuchando en %s", URL)

    if not abrir_ventana():
        # Sin Edge se usa el navegador predeterminado y el servidor queda activo.
        threading.Event().wait()
    log.info("Ventana cerrada: fin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
