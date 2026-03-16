"""
Script de diagnóstico para verificar la conexión con Alpha Vantage MCP.
"""

import subprocess
import json
import sys

def test_uv_installed():
    """Verifica que uv esté instalado."""
    print("1. Verificando instalación de uv...")
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"   ✅ uv instalado: {result.stdout.strip()}")
            return True
        else:
            print(f"   ❌ Error ejecutando uv: {result.stderr}")
            return False
    except FileNotFoundError:
        print("   ❌ uv no está instalado")
        print("   Instala con: powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_av_mcp_package():
    """Verifica que el paquete av-mcp esté disponible."""
    print("\n2. Verificando paquete av-mcp...")
    try:
        result = subprocess.run(
            ["uvx", "av-mcp", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and "Alpha Vantage MCP Server" in result.stdout:
            print("   ✅ Paquete av-mcp disponible")
            return True
        else:
            print(f"   ❌ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_mcp_server_response():
    """Verifica que el servidor MCP responda correctamente."""
    print("\n3. Verificando respuesta del servidor MCP...")
    
    # Leer API key del archivo de configuración
    try:
        with open(".kiro/settings/mcp.json", "r") as f:
            config = json.load(f)
            api_key = config["mcpServers"]["alphavantage"]["args"][1]
            print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")
    except Exception as e:
        print(f"   ❌ Error leyendo configuración: {e}")
        return False
    
    # Probar inicialización del servidor
    try:
        init_message = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        })
        
        result = subprocess.run(
            ["uvx", "av-mcp", api_key],
            input=init_message,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if "result" in response and "serverInfo" in response["result"]:
                    server_name = response["result"]["serverInfo"]["name"]
                    server_version = response["result"]["serverInfo"]["version"]
                    print(f"   ✅ Servidor respondió: {server_name} v{server_version}")
                    return True
                else:
                    print(f"   ❌ Respuesta inesperada: {result.stdout}")
                    return False
            except json.JSONDecodeError:
                print(f"   ❌ Respuesta no es JSON válido: {result.stdout}")
                return False
        else:
            print(f"   ❌ Error del servidor: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("   ❌ Timeout esperando respuesta del servidor")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_api_key_validity():
    """Verifica que la API key sea válida haciendo una llamada real."""
    print("\n4. Verificando validez de la API key...")
    
    try:
        with open(".kiro/settings/mcp.json", "r") as f:
            config = json.load(f)
            api_key = config["mcpServers"]["alphavantage"]["args"][1]
    except Exception as e:
        print(f"   ❌ Error leyendo configuración: {e}")
        return False
    
    # Hacer una llamada de prueba a la API de Alpha Vantage directamente
    try:
        import requests
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "Global Quote" in data:
                print("   ✅ API key válida - respuesta exitosa de Alpha Vantage")
                return True
            elif "Error Message" in data:
                print(f"   ❌ Error de API: {data['Error Message']}")
                return False
            elif "Note" in data:
                print(f"   ⚠️  Límite de API alcanzado: {data['Note']}")
                print("   La API key es válida pero has alcanzado el límite de llamadas")
                return True
            else:
                print(f"   ⚠️  Respuesta inesperada: {data}")
                return False
        else:
            print(f"   ❌ Error HTTP {response.status_code}")
            return False
            
    except ImportError:
        print("   ⚠️  requests no instalado, saltando verificación de API")
        print("   Instala con: pip install requests")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_kiro_config():
    """Verifica la configuración de Kiro."""
    print("\n5. Verificando configuración de Kiro...")
    
    try:
        with open(".kiro/settings/mcp.json", "r") as f:
            config = json.load(f)
            
        # Verificar estructura
        if "mcpServers" not in config:
            print("   ❌ Falta 'mcpServers' en la configuración")
            return False
            
        if "alphavantage" not in config["mcpServers"]:
            print("   ❌ Falta 'alphavantage' en mcpServers")
            return False
            
        av_config = config["mcpServers"]["alphavantage"]
        
        # Verificar campos requeridos
        if av_config.get("command") != "uvx":
            print(f"   ❌ Command incorrecto: {av_config.get('command')}")
            return False
            
        if not isinstance(av_config.get("args"), list) or len(av_config["args"]) != 2:
            print(f"   ❌ Args incorrectos: {av_config.get('args')}")
            return False
            
        if av_config["args"][0] != "av-mcp":
            print(f"   ❌ Primer arg debe ser 'av-mcp': {av_config['args'][0]}")
            return False
            
        print("   ✅ Configuración de Kiro correcta")
        print(f"   Command: {av_config['command']}")
        print(f"   Args: {av_config['args']}")
        print(f"   Disabled: {av_config.get('disabled', False)}")
        
        return True
        
    except FileNotFoundError:
        print("   ❌ Archivo .kiro/settings/mcp.json no encontrado")
        return False
    except json.JSONDecodeError as e:
        print(f"   ❌ Error parseando JSON: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Ejecuta todos los tests de diagnóstico."""
    print("=" * 60)
    print("DIAGNÓSTICO DE CONEXIÓN ALPHA VANTAGE MCP")
    print("=" * 60)
    
    results = []
    
    # Test 1: uv instalado
    results.append(("uv instalado", test_uv_installed()))
    
    # Test 2: av-mcp disponible
    if results[0][1]:
        results.append(("av-mcp disponible", test_av_mcp_package()))
    else:
        print("\n⏭️  Saltando tests restantes (uv no instalado)")
        return False
    
    # Test 3: Servidor MCP responde
    if results[1][1]:
        results.append(("Servidor MCP responde", test_mcp_server_response()))
    else:
        print("\n⏭️  Saltando tests restantes (av-mcp no disponible)")
        return False
    
    # Test 4: API key válida
    api_result = test_api_key_validity()
    if api_result is not None:
        results.append(("API key válida", api_result))
    
    # Test 5: Configuración de Kiro
    results.append(("Configuración Kiro", check_kiro_config()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ Todos los tests pasaron!")
        print("\nPróximos pasos:")
        print("1. Reinicia Kiro completamente")
        print("2. Verifica en el panel de MCP que el servidor esté conectado")
        print("3. Si sigue sin funcionar, revisa los logs de MCP en Kiro")
    else:
        print("\n❌ Algunos tests fallaron")
        print("\nAcciones recomendadas:")
        print("1. Revisa los errores arriba")
        print("2. Asegúrate de tener uv instalado")
        print("3. Verifica que tu API key sea correcta")
        print("4. Reinicia Kiro después de corregir los problemas")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
