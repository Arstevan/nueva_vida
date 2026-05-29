from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_mail import Mail, Message # 1. IMPORTAR LIBRERÍAS DE CORREO

app = Flask(__name__)
app.secret_key = 'nueva_vida_secret'

# Configuración Base de Datos
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'consejeria_nv'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# 2. CONFIGURACIÓN DE MAIL (AJUSTA CON TUS DATOS)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'iglesianuevavidabq@gmail.com' # CAMBIA ESTO
app.config['MAIL_PASSWORD'] = 'souc mggu iqzc wstc'      # CAMBIA ESTO (Contraseña de App)

mysql = MySQL(app)
mail = Mail(app) # 3. INICIALIZAR MAIL

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
        rol = 'miembro' 
        
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO usuarios (Nombres, Apellidos, Email, Contrasena, rol) VALUES (%s, %s, %s, %s, %s)", 
                        (nombres, apellidos, email, contrasena, rol))
        mysql.connection.commit()
        cursor.close()
        
        flash('Registro exitoso, ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
        
    return render_template('registro.html')

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
            session['usuario_id'] = usuario['Id_miembro'] 
            session['usuario_nombre'] = usuario['Nombres']
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

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM citas WHERE Id_miembro = %s ORDER BY Fecha DESC", (session['usuario_id'],))
    citas = cursor.fetchall()
    
    return render_template('panel_usuario.html', citas=citas)

# ==============================
# RUTA CAMBIAR ESTADO CITA (CORREO DETALLADO)
# ==============================
@app.route('/cambiar-estado/<int:id_cita>/<string:nuevo_estado>', methods=['POST'])
def cambiar_estado_cita(id_cita, nuevo_estado):
    if 'usuario_id' not in session or session['usuario_rol'] != 'admin':
        flash("Acceso denegado", "error")
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    
    # 1. Obtenemos datos del usuario y de la cita
    cursor.execute("""
        SELECT u.Email, u.Nombres, c.Fecha, c.Hora 
        FROM usuarios u 
        JOIN citas c ON u.Id_miembro = c.Id_miembro 
        WHERE c.Id_citas = %s
    """, (id_cita,))
    usuario = cursor.fetchone()
    
    # 2. Actualizamos el estado
    cursor.execute("UPDATE citas SET Estado = %s WHERE Id_citas = %s", (nuevo_estado, id_cita))
    mysql.connection.commit()
    
    # 3. Si se confirma, enviamos el correo detallado
    if nuevo_estado == 'Confirmada' and usuario:
        msg = Message("Cita Confirmada - Iglesia Nueva Vida",
                      sender="iglesianuevavidabq@gmail.com",
                      recipients=[usuario['Email']])
        
        # Cuerpo del mensaje profesional
        msg.body = (f"¡Hola, {usuario['Nombres']}!\n\n"
                    f"Reciba un cordial saludo de parte de la Iglesia Nueva Vida.\n\n"
                    f"Nos complace informarle que su solicitud de cita de consejería ha sido aprobada y confirmada exitosamente.\n\n"
                    f"Detalles de su cita:\n"
                    f"📅 Fecha: {usuario['Fecha']}\n"
                    f"⏰ Hora: {usuario['Hora']}\n\n"
                    f"Le recordamos asistir puntualmente. Si por algún motivo no puede asistir, le agradecemos notificarnos con antelación a través de nuestra plataforma o contactando a la iglesia.\n\n"
                    f"¡Estamos atentos para servirle y compartir juntos en este tiempo de bendición!\n\n"
                    f"Atentamente,\n"
                    f"Equipo de Consejería - Iglesia Nueva Vida")
        
        try:
            mail.send(msg)
            flash(f"Cita confirmada y correo enviado a {usuario['Nombres']}", "success")
        except Exception as e:
            flash("Cita confirmada, pero hubo un problema al enviar el correo.", "warning")
            print(f"Error: {e}")
    else:
        flash(f"Cita actualizada a {nuevo_estado}", "success")
    
    cursor.close()
    return redirect(url_for('panel_admin'))

# ==============================
# RUTA PANEL ADMIN (FILTRANDO CITAS)
# ==============================
@app.route('/panel-admin')
def panel_admin():
    if 'usuario_id' not in session or session.get('usuario_rol') != 'admin':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    # AGREGAMOS EL FILTRO: WHERE c.Estado != 'Cancelada'
    query = """
        SELECT c.*, u.Nombres AS NombreMiembro, u.Apellidos AS ApellidoMiembro 
        FROM citas c
        JOIN usuarios u ON c.Id_miembro = u.Id_miembro
        WHERE c.Estado != 'Cancelada'
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
    app.run(debug=True, use_reloader=False)
