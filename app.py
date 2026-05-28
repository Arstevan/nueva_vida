from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'nueva_vida_secret'

# Configuración Base de Datos
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'consejeria_nv'
# Importante: Esto ayuda a que los resultados sean más fáciles de manejar como diccionarios
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# ==============================
# RUTA INICIO
# ==============================
@app.route('/')
def inicio():
    return render_template('index.html')

# ==============================
# RUTA REGISTRO
# ==============================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombres = request.form['nombres']
        apellidos = request.form['apellidos']
        email = request.form['email']
        contrasena = request.form['contrasena']
        rol = 'miembro' # Ajustado al valor que vi en tu base de datos
        
        cursor = mysql.connection.cursor()
        # Asegúrate de que los nombres de columnas coincidan con tu tabla 'usuarios'
        cursor.execute("INSERT INTO usuarios (Nombres, Apellidos, Email, Contrasena, rol) VALUES (%s, %s, %s, %s, %s)", 
                       (nombres, apellidos, email, contrasena, rol))
        mysql.connection.commit()
        cursor.close() # Buena práctica cerrar el cursor
        
        flash('Registro exitoso, ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
        
    return render_template('registro.html')
# ==============================
# ==============================
# RUTA LOGIN
# ==============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        contrasena = request.form['contrasena']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE Email=%s AND Contrasena=%s", (email, contrasena))
        usuario = cursor.fetchone()
        
        if usuario:
            # AQUÍ ESTABA EL ERROR: Cambiamos 'Id_usuario' por 'Id_miembro'
            session['usuario_id'] = usuario['Id_miembro'] 
            session['usuario_nombre'] = usuario['Nombres']
            # Asegúrate que el campo en tu BD se llame 'rol' o 'Rol' (mira tu tabla)
            session['usuario_rol'] = usuario['rol'] 
            
            if usuario['rol'] == 'admin':
                return redirect(url_for('panel_admin'))
            else:
                return redirect(url_for('panel_usuario'))
        else:
            flash("Correo o contraseña incorrectos", "error")
    return render_template('login.html')
# ==============================
# RUTA PANEL USUARIO
# ==============================
@app.route('/panel-usuario', methods=['GET', 'POST'])
def panel_usuario():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        motivo = request.form['motivo']
        fecha = request.form['fecha']
        hora = request.form['hora']
        
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO citas (Especialidad, Fecha, Hora, Id_miembro, Estado) VALUES (%s, %s, %s, %s, %s)", 
                       (motivo, fecha, hora, session['usuario_id'], 'Pendiente'))
        mysql.connection.commit()
        flash('Solicitud enviada con éxito', 'success')
        return redirect(url_for('panel_usuario'))

    # Obtenemos las citas
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM citas WHERE Id_miembro = %s ORDER BY Fecha DESC", (session['usuario_id'],))
    citas = cursor.fetchall()
    
    return render_template('panel_usuario.html', citas=citas)

# ==============================
# RUTA CAMBIAR ESTADO CITA
# ==============================
@app.route('/cambiar-estado/<int:id_cita>/<string:nuevo_estado>', methods=['POST'])
def cambiar_estado_cita(id_cita, nuevo_estado):
    if 'usuario_id' not in session or session['usuario_rol'] != 'admin':
        flash("Acceso denegado", "error")
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    # Actualiza el estado en la base de datos
    cursor.execute("UPDATE citas SET Estado = %s WHERE Id_citas = %s", (nuevo_estado, id_cita))
    mysql.connection.commit()
    cursor.close()
    
    flash(f"Cita actualizada a {nuevo_estado}", "success")
    return redirect(url_for('panel_admin'))

# ==============================
# RUTA PANEL ADMIN (CORREGIDA)
# ==============================
@app.route('/panel-admin')
def panel_admin():
    # Verificación de seguridad
    if 'usuario_id' not in session or session.get('usuario_rol') != 'admin':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    # La consulta con JOIN es lo que permite que {{ cita.NombreMiembro }} funcione
    query = """
        SELECT c.*, u.Nombres AS NombreMiembro, u.Apellidos AS ApellidoMiembro 
        FROM citas c
        JOIN usuarios u ON c.Id_miembro = u.Id_miembro
        ORDER BY c.Fecha ASC
    """
    cursor.execute(query)
    citas = cursor.fetchall()
    cursor.close()
    
    return render_template('panel_admin.html', citas=citas)
# ==============================
# RUTA LOGOUT
# ==============================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # 'use_reloader=False' evita que se reinicie solo
    app.run(debug=True, use_reloader=False)
