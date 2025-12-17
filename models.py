from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), default='postulante')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    postulante = db.relationship('Postulante', backref='usuario', uselist=False)
    archivos = db.relationship('Archivo', backref='usuario')

class Postulante(db.Model):
    __tablename__ = 'postulantes'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    dni = db.Column(db.String(20))
    estado = db.Column(db.String(20), default='registrado')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

class Archivo(db.Model):
    __tablename__ = 'archivos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nombre_original = db.Column(db.String(255), nullable=False)
    nombre_guardado = db.Column(db.String(255), nullable=False)
    extension = db.Column(db.String(10), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    ruta = db.Column(db.String(255), nullable=False)
    tamano = db.Column(db.Integer, nullable=False)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)