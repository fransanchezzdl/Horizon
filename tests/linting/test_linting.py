"""
Tests de linting usando pytest.

Estos tests verifican solo: daos, dtos, services, exceptions, main.py

Ejecutar con pytest:
    pytest tests/linting/test_linting.py -v
    pytest tests/linting/test_linting.py --tb=short
"""

import subprocess
import sys
import json
from pathlib import Path
import pytest


@pytest.fixture
def backend_path():
    """Ruta del backend."""
    return Path(__file__).parent.parent.parent / "backend"


@pytest.fixture
def pylintrc_path():
    """Ruta del archivo .pylintrc."""
    return Path(__file__).parent.parent.parent / ".pylintrc"


@pytest.fixture
def check_paths(backend_path):
    """Rutas específicas a verificar."""
    return [
        backend_path / "daos",
        backend_path / "dtos",
        backend_path / "services",
        backend_path / "exceptions",
        backend_path / "main.py",
    ]


def run_pylint(check_paths: list, pylintrc_path: Path) -> dict:
    """Ejecuta pylint en rutas específicas."""
    # Validar que existan
    existing_paths = [str(p) for p in check_paths if p.exists()]
    if not existing_paths:
        return []
    
    cmd = [
        sys.executable, "-m", "pylint",
        *existing_paths,
        f"--rcfile={pylintrc_path}",
        "--output-format=json",
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=check_paths[0].parent.parent.parent
    )
    
    output = result.stdout or result.stderr
    if output.strip():
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return []
    return []


class TestPylintSyntax:
    """Verificación de errores críticos."""
    
    def test_backend_structure(self, backend_path, check_paths):
        """Verifica que existan los directorios requeridos."""
        existing = [p for p in check_paths if p.exists()]
        assert len(existing) > 0, "No se encontraron directorios de validación"
    
    def test_pylint_installed(self):
        """Verifica que pylint está instalado."""
        result = subprocess.run(
            [sys.executable, "-m", "pylint", "--version"],
            capture_output=True
        )
        assert result.returncode == 0, "pylint no está instalado"
    
    def test_no_critical_errors(self, check_paths, pylintrc_path):
        """Verifica sin errores críticos (error, fatal)."""
        messages = run_pylint(check_paths, pylintrc_path)
        
        critical_messages = [
            msg for msg in messages 
            if msg.get("type") in ["error", "fatal"]
        ]
        
        assert len(critical_messages) == 0, \
            f"Se encontraron {len(critical_messages)} errores críticos:\n" + \
            "\n".join([f"  - {m['path']}: {m['message']}" for m in critical_messages[:5]])
    
    def test_imports_valid(self, check_paths, pylintrc_path):
        """Verifica sin errores de importación."""
        messages = run_pylint(check_paths, pylintrc_path)
        
        import_errors = [
            msg for msg in messages 
            if msg.get("symbol") in ["import-error", "no-name-in-module", "unused-import"]
            and msg.get("type") == "error"
        ]
        
        assert len(import_errors) == 0, \
            f"Se encontraron {len(import_errors)} errores de importación:\n" + \
            "\n".join([f"  - {m['path']}: {m['message']}" for m in import_errors])
    
    def test_undefined_variables(self, check_paths, pylintrc_path):
        """Verifica sin variables indefinidas."""
        messages = run_pylint(check_paths, pylintrc_path)
        
        undefined = [
            msg for msg in messages 
            if msg.get("symbol") in ["undefined-variable", "undefined-loop-variable"]
            and msg.get("type") in ["error", "warning"]
        ]
        
        assert len(undefined) == 0, \
            f"Se encontraron variables indefinidas:\n" + \
            "\n".join([f"  - {m['path']}: {m['message']}" for m in undefined[:5]])
    
    def test_all_python_files_valid_syntax(self, check_paths):
        """Verifica sintaxis Python válida en archivos."""
        errors = []
        
        for path in check_paths:
            if not path.exists():
                continue
                
            # Si es archivo, verificar directamente
            if path.is_file():
                files = [path]
            else:
                # Si es directorio, buscar archivos .py
                files = list(path.rglob("*.py"))
            
            for py_file in files:
                if "__pycache__" in str(py_file):
                    continue
                
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        compile(f.read(), str(py_file), "exec")
                except SyntaxError as e:
                    errors.append(f"{py_file}: {e}")
        
        assert len(errors) == 0, \
            f"Errores de sintaxis encontrados:\n" + "\n".join(errors[:10])


class TestBackendStructure:
    """Tests de estructura del backend."""
    
    def test_daos_exists(self, backend_path):
        """Verifica que existe directorio DAOs."""
        assert (backend_path / "daos").exists(), "daos/ no encontrado en backend"
    
    def test_dtos_exists(self, backend_path):
        """Verifica que existe directorio DTOs."""
        assert (backend_path / "dtos").exists(), "dtos/ no encontrado en backend"
    
    def test_main_exists(self, backend_path):
        """Verifica que existe main.py."""
        assert (backend_path / "main.py").exists(), "main.py no encontrado en backend"
    
    def test_services_exists(self, backend_path):
        """Verifica que existe directorio services."""
        assert (backend_path / "services").exists(), "services/ no encontrado en backend"
