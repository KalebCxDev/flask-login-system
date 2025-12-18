from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Usuario, Postulante, Archivo
from datetime import datetime
from flask_mail import Message
import random
import os
import uuid
from config_mail import init_mail, mail

app = Flask(__name__)
app.secret_key = 'mi-clave-secreta'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "instance", "app.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CARPETA_ARCHIVOS = os.path.join(BASE_DIR, 'uploads')
EXTENSIONES_PERMITIDAS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xlsx', 'txt', 'gif', 'webp'}
TAMANO_MAXIMO = 5 * 1024 * 1024
db.init_app(app)
init_mail(app)
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
os.makedirs(CARPETA_ARCHIVOS, exist_ok=True)

def archivo_valido(nombre):
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS
def validar_dni(dni):
    return len(dni) == 8 and dni.isdigit()
def usuario_autenticado():
    return 'user_id' in session
def obtener_postulante():
    return Postulante.query.filter_by(usuario_id=session['user_id']).first() if usuario_autenticado() else None
def obtener_archivo_usuario(file_id):
    return Archivo.query.filter_by(id=file_id, usuario_id=session['user_id']).first() if usuario_autenticado() else None

@app.route('/')
def index():
    return render_template('register.html')

@app.route('/postular', methods=['POST'])
def postular():
    nombres = request.form.get('nombres', '').strip()
    apellidos = request.form.get('apellidos', '').strip()
    fecha_nac = request.form.get('fecha_nacimiento')
    correo = request.form.get('correo', '').strip().lower()
    dni = request.form.get('dni', '').strip()
    password = request.form.get('password', '')
    password_confirm = request.form.get('password_confirm', '')

    if not all([nombres, apellidos, fecha_nac, correo, dni, password]):
        flash('Todos los campos son obligatorios', 'error')
        return redirect(url_for('index'))

    if password != password_confirm:
        flash('Las contraseñas no coinciden', 'error')
        return redirect(url_for('index'))

    if not validar_dni(dni):
        flash('El DNI debe tener 8 dígitos', 'error')
        return redirect(url_for('index'))

    if Usuario.query.filter_by(email=correo).first():
        flash('El correo ya está registrado', 'error')
        return redirect(url_for('index'))

    archivo = request.files.get('archivo_de_identidad')

    try:
        nuevo_usuario = Usuario(
            email=correo,
            password_hash=generate_password_hash(password),
            tipo='postulante'
        )
        db.session.add(nuevo_usuario)
        db.session.flush()

        nuevo_postulante = Postulante(
            usuario_id=nuevo_usuario.id,
            nombres=nombres,
            apellidos=apellidos,
            fecha_nacimiento=datetime.strptime(fecha_nac, '%Y-%m-%d').date(),
            dni=dni,
            estado='pendiente'
        )
        db.session.add(nuevo_postulante)

        if archivo and archivo.filename:
            if not archivo_valido(archivo.filename):
                flash('Tipo de archivo no permitido', 'error')
                return redirect(url_for('index'))

            ext = archivo.filename.rsplit('.', 1)[1].lower()
            nombre_unico = f"{uuid.uuid4()}.{ext}"
            ruta = os.path.join(CARPETA_ARCHIVOS, nombre_unico)

            archivo.save(ruta)
            tamano = os.path.getsize(ruta)

            if tamano > TAMANO_MAXIMO:
                os.remove(ruta)
                flash('El archivo supera el tamaño máximo permitido (5MB)', 'error')
                return redirect(url_for('index'))

            nuevo_archivo = Archivo(
                usuario_id=nuevo_usuario.id,
                nombre_original=archivo.filename,
                nombre_guardado=nombre_unico,
                extension=ext,
                mime_type='application/octet-stream',
                ruta=ruta,
                tamano=tamano
            )
            db.session.add(nuevo_archivo)

        codigo_verificacion = str(random.randint(100000, 999999))
        session['correo_verificar'] = correo
        session['codigo_verificacion'] = codigo_verificacion

        db.session.commit()
        try:
            msg = Message(
                subject="Verifica tu correo en Mi App",
                recipients=[correo],
                body=f"Hola {nombres}, tu código de verificación es: {codigo_verificacion}"
            )
            mail.send(msg)
        except Exception as e:
            print(f"Error enviando correo: {e}")
            flash('No se pudo enviar el correo de verificación, inténtalo más tarde', 'error')

        flash(f'Registro exitoso. Se ha enviado un código de verificación a {correo}', 'success')
        return redirect(url_for('verify'))

    except Exception as e:
        db.session.rollback()
        flash('Error en el registro', 'error')
        return redirect(url_for('index'))

@app.errorhandler(413)
def archivo_demasiado_grande(e):
    flash('El archivo supera el tamaño máximo permitido (5MB)', 'error')
    return redirect(request.referrer or url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()
        password = request.form.get('password', '')
        usuario = Usuario.query.filter_by(email=correo).first()
        if not usuario or not check_password_hash(usuario.password_hash, password):
            flash('Correo o contraseña incorrectos', 'error')
            return render_template('login.html')
        session['user_id'] = usuario.id
        session['email'] = usuario.email
        flash('Bienvenido!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo')
        codigo_esperado = session.get('codigo_verificacion')
        if codigo_ingresado == codigo_esperado:
            session.pop('correo_verificar', None)
            session.pop('codigo_verificacion', None)
            flash('Correo verificado! Ya puedes iniciar sesión', 'success')
            return redirect(url_for('login'))
        else:
            flash('Código incorrecto', 'error')

    return render_template('verify.html')
@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not usuario_autenticado():
        return redirect(url_for('login'))
    postulante = obtener_postulante()
    return render_template('dashboard.html', estado=postulante.estado if postulante else 'pendiente')

@app.route('/perfil')
def perfil():
    if not usuario_autenticado():
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['user_id'])
    postulante = obtener_postulante()
    datos = {'email': usuario.email,'nombres': postulante.nombres if postulante else '','apellidos': postulante.apellidos if postulante else '','dni': postulante.dni if postulante else ''}
    return render_template('profile.html', usuario=datos)

@app.route('/perfil/editar', methods=['POST'])
def editar_perfil():
    if not usuario_autenticado():
        return redirect(url_for('login'))
    nombres = request.form.get('nombres', '').strip()
    apellidos = request.form.get('apellidos', '').strip()
    dni = request.form.get('dni', '').strip()
    if not validar_dni(dni):
        flash('El DNI debe tener 8 dígitos', 'error')
        return redirect(url_for('perfil'))
    postulante = obtener_postulante()
    postulante.nombres = nombres
    postulante.apellidos = apellidos
    postulante.dni = dni
    db.session.commit()
    flash('Perfil actualizado', 'success')
    return redirect(url_for('perfil'))

@app.route('/mis_archivos')
def mis_archivos():
    if not usuario_autenticado():
        return redirect(url_for('login'))
    archivos = Archivo.query.filter_by(usuario_id=session['user_id']).order_by(Archivo.fecha_subida.desc()).all()
    return render_template('files.html', archivos=archivos)

@app.route('/subir_archivo', methods=['POST'])
def subir_archivo():
    if not usuario_autenticado():
        return redirect(url_for('login'))
    archivo = request.files.get('archivo')
    if not archivo or not archivo.filename:
        flash('No seleccionaste ningún archivo', 'error')
        return redirect(url_for('mis_archivos'))
    if not archivo_valido(archivo.filename):
        flash('Tipo de archivo no permitido', 'error')
        return redirect(url_for('mis_archivos'))
    ext = archivo.filename.rsplit('.', 1)[1].lower()
    nombre_unico = f"{uuid.uuid4()}.{ext}"
    ruta = os.path.join(CARPETA_ARCHIVOS, nombre_unico)
    archivo.save(ruta)
    tamano = os.path.getsize(ruta)
    if tamano > TAMANO_MAXIMO:
        os.remove(ruta)
        flash('El archivo supera el tamaño máximo permitido (5MB)', 'error')
        return redirect(url_for('mis_archivos'))

    nuevo_archivo = Archivo(usuario_id=session['user_id'],nombre_original=archivo.filename,
        nombre_guardado=nombre_unico,extension=ext,mime_type='application/octet-stream',ruta=ruta,tamano=tamano)
    db.session.add(nuevo_archivo)
    db.session.commit()
    flash('Archivo subido correctamente', 'success')
    return redirect(url_for('mis_archivos'))

@app.route('/archivo/<int:file_id>')
def descargar_archivo(file_id):
    if not usuario_autenticado():
        return redirect(url_for('login'))
    archivo = obtener_archivo_usuario(file_id)
    if not archivo:
        flash('Archivo no encontrado', 'error')
        return redirect(url_for('mis_archivos'))
    return send_file(archivo.ruta, as_attachment=True, download_name=archivo.nombre_original)

@app.route('/archivo/<int:file_id>/eliminar', methods=['POST'])
def eliminar_archivo(file_id):
    if not usuario_autenticado():
        return redirect(url_for('login'))
    archivo = obtener_archivo_usuario(file_id)
    if archivo:
        if os.path.exists(archivo.ruta):
            os.remove(archivo.ruta)
        db.session.delete(archivo)
        db.session.commit()
        flash('Archivo eliminado', 'success')
    return redirect(url_for('mis_archivos'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)