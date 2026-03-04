class ActivoResponse:
    def __init__(self, ticker: str, nombre_completo: str, estabilidad: str, tamano: str):
        self.ticker = ticker
        self.nombre_completo = nombre_completo
        self.estabilidad = estabilidad
        self.tamano = tamano

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "nombre_completo": self.nombre_completo,
            "estabilidad": self.estabilidad,
            "tamano": self.tamano
        }
