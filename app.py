from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Usuario, Postulante, Archivo
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'mi-clave-secreta'

# Configuración básica
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CARPETA_ARCHIVOS = 'uploads'

db.init_app(app)
os.makedirs(CARPETA_ARCHIVOS, exist_ok=True)

# ===== FUNCIONES AUXILIARES =====
def archivo_valido(nombre):
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in {'pdf', 'png', 'jpg', 'jpeg'}

def usuario_autenticado():
    return 'user_id' in session

# ===== RUTAS PÚBLICAS =====
@app.route('/')
def index():
    return render_template('register.html')

@app.route('/postular', methods=['POST'])
def postular():
    # Datos básicos
    nombres = request.form['nombres']
    apellidos = request.form['apellidos']
    fecha_nac = request.form['fecha_nacimiento']
    correo = request.form['correo']
    dni = request.form['dni']
    password = request.form['password']
    
    # Validaciones básicas
    if Usuario.query.filter_by(email=correo).first():
        flash('Correo ya registrado', 'error')
        return redirect(url_for('index'))
    
    # Crear usuario
    nuevo_usuario = Usuario(
        email=correo,
        password_hash=generate_password_hash(password)
    )
    db.session.add(nuevo_usuario)
    db.session.flush()
    
    # Crear postulante
    nuevo_postulante = Postulante(
        usuario_id=nuevo_usuario.id,
        nombres=nombres,
        apellidos=apellidos,
        fecha_nacimiento=datetime.strptime(fecha_nac, '%Y-%m-%d').date(),
        dni=dni,
        estado='pendiente'
    )
    db.session.add(nuevo_postulante)
    
    # Subir archivo si existe
    archivo = request.files.get('archivo_de_identidad')
    if archivo and archivo_valido(archivo.filename):
        nombre_unico = f"{correo}_{archivo.filename}"
        ruta = os.path.join(CARPETA_ARCHIVOS, nombre_unico)
        archivo.save(ruta)
        
        nuevo_archivo = Archivo(
            usuario_id=nuevo_usuario.id,
            nombre_original=archivo.filename,
            nombre_guardado=nombre_unico,
            ruta=ruta
        )
        db.session.add(nuevo_archivo)
    
    db.session.commit()
    flash('Registro exitoso', 'success')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        
        usuario = Usuario.query.filter_by(email=correo).first()
        
        if usuario and check_password_hash(usuario.password_hash, password):
            session['user_id'] = usuario.id
            flash('Bienvenido', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== RUTAS PRIVADAS =====
@app.route('/dashboard')
def dashboard():
    if not usuario_autenticado():
        return redirect(url_for('login'))
    
    postulante = Postulante.query.filter_by(usuario_id=session['user_id']).first()
    estado = postulante.estado if postulante else 'pendiente'
    
    return render_template('dashboard.html', estado=estado)

@app.route('/perfil')
def perfil():
    if not usuario_autenticado():
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get(session['user_id'])
    postulante = Postulante.query.filter_by(usuario_id=session['user_id']).first()
    
    return render_template('profile.html', usuario=usuario, postulante=postulante)

@app.route('/mis_archivos')
def mis_archivos():
    if not usuario_autenticado():
        return redirect(url_for('login'))
    
    archivos = Archivo.query.filter_by(usuario_id=session['user_id']).all()
    return render_template('files.html', archivos=archivos)

@app.route('/subir_archivo', methods=['POST'])
def subir_archivo():
    if not usuario_autenticado():
        return redirect(url_for('login'))
    
    archivo = request.files['archivo']
    if archivo and archivo_valido(archivo.filename):
        nombre_unico = f"{session['user_id']}_{archivo.filename}"
        ruta = os.path.join(CARPETA_ARCHIVOS, nombre_unico)
        archivo.save(ruta)
        
        nuevo_archivo = Archivo(
            usuario_id=session['user_id'],
            nombre_original=archivo.filename,
            nombre_guardado=nombre_unico,
            ruta=ruta
        )
        db.session.add(nuevo_archivo)
        db.session.commit()
        flash('Archivo subido', 'success')
    
    return redirect(url_for('mis_archivos'))

# Crear tablas al inicio
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)