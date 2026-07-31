"""Prepara TODO lo que la demo necesita para arrancar, en un solo comando.

Lo llama el archivo ejecutar_backend.bat (Windows) y ejecutar_backend.sh (Linux/Mac)
para no tener que escribir varios comandos de Python a mano.

Hace 4 cosas:
  1. Crea la base de datos SQLite con todos los datos simulados (seed).
  2. Entrena el modelo de riesgo de desercion.
  3. Calcula el score SRD de cada estudiante.
  4. Siembra los eventos base del log de metadatos.

Se puede volver a ejecutar cuando se quiera: borra la base anterior y la
regenera desde cero.
"""
import os
import sys
import shutil

# Trabajar siempre desde la carpeta donde vive este archivo (backend/)
AQUI = os.path.dirname(os.path.abspath(__file__))
os.chdir(AQUI)
sys.path.insert(0, AQUI)

DB = os.path.join(AQUI, "gyverlabs_demo.db")
DATOS = os.path.join(AQUI, "datos")


def linea(txt):
    print("")
    print("=" * 62)
    print(f"  {txt}")
    print("=" * 62)


def main():
    reset = "--reset" in sys.argv or "-r" in sys.argv

    if reset and os.path.exists(DB):
        os.remove(DB)
        print("Base de datos anterior eliminada.")
    if reset and os.path.isdir(DATOS):
        for f in os.listdir(DATOS):
            if f.endswith((".jsonl", ".csv")):
                try:
                    os.remove(os.path.join(DATOS, f))
                except OSError:
                    pass

    if os.path.exists(DB) and not reset:
        print("La base de datos ya existe. No hay nada que preparar.")
        print("Si quieres regenerarla desde cero, ejecuta:")
        print("   python preparar_datos.py --reset")
        return 0

    # ---------- 1. Datos simulados ----------
    linea("PASO 1 de 4  ·  Generando datos de demostracion")
    import seed_data
    seed_data.main()

    # ---------- 2. Modelo de riesgo ----------
    linea("PASO 2 de 4  ·  Entrenando el modelo de riesgo")
    try:
        from ml import train_demo
        train_demo.main()
    except Exception as e:
        print(f"Aviso: no se pudo entrenar el modelo ({e}).")
        print("El sistema funciona igual: usara el modelo de respaldo por reglas.")

    # ---------- 3. Scores SRD ----------
    linea("PASO 3 de 4  ·  Calculando el riesgo de cada estudiante")
    try:
        from database import SessionLocal
        from services import srd_service
        db = SessionLocal()
        n = srd_service.recalcular_todos(db)
        db.close()
        print(f"Scores calculados para {n} estudiantes.")
    except Exception as e:
        print(f"Aviso: no se pudieron calcular los scores ({e}).")

    # ---------- 4. Log de metadatos ----------
    linea("PASO 4 de 4  ·  Sembrando el log de metadatos")
    try:
        import metadatos
        metadatos.registrar_evento("SISTEMA_INICIADO", "Sistema",
                                   payload={"version": "0.5.0-v4"})
        metadatos.registrar_evento("SEED_GENERADO", "Sistema")
        metadatos.registrar_evento("MODELO_ENTRENADO", "Sistema")
        print("Log de metadatos listo.")
    except Exception as e:
        print(f"Aviso: no se pudo sembrar el log ({e}).")

    linea("LISTO  ·  La base de datos quedo preparada")
    print(f"Archivo: {DB}")
    tam = os.path.getsize(DB) / 1024 / 1024 if os.path.exists(DB) else 0
    print(f"Tamano:  {tam:.1f} MB")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print("")
        print("ERROR al preparar los datos:")
        print(f"   {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
