from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__) #Oigan por que esto debe ser si o si "__name__"?
app.secret_key = 'clave-secreta'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'instance', 'app.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('register.html')

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
            INSERT INTO postulantes
            (nombres, apellidos, fecha_nacimiento, correo, dni)
            VALUES (?, ?, ?, ?, ?)
        """, (nombres, apellidos, fecha_nacimiento, correo, dni))

        conn.commit()
        flash('Postulación registrada correctamente', 'success')

    except sqlite3.IntegrityError: flash('El correo ya está registrado', 'error')
    finally: conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    app.run(debug=True)
