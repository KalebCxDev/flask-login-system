import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import tempfile
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

def upload_to_cloudinary(file_obj, folder="postulantes"):
    """Sube archivo a Cloudinary y devuelve URL segura"""
    try:
        temp_path = os.path.join(tempfile.gettempdir(), f"{datetime.now().timestamp()}_{file_obj.filename}")
        file_obj.save(temp_path)
        result = cloudinary.uploader.upload(
            temp_path,
            folder=folder,
            resource_type="auto",
            use_filename=True,
            unique_filename=True,
            overwrite=False,
            quality="auto:good",
            fetch_format="auto"
        )
        os.remove(temp_path)
        
        return {
            'success': True,
            'public_id': result['public_id'],
            'secure_url': result['secure_url'],
            'format': result['format'],
            'bytes': result['bytes']
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def delete_from_cloudinary(public_id):
    """Elimina archivo de Cloudinary"""
    try:
        result = cloudinary.uploader.destroy(public_id)
        return {'success': True, 'result': result}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_secure_url(public_id, **options):
    """Genera URL segura con opciones de transformación"""
    return cloudinary.utils.cloudinary_url(
        public_id,
        **options
    )[0]

def get_optimized_url(public_id, width=800, quality=80):
    """Devuelve URL optimizada (más rápida, menos datos)"""
    return cloudinary.utils.cloudinary_url(
        public_id,
        width=width,
        quality=quality,
        fetch_format="auto"
    )[0]