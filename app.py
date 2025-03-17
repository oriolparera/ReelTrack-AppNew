from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, url_for, redirect
import sqlite3
import random
import string
import os
from datetime import datetime
import qrcode
import chatbot


app = Flask(__name__)
app.secret_key = 'clau_secreta_segura'

DATABASE = "bobines.db"

# ✅ Connexió a la base de dades
def conectar_db():
    conexion = sqlite3.connect(DATABASE, timeout=30)
    conexion.execute('PRAGMA journal_mode=WAL;')
    conexion.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_bobina TEXT NOT NULL,
            ruta_qr TEXT NOT NULL,
            comentaris TEXT,
            bobinas_origen TEXT,
            fecha TEXT NOT NULL,
            maquina TEXT,
            treballador TEXT,
            tensio REAL,
            gruix_material REAL,
            amplada REAL,
            tipus_material TEXT,
            longitud REAL,
            estat TEXT DEFAULT 'Nova'
        )
    ''')
    return conexion

# ✅ Ruta para mostrar la interfaz del chatbot
@app.route('/chatbot', methods=['GET'])
def chatbot_page():
    return render_template("chatbot.html")

# ✅ Ruta para recibir consultas del usuario y devolver respuestas
@app.route('/chatbot', methods=['POST'])
def chatbot_response():
    data = request.json
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"response": "❌ Please enter a valid message."})

    response = chatbot.consulta(user_message)  # Llama a la función en chatbot.py
    return jsonify({"response": response})


@app.route('/verificar_bobina/<id_bobina>', methods=['GET'])
def verificar_bobina(id_bobina):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute('SELECT COUNT(*) FROM historial WHERE id_bobina = ?', (id_bobina,))
    existe = cursor.fetchone()[0] > 0
    conexion.close()

    return jsonify({'existe': existe})

# ✅ Generar ID personalitzat
def generar_id_personalitzat():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ✅ Generar codi QR
def generar_qr(id_bobina):
    qr_directory = "static/qrs"  # ✅ Ensure QR is saved in a visible directory

    if not os.path.exists(qr_directory):
        os.makedirs(qr_directory)

    qr_path = os.path.join(qr_directory, f"qr_bobina_{id_bobina}.png")

    qr = qrcode.make(id_bobina)
    qr.save(qr_path)

    return f"/{qr_path}"  # ✅ Ensure path is correct for HTML rendering


# ✅ Ruta pàgina principal
@app.route('/')
def index():
    return render_template('index.html')

@app.route("/get_reel_params/<reel_id>")
def get_reel_params(reel_id):
    try:
        # Connect to the database
        conexion = conectar_db()
        cursor = conexion.cursor()

        # Fetch parameters from the database for the given reel ID
        cursor.execute("""
            SELECT tensio, gruix_material, amplada, tipus_material, longitud 
            FROM historial WHERE id_bobina = ?
        """, (reel_id,))
        result = cursor.fetchone()

        conexion.close()

        # If no reel is found, return an error
        if not result:
            return jsonify({"success": False, "error": "Reel not found"})

        # Return the retrieved parameters in JSON format
        return jsonify({
            "success": True,
            "tensio": result[0] if result[0] is not None else "",
            "gruix_material": result[1] if result[1] is not None else "",
            "amplada": result[2] if result[2] is not None else "",
            "tipus_material": result[3] if result[3] is not None else "",
            "longitud": result[4] if result[4] is not None else ""
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ✅ Crear noves bobines
@app.route('/crear_bobines', methods=['GET', 'POST'])
def crear_bobines():
    print(f"Crida Form 1")
    if request.method == 'GET':
        print(f"Crida Form")
        return render_template('crear_bobines.html')  # ✅ Mostrem el formulari

    try:
        origen_ids = request.form.getlist('origen_id')  # 📌 Recollim les bobines escanejades
        maquina = request.form.get('maquina')
        treballador = request.form.get('nom_treballador')
        nou_comentari = request.form.get('comentaris', '').strip()
        num_noves_bobines = int(request.form.get('num_noves_bobines', 1))  # 📌 Nombre de bobines a crear

        # 📌 Nous paràmetres
        tensio = request.form.get('tensio')
        gruix_material = request.form.get('gruix_material')
        amplada = request.form.get('amplada')
        tipus_material = request.form.get('tipus_material')
        longitud = request.form.get('longitud')

        # ✅ Si no hi ha bobina mare, es posa com a NULL
        bobina_mare = ', '.join(origen_ids) if origen_ids else None

        print(f"📥📥📥📥 Bobines origen: {origen_ids}, Creant {num_noves_bobines} bobines noves.")

        qrs_generats = []
        conexion = conectar_db()
        cursor = conexion.cursor()

        for _ in range(num_noves_bobines):
            nou_id = generar_id_personalitzat()
            ruta_qr = generar_qr(nou_id)
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"🆕 Generant nova bobina: {nou_id} | Pare: {bobina_mare}")

            cursor.execute('''
                INSERT INTO historial (id_bobina, ruta_qr, comentaris, bobinas_origen, fecha, maquina, treballador, 
                tensio, gruix_material, amplada, tipus_material, longitud, estat)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nou_id, ruta_qr, nou_comentari, bobina_mare, fecha, maquina, treballador,
                  tensio, gruix_material, amplada, tipus_material, longitud, 'Nova'))

            qrs_generats.append({'id': nou_id, 'ruta_qr': ruta_qr.replace("./qrs/", "/qrs/")})

        conexion.commit()
        conexion.close()

        print(f"✅ Bobines creades: {len(qrs_generats)}")
        return render_template("resultat_creacio.html", qrs=qrs_generats)

    except Exception as e:
        print(f"⚠️ Error al crear bobines: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ✅ Consulta bobines
@app.route('/consulta', methods=['GET'])
def consulta():
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM historial ORDER BY fecha DESC')
    bobines = cursor.fetchall()
    conexion.close()
    return render_template('consulta.html', bobines=bobines)

# ✅ Vista detallada d'una bobina
@app.route('/bobina/<id_bobina>')
def ver_bobina(id_bobina):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM historial WHERE id_bobina = ?', (id_bobina,))
    bobina = cursor.fetchone()
    conexion.close()

    if not bobina:
        return "Bobina no trobada", 404

    return render_template('ver_qr.html', bobina=bobina)

def buscar_antecesores(cursor, id_bobina, bobines_anteriors, edges):
    """
    Función recursiva para encontrar todas las bobinas anteriores (padres)
    """
    cursor.execute('SELECT * FROM historial WHERE id_bobina = ?', (id_bobina,))
    bobina = cursor.fetchone()

    if bobina and bobina[4]:  # bobina[4] es bobinas_origen
        ids_origen = [id.strip() for id in bobina[4].split(',')]
        for origen_id in ids_origen:
            cursor.execute('SELECT * FROM historial WHERE id_bobina = ?', (origen_id,))
            resultat = cursor.fetchone()
            if resultat:
                bobines_anteriors.append(resultat)
                edges.append((origen_id, id_bobina))  # 🔹 Conectamos padre → hijo
                buscar_antecesores(cursor, origen_id, bobines_anteriors, edges)  # 🔄 Llamada recursiva


def buscar_descendientes(cursor, id_bobina, bobines_derivades, edges):
    """
    Función recursiva para encontrar todas las bobinas derivadas (hijos)
    """
    cursor.execute('SELECT * FROM historial WHERE bobinas_origen LIKE ?', (f"%{id_bobina}%",))
    derivades = cursor.fetchall()

    for derivada in derivades:
        bobines_derivades.append(derivada)
        edges.append((id_bobina, derivada[1]))  # 🔹 Conectamos padre → hijo
        buscar_descendientes(cursor, derivada[1], bobines_derivades, edges)  # 🔄 Llamada recursiva


@app.route('/esquema/<id_bobina>')
def esquema_bobina(id_bobina):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    print(f"📥📥📥📥 IdBobina: {id_bobina}")

    # 📌 Obtenemos la bobina seleccionada
    cursor.execute('SELECT * FROM historial WHERE id_bobina = ?', (id_bobina,))
    bobina = cursor.fetchone()

    if not bobina:
        return f"❌ Bobina amb ID {id_bobina} no trobada.", 404

    # 📌 Búsqueda recursiva de padres e hijos
    bobines_anteriors = []
    bobines_derivades = []
    edges = []  # 🔹 Aquí guardamos las conexiones correctas

    buscar_antecesores(cursor, id_bobina, bobines_anteriors, edges)
    buscar_descendientes(cursor, id_bobina, bobines_derivades, edges)

    conn.close()

    print(f"📥📥📥📥 Crida: {bobina} || {bobines_derivades} || {bobines_anteriors} || {edges}")
    return render_template('esquema.html', bobina=bobina, derivades=bobines_derivades, anteriors=bobines_anteriors, edges=edges)


# ✅ Ruta para descargar QR de una bobina
@app.route('/imprimir_qr/<id_bobina>', methods=['GET'])
def imprimir_qr(id_bobina):
    ruta_qr = f'static/qrs/qr_bobina_{id_bobina}.png'
    if os.path.exists(ruta_qr):
        return send_file(ruta_qr, mimetype='image/png', as_attachment=True)
    else:
        return "❌ QR no trobat", 404

@app.route('/processar_bobines', methods=['POST'])
def processar_bobines():
    try:
        print(f"📥📥📥📥: Inici processar bobines")
        treballador = request.form.get('treballador')
        maquina = request.form.get('maquina')
        num_noves_bobines = int(request.form.get('num_noves_bobines', 1))  # 📌 Obtenim el número correcte
        origen_ids = request.form.getlist('bobines')  # 📌 Bobines escanejades
        nou_comentari = request.form.get('comentaris', None)  # 📝 Comentaris opcionals

        # ✅ Nous paràmetres afegits
        tensio = request.form.get('tensio')
        gruix_material = request.form.get('gruix_material')
        amplada = request.form.get('amplada')
        tipus_material = request.form.get('tipus_material')
        longitud = request.form.get('longitud')

        print(f"📥📥📥📥: Bobines mare: {origen_ids}, Num. Sortida: {num_noves_bobines}")

        qrs_generats = []
        conexion = conectar_db()
        cursor = conexion.cursor()

        bobina_mare = ', '.join(origen_ids) if origen_ids else None  # 📌 Guardem la bobina mare

        for _ in range(num_noves_bobines):  # 📌 Genera tantes bobines com s'indiqui
            nou_id = generar_id_personalitzat()
            ruta_qr = generar_qr(nou_id)
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"🆕 Generant nova bobina: {nou_id} | Pare: {bobina_mare}")

            cursor.execute('''
                INSERT INTO historial (id_bobina, ruta_qr, comentaris, bobinas_origen, fecha, maquina, treballador, 
                tensio, gruix_material, amplada, tipus_material, longitud, estat)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nou_id, ruta_qr, nou_comentari, bobina_mare, fecha, maquina, treballador,
                  tensio, gruix_material, amplada, tipus_material, longitud, 'Nova'))

            qrs_generats.append({'id': nou_id, 'ruta_qr': ruta_qr.replace("./qrs/", "/qrs/")})

        conexion.commit()
        conexion.close()

        print(f"✅ Bobines creades: {len(qrs_generats)}")
        return render_template("resultat_creacio.html", qrs=qrs_generats)

    except Exception as e:
        print(f"⚠️ Error al processar bobines: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ✅ Nueva ruta para mostrar el QR de la bobina verge en una pantalla independiente
@app.route('/resultat_creacio_verge')
def resultat_creacio_verge():
    id_bobina = request.args.get('id_bobina')
    ruta_qr = request.args.get('ruta_qr')
    return render_template('resultat_creacio_verge.html', id_bobina=id_bobina, ruta_qr=ruta_qr)

# ✅ Crear bobina verge con redirección a la página de QR

@app.route('/crear_bobina_verge', methods=['GET', 'POST'])
def crear_bobina_verge():
    if request.method == 'GET':
        return render_template('crear_bobina_verge.html')

    try:
        # ✅ Recoger parámetros
        tensio = request.form.get('tensio')
        gruix_material = request.form.get('gruix_material')
        amplada = request.form.get('amplada')
        tipus_material = request.form.get('tipus_material')
        longitud = request.form.get('longitud')

        if not all([tensio, gruix_material, amplada, tipus_material, longitud]):
            return jsonify({'success': False, 'error': '❗ All parameters must be filled in.'})

        # ✅ Convertir a tipo correcto
        tensio = float(tensio)
        gruix_material = float(gruix_material)
        amplada = float(amplada)
        longitud = float(longitud)

        # ✅ Generar ID y QR
        id_bobina = generar_id_personalitzat()
        ruta_qr = generar_qr(id_bobina)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ✅ Guardar en base de datos
        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute('''
            INSERT INTO historial (id_bobina, ruta_qr, comentaris, bobinas_origen, fecha, maquina, treballador, 
                                  tensio, gruix_material, amplada, tipus_material, longitud, estat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id_bobina, ruta_qr, 'Primary Reel', 'Primary Reel', fecha, 'Primary Reel', 'Primary Reel', tensio, gruix_material, amplada, tipus_material, longitud, 'Nova'))
        conexion.commit()
        conexion.close()

        # ✅ Redirigir a la nueva página con el QR
        return redirect(url_for('resultat_creacio_verge', id_bobina=id_bobina, ruta_qr=ruta_qr))

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/eliminar_bobina/<id_bobina>', methods=['DELETE'])
def eliminar_bobina(id_bobina):
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()

        # Verify if reel exists before deleting
        cursor.execute('SELECT COUNT(*) FROM historial WHERE id_bobina = ?', (id_bobina,))
        exists = cursor.fetchone()[0] > 0

        if not exists:
            return jsonify({'success': False, 'error': 'Reel ID not found'})

        # Delete the reel from the database
        cursor.execute('DELETE FROM historial WHERE id_bobina = ?', (id_bobina,))
        conexion.commit()
        conexion.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/maquina/<nom_maquina>')
def pagina_maquina(nom_maquina):
    treballador = request.args.get('treballador', 'Unknown')
    bobines_text = request.args.get('bobines', '')
    num_noves_bobines = request.args.get('num_noves_bobines', '1')  # ✅ Default to "1"
    comentaris = request.args.get('comentaris', '')

    if nom_maquina == "flexo":
        return render_template("maquina_flexo.html", treballador=treballador, bobines=bobines_text, num_noves_bobines=num_noves_bobines, comentaris=comentaris, nom_maquina=nom_maquina)
    elif nom_maquina == "laminator":
        return render_template("maquina_laminator.html", treballador=treballador, bobines=bobines_text, num_noves_bobines=num_noves_bobines, comentaris=comentaris, nom_maquina=nom_maquina)
    elif nom_maquina == "slitter":
        return render_template("maquina_slitter.html", treballador=treballador, bobines=bobines_text, num_noves_bobines=num_noves_bobines, comentaris=comentaris, nom_maquina=nom_maquina)
    else:
        return "❌ Machine not found", 404

@app.route('/qrs/<filename>')
def send_qr(filename):
    return send_from_directory('static/qrs', filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
