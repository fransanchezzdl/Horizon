"""
Checkpoint de prediction_log — exporta e importa el estado completo de la tabla.

Uso:
    # Exportar estado actual (antes de hacer backfill)
    python -m backend.scripts.checkpoint_prediction_log export

    # Restaurar desde un checkpoint (si el backfill salió mal)
    python -m backend.scripts.checkpoint_prediction_log restore checkpoints/prediction_log_20260414_123456.json

    # Listar checkpoints disponibles
    python -m backend.scripts.checkpoint_prediction_log list
"""

import json
import os
import sys
from datetime import datetime, date

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "checkpoints")
TABLE = "prediction_log"


def _get_supabase():
    from ..database import supabase
    return supabase


def export_checkpoint() -> str:
    """
    Descarga todos los registros de prediction_log y los guarda en un JSON.
    Devuelve la ruta del archivo generado.
    """
    supabase = _get_supabase()

    print("[checkpoint] Descargando prediction_log desde Supabase...")
    all_rows = []
    page_size = 1000
    offset = 0

    while True:
        result = (
            supabase.table(TABLE)
            .select("*")
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = result.data or []
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(CHECKPOINT_DIR, f"prediction_log_{timestamp}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2, default=str)

    print(f"[checkpoint] {len(all_rows)} registros exportados -> {filename}")
    return filename


def restore_checkpoint(filepath: str):
    """
    Restaura prediction_log desde un checkpoint JSON.

    ADVERTENCIA: Borra todos los registros actuales y los reemplaza por los del checkpoint.
    Pide confirmación explícita antes de proceder.
    """
    if not os.path.exists(filepath):
        print(f"[ERROR] No se encuentra el archivo: {filepath}")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        rows = json.load(f)

    print(f"\n[checkpoint] Checkpoint cargado: {len(rows)} registros desde {filepath}")
    print("[checkpoint] ADVERTENCIA: Esto borrará TODOS los registros actuales de prediction_log.")
    confirm = input("¿Continuar? Escribe 'SI' para confirmar: ").strip()
    if confirm != "SI":
        print("[checkpoint] Restauración cancelada.")
        return

    supabase = _get_supabase()

    # Borrar todos los registros actuales
    print("[checkpoint] Borrando registros actuales...")
    # Supabase no tiene DELETE sin filtro directo — filtramos por id > 0
    supabase.table(TABLE).delete().gt("id", 0).execute()

    # Reinsertar en bloques de 500 (límite de Supabase)
    print(f"[checkpoint] Reinsertando {len(rows)} registros...")
    chunk_size = 500
    inserted = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        # Eliminar el campo 'id' para que Supabase lo regenere y evitar conflictos
        clean_chunk = [{k: v for k, v in row.items() if k != "id"} for row in chunk]
        supabase.table(TABLE).insert(clean_chunk).execute()
        inserted += len(chunk)
        print(f"  → {inserted}/{len(rows)}")

    print(f"[checkpoint] Restauración completada: {inserted} registros insertados.")


def list_checkpoints():
    """Lista los checkpoints disponibles ordenados por fecha."""
    if not os.path.exists(CHECKPOINT_DIR):
        print("[checkpoint] No hay checkpoints guardados todavía.")
        return

    files = sorted(
        [f for f in os.listdir(CHECKPOINT_DIR) if f.startswith("prediction_log_") and f.endswith(".json")],
        reverse=True
    )

    if not files:
        print("[checkpoint] No hay checkpoints guardados todavía.")
        return

    print(f"[checkpoint] Checkpoints disponibles en {CHECKPOINT_DIR}:")
    for f in files:
        path = os.path.join(CHECKPOINT_DIR, f)
        size_kb = os.path.getsize(path) / 1024
        print(f"  {f}  ({size_kb:.1f} KB)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "export":
        export_checkpoint()
    elif cmd == "restore":
        if len(sys.argv) < 3:
            print("[ERROR] Debes indicar la ruta del checkpoint.")
            print("  Uso: python -m backend.scripts.checkpoint_prediction_log restore <ruta>")
            sys.exit(1)
        restore_checkpoint(sys.argv[2])
    elif cmd == "list":
        list_checkpoints()
    else:
        print(f"[ERROR] Comando desconocido: {cmd}")
        print("Comandos disponibles: export | restore <ruta> | list")
        sys.exit(1)


if __name__ == "__main__":
    main()
