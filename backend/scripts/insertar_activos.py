from ..daos.activo_dao import ActivoDAO

def insertar_activos_iniciales():
    lista = [
        {"ticker": "AAPL", "nombre_completo": "Apple Inc.", "estabilidad": "Alta", "tamano": "Grande"},
        {"ticker": "MSFT", "nombre_completo": "Microsoft Corp.", "estabilidad": "Alta", "tamano": "Grande"},
        {"ticker": "TSLA", "nombre_completo": "Tesla Inc.", "estabilidad": "Media", "tamano": "Grande"},
        {"ticker": "GOOGL", "nombre_completo": "Alphabet Inc.", "estabilidad": "Alta", "tamano": "Grande"},
        {"ticker": "AMZN", "nombre_completo": "Amazon.com Inc.", "estabilidad": "Media", "tamano": "Grande"},
        {"ticker": "NVDA", "nombre_completo": "NVIDIA Corp.", "estabilidad": "Media", "tamano": "Grande"},
        {"ticker": "META", "nombre_completo": "Meta Platforms Inc.", "estabilidad": "Media", "tamano": "Grande"},
        {"ticker": "NFLX", "nombre_completo": "Netflix Inc.", "estabilidad": "Media", "tamano": "Mediana"},
        {"ticker": "BABA", "nombre_completo": "Alibaba Group", "estabilidad": "Baja", "tamano": "Grande"},
        {"ticker": "INTC", "nombre_completo": "Intel Corp.", "estabilidad": "Media", "tamano": "Grande"},
    ]
    for activo in lista:
        ActivoDAO.crear_activo(**activo)

if __name__ == "__main__":
    insertar_activos_iniciales()
    print("Activos insertados correctamente.")
