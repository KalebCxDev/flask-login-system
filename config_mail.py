# -- Configuracion del sistema de correo -- #
# 01: imports y setup inicial de flask-mail
import os
from dotenv import load_dotenv  # para manejar variables de entorno
from flask_mail import Mail  # extension de flask para enviar correos

load_dotenv()  # carga las variables del archivo .env
mail = Mail()  # crea una instancia de Mail

# 02: funcion para configurar el correo en la app
def init_mail(app):
    """Configura los parametros de correo para la aplicacion flask"""
    
    # configuracion del servidor SMTP
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')  # servidor de correo (ej: smtp.gmail.com)
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))  # puerto (default 587)
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'  # usa TLS si es true
    # credenciales de autenticacion
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # usuario del correo
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # contraseña o app password
    # remitente por defecto
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    # inicializa la extension con la app
    mail.init_app(app)  # vincula mail con la aplicacion flask