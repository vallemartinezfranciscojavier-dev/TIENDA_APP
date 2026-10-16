"""
Verificación del .exe (Fase 15): arranca el ejecutable en offscreen y
comprueba que inicializa solo su entorno, igual que en verificaciones de
fases anteriores (Fase 12/14):
  - el proceso sigue vivo tras N segundos (no crashea al importar),
  - crea data/tienda.db y data/errores.log junto al exe,
  - el log de errores queda vacío (sin tracebacks).
Luego lo termina limpiamente.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Consolas Windows (cp1252) no entienden '✔'/'✘': forzar UTF-8 en la salida.
if sys.stdout and getattr(sys.stdout, "buffer", None) is not None:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

EXE_DIR = Path(__file__).parent / "dist" / "Sistema de Gestion Comercial"
EXE = EXE_DIR / "Sistema de Gestion Comercial.exe"

fallos = []
ok_count = 0


def check(nombre, cond, extra=""):
    global ok_count
    if cond:
        ok_count += 1
        print(f"  ✔ {nombre}")
    else:
        fallos.append(nombre)
        print(f"  ✘ {nombre} {extra}")


def main():
    check("exe existe", EXE.exists(), str(EXE))
    if not EXE.exists():
        sys.exit(1)

    # Limpiar datos de una corrida anterior para partir de cero.
    for d in (EXE_DIR / "data", EXE_DIR / "backups"):
        if d.exists():
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.Popen([str(EXE)], env=env, cwd=str(EXE_DIR))

    time.sleep(18)
    vivo = proc.poll() is None
    check("proceso vivo tras 18s", vivo,
          f"codigo_salida={proc.poll() if not vivo else '-'}")

    data = EXE_DIR / "data"
    tienda_db = data / "tienda.db"
    errores = data / "errores.log"
    check("crea data/tienda.db (init_db)", tienda_db.exists())
    check("crea data/errores.log", errores.exists())

    log_txt = errores.read_text(encoding="utf-8", errors="replace") if errores.exists() else ""
    sin_traceback = ("Traceback" not in log_txt
                      and "ERROR" not in log_txt.upper()
                      and "Exception" not in log_txt)
    check("errores.log sin crash (sin Traceback/EXCEPTION)", sin_traceback,
          repr(log_txt[:300]))
    check("log muestra pantalla de login", "pantalla de inicio" in log_txt,
          repr(log_txt[:200]))

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    print()
    print("=" * 60)
    if fallos:
        print(f"EXE FASE 15: {ok_count} OK, {len(fallos)} FALLOS:")
        for f in fallos:
            print("  -", f)
        sys.exit(1)
    print(f"EXE FASE 15: EL EJECUTABLE ARRANCA OK ({ok_count} checks)")
    sys.exit(0)


if __name__ == "__main__":
    main()