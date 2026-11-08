import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def subir_imagen(file_path, folder="olympo/projects"):
    """
    Sube una imagen a Cloudinary y devuelve la URL segura.
    :param file_path: Ruta del archivo local o stream de datos.
    :param folder: Carpeta donde se guardará en Cloudinary.
    :return: URL segura de la imagen.
    """
    try:
        upload_result = cloudinary.uploader.upload(file_path, folder=folder)
        return upload_result.get("secure_url")
    except Exception as e:
        print(f"Error al subir imagen a Cloudinary: {e}")
        return None

def eliminar_imagen(public_id):
    """
    Elimina una imagen de Cloudinary.
    :param public_id: El ID público de la imagen (ej: 'olympo/projects/imagen_name').
    """
    try:
        cloudinary.uploader.destroy(public_id)
        return True
    except Exception as e:
        print(f"Error al eliminar imagen de Cloudinary: {e}")
        return False
