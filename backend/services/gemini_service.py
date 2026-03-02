"""Servicio para interactuar con la API de Google Gemini."""

import os
from dotenv import load_dotenv
from google.genai import Client


# Primero intentamos cargar el .env que está junto a database.py (backend/.env)
base_dir = os.path.dirname(os.path.dirname(__file__))  # Subimos desde services/ a backend/
local_env = os.path.join(base_dir, ".env")
load_dotenv(local_env)
# Si no existe, intentar cargar un .env en el cwd por compatibilidad
load_dotenv()


class GeminiService:
    def __init__(self):
        """Inicializa el servicio de Gemini con la API key del .env"""
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY no está configurada en las variables de entorno. "
                "Asegúrate de incluirla en tu archivo backend/.env"
            )
        
        self.client = Client(api_key=api_key)

    def generar_respuesta(self, id_usuario: str, mensaje: str) -> str:
        """
        Genera una respuesta usando la API de Google Gemini.
        
        Args:
            id_usuario: ID del usuario (usado para RLS en Supabase más adelante)
            mensaje: Mensaje del usuario a procesar
            
        Returns:
            str: Respuesta generada por Gemini
            
        Raises:
            Exception: Si hay error al conectar con Gemini
        """
        try:
            # Puedes agregar contexto del usuario aquí si es necesario
            # por ejemplo, obtener su información de perfil para personalizar respuestas
            
            prompt = f"""Eres un asesor financiero experto llamado 'Asesor Horizon'.
Tu responsabilidad es ayudar a usuarios con preguntas sobre finanzas, inversión y gestión de portafolios.

Usuario ID: {id_usuario}
Pregunta: {mensaje}

Proporciona una respuesta útil, clara y concisa. Si la pregunta no está relacionada con finanzas, 
sugiere amablemente que te enfocas en temas financieros."""
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            return response.text if response.text else "No se pudo generar una respuesta."
            
        except Exception as e:
            raise Exception(f"Error al generar respuesta con Gemini: {str(e)}")


# Instancia global del servicio
gemini_service = GeminiService()
