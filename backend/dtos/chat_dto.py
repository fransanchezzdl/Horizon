from pydantic import BaseModel


# DTO para recibir un mensaje del chatbot desde el frontend
class ChatMessageRequest(BaseModel):
    id_usuario: str
    message: str


# DTO para la respuesta del modelo IA
class ChatMessageResponse(BaseModel):
    usuario_mensaje: str
    respuesta_ia: str
