from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Usuario, Postulante, Archivo
from datetime import datetime
from flask_mail import Message
import random
import os
import uuid
from config_mail import init_mail, mail
from functools import wraps
from cloudinary_utils import subir_archivo, eliminar_archivo

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
directorio_base = os.path.abspath(os.path.dirname(__file__))
app.config.update(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(directorio_base, 'instance', 'app.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=5 * 1024 * 1024
)

CARPETA_ARCHIVOS = os.path.join(directorio_base, 'uploads')
EXTENSIONES_PERMITIDAS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xlsx', 'txt', 'gif', 'webp'}

db.init_app(app)
init_mail(app)
os.makedirs(CARPETA_ARCHIVOS, exist_ok=True)

def login_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorador

def admin_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión', 'error')
            return redirect(url_for('login'))
        usuario = Usuario.query.get(session['user_id'])
        if not usuario or usuario.tipo != 'admin':
            flash('Acceso no autorizado', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorador

def archivo_valido(nombre_archivo):
    return '.' in nombre_archivo and nombre_archivo.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS

def validar_dni(dni):
    return len(dni) == 8 and dni.isdigit()

def guardar_archivo(archivo, id_usuario=None):
    if not archivo or not archivo.filename:
        return None, 'No seleccionaste ningún archivo'
    if not archivo_valido(archivo.filename):
        return None, 'Tipo de archivo no permitido'
    usar_cloudinary = all([
        os.environ.get('CLOUDINARY_CLOUD_NAME'),
        os.environ.get('CLOUDINARY_API_KEY'),
        os.environ.get('CLOUDINARY_API_SECRET')
    ])
    id_usuario_final = id_usuario or session['user_id']
    if usar_cloudinary:
        extension = archivo.filename.rsplit('.', 1)[1].lower()
        if extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            tipo_recurso = 'image'
        elif extension in ['mp4', 'webm', 'ogg']:
            tipo_recurso = 'video'
        else:
            tipo_recurso = 'raw'
        resultado = subir_archivo(
            archivo,
            folder=f"postulantes/user_{id_usuario_final}",
            resource_type=tipo_recurso
        )
        if not resultado['success']:
            return None, f'Error Cloudinary: {resultado["error"]}'
        nuevo_archivo = Archivo(
            usuario_id=id_usuario_final,
            nombre_original=archivo.filename,
            nombre_guardado=resultado['public_id'],
            extension=resultado['format'],
            mime_type=f"application/{resultado['format']}",
            ruta=resultado['secure_url'],
            tamano=resultado['bytes']
        )
    else:
        extension = archivo.filename.rsplit('.', 1)[1].lower()
        nombre_unico = f"{uuid.uuid4()}.{extension}"
        ruta_local = os.path.join(CARPETA_ARCHIVOS, nombre_unico)
        archivo.save(ruta_local)
        if os.path.getsize(ruta_local) > app.config['MAX_CONTENT_LENGTH']:
            os.remove(ruta_local)
            return None, 'El archivo supera 5MB'
        nuevo_archivo = Archivo(
            usuario_id=id_usuario_final,
            nombre_original=archivo.filename,
            nombre_guardado=nombre_unico,
            extension=extension,
            mime_type='',
            ruta=ruta_local,
            tamano=os.path.getsize(ruta_local)
        )
    db.session.add(nuevo_archivo)
    return nuevo_archivo, None

@app.route('/')
def index():
    return render_template('register.html')

@app.route('/postular', methods=['POST'])
def postular():
    campos = ['nombres', 'apellidos', 'fecha_nacimiento', 'correo', 'dni', 'password']
    datos = {campo: request.form.get(campo, '').strip() for campo in campos}
    datos['correo'] = datos['correo'].lower()
    if not all(datos.values()):
        flash('Todos los campos son obligatorios', 'error')
        return redirect(url_for('index'))
    if request.form.get('password') != request.form.get('password_confirm'):
        flash('Las contraseñas no coinciden', 'error')
        return redirect(url_for('index'))
    if not validar_dni(datos['dni']):
        flash('El DNI debe tener 8 dígitos', 'error')
        return redirect(url_for('index'))
    if Usuario.query.filter_by(email=datos['correo']).first():
        flash('El correo ya está registrado', 'error')
        return redirect(url_for('index'))
    try:
        nuevo_usuario = Usuario(
            email=datos['correo'],
            password_hash=generate_password_hash(datos['password']),
            tipo='postulante',
            verificado=False
        )
        db.session.add(nuevo_usuario)
        db.session.flush()
        nuevo_postulante = Postulante(
            usuario_id=nuevo_usuario.id,
            nombres=datos['nombres'],
            apellidos=datos['apellidos'],
            fecha_nacimiento=datetime.strptime(datos['fecha_nacimiento'], '%Y-%m-%d').date(),
            dni=datos['dni'],
            estado='pendiente'
        )
        db.session.add(nuevo_postulante)
        archivo = request.files.get('archivo_de_identidad')
        if archivo and archivo.filename:
            guardar_archivo(archivo, nuevo_usuario.id)
        codigo = str(random.randint(100000, 999999))
        session.update({
            'correo_verificar': datos['correo'],
            'codigo_verificacion': codigo
        })
        try:
            mensaje = Message(
                "Verifica tu correo en App Iestpoxapampa",
                recipients=[datos['correo']]
            )
            mensaje.html = render_template(
                "verify_email.html",
                nombres=datos['nombres'],
                codigo=codigo
            )
            mail.send(mensaje)
        except Exception:
            pass
        db.session.commit()
        flash(f'Registro exitoso. Código enviado a {datos["correo"]}', 'success')
        return redirect(url_for('verify'))
    except Exception:
        db.session.rollback()
        flash('Error en el registro', 'error')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()
        contrasena = request.form.get('password', '')
        usuario = Usuario.query.filter_by(email=correo).first()
        if not usuario or not check_password_hash(usuario.password_hash, contrasena):
            flash('Correo o contraseña incorrectos', 'error')
        elif usuario.tipo == 'postulante' and not usuario.verificado:
            flash('Debes verificar tu correo primero', 'error')
            return redirect(url_for('verify'))
        else:
            session.update({
                'user_id': usuario.id,
                'email': usuario.email,
                'tipo_usuario': usuario.tipo
            })
            flash('Bienvenido!', 'success')
            if usuario.tipo == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo')
        codigo_correcto = session.get('codigo_verificacion')
        if codigo_ingresado == codigo_correcto:
            correo = session.get('correo_verificar')
            usuario = Usuario.query.filter_by(email=correo).first()
            if usuario:
                usuario.verificado = True
                db.session.commit()
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
@login_requerido
def dashboard():
    if session.get('tipo_usuario') == 'admin':
        return redirect(url_for('admin_dashboard'))
    postulante = Postulante.query.filter_by(usuario_id=session['user_id']).first()
    estado = postulante.estado if postulante else 'pendiente'
    return render_template('dashboard.html', estado=estado)

@app.route('/perfil')
@login_requerido
def perfil():
    usuario = Usuario.query.get(session['user_id'])
    postulante = Postulante.query.filter_by(usuario_id=session['user_id']).first()
    datos_usuario = {
        'email': usuario.email,
        'nombres': postulante.nombres if postulante else '',
        'apellidos': postulante.apellidos if postulante else '',
        'dni': postulante.dni if postulante else ''
    }    
    return render_template('profile.html', usuario=datos_usuario)

@app.route('/perfil/editar', methods=['POST'])
@login_requerido
def editar_perfil():
    dni = request.form.get('dni', '').strip()
    if not validar_dni(dni):
        flash('El DNI debe tener 8 dígitos', 'error')
        return redirect(url_for('perfil'))
    postulante = Postulante.query.filter_by(usuario_id=session['user_id']).first()
    if postulante:
        postulante.nombres = request.form.get('nombres', '').strip()
        postulante.apellidos = request.form.get('apellidos', '').strip()
        postulante.dni = dni
        db.session.commit()
        flash('Perfil actualizado', 'success')
    return redirect(url_for('perfil'))

@app.route('/mis_archivos')
@login_requerido
def mis_archivos():
    archivos = Archivo.query.filter_by(usuario_id=session['user_id'])\
               .order_by(Archivo.fecha_subida.desc())\
               .all()
    return render_template('files.html', archivos=archivos)

@app.route('/subir_archivo', methods=['POST'])
@login_requerido
def subir_archivo():
    archivo = request.files.get('archivo')
    archivo_guardado, error = guardar_archivo(archivo)
    if error:
        flash(error, 'error')
    else:
        db.session.commit()
        flash('Archivo subido correctamente', 'success')
    return redirect(url_for('mis_archivos'))

@app.route('/archivo/<int:id_archivo>')
@login_requerido
def descargar_archivo(id_archivo):
    archivo = Archivo.query.filter_by(
        id=id_archivo,
        usuario_id=session['user_id']
    ).first_or_404()
    if archivo.ruta.startswith('https://res.cloudinary.com'):
        return redirect(archivo.ruta)
    return send_file(
        archivo.ruta,
        as_attachment=True,
        download_name=archivo.nombre_original
    )

@app.route('/archivo/<int:id_archivo>/eliminar', methods=['POST'])
@login_requerido
def eliminar_archivo(id_archivo):
    archivo = Archivo.query.filter_by(
        id=id_archivo,
        usuario_id=session['user_id']
    ).first()
    if archivo:
        try:
            if archivo.ruta.startswith('https://res.cloudinary.com'):
                partes = archivo.ruta.split('/upload/')
                if len(partes) > 1:
                    id_publico = partes[1].split('/')[-1].split('.')[0]
                    eliminar_archivo(id_publico)
            else:
                if os.path.exists(archivo.ruta):
                    os.remove(archivo.ruta)
            db.session.delete(archivo)
            db.session.commit()
            flash('Archivo eliminado', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar: {str(e)}', 'error')
    return redirect(url_for('mis_archivos'))

@app.route('/admin/dashboard')
@admin_requerido
def admin_dashboard():
    total_usuarios = Usuario.query.filter_by(tipo='postulante').count()
    total_archivos = Archivo.query.count()
    postulantes_pendientes = Postulante.query.filter_by(estado='pendiente').count()
    return render_template('admin_dashboard.html',
                         total_usuarios=total_usuarios,
                         total_archivos=total_archivos,
                         postulantes_pendientes=postulantes_pendientes)
    
@app.route('/admin/usuarios')
@admin_requerido

def admin_usuarios():
    postulantes = Postulante.query.join(Usuario)\
                   .filter(Usuario.tipo == 'postulante')\
                   .all()
    return render_template('admin_usuarios.html', postulantes=postulantes)

@app.route('/admin/cambiar_estado/<int:postulante_id>', methods=['POST'])
@admin_requerido
def cambiar_estado_postulante(postulante_id):
    postulante = Postulante.query.get_or_404(postulante_id)
    nuevo_estado = request.form.get('estado')
    if nuevo_estado in ['pendiente', 'aprobado', 'rechazado']:
        postulante.estado = nuevo_estado
        db.session.commit()
        flash(f'Estado cambiado a {nuevo_estado}', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/archivos')
@admin_requerido
def admin_archivos():
    archivos = Archivo.query.join(Usuario)\
               .order_by(Archivo.fecha_subida.desc())\
               .all()
    return render_template('admin_archivos.html', archivos=archivos)

@app.route('/admin/descargar_archivo/<int:id_archivo>')
@admin_requerido
def admin_descargar_archivo(id_archivo):
    archivo = Archivo.query.get_or_404(id_archivo)
    
    return send_file(
        archivo.ruta,
        as_attachment=True,
        download_name=archivo.nombre_original
    )

@app.route('/admin/archivo/<int:id_archivo>/eliminar', methods=['POST'])
@admin_requerido
def admin_eliminar_archivo(id_archivo):
    archivo = Archivo.query.get_or_404(id_archivo)
    try:
        if os.path.exists(archivo.ruta):
            os.remove(archivo.ruta)
        
        db.session.delete(archivo)
        db.session.commit()
        flash('Archivo eliminado correctamente', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar archivo', 'error')
    
    return redirect(url_for('admin_archivos'))

@app.errorhandler(413)
def archivo_demasiado_grande(e):
    flash('El archivo supera el tamaño máximo permitido (5MB)', 'error')
    return redirect(request.referrer or url_for('index'))
with app.app_context():
    db.create_all()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)