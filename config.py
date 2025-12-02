import os

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================

FONT_FAMILY = "Poppins"
NOMBRE_EMPRESA_ONEDRIVE = "Tecnocomp Computacion Ltda"
CARPETA_LOCAL_INFORMES = "Informes"

# Tareas por defecto
TAREAS_MANTENIMIENTO = [
    "Borrar Temporales", "Actualizaciones Windows", "Revisión Antivirus",
    "Limpieza Física", "Optimización Disco", "Revisión Cables"
]

# DATOS INICIALES (Necesarios para la migración a Base de Datos)
CORREOS_POR_CLIENTE = {
    "Intermar": "contacto@intermar.cl",
    "Las200": "admin@las200.cl"
}

USUARIOS_POR_CLIENTE = {
    "Intermar": ["Raimundo Chico", "Raimundo Grande", "Usuario ejemplo"],
    "Las200": ["Nieves Vallejos", "Jennifer No se cuanto", "Benjamin Practicas"]
}

# Configuración de Email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_REMITENTE = "enviodeinformestc1234@gmail.com"
EMAIL_PASSWORD = "gedc vmtb rjph hyrn"

# Paleta de Colores
COLOR_PRIMARIO = "#0583F2"
COLOR_SECUNDARIO = "#2685BF"
COLOR_ACCENTO = "#2BB9D9"
COLOR_ROJO_SUAVE = "#FFE5E5"
COLOR_AZUL_SUAVE = "#E0F2FF"
COLOR_BLANCO = "#FFFFFF"

COLORES = {
    "light": {
        "fondo": "#F5F8FA", "superficie": "#FFFFFF", "texto": "#0D0D0D",
        "texto_sec": "grey", "sombra": "#1A0583F2", "borde": "#E0E0E0",
        "input_bg": "#FFFFFF", "card_bg": "#FFFFFF"
    },
    "dark": {
        "fondo": "#121212", "superficie": "#1E1E1E", "texto": "#FFFFFF",
        "texto_sec": "#B0B0B0", "sombra": "#00000000", "borde": "#333333",
        "input_bg": "#2C2C2C", "card_bg": "#1E1E1E"
    }
}

COLORES_GRAFICOS = ["blue", "purple", "teal", "orange", "pink", "cyan", "indigo"]

# Asegurar directorios
if not os.path.exists(CARPETA_LOCAL_INFORMES):
    os.makedirs(CARPETA_LOCAL_INFORMES)