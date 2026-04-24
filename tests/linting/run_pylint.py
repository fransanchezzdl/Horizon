#!/usr/bin/env python3
"""
Ejecución de pylint sobre directorios específicos del backend.

Verifica: daos, dtos, main.py, services, exceptions

Uso:
    python tests/linting/run_pylint.py              Análisis básico
    python tests/linting/run_pylint.py --verbose    Con detalles
    python tests/linting/run_pylint.py --reports    Genera reportes JSON
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
import argparse
import subprocess


class LintingRunner:
    """Ejecutor de linting para el backend."""

    def __init__(self, backend_path: Path = None):
        """Inicializa el runner."""
        self.backend_path = backend_path or Path(__file__).parent.parent.parent / "backend"
        self.root_path = Path(__file__).parent.parent.parent
        self.pylintrc_path = self.root_path / ".pylintrc"
        self.runner_script = self.root_path / "scripts" / "run_tool_with_fallback.py"
        
        # Directorios a verificar
        self.check_paths = [
            self.backend_path / "daos",
            self.backend_path / "dtos",
            self.backend_path / "services",
            self.backend_path / "exceptions",
            self.backend_path / "main.py",
        ]
        
    def run_pylint(self, verbose: bool = False) -> Dict[str, Any]:
        """Ejecuta pylint sobre directorios específicos.
        
        Args:
            verbose: Si True, muestra salida detallada
            
        Returns:
            Diccionario con resultados del linting
        """
        # Validar que existan las rutas
        existing_paths = []
        for path in self.check_paths:
            if path.exists():
                existing_paths.append(str(path))
        
        if not existing_paths:
            print(f"Error: No se encontraron directorios en: {self.backend_path}")
            return {"error": "No paths found", "code": 1}
        
        cmd = [
            sys.executable,
            str(self.runner_script),
            "pylint",
            *existing_paths,
            f"--rcfile={self.pylintrc_path}",
            "--output-format=json",
        ]
        
        try:
            print("Iniciando linting con animacion de carga...")
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=None,
                text=True,
                cwd=self.root_path
            )
            
            output = result.stdout or ""
            
            if output.strip():
                try:
                    messages = json.loads(output)
                except json.JSONDecodeError:
                    messages = []
            else:
                messages = []
            
            if verbose:
                print("\nLinting completado")
                print(f"Total de problemas: {len(messages)}")
                print(f"Directorios verificados: daos, dtos, services, exceptions, main.py")
                
                by_type = {}
                for msg in messages:
                    msg_type = msg.get("type", "unknown")
                    by_type[msg_type] = by_type.get(msg_type, 0) + 1
                
                if by_type:
                    print("\nResumen por tipo:")
                    for msg_type, count in sorted(by_type.items()):
                        print(f"  {msg_type}: {count}")
                        
                if messages:
                    print("\nPrimeros 10 problemas:")
                    for i, msg in enumerate(messages[:10], 1):
                        print(f"  {i}. [{msg.get('type')}] {msg.get('path')}: "
                              f"línea {msg.get('line')} - {msg.get('message')}")
            
            return {
                "success": True,
                "total_issues": len(messages),
                "messages": messages,
                "code": 0
            }
            
        except Exception as e:
            print(f"Error ejecutando pylint: {e}")
            return {"error": str(e), "code": 1}
    
    def save_report(self, results: Dict[str, Any], filename: str = "pylint_report.json"):
        """Guarda los resultados en un archivo JSON.
        
        Args:
            results: Resultados del linting
            filename: Nombre del archivo de salida
        """
        report_path = self.root_path / "tests" / "linting" / filename
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        
        print(f"Reporte guardado en: {report_path}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Ejecutor de linting para directorios específicos del backend"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar salida detallada"
    )
    parser.add_argument(
        "--reports", "-r",
        action="store_true",
        help="Guardar reporte JSON"
    )
    
    args = parser.parse_args()
    
    runner = LintingRunner()
    results = runner.run_pylint(verbose=args.verbose)
    
    if args.reports:
        runner.save_report(results)
    
    sys.exit(results.get("code", 0))


if __name__ == "__main__":
    main()
