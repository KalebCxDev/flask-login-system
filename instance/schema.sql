PRAGMA foreign_keys = ON;


CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('admin', 'postulante')),
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS postulantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    dni TEXT,
    estado TEXT DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'aprobado', 'rechazado')),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS archivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    nombre_original TEXT NOT NULL,
    nombre_guardado TEXT NOT NULL,
    extension TEXT NOT NULL
        CHECK (extension IN (
            'pdf','jpg','jpeg','png','doc','docx',
            'xlsx','txt','gif','webp'
        )),
    mime_type TEXT NOT NULL,
    ruta TEXT NOT NULL,
    tamano INTEGER NOT NULL
        CHECK (tamano > 0 AND tamano <= 5242880),
    fecha_subida DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);


CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email
ON usuarios(email);

CREATE UNIQUE INDEX IF NOT EXISTS idx_postulantes_correo
ON postulantes(correo);

CREATE INDEX IF NOT EXISTS idx_postulantes_estado
ON postulantes(estado);

CREATE INDEX IF NOT EXISTS idx_archivos_usuario
ON archivos(usuario_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_archivos_unico
ON archivos(usuario_id, nombre_guardado);
