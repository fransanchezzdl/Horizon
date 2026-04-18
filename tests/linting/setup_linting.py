#!/usr/bin/env python3
"""
Configuración inicial de linting y pre-commit para Horizon.

Ejecutar:
    python tests/linting/setup_linting.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Ejecuta un comando y reporta el resultado."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"OK - {description}")
            return True
        else:
            print(f"Error en {description}")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Función principal de setup."""
    print("=" * 60)
    print("Configuración de Linting para Horizon")
    print("=" * 60)
    
    root_path = Path(__file__).parent.parent.parent
    
    steps_completed = []
    steps_failed = []
    
    # Paso 1: Instalar dependencias
    if run_command(
        [sys.executable, "-m", "pip", "install", "-r", str(root_path / "requirements.txt")],
        "Instalando dependencias"
    ):
        steps_completed.append("1. Dependencias instaladas")
    else:
        steps_failed.append("1. Instalación de dependencias")
        return
    
    # Paso 2: Instalar pre-commit hooks
    if run_command(
        ["pre-commit", "install"],
        "Instalando pre-commit hooks"
    ):
        steps_completed.append("2. Pre-commit hooks instalados")
    else:
        steps_failed.append("2. Instalación de pre-commit hooks")
    
    # Paso 3: Ejecutar primer test
    print("\nEjecutando verificación de herramientas...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         str(root_path / "tests" / "linting" / "test_linting.py::TestPylintSyntax::test_pylint_installed"),
         "-v"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("OK - Verificación de herramientas")
        steps_completed.append("3. Verificación de herramientas")
    else:
        print("Advertencia - Verificación incompleta")
        steps_failed.append("3. Verificación de herramientas")
    
    # Resumen
    print("\n" + "=" * 60)
    print("Resumen del Setup")
    print("=" * 60)
    
    for step in steps_completed:
        print(f"OK - {step}")
    
    for step in steps_failed:
        print(f"ERROR - {step}")
    
    if not steps_failed:
        print("\n" + "=" * 60)
        print("Setup completado exitosamente")
        print("=" * 60)
        print("\nProximos pasos:")
        print("  1. Documentación: cat tests/LINTING.md")
        print("  2. Test manual: python tests/linting/run_pylint.py --verbose")
        print("  3. O con pytest: pytest tests/linting/test_linting.py -v")
        print("\nLos cambios se verificarán automáticamente al hacer commit.\n")
        return 0
    else:
        print("\nAlgunos pasos fallaron. Por favor resuelve los errores e intenta de nuevo.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
