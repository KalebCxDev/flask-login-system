import cloudinary
import cloudinary.uploader
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

def subir_archivo(archivo, carpeta="postulantes", tipo_recurso="auto"):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=archivo.filename) as tmp:
            ruta_temp = tmp.name
            archivo.save(ruta_temp)
        resultado = cloudinary.uploader.upload(
            ruta_temp,
            folder=carpeta,
            resource_type=tipo_recurso
        )
        os.remove(ruta_temp)
        return {
            'success': True,
            'public_id': resultado['public_id'],
            'secure_url': resultado['secure_url'],
            'format': resultado['format'],
            'bytes': resultado['bytes']
        }
    except Exception as error:
        return {'success': False, 'error': str(error)}

def eliminar_archivo(id_publico):
    try:
        cloudinary.uploader.destroy(id_publico)
        return {'success': True}
    except Exception as error:
        return {'success': False, 'error': str(error)}