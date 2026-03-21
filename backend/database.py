import os
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Optional


# Primero intentamos cargar el .env que está junto a este archivo (backend/.env)
base_dir = os.path.dirname(__file__)
local_env = os.path.join(base_dir, ".env")
load_dotenv(local_env)
# Si no existe, intentar cargar un .env en el cwd por compatibilidad
load_dotenv()


def _get_env_var(*names: str) -> Optional[str]:
    """Busca la primera variable de entorno disponible en `names` y la devuelve."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None

url: Optional[str] = _get_env_var("SUPABASE_URL")
key: Optional[str] = _get_env_var("SUPABASE_KEY", "SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError(
        "Faltan las credenciales de Supabase en las variables de entorno.\n"
        "Define SUPABASE_URL y SUPABASE_KEY (o SUPABASE_ANON_KEY) en un .env"
    )


# Inicializar cliente de Supabase (reutilizable en todo el backend)
supabase: Client = create_client(url, key)


def get_supabase() -> Client:
    """Helper para obtener el cliente (útil para tests o reinicios)."""
    return supabase