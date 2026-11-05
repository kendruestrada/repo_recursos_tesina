import os
import json
import random
import urllib3
from aws_synthetics.common import synthetics_logger as logger


def handler(event, context):
    api_endpoint = os.environ.get("TEST_015_API_ENDPOINT")
    if not api_endpoint:
        raise ValueError("Falta la variable de entorno TEST_015_API_ENDPOINT")

    user_id = f"user_test_{random.randint(1000, 9999)}"
    logger.info(f"Iniciando Test 015 para usuario: {user_id}")

    http = urllib3.PoolManager()

    def make_request(method, path, body=None):
        url = f"{api_endpoint}{path}"
        headers = {"Content-Type": "application/json"}
        encoded_body = json.dumps(body) if body else None

        logger.info(f"Peticion: {method} {url}")
        response = http.request(method, url, headers=headers, body=encoded_body)

        try:
            data = json.loads(response.data.decode("utf-8"))
        except:
            data = response.data.decode("utf-8")

        logger.info(f"Estado Respuesta: {response.status}")
        return response.status, data

    # 1. Subir Foto de Perfil
    logger.info("### Paso 1: Subiendo Fotos")
    status, profile_data = make_request(
        "POST", "/photos/upload", {"user_id": user_id, "photo_type": "profile"}
    )
    if status not in [200, 201]:
        raise Exception(f"Fallo al subir foto de perfil: {profile_data}")
    profile_id = profile_data.get("photo_id") or profile_data.get("id")
    logger.info(f"Foto de perfil subida: {profile_id}")

    # 1. Subir Fotos de Galeria (3x)
    for i in range(3):
        status, _ = make_request(
            "POST",
            "/photos/upload",
            {"user_id": user_id, "photo_type": "gallery", "filename": f"img_{i}.jpg"},
        )
        if status not in [200, 201]:
            raise Exception("Fallo al subir foto de galeria")
        logger.info(f"Foto de galeria {i} subida")

    # 2. Borrar Perfil (Gatillo)
    logger.info(f"### Paso 2: Borrando foto de perfil {profile_id}")
    status, _ = make_request("DELETE", f"/photos/{profile_id}")
    if status not in [200, 204]:
        raise Exception("Fallo al borrar foto de perfil")
    logger.info("Foto de perfil borrada correctamente")

    # 3. Verificar Bug
    logger.info("### Paso 3: Verificando el Desastre (Bug)")
    status, photos = make_request("GET", f"/photos/user/{user_id}")
    photos_list = photos.get("photos", photos) if isinstance(photos, dict) else photos
    logger.info(f"Fotos encontradas en DB: {photos_list}")

    # Verificar si existe metadata de galeria pero archivo fisico falta
    gallery_photos = [p for p in photos_list if p.get("type") == "gallery"]
    if not gallery_photos:
        logger.error(
            "No se encontró metadata de galería (Bug no reproducido o diferente)"
        )
        raise Exception("Fallo: Metadata de galería eliminada")


    if photos.get("consistent") == False and len(photos.get("orphaned_metadata")) > 0:
        logger.info("Bug verificado: Metadata existe, archivo S3 falta")
        return {
            "statusCode": 200,
            "body": "Bug verificado: Metadata existe, archivo S3 falta",
        }

    raise Exception("Bug no reproducido: Las fotos aun existen")
