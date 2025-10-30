# --- app.py (El "Motor" y "Cocina") ---
# Esta versión INCLUYE la corrección para el bug
# de espacios en la lista de materias.

import os
import shutil
from pathlib import Path
import time
import unicodedata
import re
import csv
from datetime import datetime
import getpass
import json # Necesario para enviar datos al HTML
import webbrowser # Para abrir el navegador
import threading # Para abrir el navegador después de que inicie Flask

# --- Importaciones de Flask ---
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# --- Configuración de Flask ---
app = Flask(__name__)
# Permitir que nuestro HTML hable con nuestro servidor Python
CORS(app) 

# --- Constantes Globales ---
# Carpeta privada del USUARIO (para perfiles)
APP_DATA_DIR = Path(os.environ.get('APPDATA', Path.home())) / "OrganizadorMaterias"
PERFILES_CSV = APP_DATA_DIR / "perfiles.csv"
# Carpeta pública del SCRIPT (para el log)
SCRIPT_DIR = Path(__file__).parent
ADMIN_LOG_CSV = SCRIPT_DIR / "admin_log.csv"
MATERIAS_SEPARATOR = "|"

# --- Funciones de Ayuda (Impresión y Rutas) ---

def print_success(message):
    print(f"\033[92m[ÉXITO] {message}\033[0m")

def print_error(message):
    print(f"\033[91m[ERROR] {message}\033[0m")

def print_warning(message):
    print(f"\033[93m[AVISO] {message}\033[0m")

def get_default_directories():
    """
    Encuentra las carpetas comunes del usuario (Descargas, etc.)
    Probando rutas en Español e Inglés, con y sin OneDrive.
    """
    home = Path.home()
    carpetas = {
        'Descargas': [
            home / "OneDrive" / "Descargas", home / "Descargas",
            home / "OneDrive" / "Downloads", home / "Downloads"
        ],
        'Documentos': [
            home / "OneDrive" / "Documentos", home / "Documentos",
            home / "OneDrive" / "Documents", home / "Documents"
        ],
        'Escritorio': [
            home / "OneDrive" / "Escritorio", home / "Escritorio",
            home / "OneDrive" / "Desktop", home / "Desktop"
        ],
        'Imágenes': [
            home / "OneDrive" / "Imágenes", home / "Imágenes",
            home / "OneDrive" / "Pictures", home / "Pictures"
        ],
        'Música': [
            home / "OneDrive" / "Música", home / "Música",
            home / "OneDrive" / "Music", home / "Music"
        ],
        'Videos': [
            home / "OneDrive" / "Videos", home / "Videos",
            home / "OneDrive" / "Videos", home / "Videos"
        ]
    }

    rutas_encontradas = {}
    for nombre, candidatas in carpetas.items():
        for ruta in candidatas:
            if ruta.is_dir():
                rutas_encontradas[nombre] = str(ruta)
                break # Encontramos una, pasar a la siguiente
    return rutas_encontradas

# --- Lógica Principal (El Organizador) ---

def normalize_text(text):
    if not text:
        return ""
    text = str(text)
    text = text.lower()
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text) 
        if unicodedata.category(c) != 'Mn'
    )
    return text

def sanitize_folder_name(name):
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = name.strip().replace(" ", "_")
    return name if name else "Sin_Nombre"

def get_unique_path(destination):
    if not destination.exists():
        return destination
    
    base = destination.parent / destination.stem
    ext = destination.suffix
    i = 1
    while True:
        new_name = f"{base} ({i}){ext}"
        new_path = Path(new_name)
        if not new_path.exists():
            return new_path
        i += 1

def organize_by_subject(source_dir_str, dest_dir_str, subjects_pipe, manejo_otros, profile_id):
    source_dir = Path(source_dir_str)
    dest_dir = Path(dest_dir_str)
    
    # Manejo de 'None' o string vacío
    subjects_list = subjects_pipe.split(MATERIAS_SEPARATOR) if subjects_pipe else []
    
    subjects_normalized = [normalize_text(s) for s in subjects_list if s] # Lista de materias normalizadas
    report = {'moved': 0, 'renamed': 0, 'skipped': 0, 'errors': 0}
    
    # Crear carpetas de materias
    for subject in subjects_normalized:
        folder_name = sanitize_folder_name(subject)
        (dest_dir / folder_name).mkdir(parents=True, exist_ok=True)
    
    # Crear carpeta "Otros" si es necesario
    others_dir = dest_dir / "Otros"
    if manejo_otros == "Mover":
        others_dir.mkdir(parents=True, exist_ok=True)

    log_rows = []
    username = get_username()
    
    for item in source_dir.iterdir():
        # Ignorar accesos directos y el propio log
        if item.is_symlink() or item.name.endswith(".lnk") or item.name == ADMIN_LOG_CSV.name:
            report['skipped'] += 1
            continue
            
        # Ignorar carpetas si no se van a mover (ej. venv)
        if item.is_dir() and item.name == 'venv':
             report['skipped'] += 1
             continue

        item_normalized = normalize_text(item.name)
        matched_subject = None
        
        for subject in subjects_normalized:
            if subject in item_normalized:
                matched_subject = subject
                break
        
        status = ""
        final_destination_str = ""
        original_path_str = str(item) # Guardar la ruta original aquí
        
        try:
            target_dir = None
            if matched_subject:
                target_dir = dest_dir / sanitize_folder_name(matched_subject)
            elif manejo_otros == "Mover":
                target_dir = others_dir
                matched_subject = "Otros"
            
            if target_dir:
                file_hash = "" # Nota: Hashing puede ser lento, omitido por ahora
                file_size = 0
                if item.is_file():
                    file_size = item.stat().st_size
                elif item.is_dir():
                    # Calcular tamaño de carpeta (puede ser lento) o dejar en 0
                    try:
                        file_size = sum(f.stat().st_size for f in item.glob('**/*') if f.is_file())
                    except Exception:
                        file_size = 0 # Ignorar si hay errores de permisos, etc.

                
                destination_path = get_unique_path(target_dir / item.name)
                final_destination_str = str(destination_path)
                
                shutil.move(item, destination_path)
                
                if str(destination_path) == str(target_dir / item.name):
                    status = "MOVIDO"
                    report['moved'] += 1
                else:
                    status = "RENOMBRADO"
                    report['renamed'] += 1
            else:
                status = "OMITIDO"
                report['skipped'] += 1
        
        except Exception as e:
            print_error(f"No se pudo mover {item.name}: {e}")
            status = "ERROR"
            report['errors'] += 1
            final_destination_str = f"ERROR: {e}"
            file_size = 0 # No hay tamaño si hay error

        # Registrar en el log
        # (Registrar todo excepto los 'OMITIDO' que no se querían mover)
        if not (status == "OMITIDO" and manejo_otros != "Mover"):
             log_rows.append({
                'log_timestamp': datetime.now().isoformat(),
                'username': username,
                'id_perfil': profile_id,
                'file_original_path': original_path_str,
                'file_new_path': final_destination_str,
                'file_size_bytes': file_size,
                'subject_assigned': matched_subject if matched_subject else "N/A",
                'status': status,
                'file_hash': file_hash  # Aún vacío, pero la columna existe
            })

    log_to_admin_csv(log_rows)
    return report

# --- Lógica de Perfiles (CSV) ---

def get_username():
    try:
        return getpass.getuser()
    except Exception:
        return "usuario_desconocido"

def load_profiles():
    if not PERFILES_CSV.exists():
        return {}
    
    profiles = {}
    try:
        with open(PERFILES_CSV, mode='r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                profiles[row['id_perfil']] = row
        return profiles
    except Exception as e:
        print_error(f"No se pudo leer {PERFILES_CSV}: {e}")
        return {}

def save_profiles(profiles_data):
    if not profiles_data:
        # Si el diccionario está vacío, podemos borrar el archivo o guardar un archivo vacío
        try:
            if PERFILES_CSV.exists():
                os.remove(PERFILES_CSV)
            print_warning("No hay perfiles, se ha limpiado el archivo.")
        except Exception as e:
            print_error(f"No se pudo borrar {PERFILES_CSV}: {e}")
        return

    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Obtener todas las llaves de todos los perfiles para estar seguros
        all_keys = set()
        for profile in profiles_data.values():
            all_keys.update(profile.keys())
        fieldnames = sorted(list(all_keys)) # Ordenar para consistencia
        
        with open(PERFILES_CSV, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for profile in profiles_data.values():
                writer.writerow(profile)
    except Exception as e:
        print_error(f"No se pudo guardar {PERFILES_CSV}: {e}")

# --- Lógica de Log (CSV) ---

ADMIN_LOG_FIELDNAMES = [
    'log_timestamp', 'username', 'id_perfil', 'file_original_path', 
    'file_new_path', 'file_size_bytes', 'subject_assigned', 'status', 'file_hash'
]

def setup_admin_log():
    try:
        # Asegurarse que la carpeta del log exista (ahora es local)
        SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Si el log no existe, crear y escribir cabecera
        if not ADMIN_LOG_CSV.exists():
            with open(ADMIN_LOG_CSV, mode='w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=ADMIN_LOG_FIELDNAMES)
                writer.writeheader()
    except Exception as e:
        print_error(f"¡Error crítico al crear admin_log.csv! {e}")
        print_warning("La app podría no funcionar. Intenta mover la carpeta a 'Documentos'.")

def log_to_admin_csv(rows):
    if not rows:
        return
    try:
        with open(ADMIN_LOG_CSV, mode='a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=ADMIN_LOG_FIELDNAMES)
            for row in rows:
                writer.writerow(row)
    except Exception as e:
        print_error(f"No se pudo escribir en admin_log.csv: {e}")

# --- Setup Inicial ---

def setup():
    print("Ejecutando setup inicial...")
    # 1. Asegurar que la carpeta de perfiles del usuario exista
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Asegurar que el log de admin (local) exista
    setup_admin_log()
    print("Setup completado.")

# -------------------------------------------------
# --- RUTAS DE LA API (Las "Puertas" de Flask) ---
# -------------------------------------------------

@app.route('/')
def index():
    """ Sirve el archivo HTML principal (la "cara" de la app) """
    return render_template('index.html')

@app.route('/api/get-default-folders')
def api_get_default_folders():
    """ Devuelve las carpetas comunes (Descargas, etc.) al HTML """
    try:
        paths = get_default_directories()
        return jsonify({'status': 'success', 'paths': paths})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get-profiles')
def api_get_profiles():
    """ Devuelve todos los perfiles guardados del usuario Y el nombre de usuario """
    try:
        profiles = load_profiles()
        # --- ¡ESTA ES LA ACTUALIZACIÓN! ---
        # Ahora también enviamos el nombre de usuario.
        username = get_username().capitalize() # Poner en mayúscula la primera letra
        return jsonify({'status': 'success', 'profiles': profiles, 'username': username})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/create-profile', methods=['POST'])
def api_create_profile():
    """ Crea y guarda un nuevo perfil """
    try:
        data = request.json
        profiles = load_profiles()
        
        # Validación simple de datos
        required_keys = ['nombre_visible', 'ruta_origen', 'ruta_destino', 'nombre_carpeta_principal', 'manejo_otros']
        if not all(key in data and data[key] for key in required_keys):
            return jsonify({'status': 'error', 'message': 'Faltan datos requeridos.'}), 400
        
        profile_id = f"perfil_{int(time.time())}"
        now = datetime.now().isoformat()
        
        # Crear la ruta de destino final para mostrar en la UI
        ruta_destino_final = str(Path(data['ruta_destino']) / sanitize_folder_name(data['nombre_carpeta_principal']))

        # --- CORRECCIÓN de bug de espacio ---
        materias_str = data.get('lista_materias_str', '')
        materias_list = [s.strip() for s in materias_str.split(',') if s.strip()]
        materias_pipe_str = MATERIAS_SEPARATOR.join(materias_list)
        # --- FIN DE LA CORRECCIÓN ---

        new_profile = {
            "id_perfil": profile_id,
            "nombre_visible": data['nombre_visible'],
            "lista_materias_pipe": materias_pipe_str, # Usar la cadena limpia
            "ruta_origen": data['ruta_origen'],
            "ruta_destino": data['ruta_destino'],
            "nombre_carpeta_principal": data['nombre_carpeta_principal'],
            "ultimo_uso_timestamp": now,
            "creado_en_timestamp": now,
            "contador_archivos_movidos": "0",
            "manejo_otros": data['manejo_otros'],
            "ruta_destino_final": ruta_destino_final # Dato extra para la UI
        }
        
        profiles[profile_id] = new_profile
        save_profiles(profiles)
        
        return jsonify({'status': 'success', 'profile': new_profile})
        
    except Exception as e:
        print_error(f"Error en /api/create-profile: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/delete-profile', methods=['POST'])
def api_delete_profile():
    """ Borra un perfil existente """
    try:
        data = request.json
        profile_id = data.get('profile_id')
        
        profiles = load_profiles()
        if profile_id in profiles:
            del profiles[profile_id]
            save_profiles(profiles)
            return jsonify({'status': 'success', 'message': 'Perfil borrado.'})
        else:
            return jsonify({'status': 'error', 'message': 'Perfil no encontrado.'}), 404
            
    except Exception as e:
        print_error(f"Error en /api/delete-profile: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/run-profile', methods=['POST'])
def api_run_profile():
    """ Ejecuta la lógica de organización de un perfil """
    try:
        data = request.json
        profile_id = data.get('profile_id')
        
        profiles = load_profiles()
        if profile_id not in profiles:
            return jsonify({'status': 'error', 'message': 'Perfil no encontrado.'}), 404
            
        profile = profiles[profile_id]
        
        # Validar rutas
        source_dir = Path(profile['ruta_origen'])
        dest_parent_dir = Path(profile['ruta_destino'])
        if not source_dir.is_dir():
            return jsonify({'status': 'error', 'message': f"La carpeta de origen no existe: {source_dir}"}), 400
        if not dest_parent_dir.is_dir():
            return jsonify({'status': 'error', 'message': f"La carpeta de destino no existe: {dest_parent_dir}"}), 400
        
        # Crear la carpeta de destino principal
        dest_dir = dest_parent_dir / sanitize_folder_name(profile['nombre_carpeta_principal'])
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # --- Ejecutar la lógica principal ---
        report = organize_by_subject(
            str(source_dir),
            str(dest_dir),
            profile.get('lista_materias_pipe'), # Usar .get() para seguridad
            profile['manejo_otros'],
            profile_id
        )
        
        # Actualizar perfil y guardar
        total_moved = int(profile.get('contador_archivos_movidos', 0)) + report['moved'] + report['renamed']
        profile['contador_archivos_movidos'] = str(total_moved)
        profile['ultimo_uso_timestamp'] = datetime.now().isoformat()
        profiles[profile_id] = profile
        save_profiles(profiles)
        
        return jsonify({'status': 'success', 'report': report})

    except Exception as e:
        print_error(f"Error en /api/run-profile: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- Funciones de Arranque ---

def open_browser():
    """ Abre el navegador web en la URL de la app """
    try:
        webbrowser.open_new(f"http://127.0.0.1:5000/")
    except Exception as e:
        print_warning(f"No se pudo abrir el navegador. Abre http://127.0.0.1:5000/ manualmente. ({e})")

if __name__ == '__main__':
    setup() # Ejecutar el setup inicial
    print_success("Iniciando servidor Flask en http://127.0.0.1:5000/")
    print_warning("Cierra esta ventana (o presiona Ctrl+C) para detener la aplicación.")
    # Abrir el navegador 1 segundo después de que Flask inicie
    threading.Timer(1, open_browser).start()
    app.run(host='127.0.0.1', port=5000, debug=False)

