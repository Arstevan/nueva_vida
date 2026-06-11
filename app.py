from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer as Serializer


app = Flask(__name__)
app.secret_key = 'nueva_vida_secret'

# Configuración Base de Datos
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'consejeria_nv'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Configuración de Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'iglesianuevavidabq@gmail.com'
app.config['MAIL_PASSWORD'] = 'souc mggu iqzc wstc' 

mysql = MySQL(app)
mail = Mail(app)

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
        email = request.form['email'].strip()
        contrasena = request.form['contrasena'].strip()
        
        cursor = mysql.connection.cursor()
        # Buscamos solo por email primero para verificar si existe
        cursor.execute("SELECT * FROM usuarios WHERE Email=%s", (email,))
        usuario = cursor.fetchone()
        cursor.close()
        
        if usuario:
            # Comparamos contraseñas quitando espacios en ambos lados
            # Asegúrate de usar la llave 'Contrasena' (con C mayúscula) como en tu tabla
            if str(usuario['Contrasena']).strip() == contrasena:
                session.clear() # Limpiamos sesión antigua
                session['usuario_id'] = usuario['Id_miembro']
                session['usuario_nombre'] = usuario['Nombres']
                session['usuario_rol'] = usuario['rol']
                
                # Redirección basada en el rol
                if usuario['rol'] == 'admin':
                    return redirect(url_for('panel_admin'))
                else:
                    return redirect(url_for('panel_usuario'))
            else:
                flash("Contraseña incorrecta.", "error")
        else:
            flash("Correo no registrado.", "error")
            
    return render_template('login.html')


# ==============================
# LÓGICA DE RECUPERACIÓN DE CONTRASEÑA
# ==============================
def get_reset_token(email):
    s = Serializer(app.secret_key, salt='recuperar-pass')
    return s.dumps(email)

def verify_reset_token(token):
    s = Serializer(app.secret_key, salt='recuperar-pass')
    try:
        email = s.loads(token, max_age=1800) # Expira en 30 minutos
        return email
    except:
        return None

@app.route('/olvidar-password', methods=['GET', 'POST'])
def olvidar_password():
    if request.method == 'POST':
        email = request.form['email']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE Email = %s", (email,))
        usuario = cursor.fetchone()
        
        if usuario:
            token = get_reset_token(email)
            link = url_for('reset_password', token=token, _external=True)
            msg = Message("Recuperación de Contraseña - Nueva Vida",
                          sender="iglesianuevavidabq@gmail.com",
                          recipients=[email])
            msg.body = f"Hola, has solicitado recuperar tu acceso. Haz clic aquí para cambiar tu contraseña: {link}"
            mail.send(msg)
            flash("Se ha enviado un enlace de recuperación a tu correo.", "success")
        else:
            flash("Correo no encontrado en el sistema.", "error")
    return render_template('olvidar_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash('El enlace es inválido o ha expirado.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nueva_pass = request.form['contrasena'] # Guardamos tal cual
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE usuarios SET Contrasena = %s WHERE Email = %s", (nueva_pass, email))
        mysql.connection.commit()
        cursor.close()
        
        flash("Contraseña actualizada exitosamente.", "success")
        return redirect(url_for('login'))
        
    return render_template('reset_password.html')

# ==============================
# RUTA PANEL USUARIO
# ==============================
@app.route('/panel-usuario', methods=['GET', 'POST'])
def panel_usuario():
    # ... tu código aquí ...
    if 'usuario_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        motivo = request.form['motivo']
        fecha = request.form['fecha']
        hora = request.form['hora']
        
        cursor = mysql.connection.cursor()
        
        # A) Verificar si el día está bloqueado por el administrador
        cursor.execute("SELECT * FROM dias_bloqueados WHERE fecha_bloqueada = %s", (fecha,))
        bloqueado = cursor.fetchone()
        
        # B) Verificar si ya hay una cita en ese horario
        cursor.execute("SELECT COUNT(*) as total FROM citas WHERE Fecha = %s AND Hora = %s AND Estado != 'Cancelada'", 
                       (fecha, hora))
        cita_existente = cursor.fetchone()
        
        if bloqueado:
            flash(f"Lo sentimos, el día {fecha} no está disponible para consejería.", "error")
        elif cita_existente['total'] > 0:
            flash("Este horario ya está reservado. Por favor elige otro.", "error")
        else:
            # 3. GUARDAR CITA
            cursor.execute("INSERT INTO citas (Especialidad, Fecha, Hora, Id_miembro, Estado) VALUES (%s, %s, %s, %s, %s)", 
                           (motivo, fecha, hora, session['usuario_id'], 'Pendiente'))
            mysql.connection.commit()
            flash('Solicitud enviada con éxito.', 'success')
            
        cursor.close()
        return redirect(url_for('panel_usuario'))

    # Para mostrar las citas del usuario
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM citas WHERE Id_miembro = %s ORDER BY Fecha DESC", (session['usuario_id'],))
    citas = cursor.fetchall()
    cursor.close()
    return render_template('panel_usuario.html', citas=citas)

# ==============================
# RUTA PARA BLOQUEAR DÍAS (Faltaba esta)
# ==============================
@app.route('/bloquear-dia', methods=['POST'])
def bloquear_dia():
    if 'usuario_id' not in session or session.get('usuario_rol') != 'admin':
        return redirect(url_for('login'))
    
    fecha = request.form['fecha_bloqueo']
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO dias_bloqueados (fecha_bloqueada) VALUES (%s)", (fecha,))
    mysql.connection.commit()
    cursor.close()
    
    flash(f"Día {fecha} bloqueado exitosamente.", "success")
    return redirect(url_for('panel_admin'))




# ==============================
# RUTA DESBLOQUEAR DIA
# ==============================
@app.route('/desbloquear-dia/<string:fecha>', methods=['POST'])
def desbloquear_dia(fecha):
    if 'usuario_id' not in session or session.get('usuario_rol') != 'admin':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM dias_bloqueados WHERE fecha_bloqueada = %s", (fecha,))
    mysql.connection.commit()
    cursor.close()
    
    flash(f"Día {fecha} desbloqueado exitosamente.", "success")
    return redirect(url_for('panel_admin'))



# ==============================
# RUTA CAMBIAR ESTADO CITA
# ==============================
@app.route('/cambiar-estado/<int:id_cita>/<string:nuevo_estado>', methods=['POST'])
def cambiar_estado_cita(id_cita, nuevo_estado):
    if 'usuario_id' not in session or session['usuario_rol'] != 'admin':
        flash("Acceso denegado", "error")
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    
    # 1. Obtenemos los datos completos (Email, Nombres, Fecha y Hora)
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
    
    if usuario:
        try:
            if nuevo_estado == 'Confirmada':
                asunto = "Cita Confirmada - Iglesia Nueva Vida"
                msg_cuerpo = (f"¡Hola, {usuario['Nombres']}!\n\n"
                            f"Reciba un cordial saludo de parte de la Iglesia Nueva Vida.\n\n"
                            f"Nos complace informarle que su solicitud de cita de consejería ha sido aprobada y confirmada exitosamente.\n\n"
                            f"Detalles de su cita:\n"
                            f"📅 Fecha: {usuario['Fecha']}\n"
                            f"⏰ Hora: {usuario['Hora']}\n\n"
                            f"Le recordamos asistir puntualmente. Si por algún motivo no puede asistir, le agradecemos notificarnos con antelación a través de nuestra plataforma o contactando a la iglesia.\n\n"
                            f"¡Estamos atentos para servirle y compartir juntos en este tiempo de bendición!\n\n"
                            f"Atentamente,\n"
                            f"Equipo de Consejería - Iglesia Nueva Vida")
            else:
                asunto = "Cita Cancelada - Iglesia Nueva Vida"
                msg_cuerpo = (f"¡Hola, {usuario['Nombres']}!\n\n"
                            f"Reciba un cordial saludo de parte de la Iglesia Nueva Vida.\n\n"
                            f"Lamentamos informarle que su cita de consejería ha sido cancelada.\n\n"
                            f"Detalles de la cita cancelada:\n"
                            f"📅 Fecha: {usuario['Fecha']}\n"
                            f"⏰ Hora: {usuario['Hora']}\n\n"
                            f"Si desea reprogramar o tiene alguna duda, por favor contáctenos a través de nuestra plataforma.\n\n"
                            f"Atentamente,\n"
                            f"Equipo de Consejería - Iglesia Nueva Vida")

            msg = Message(asunto, sender="iglesianuevavidabq@gmail.com", recipients=[usuario['Email']])
            msg.body = msg_cuerpo
            mail.send(msg)
            flash(f"Cita {nuevo_estado} y correo enviado correctamente.", "success")
            
        except Exception as e:
            flash(f"Cita {nuevo_estado}, pero falló el envío del correo.", "warning")
            print(f"Error: {e}")
    
    cursor.close()
    return redirect(url_for('panel_admin'))

# ==============================
# RUTA PANEL ADMIN (FILTRADO)
# ==============================
@app.route('/panel-admin')
def panel_admin():
    if 'usuario_id' not in session or session.get('usuario_rol') != 'admin':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    # Obtener citas
    query = """
        SELECT c.*, u.Nombres AS NombreMiembro, u.Apellidos AS ApellidoMiembro 
        FROM citas c
        JOIN usuarios u ON c.Id_miembro = u.Id_miembro
        WHERE c.Estado != 'Cancelada'
        ORDER BY c.Fecha ASC
    """
    cursor.execute(query)
    citas = cursor.fetchall()
    
    # Obtener fechas bloqueadas (NUEVO)
    cursor.execute("SELECT fecha_bloqueada FROM dias_bloqueados ORDER BY fecha_bloqueada ASC")
    dias_bloqueados = cursor.fetchall()
    
    cursor.close()
    
    return render_template('panel_admin.html', citas=citas, dias_bloqueados=dias_bloqueados)



# ==============================
# RUTA LOGOUT
# ==============================
@app.route('/logout')
def logout():
    session.clear()
    # Debe ser 'consejeria' (sin tilde), igual que en tu HTML
    return redirect(url_for('inicio', _anchor='consejeria'))


# ==============================
# RUTA HISTORIAL DE CITAS
# ==============================
@app.route('/historial-citas')
def historial_citas():
    if 'usuario_id' not in session or session.get('usuario_rol') != 'admin':
        return redirect(url_for('login'))
    
    # Capturamos las fechas del formulario
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    cursor = mysql.connection.cursor()
    
    # Consulta base
    query = """
        SELECT c.*, u.Nombres AS NombreMiembro, u.Apellidos AS ApellidoMiembro 
        FROM citas c
        JOIN usuarios u ON c.Id_miembro = u.Id_miembro
    """
    params = []
    
    # Aplicamos filtro si el usuario ingresó ambas fechas
    if fecha_inicio and fecha_fin:
        query += " WHERE c.Fecha BETWEEN %s AND %s"
        params = [fecha_inicio, fecha_fin]
    
    query += " ORDER BY c.Fecha DESC"
    
    cursor.execute(query, tuple(params))
    citas = cursor.fetchall()
    cursor.close()
    
    return render_template('historial.html', citas=citas)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
