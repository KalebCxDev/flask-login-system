import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from models import Usuario
from werkzeug.security import generate_password_hash

def crear_admin():
    with app.app_context():
        print("\n" + "=" * 50)
        print("CREAR USUARIO ADMINISTRADOR")
        print("=" * 50)
        correo = input("Correo electrónico: ").strip().lower()
        if Usuario.query.filter_by(email=correo).first():
            print(f" El correo {correo} ya existe")
            return
        contrasena = input("Contraseña: ").strip()
        confirmar = input("Confirmar contraseña: ").strip()
        if contrasena != confirmar:
            print(" Las contraseñas no coinciden")
            return
        if len(contrasena) < 6:
            print(" La contraseña debe tener al menos 6 caracteres")
            return
        try:
            administrador = Usuario(
                email=correo,
                password_hash=generate_password_hash(contrasena),
                tipo='admin',
                verificado=True
            )
            db.session.add(administrador)
            db.session.commit()
            print("\n ✓ Administrador creado exitosamente")
            print(f"   Correo: {correo}")
            print(f"   Tipo: Administrador")
            print(f"   ID: {administrador.id}")
            print("\n   Guarda estas credenciales")
        except Exception as error:
            db.session.rollback()
            print(f" ✗ Error: {error}")

if __name__ == '__main__':
    crear_admin()