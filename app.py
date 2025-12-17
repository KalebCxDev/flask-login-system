from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'clave-secreta'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'instance', 'app.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# - Rutas publicas

@app.route('/')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    return redirect(url_for('verify'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        return redirect(url_for('login'))
    return render_template('verify.html')

@app.route('/logout')
def logout():
    return redirect(url_for('login'))

# - Rutas privadas

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/profile')
def profile():
    return render_template('profile.html')


@app.route('/profile/edit', methods=['POST'])
def edit_profile():
    return redirect(url_for('profile'))


@app.route('/files')
def files():
    return render_template('files.html')


@app.route('/files/upload', methods=['POST'])
def upload_file():
    return redirect(url_for('files'))


@app.route('/files/<int:file_id>')
def file_detail(file_id):
    return redirect(url_for('files'))

# - Postulacion

@app.route('/postular', methods=['POST'])
def postular():
    nombres = request.form['nombres']
    apellidos = request.form['apellidos']
    fecha_nacimiento = request.form['fecha_nacimiento']
    correo = request.form['correo']
    dni = request.form.get('dni')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO usuarios (email, password_hash, tipo)
            VALUES (?, ?, ?)
        """, (correo, 'hash_temporal', 'postulante'))
        
        
        usuario_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO postulantes
            (usuario_id, nombres, apellidos, fecha_nacimiento, dni)
            VALUES (?, ?, ?, ?, ?)
        """, (usuario_id, nombres, apellidos, fecha_nacimiento, dni))
        conn.commit()
        flash('Postulación registrada correctamente', 'success')

    except sqlite3.IntegrityError:
        flash('El correo ya está registrado', 'error')

    finally:
        conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    app.run(debug=True)