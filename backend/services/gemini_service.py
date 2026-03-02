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
            # No lanzar error aquí, dejar que falle cuando se intente usar
            self.client = None
            self.api_key_missing = True
        else:
            try:
                self.client = Client(api_key=api_key)
                self.api_key_missing = False
            except Exception as e:
                self.client = None
                self.api_key_missing = True
                print(f"[GEMINI] Error al inicializar cliente: {e}")

    def generar_respuesta(self, mensaje: str) -> str:
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
        # Verificar si hay API key configurada
        if self.api_key_missing or not self.client:
            raise Exception(
                "API key de Gemini no configurada. Asegúrate de incluir GEMINI_API_KEY en tu archivo backend/.env"
            )
        
        try:
            # Podemos agregar contexto del usuario aquí si es necesario
            # por ejemplo, obtener su información de perfil para personalizar respuestas
            
            prompt = f"""
Eres un asesor financiero experto llamado 'Asesor Horizon'. Te encuentras en
una aplicación llamada Horizon, en la sección de AcademIA. Esta aplicación ofrece la posibilidad
de probar portfolios ficticios, realizar predicciones con modelos de Machine Learning, y acceder
a cursos de educación financiera básica, para personas que quieran iniciarse en el mundo de las
inversiones.

Tu responsabilidad es ayudar a usuarios con preguntas sobre finanzas, inversión y gestión de portfolios.

Pregunta: {mensaje}

Proporciona una respuesta útil, clara y concisa. Si la pregunta no está relacionada con la aplicación Horizon, 
sugiere amablemente que te enfocas en temas financieros y educativos.

Nunca asegures beneficios ni aconsejes inversiones reales, siempre usar la AcademIA para aprender con portfolios
ficticios. 

Si el usuario pregunta por sus datos, indícale que por seguridad, como modelo y asesor, no recibes esa información
y queda encriptada en la base de datos de la aplicación.

No te presentes en cada mensaje, el usuario ya te conoce."""
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            return response.text if response.text else "No se pudo generar una respuesta."
            
        except Exception as e:
            raise Exception(f"Error al generar respuesta con Gemini: {str(e)}")


# Instancia global del servicio
gemini_service = GeminiService()
