#!/usr/bin/env python3
"""Ejecutor de herramientas Python con fallback de entorno.

Prioriza el interprete del venv del proyecto; si no existe, usa el Python actual.
Muestra un spinner ASCII mientras se ejecuta el comando para evitar sensacion de bloqueo.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence, TextIO

ROOT = Path(__file__).resolve().parent.parent.parent
SPINNER_FRAMES = ("|", "/", "-", "\\")


def resolve_progress_stream(in_pre_commit: bool) -> TextIO | None:
    """Obtiene un stream para progreso en tiempo real.

    Prioridad:
    1) stderr interactivo
    2) consola real del sistema (CONOUT$/tty) para evitar captura de pre-commit
    3) None si no hay canal apto
    """
    if sys.stderr.isatty():
        return sys.stderr

    # En pre-commit, intentamos salida directa a consola para que el spinner
    # sea visible incluso cuando la herramienta captura stdout/stderr.
    if in_pre_commit:
        if os.name == "nt":
            try:
                return open("CONOUT$", "w", encoding="utf-8", buffering=1)
            except OSError:
                return None

        try:
            return open("/dev/tty", "w", encoding="utf-8", buffering=1)
        except OSError:
            return None

    return None


def resolve_python_executable() -> tuple[Path, bool]:
    candidates = [
        ROOT / "backend" / "venv" / "Scripts" / "python.exe",
        ROOT / "backend" / "venv" / "bin" / "python",
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
        ROOT / "venv" / "Scripts" / "python.exe",
        ROOT / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate, True
    return Path(sys.executable), False


def run_with_spinner(command: Sequence[str], label: str) -> int:
    in_pre_commit = os.getenv("PRE_COMMIT") is not None
    progress_stream = resolve_progress_stream(in_pre_commit)

    # Sin stream de progreso (pre-commit/no TTY), ejecutamos directo.
    if progress_stream is None:
        return subprocess.call(command, cwd=ROOT)

    # Evita bloqueos por buffers: dejamos stdout/stderr directos al terminal.
    process = subprocess.Popen(command, cwd=ROOT)

    frame_idx = 0
    start = time.time()
    spinner_line_initialized = False

    if in_pre_commit and progress_stream is not None:
        # Reserva una línea propia para el spinner y evita pisar la del hook.
        progress_stream.write("\n")
        progress_stream.flush()
        spinner_line_initialized = True

    while process.poll() is None:
        elapsed = int(time.time() - start)
        frame = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]
        progress_stream.write(f"\r{label} {frame} {elapsed}s")
        progress_stream.flush()
        frame_idx += 1
        time.sleep(0.1)

    elapsed_total = int(time.time() - start)
    if spinner_line_initialized:
        progress_stream.write(f"\r{label} listo ({elapsed_total}s)\n")
    else:
        progress_stream.write("\r" + " " * 100 + "\r")
    progress_stream.flush()
    if progress_stream is not sys.stderr:
        progress_stream.close()

    return process.wait()


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python tests/scripts/run_tool_with_fallback.py <modulo> [args...]", file=sys.stderr)
        return 2

    module = sys.argv[1]
    args = sys.argv[2:]
    python_executable, from_local_venv = resolve_python_executable()
    in_pre_commit = os.getenv("PRE_COMMIT") is not None

    if not in_pre_commit:
        if from_local_venv:
            print(f"[runner] Usando venv: {python_executable}", file=sys.stderr)
        else:
            print(
                f"[runner] Sin venv local, usando Python del sistema: {python_executable}",
                file=sys.stderr,
            )

    command = [str(python_executable), "-m", module, *args]
    return run_with_spinner(command, label=f"Ejecutando {module}")


if __name__ == "__main__":
    raise SystemExit(main())
