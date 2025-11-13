import pandas as pd
import matplotlib.pyplot as plt
import sys
from pathlib import Path
import os
import getpass
from datetime import datetime

# --- CONFIGURACIÓN ---
# Define las rutas a los archivos CSV
# (Esto asume que el script de análisis está en la misma carpeta que el log)
SCRIPT_DIR = Path(__file__).parent
ADMIN_LOG_PATH = SCRIPT_DIR / "admin_log.csv"
APP_DATA_ROOT = Path(os.environ.get('APPDATA', Path.home()))

# --- Nombres de columna SINCRONIZADOS ---
COLUMNAS_LOG = [
    'log_timestamp', 'id_perfil', 'username', 'file_original_path', 
    'subject_assigned', 'status', 'file_new_path', 'file_hash', 'file_size_bytes'
]
COLUMNAS_PERFILES = [
    'id_perfil', 'nombre_visible', 'lista_materias_pipe', 'manejo_otros', 
    'ultimo_uso_timestamp', 'creado_en_timestamp', 'contador_archivos_movidos'
]
# --- FIN DE CONFIGURACIÓN ---

# --- Funciones de Carga de Datos ---

def cargar_admin_log():
    """Carga el log de administrador (público)."""
    print(f"Cargando log de administrador desde: {ADMIN_LOG_PATH}")
    if not ADMIN_LOG_PATH.exists():
        print_error(f"Error: No se encontró '{ADMIN_LOG_PATH}'.")
        print_error("Asegúrate de que 'admin_log.csv' esté en la misma carpeta que este script.")
        print_error("Usa la app 'Desshufle.bat' primero para generar un log.")
        return None
    
    try:
        df_log = pd.read_csv(
            ADMIN_LOG_PATH, 
            header=0,      # Usar la primera fila como cabecera
            dtype=str, # Cargar todo como string primero
            on_bad_lines='skip' # Ignorar líneas rotas
        )
        
        # --- Validación de Columnas ---
        columnas_faltantes = [col for col in COLUMNAS_LOG if col not in df_log.columns]
        if columnas_faltantes:
            print_error(f"Error: El admin_log.csv no tiene las columnas esperadas: {columnas_faltantes}")
            return None
        # --- Fin Validación ---
        
        if df_log.empty:
            print_error("Error: El archivo admin_log.csv está vacío (no tiene filas de datos).")
            return None

        # --- Conversión manual y explícita de fechas ---
        df_log['log_timestamp'] = pd.to_datetime(
            df_log['log_timestamp'], 
            errors='coerce' # Dejar que Pandas autodetecte el formato
        )
        
        # Si 'coerce' falló (creó NaT - Not a Time), eliminamos esas filas
        df_log = df_log.dropna(subset=['log_timestamp'])

        if df_log.empty:
            print_error("Error: No se pudieron leer fechas válidas ('log_timestamp') del CSV.")
            print_error("Revisa que la columna 'log_timestamp' no esté vacía o corrupta.")
            return None
        
        # Convertir columnas numéricas
        df_log['file_size_bytes'] = pd.to_numeric(df_log['file_size_bytes'], errors='coerce').fillna(0)
        
        print_success("Log de administrador cargado.")
        return df_log
        
    except FileNotFoundError:
        print_error(f"Error: El archivo '{ADMIN_LOG_PATH}' no existe.")
    except KeyError as e:
        print_error(f"Error crítico al leer admin_log.csv: Falta la columna {e}.")
        print_error("El admin_log.csv no coincide con la estructura esperada por el script.")
    except Exception as e:
        print_error(f"Error inesperado al leer admin_log.csv: {e}")
    
    return None

def cargar_perfiles_locales():
    """Carga los perfiles del usuario actual (privado)."""
    username = getpass.getuser()
    perfil_csv_path = APP_DATA_ROOT / "OrganizadorMaterias" / "perfiles.csv"
    
    print(f"Cargando perfiles locales para '{username}' desde: {perfil_csv_path}")

    if not perfil_csv_path.exists():
        print_warning(f"No se encontró '{perfil_csv_path}'.")
        print_warning("El análisis se ejecutará sin nombres de perfiles (solo IDs).")
        return pd.DataFrame(columns=COLUMNAS_PERFILES) # Devolver DF vacío

    try:
        df_perfil = pd.read_csv(perfil_csv_path, dtype=str)
        
        columnas_existentes = [col for col in COLUMNAS_PERFILES if col in df_perfil.columns]
        df_perfil_filtrado = df_perfil[columnas_existentes]

        # Convertir columnas numéricas
        if 'contador_archivos_movidos' in df_perfil_filtrado.columns:
            df_perfil_filtrado['contador_archivos_movidos'] = pd.to_numeric(df_perfil_filtrado['contador_archivos_movidos'], errors='coerce').fillna(0)
        
        # Convertir fechas
        if 'ultimo_uso_timestamp' in df_perfil_filtrado.columns:
            df_perfil_filtrado['ultimo_uso_timestamp'] = pd.to_datetime(df_perfil_filtrado['ultimo_uso_timestamp'], errors='coerce')
        if 'creado_en_timestamp' in df_perfil_filtrado.columns:
            df_perfil_filtrado['creado_en_timestamp'] = pd.to_datetime(df_perfil_filtrado['creado_en_timestamp'], errors='coerce')

        print_success("Perfiles locales cargados.")
        return df_perfil_filtrado
        
    except Exception as e:
        print_error(f"Error al leer perfiles.csv: {e}")
        return pd.DataFrame(columns=COLUMNAS_PERFILES) # Devolver DF vacío

# --- Funciones de Filtros Interactivos ---

def obtener_filtros_interactivos(df_log):
    """Pregunta al usuario por filtros de fecha y usuario."""
    print_header("Filtros Interactivos")
    
    # --- Filtro de Fecha ---
    print("\n--- Filtro de Fecha ---")
    min_date = df_log['log_timestamp'].min().date()
    max_date = df_log['log_timestamp'].max().date()
    print(f"Rango de datos disponible: {min_date} a {max_date}")

    fecha_inicio_str = input(f"Fecha de inicio (YYYY-MM-DD) [Enter para {min_date}]: ")
    fecha_fin_str = input(f"Fecha de fin (YYYY-MM-DD) [Enter para {max_date}]: ")

    try:
        fecha_inicio = pd.to_datetime(fecha_inicio_str).date() if fecha_inicio_str else min_date
        fecha_fin = pd.to_datetime(fecha_fin_str).date() if fecha_fin_str else max_date
    except ValueError:
        print_warning("Fecha inválida. Usando el rango completo.")
        fecha_inicio, fecha_fin = min_date, max_date
    
    # Convertir a datetime para filtrar
    # ¡YA NO NECESITAMOS ESTAS LÍNEAS! Las variables ya son 'date'
    # fecha_inicio = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
    # fecha_fin = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 59, 59)

    # --- ¡CORRECCIÓN! Comparamos .dt.date (solo la fecha) con nuestras variables de fecha ---
    df_filtrado = df_log[
        (df_log['log_timestamp'].dt.date >= fecha_inicio) & 
        (df_log['log_timestamp'].dt.date <= fecha_fin)
    ]
    
    # --- Filtro de Usuario ---
    print("\n--- Filtro de Usuario ---")
    usuarios_disponibles = df_filtrado['username'].unique()
    # Manejar el caso de que no haya usuarios en el rango
    if usuarios_disponibles.size == 0:
        print("No hay usuarios disponibles en este rango de fechas.")
        return df_filtrado # Devolver DF vacío
        
    print(f"Usuarios disponibles: {', '.join(usuarios_disponibles)}")
    usuario_str = input("Nombre de usuario [Enter para TODOS]: ")

    if usuario_str and usuario_str in usuarios_disponibles:
        df_filtrado = df_filtrado[df_filtrado['username'] == usuario_str]
        print_success(f"Filtrando por usuario: {usuario_str}")
    else:
        print_success("Mostrando datos de TODOS los usuarios.")
    
    return df_filtrado

# --- Funciones de Análisis y Gráficos ---

def analizar_datos(df_log_filtrado, df_perfiles_locales):
    """Imprime los 10 análisis estadísticos en la consola."""
    
    if df_log_filtrado.empty:
        print_warning("\nNo hay datos para analizar con los filtros seleccionados.")
        return

    print_header("Análisis Estadístico (10 Puntos)")

    df_merged = df_log_filtrado.merge(
        df_perfiles_locales[['id_perfil', 'nombre_visible']], 
        on='id_perfil', 
        how='left'
    )
    df_merged['nombre_visible'] = df_merged['nombre_visible'].fillna('Perfil Desconocido (Otro Usuario)')

    # --- 1. KPIs Generales ---
    print_subheader("1. KPIs Generales")
    total_acciones = len(df_log_filtrado)
    total_bytes = df_log_filtrado['file_size_bytes'].sum()
    total_mb = total_bytes / (1024 * 1024)
    usuarios_activos = df_log_filtrado['username'].nunique()
    print(f"  - Total de acciones registradas: {total_acciones}")
    print(f"  - Total de GB organizados: {total_mb / 1024:.2f} GB")
    print(f"  - Usuarios activos en el periodo: {usuarios_activos}")

    # --- 2. Tasas y Promedios Clave ---
    print_subheader("2. Tasas y Promedios Clave")
    acciones_movidas = (df_log_filtrado['status'] == 'MOVIDO').sum()
    acciones_renombradas = (df_log_filtrado['status'] == 'RENOMBRADO').sum()
    acciones_omitidas = (df_log_filtrado['status'] == 'OMITIDO').sum()
    acciones_error = (df_log_filtrado['status'] == 'ERROR').sum()
    
    if total_acciones > 0:
        print(f"  - Tasa de éxito (Movido/Renombrado): {((acciones_movidas + acciones_renombradas) / total_acciones) * 100:.1f}%")
        print(f"  - Tasa de renombrado (Duplicados): {(acciones_renombradas / total_acciones) * 100:.1f}%")
        print(f"  - Tasa de error: {(acciones_error / total_acciones) * 100:.1f}%")
    
    if (acciones_movidas + acciones_renombradas) > 0:
        bytes_movidos = df_log_filtrado[df_log_filtrado['status'].isin(['MOVIDO', 'RENOMBRADO'])]['file_size_bytes'].sum()
        mb_movidos = bytes_movidos / (1024 * 1024)
        mb_promedio_movido = mb_movidos / (acciones_movidas + acciones_renombradas)
        print(f"  - Tamaño promedio de archivo movido: {mb_promedio_movido:.2f} MB")
    else:
        print("  - No se movieron archivos en este periodo.")

    # --- 3. Análisis de Estado (Resultados de Acciones) ---
    print_subheader("3. Desglose de Acciones (Status)")
    print(df_log_filtrado['status'].value_counts().to_string(header=False))

    # --- 4. Análisis de Materias (Subject Assigned) ---
    print_subheader("4. Materias (Palabras Clave) Más Populares")
    materias_reales = df_log_filtrado[
        ~df_log_filtrado['subject_assigned'].isin(['N/A', 'Otros', None, ''])
    ]['subject_assigned']
    
    if materias_reales.empty:
        print("  - No se asignó ninguna materia (palabra clave) en este periodo.")
    else:
        print(materias_reales.value_counts().head(10).to_string(header=False))
    
    otros_conteo = (df_log_filtrado['subject_assigned'] == 'Otros').sum()
    print(f"  - Archivos movidos a 'Otros': {otros_conteo}")

    # --- 5. Análisis de Usuarios (Username) ---
    print_subheader("5. Top 5 Usuarios por Actividad (Acciones)")
    print(df_log_filtrado['username'].value_counts().head(5).to_string(header=False))

    # --- 6. Análisis de Perfiles (Profile ID) ---
    print_subheader("6. Perfiles Más Usados (por Nombre)")
    uso_de_perfiles = df_merged['nombre_visible'].value_counts().to_frame(name='conteo_acciones')
    print(uso_de_perfiles.to_string())

    # --- 7. Actividad por Hora del Día (Horas Pico) ---
    print_subheader("7. Actividad por Hora del Día (0-23)")
    horas_pico = df_log_filtrado['log_timestamp'].dt.hour.value_counts().sort_index()
    print(horas_pico.to_string())
    if not horas_pico.empty:
        print(f"  - Hora Pico de Uso: {horas_pico.idxmax()} hrs (con {horas_pico.max()} acciones)")

    # --- 8. Tipos de Archivo Más Comunes (Extensión) ---
    print_subheader("8. Tipos de Archivo Más Comunes (Extensión)")
    
    def get_extension(path_str):
        try:
            if not isinstance(path_str, str):
                return "N/A (No es path)"
            ext = Path(path_str).suffix.lower()
            return ext if ext else "Sin Extensión"
        except Exception:
            return "N/A (Error)"
            
    df_log_filtrado_copy = df_log_filtrado.copy()
    df_log_filtrado_copy['extension'] = df_log_filtrado_copy['file_original_path'].apply(get_extension)
    
    extensiones = df_log_filtrado_copy[~df_log_filtrado_copy['extension'].isin(["Sin Extensión", "N/A (No es path)", "N/A (Error)"])]
    if extensiones.empty:
        print("  - No se encontraron extensiones de archivo para analizar.")
    else:
        print(extensiones['extension'].value_counts().head(10).to_string(header=False))

    # --- 9. Errores y Omisiones (Análisis de Fallos) ---
    print_subheader("9. Análisis de Errores y Omisiones")
    if acciones_error > 0:
        print(f"  - {acciones_error} archivos generaron un error.")
    else:
        print("  - ¡Cero errores en este periodo!")
        
    if acciones_omitidas > 0:
        print(f"  - {acciones_omitidas} archivos fueron omitidos (probablemente 'Ignorar' estaba activo).")

    # --- 10. Actividad por Día (Series de Tiempo) ---
    print_subheader("10. Acciones por Día (Series de Tiempo)")
    actividad_diaria = df_log_filtrado.set_index('log_timestamp').resample('D').size()
    print(actividad_diaria.to_string())

# --- Función de Gráficos ---

def generar_graficos(df_log_filtrado, df_perfiles_locales):
    """Genera y guarda 5 gráficos PNG usando Matplotlib."""
    
    if df_log_filtrado.empty:
        print_warning("\nNo hay datos para graficar (DataFrame vacío después de filtros).")
        return

    print_header("Generando Gráficos (PNG)")
    
    df_merged = df_log_filtrado.merge(
        df_perfiles_locales[['id_perfil', 'nombre_visible']], 
        on='id_perfil', 
        how='left'
    )
    df_merged['nombre_visible'] = df_merged['nombre_visible'].fillna('Perfil Desconocido')

    # --- Gráfico 1: Pie de Estados (Resultados) ---
    try:
        plt.figure(figsize=(8, 8))
        status_counts = df_log_filtrado['status'].value_counts()
        if status_counts.empty:
             print_warning("  - Gráfico 1 (Pie de Status) omitido: No hay datos de 'status'.")
        else:
            plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=90, colors=['#4A5C36', '#D4E289', '#E57373', '#F8F3D8'])
            plt.title('Gráfico 1: Desglose de Acciones (Status)')
            plt.savefig(SCRIPT_DIR / '1_grafico_acciones_status.png')
            plt.close()
            print_success("  - Gráfico 1 (Pie de Status) guardado.")
    except Exception as e:
        print_error(f"  - Error al generar Gráfico 1: {e}")

    # --- Gráfico 2: Barras de Top 5 Usuarios ---
    try:
        plt.figure(figsize=(10, 6))
        user_counts = df_log_filtrado['username'].value_counts().head(5)
        if user_counts.empty:
             print_warning("  - Gráfico 2 (Top Usuarios) omitido: No hay datos de 'username'.")
        else:
            user_counts.plot(kind='bar', color='#4A5C36')
            plt.title('Gráfico 2: Top 5 Usuarios por Actividad')
            plt.xlabel('Usuario')
            plt.ylabel('Cantidad de Acciones')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(SCRIPT_DIR / '2_grafico_top_usuarios.png')
            plt.close()
            print_success("  - Gráfico 2 (Top Usuarios) guardado.")
    except Exception as e:
        print_error(f"  - Error al generar Gráfico 2: {e}")

    # --- Gráfico 3: Barras de Top 10 Materias ---
    try:
        materias_reales = df_log_filtrado[~df_log_filtrado['subject_assigned'].isin(['N/A', 'Otros', None, ''])].loc[:,'subject_assigned']
        if not materias_reales.empty:
            plt.figure(figsize=(10, 6))
            materia_counts = materias_reales.value_counts().head(10)
            materia_counts.plot(kind='barh', color='#D4E289')
            plt.title('Gráfico 3: Top 10 Materias (Palabras Clave) Usadas')
            plt.xlabel('Cantidad de Archivos')
            plt.ylabel('Materia')
            plt.gca().invert_yaxis() # La más popular arriba
            plt.tight_layout()
            plt.savefig(SCRIPT_DIR / '3_grafico_top_materias.png')
            plt.close()
            print_success("  - Gráfico 3 (Top Materias) guardado.")
        else:
            print_warning("  - Gráfico 3 (Top Materias) omitido: no hay datos de materias.")
    except Exception as e:
        print_error(f"  - Error al generar Gráfico 3: {e}")

    # --- Gráfico 4: Línea de Actividad por Día ---
    try:
        plt.figure(figsize=(12, 6))
        actividad_diaria = df_log_filtrado.set_index('log_timestamp').resample('D').size()
        if actividad_diaria.empty:
             print_warning("  - Gráfico 4 (Actividad por Día) omitido: No hay datos para la serie de tiempo.")
        else:
            actividad_diaria.plot(kind='line', marker='o', color='#4A5C36')
            plt.title('Gráfico 4: Actividad por Día (Series de Tiempo)')
            plt.xlabel('Fecha')
            plt.ylabel('Cantidad de Acciones')
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()
            plt.savefig(SCRIPT_DIR / '4_grafico_actividad_diaria.png')
            plt.close()
            print_success("  - Gráfico 4 (Actividad por Día) guardado.")
    except Exception as e:
        print_error(f"  - Error al generar Gráfico 4: {e}")

    # --- Gráfico 5: Barras de Hora del Día ---
    try:
        plt.figure(figsize=(10, 6))
        horas_pico = df_log_filtrado['log_timestamp'].dt.hour.value_counts().sort_index()
        if horas_pico.empty:
             print_warning("  - Gráfico 5 (Horas Pico) omitido: No hay datos de horas.")
        else:
            horas_pico.plot(kind='bar', color='#4A5C36')
            plt.title('Gráfico 5: Actividad por Hora del Día (Picos de Uso)')
            plt.xlabel('Hora del Día (0-23)')
            plt.ylabel('Cantidad de Acciones')
            plt.xticks(rotation=0)
            plt.tight_layout()
            plt.savefig(SCRIPT_DIR / '5_grafico_horas_pico.png')
            plt.close()
            print_success("  - Gráfico 5 (Horas Pico) guardado.")
    except Exception as e:
        print_error(f"  - Error al generar Gráfico 5: {e}")


# --- Funciones de Utilidad (Impresión) ---
def print_header(title):
    print("\n" + "="*70)
    print(f" {title.upper()} ".center(70, "="))
    print("="*70)

def print_subheader(title):
    print(f"\n--- {title} ---")

def print_success(message):
    # Verde
    print(f"\033[92m[ÉXITO] {message}\033[0m")

def print_error(message):
    # Rojo
    print(f"\033[91m[ERROR] {message}\033[0m")

def print_warning(message):
    # Amarillo
    print(f"\033[93m[AVISO] {message}\033[0m")

# --- Función Principal ---
def main():
    # 1. Cargar Datos
    print_header("Fase 1: Carga de Datos")
    df_log_completo = cargar_admin_log()
    if df_log_completo is None:
        print_error("Fallo crítico al cargar 'admin_log.csv'. El script no puede continuar.")
        sys.exit(1)
        
    df_perfiles = cargar_perfiles_locales()

    # 2. Obtener Filtros
    df_log_filtrado = obtener_filtros_interactivos(df_log_completo)

    # 3. Realizar Análisis
    analizar_datos(df_log_filtrado, df_perfiles)
    
    # 4. Generar Gráficos
    generar_graficos(df_log_filtrado, df_perfiles)
    
    print_header("Análisis Completado")
    print_success(f"Reporte impreso en consola y gráficos (si se generaron) guardados en:\n{SCRIPT_DIR}")

if __name__ == "__main__":
    main()
