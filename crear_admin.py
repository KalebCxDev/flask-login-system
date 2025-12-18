#!/usr/bin/env python3
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Usuario
from werkzeug.security import generate_password_hash

def crear_admin():
    with app.app_context():
        print("\n" + "="*50)
        print("CREACIÓN DE USUARIO ADMINISTRADOR")
        print("="*50)

        email = input("Correo electrónico del administrador: ").strip().lower()
        if Usuario.query.filter_by(email=email).first():
            print(f" El correo {email} ya está registrado")
            return
        
        password = input("Contraseña: ").strip()
        confirm_password = input("Confirmar contraseña: ").strip()
        
        if password != confirm_password:
            print("Las contraseñas no coinciden")
            return
        
        if len(password) < 6:
            print("La contraseña debe tener al menos 6 caracteres")
            return
        try:
            admin = Usuario(
                email=email,
                password_hash=generate_password_hash(password),
                tipo='admin',
                verificado=True
            )
            
            db.session.add(admin)
            db.session.commit()
            
            print("\n Usuario administrador creado exitosamente")
            print(f"   Email: {email}")
            print(f"   Tipo: Administrador")
            print(f"   ID: {admin.id}")
            print("\n  Guarda estas credenciales en un lugar seguro")
            
        except Exception as e:
            db.session.rollback()
            print(f" error al crear administrador: {str(e)}")
if __name__ == '__main__':
    crear_admin()