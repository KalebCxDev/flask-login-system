from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Usuario, Postulante, Archivo
from datetime import datetime
from flask_mail import Message
import random, os, uuid
from config_mail import init_mail, mail
from functools import wraps
from cloudinary_utils import upload_to_cloudinary, delete_from_cloudinary, get_secure_url

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config.update(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=5 * 1024 * 1024
)

CARPETA_ARCHIVOS = os.path.join(BASE_DIR, 'uploads')
EXTENSIONES_PERMITIDAS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xlsx', 'txt', 'gif', 'webp'}
db.init_app(app)
init_mail(app)
os.makedirs(CARPETA_ARCHIVOS, exist_ok=True)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión', 'error'); return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or Usuario.query.get(session['user_id']).tipo != 'admin':
            flash('Acceso no autorizado', 'error'); return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def archivo_valido(nombre):
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS

def validar_dni(dni):
    return len(dni) == 8 and dni.isdigit()

def guardar_archivo(archivo, usuario_id=None):
    if not archivo or not archivo.filename:
        return None, 'No seleccionaste ningún archivo'
    
    if not archivo_valido(archivo.filename):
        return None, 'Tipo de archivo no permitido'
    
    use_cloudinary = all([
        os.environ.get('CLOUDINARY_CLOUD_NAME'),
        os.environ.get('CLOUDINARY_API_KEY'),
        os.environ.get('CLOUDINARY_API_SECRET')
    ])
    
    if use_cloudinary:
        ext = archivo.filename.rsplit('.', 1)[1].lower()

        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            resource_type = 'image'
        elif ext in ['mp4', 'webm', 'ogg']:
            resource_type = 'video'
        else:
            resource_type = 'raw'

        result = upload_to_cloudinary(
            archivo,
            folder=f"postulantes/user_{usuario_id or session['user_id']}",
            resource_type=resource_type
        )
        
        if not result['success']:
            return None, f'Error Cloudinary: {result["error"]}'
        
        nuevo_archivo = Archivo(
            usuario_id=usuario_id or session['user_id'],
            nombre_original=archivo.filename,
            nombre_guardado=result['public_id'],
            extension=result['format'],
            mime_type=f"application/{result['format']}",
            ruta=result['secure_url'],
            tamano=result['bytes']
        )
    else:
        ext = archivo.filename.rsplit('.', 1)[1].lower()
        nombre_unico = f"{uuid.uuid4()}.{ext}"
        ruta_local = os.path.join(CARPETA_ARCHIVOS, nombre_unico)
        
        archivo.save(ruta_local)
        
        if os.path.getsize(ruta_local) > app.config['MAX_CONTENT_LENGTH']:
            os.remove(ruta_local)
            return None, 'El archivo supera 5MB'
        
        nuevo_archivo = Archivo(
            usuario_id=usuario_id or session['user_id'],
            nombre_original=archivo.filename,
            nombre_guardado=nombre_unico,
            extension=ext,
            mime_type=result.get('resource_type'),
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
    datos = {k: request.form.get(k, '').strip() for k in ['nombres', 'apellidos', 'fecha_nacimiento', 'correo', 'dni', 'password']}
    datos['correo'] = datos['correo'].lower()
    
    if not all(datos.values()): flash('Todos los campos son obligatorios', 'error'); return redirect(url_for('index'))
    if request.form.get('password') != request.form.get('password_confirm'): flash('Las contraseñas no coinciden', 'error'); return redirect(url_for('index'))
    if not validar_dni(datos['dni']): flash('El DNI debe tener 8 dígitos', 'error'); return redirect(url_for('index'))
    if Usuario.query.filter_by(email=datos['correo']).first(): flash('El correo ya está registrado', 'error'); return redirect(url_for('index'))
    
    try:
        nuevo_usuario = Usuario(email=datos['correo'], password_hash=generate_password_hash(datos['password']), tipo='postulante', verificado=False)
        db.session.add(nuevo_usuario); db.session.flush()
        
        nuevo_postulante = Postulante(usuario_id=nuevo_usuario.id, nombres=datos['nombres'], apellidos=datos['apellidos'],
            fecha_nacimiento=datetime.strptime(datos['fecha_nacimiento'], '%Y-%m-%d').date(), dni=datos['dni'], estado='pendiente')
        db.session.add(nuevo_postulante)
        
        archivo = request.files.get('archivo_de_identidad')
        if archivo and archivo.filename: guardar_archivo(archivo, nuevo_usuario.id)
        
        codigo = str(random.randint(100000, 999999))
        session.update({'correo_verificar': datos['correo'], 'codigo_verificacion': codigo})
        
        try:
            msg = Message("Verifica tu correo en App Iestpoxapampa", recipients=[datos['correo']])
            msg.html = render_template("verify_email.html", nombres=datos['nombres'], codigo=codigo); mail.send(msg)
        except: pass
        
        db.session.commit()
        flash(f'Registro exitoso. Código enviado a {datos["correo"]}', 'success')
        return redirect(url_for('verify'))
    except:
        db.session.rollback(); flash('Error en el registro', 'error'); return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = Usuario.query.filter_by(email=request.form.get('correo', '').strip().lower()).first()
        if not usuario or not check_password_hash(usuario.password_hash, request.form.get('password', '')):
            flash('Correo o contraseña incorrectos', 'error')
        elif usuario.tipo == 'postulante' and not usuario.verificado:
            flash('Debes verificar tu correo primero', 'error'); return redirect(url_for('verify'))
        else:
            session.update({'user_id': usuario.id, 'email': usuario.email, 'tipo_usuario': usuario.tipo})
            flash('Bienvenido!', 'success')
            return redirect(url_for('admin_dashboard' if usuario.tipo == 'admin' else 'dashboard'))
    return render_template('login.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        if request.form.get('codigo') == session.get('codigo_verificacion'):
            if usuario := Usuario.query.filter_by(email=session.get('correo_verificar')).first():
                usuario.verificado = True; db.session.commit()
            session.pop('correo_verificar', None); session.pop('codigo_verificacion', None)
            flash('Correo verificado! Ya puedes iniciar sesión', 'success'); return redirect(url_for('login'))
        flash('Código incorrecto', 'error')
    return render_template('verify.html')

@app.route('/logout')
def logout():
    session.clear(); flash('Sesión cerrada', 'success'); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('tipo_usuario') == 'admin': return redirect(url_for('admin_dashboard'))
    postulante = Postulante.query.filter_by(usuario_id=session['user_id']).first()
    return render_template('dashboard.html', estado=postulante.estado if postulante else 'pendiente')

@app.route('/perfil')
@login_required
def perfil():
    usuario = Usuario.query.get(session['user_id'])
    postulante = Postulante.query.filter_by(usuario_id=session['user_id']).first()
    return render_template('profile.html', usuario={'email': usuario.email, 'nombres': postulante.nombres if postulante else '',
        'apellidos': postulante.apellidos if postulante else '', 'dni': postulante.dni if postulante else ''})

@app.route('/perfil/editar', methods=['POST'])
@login_required
def editar_perfil():
    dni = request.form.get('dni', '').strip()
    if not validar_dni(dni): flash('El DNI debe tener 8 dígitos', 'error'); return redirect(url_for('perfil'))
    postulante = Postulante.query.filter_by(usuario_id=session['user_id']).first()
    if postulante:
        postulante.nombres = request.form.get('nombres', '').strip()
        postulante.apellidos = request.form.get('apellidos', '').strip()
        postulante.dni = dni
        db.session.commit(); flash('Perfil actualizado', 'success')
    return redirect(url_for('perfil'))

@app.route('/mis_archivos')
@login_required
def mis_archivos():
    return render_template('files.html', archivos=Archivo.query.filter_by(usuario_id=session['user_id']).order_by(Archivo.fecha_subida.desc()).all())

@app.route('/subir_archivo', methods=['POST'])
@login_required
def subir_archivo():
    archivo, error = guardar_archivo(request.files.get('archivo'))
    if error: flash(error, 'error')
    else: db.session.commit(); flash('Archivo subido correctamente', 'success')
    return redirect(url_for('mis_archivos'))

@app.route('/archivo/<int:file_id>')
@login_required
def descargar_archivo(file_id):
    archivo = Archivo.query.filter_by(id=file_id, usuario_id=session['user_id']).first_or_404()
    if archivo.ruta.startswith('https://res.cloudinary.com'):
        return redirect(archivo.ruta)
    return send_file(archivo.ruta, as_attachment=True, download_name=archivo.nombre_original)

@app.route('/archivo/<int:file_id>/eliminar', methods=['POST'])
@login_required
def eliminar_archivo(file_id):
    archivo = Archivo.query.filter_by(id=file_id, usuario_id=session['user_id']).first()
    if archivo:
        try:
            if archivo.ruta.startswith('https://res.cloudinary.com'):
                parts = archivo.ruta.split('/upload/')
                if len(parts) > 1:
                    public_id = parts[1].split('/')[-1].split('.')[0]
                    delete_from_cloudinary(public_id)
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
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', total_usuarios=Usuario.query.filter_by(tipo='postulante').count(),
        total_archivos=Archivo.query.count(), postulantes_pendientes=Postulante.query.filter_by(estado='pendiente').count())

@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    return render_template('admin_usuarios.html', postulantes=Postulante.query.join(Usuario).filter(Usuario.tipo == 'postulante').all())

@app.route('/admin/cambiar_estado/<int:postulante_id>', methods=['POST'])
@admin_required
def cambiar_estado_postulante(postulante_id):
    postulante = Postulante.query.get_or_404(postulante_id)
    if (estado := request.form.get('estado')) in ['pendiente', 'aprobado', 'rechazado']:
        postulante.estado = estado; db.session.commit(); flash(f'Estado cambiado a {estado}', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/archivos')
@admin_required
def admin_archivos():
    return render_template('admin_archivos.html', archivos=Archivo.query.join(Usuario).order_by(Archivo.fecha_subida.desc()).all())

@app.route('/admin/descargar_archivo/<int:file_id>')
@admin_required
def admin_descargar_archivo(file_id):
    archivo = Archivo.query.get_or_404(file_id)
    return send_file(archivo.ruta, as_attachment=True, download_name=archivo.nombre_original)

@app.route('/admin/archivo/<int:file_id>/eliminar', methods=['POST'])
@admin_required
def admin_eliminar_archivo(file_id):
    archivo = Archivo.query.get_or_404(file_id)
    try:
        if os.path.exists(archivo.ruta): os.remove(archivo.ruta)
        db.session.delete(archivo); db.session.commit(); flash('Archivo eliminado correctamente', 'success')
    except: db.session.rollback(); flash('Error al eliminar archivo', 'error')
    return redirect(url_for('admin_archivos'))

@app.errorhandler(413)
def archivo_demasiado_grande(e):
    flash('El archivo supera el tamaño máximo permitido (5MB)', 'error')
    return redirect(request.referrer or url_for('index'))

with app.app_context(): db.create_all()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)