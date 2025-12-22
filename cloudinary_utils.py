# -- configuracion de Cloudinary -- #
# 01: imports y configuracion del servicio
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import tempfile
from datetime import datetime
from dotenv import load_dotenv  # para cargar variables de entorno

load_dotenv()  # carga las variables del archivo .env

# configura cloudinary con las credenciales
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True  # usa https
)

# -- funciones para manejo de archivos en cloudinary -- #
# 01: sube un archivo a cloudinary
def upload_to_cloudinary(file_obj, folder="postulantes", resource_type="auto"):
    try:
        # crea un archivo temporal para subir
        temp_path = os.path.join(
            tempfile.gettempdir(),
            f"{datetime.now().timestamp()}_{file_obj.filename}"  # nombre unico con timestamp
        )
        file_obj.save(temp_path)  # guarda el archivo en disco temporal

        # sube el archivo a cloudinary
        result = cloudinary.uploader.upload(
            temp_path,
            folder=folder,  # carpeta donde se guardara
            resource_type=resource_type,  # tipo de recurso (imagen, video, etc)
            use_filename=True,  # usa el nombre original
            unique_filename=True,  # asegura que sea unico
            overwrite=False,  # no sobreescribe
            quality="auto:good",  # calidad automatica
            fetch_format="auto"  # formato optimo
        )

        os.remove(temp_path)  # elimina el archivo temporal

        # retorna los datos importantes
        return {
            'success': True,
            'public_id': result['public_id'],  # identificador unico en cloudinary
            'secure_url': result['secure_url'],  # url para acceder al archivo
            'format': result['format'],  # formato del archivo
            'bytes': result['bytes'],  # tamaño en bytes
            'resource_type': result['resource_type']  # tipo de recurso
        }

    except Exception as e:
        # si hay error, retorna falso con el mensaje
        return {'success': False, 'error': str(e)}

# 02: elimina archivo de cloudinary
def delete_from_cloudinary(public_id):
    """Elimina archivo de Cloudinary"""
    try:
        result = cloudinary.uploader.destroy(public_id)  # elimina usando public_id
        return {'success': True, 'result': result}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# 03: genera url segura con opciones
def get_secure_url(public_id, **options):
    """Genera URL segura con opciones de transformación"""
    return cloudinary.utils.cloudinary_url(
        public_id,
        **options  # opciones adicionales como width, height, etc
    )[0]

# 04: url optimizada para carga rapida
def get_optimized_url(public_id, width=800, quality=80):
    """Devuelve URL optimizada (más rápida, menos datos)"""
    return cloudinary.utils.cloudinary_url(
        public_id,
        width=width,  # ancho maximo
        quality=quality,  # calidad de compresion
        fetch_format="auto"  # formato automatico
    )[0]