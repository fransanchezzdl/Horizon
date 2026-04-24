from pydantic import BaseModel, Field


# DTO para recibir un mensaje del chatbot desde el frontend
class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=100, description="Mensaje del usuario (máximo 100 caracteres)")


# DTO para la respuesta del modelo IA
class ChatMessageResponse(BaseModel):
    usuario_mensaje: str
    respuesta_ia: str
