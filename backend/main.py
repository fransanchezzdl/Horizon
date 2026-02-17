import os
from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

# Inicializar cliente de Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
# supabase: Client = create_client(url, key)

@app.get("/usuarios")
def get_usuarios():
    # Ejemplo: Traer todos los datos de la tabla 'profiles'
    response = supabase.table("profiles").select("*").execute()
    return response.data

@app.post("/crear-item")
def create_item(nombre: str):
    # Ejemplo: Insertar un dato
    data, count = supabase.table("items").insert({"name": nombre}).execute()
    return {"status": "success", "data": data}