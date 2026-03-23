from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from supabase import Client

from ..database import get_supabase, get_supabase_admin


class StorageService:
    """Servicio para gestionar avatares privados en Supabase Storage."""

    ALLOWED_MIME_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

    def __init__(
        self,
        storage_client: Optional[Client] = None,
        public_client: Optional[Client] = None,
        bucket_name: Optional[str] = None,
    ):
        # Cliente admin para escrituras/borrados (service role)
        self.storage_client = storage_client or get_supabase_admin()
        # Cliente para generar URLs firmadas
        self.public_client = public_client or get_supabase()
        self.signing_client = self.storage_client or self.public_client
        self.bucket_name = bucket_name or os.getenv("SUPABASE_AVATARS_BUCKET", "avatars")
        self.signed_url_expires_in = int(os.getenv("SUPABASE_AVATAR_SIGNED_URL_TTL", "3600"))

    def upload_avatar(self, user_id: str, file: UploadFile) -> str:
        content_type = (file.content_type or "").lower().strip()
        ext = self.ALLOWED_MIME_TYPES.get(content_type)
        if not ext:
            raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

        if not self.storage_client:
            raise HTTPException(status_code=500, detail="Falta SUPABASE_SERVICE_ROLE_KEY para subir avatares privados")

        file_bytes = file.file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Archivo vacío")
        if len(file_bytes) > self.MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="La imagen no debe superar 5MB")
        if not self._matches_magic_bytes(content_type, file_bytes):
            raise HTTPException(status_code=400, detail="Contenido de archivo inválido para el tipo de imagen")

        object_path = f"{user_id}/{uuid4().hex}{ext}"

        try:
            self.storage_client.storage.from_(self.bucket_name).upload(
                object_path,
                file_bytes,
                {
                    "content-type": content_type,
                    "upsert": "false",
                },
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error subiendo avatar: {str(e)}")

        # Se guarda el path interno. La URL para frontend se firma al responder.
        return object_path

    def delete_avatar(self, user_id: str, avatar_ref: str) -> None:
        if not avatar_ref:
            return

        if not self.storage_client:
            raise HTTPException(status_code=500, detail="Falta SUPABASE_SERVICE_ROLE_KEY para eliminar avatares privados")

        object_path = self._extract_object_path(avatar_ref)
        if not object_path:
            return

        # Si no pertenece al usuario (p.ej. avatar default compartido), no se borra.
        if not object_path.startswith(f"{user_id}/"):
            return

        try:
            self.storage_client.storage.from_(self.bucket_name).remove([object_path])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error eliminando avatar: {str(e)}")

    def is_managed_avatar(self, avatar_ref: str | None) -> bool:
        """Indica si la referencia pertenece al bucket privado gestionado (path interno)."""
        if not avatar_ref:
            return False
        if avatar_ref.startswith("data:"):
            return False
        if self._is_http_url(avatar_ref):
            return bool(self._extract_object_path(avatar_ref))
        return bool(self._extract_object_path(avatar_ref))

    def resolve_avatar_for_client(self, avatar_ref: str | None) -> str | None:
        """
        Convierte la referencia guardada a URL usable por frontend.
        - Si es URL http(s), se devuelve tal cual (caso defaults públicos).
        - Si es path interno del bucket privado, devuelve URL firmada.
        """
        if not avatar_ref:
            return None

        # Compatibilidad hacia atrás: si existe un base64 heredado, no romper login/auth.
        if avatar_ref.startswith("data:"):
            return None

        if self._is_http_url(avatar_ref):
            return avatar_ref

        object_path = self._extract_object_path(avatar_ref)
        if not object_path:
            return None

        try:
            signed = self.signing_client.storage.from_(self.bucket_name).create_signed_url(
                object_path,
                self.signed_url_expires_in,
            )
            if isinstance(signed, dict):
                return signed.get("signedURL") or signed.get("signedUrl") or signed.get("signed_url")
            return str(signed)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"No se pudo generar signed URL: {str(e)}")

    def hydrate_user_avatar(self, user):
        """Muta el objeto usuario para exponer URL de avatar resoluble por frontend."""
        if not user:
            return user
        current = getattr(user, "foto_perfil", None)
        setattr(user, "foto_perfil", self.resolve_avatar_for_client(current))
        return user

    def hydrate_user_avatar_safe(self, user, log_prefix: str = "[STORAGE]"):
        """Versión tolerante a fallos: no rompe el flujo si falla la firma del avatar."""
        if not user:
            return user
        try:
            return self.hydrate_user_avatar(user)
        except Exception as e:
            print(f"{log_prefix} Warning avatar hydrate failed: {str(e)}")
            setattr(user, "foto_perfil", None)
            return user

    def _extract_object_path(self, avatar_ref: str) -> str:
        """
        Extrae path interno del objeto.
        Soporta:
        - path interno guardado en BD: {user_id}/{file}
        - URL pública: /storage/v1/object/public/{bucket}/{path}
        - URL firmada: /storage/v1/object/sign/{bucket}/{path}?token=...
        """
        try:
            if avatar_ref and not self._is_http_url(avatar_ref):
                path = avatar_ref.strip("/")
                return path if self._looks_like_internal_object_path(path) else ""

            parsed = urlparse(avatar_ref)
            parts = [p for p in parsed.path.split("/") if p]
            # storage/v1/object/public/{bucket}/{path...}
            if len(parts) < 6:
                return ""
            if parts[0] != "storage" or parts[1] != "v1" or parts[2] != "object":
                return ""

            mode = parts[3]
            if mode not in {"public", "sign"}:
                return ""

            bucket = parts[4]
            if bucket != self.bucket_name:
                return ""

            return "/".join(parts[5:])
        except Exception:
            return ""

    def _looks_like_internal_object_path(self, path: str) -> bool:
        if not path or path.startswith("data:"):
            return False
        chunks = [p for p in path.split("/") if p]
        if len(chunks) < 2:
            return False
        filename = chunks[-1]
        return "." in filename and not filename.endswith(".")

    def _matches_magic_bytes(self, content_type: str, file_bytes: bytes) -> bool:
        if content_type == "image/jpeg":
            return len(file_bytes) >= 3 and file_bytes[:3] == b"\xff\xd8\xff"
        if content_type == "image/png":
            return len(file_bytes) >= 8 and file_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        if content_type == "image/gif":
            return len(file_bytes) >= 6 and file_bytes[:6] in (b"GIF87a", b"GIF89a")
        if content_type == "image/webp":
            return len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP"
        return False

    def _is_http_url(self, value: str) -> bool:
        return value.startswith("http://") or value.startswith("https://")


# Instancia única por proceso (app scope singleton)
storage_service = StorageService()
