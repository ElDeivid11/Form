import flet as ft
import sqlite3
import datetime
import os
import shutil
import sys
import json
import pytz 
import smtplib 
import tempfile # CLAVE PARA ANDROID
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import flet.canvas as cv
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image, ImageDraw

# ==========================================
# 1. CONFIGURACIÓN GENERAL
# ==========================================
NOMBRE_EMPRESA_ONEDRIVE = "Tecnocomp Computacion Ltda" 
NOMBRE_CARPETA_ONEDRIVE = "Visitas Terreno"
# Carpeta local solo se usará si estamos en Windows para respaldo
CARPETA_LOCAL_INFORMES = "Informes" 

TAREAS_MANTENIMIENTO = [
    "Borrar Temporales", "Actualizaciones Windows", "Revisión Antivirus", 
    "Limpieza Física", "Optimización Disco", "Revisión Cables"
]

CORREOS_POR_CLIENTE = {
    "Intermar": "contacto@intermar.cl", 
    "Las200": "admin@las200.cl"
}
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_REMITENTE = "enviodeinformestc1234@gmail.com" 
EMAIL_PASSWORD = "gedc vmtb rjph hyrn" 

USUARIOS_POR_CLIENTE = {
    "Intermar": ["Raimundo Chico", "Raimundo Grande", "Usuario ejemplo"],
    "Las200": ["Nieves Vallejos", "Jennifer No se cuanto", "Benjamin Practicas"]
}

# --- PALETA DE COLORES ---
COLOR_PRIMARIO = "#0583F2"
COLOR_SECUNDARIO = "#2685BF"
COLOR_ACCENTO = "#2BB9D9"
COLOR_ROJO_SUAVE = "#FFE5E5" 
COLOR_AZUL_SUAVE = "#E0F2FF"
COLOR_BLANCO = "#FFFFFF" 
COLOR_TEXTO_GLOBAL = "#0D0D0D" 

COLORES = {
    "light": {
        "fondo": "#F5F8FA", "superficie": "#FFFFFF", "texto": "#0D0D0D",
        "texto_sec": "grey", "sombra": "#1A0583F2", "borde": "#E0E0E0", "input_bg": "#FFFFFF"
    },
    "dark": {
        "fondo": "#121212", "superficie": "#1E1E1E", "texto": "#FFFFFF",
        "texto_sec": "#B0B0B0", "sombra": "#00000000", "borde": "#333333", "input_bg": "#2C2C2C"
    }
}

# --- CLASE PDF PERSONALIZADA (DISEÑO PREMIUM) ---
class PDFReporte(FPDF):
    def header(self):
        # Barra Azul Superior
        self.set_fill_color(5, 131, 242) # RGB #0583F2
        self.rect(0, 0, 210, 42, 'F')
        
        # Logo Blanco (logo2.png)
        logo_to_use = "logo2.png" if os.path.exists("logo2.png") else ("logo.png" if os.path.exists("logo.png") else None)
        if logo_to_use:
            try: self.image(logo_to_use, x=10, y=6, w=50) 
            except: pass
            
        # Título
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(140, 15)
        self.cell(60, 10, 'INFORME TÉCNICO', 0, 0, 'R')
        self.ln(45)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}} - App Visitas Tecnocomp', 0, 0, 'C')

def main(page: ft.Page):
    page.title = "Tecnocomp Mobile"
    page.window_width = 400
    page.window_height = 850
    page.padding = 0 
    page.scroll = "adaptive" # Vital para móviles

    # Estado Global
    app_state = {"tema": "light"}
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = COLORES["light"]["fondo"]
    
    # Variable para guardar la ruta temporal del PDF
    ultimo_pdf_generado = ft.Text("", visible=False) 

    def cambiar_tema(e):
        app_state["tema"] = "dark" if app_state["tema"] == "light" else "light"
        nuevo = app_state["tema"]
        page.theme_mode = ft.ThemeMode.DARK if nuevo == "dark" else ft.ThemeMode.LIGHT
        page.bgcolor = COLORES[nuevo]["fondo"]
        page.views.clear()
        route_change(page.route)
        page.update()

    # Solo creamos carpeta local si estamos en PC
    if sys.platform == "win32":
        if not os.path.exists(CARPETA_LOCAL_INFORMES): os.makedirs(CARPETA_LOCAL_INFORMES)

    # ==========================================
    # 2. BASE DE DATOS
    # ==========================================
    def inicializar_db():
        con = sqlite3.connect("visitas.db")
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reportes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT, cliente TEXT, tecnico TEXT, observaciones TEXT,
                imagen_path TEXT, pdf_path TEXT, detalles_usuarios TEXT
            )
        """)
        try: cur.execute("ALTER TABLE reportes ADD COLUMN pdf_path TEXT")
        except: pass
        try: cur.execute("ALTER TABLE reportes ADD COLUMN detalles_usuarios TEXT")
        except: pass
        con.commit(); con.close()
    inicializar_db()

    # ==========================================
    # 3. BACKEND
    # ==========================================
    def obtener_hora_chile():
        try: return datetime.datetime.now(pytz.timezone('Chile/Continental'))
        except: return datetime.datetime.now()

    def obtener_conteo_reportes():
        con = sqlite3.connect("visitas.db"); cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM reportes")
        total = cur.fetchone()[0]; con.close(); return total

    def obtener_historial():
        con = sqlite3.connect("visitas.db"); cur = con.cursor()
        cur.execute("SELECT id, fecha, cliente, tecnico, observaciones, pdf_path FROM reportes ORDER BY id DESC")
        datos = cur.fetchall(); con.close(); return datos

    def enviar_correo_smtp(ruta_pdf, cliente, tecnico):
        if not os.path.exists(ruta_pdf): return False, "PDF no existe."
        dest = CORREOS_POR_CLIENTE.get(cliente, "")
        if not dest: return False, f"No hay correo para {cliente}"
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMITENTE; msg['To'] = dest
        msg['Subject'] = f"Reporte - {cliente} - {datetime.datetime.now().strftime('%d/%m')}"
        cuerpo = f"""<html><body><h2 style="color:{COLOR_PRIMARIO};">Reporte de Visita</h2><p>Adjunto informe técnico.</p></body></html>"""
        msg.attach(MIMEText(cuerpo, 'html'))
        
        try:
            with open(ruta_pdf, "rb") as att:
                part = MIMEBase("application", "octet-stream"); part.set_payload(att.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(ruta_pdf)}")
            msg.attach(part)
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT); server.starttls()
            server.login(EMAIL_REMITENTE, EMAIL_PASSWORD); server.sendmail(EMAIL_REMITENTE, dest, msg.as_string()); server.quit()
            return True, f"Enviado a {dest}"
        except Exception as e: return False, f"Error Envío: {e}"

    def copiar_a_onedrive(ruta_pdf):
        if sys.platform != "win32": return False, "OneDrive sync solo en PC"
        if not ruta_pdf or not os.path.exists(ruta_pdf): return False, "PDF no existe"
        home = os.path.expanduser("~")
        posibles = [os.path.join(home, f"OneDrive - {NOMBRE_EMPRESA_ONEDRIVE}"), os.path.join(home, "OneDrive")]
        root = next((p for p in posibles if os.path.exists(p)), None)
        if not root: return False, "No OneDrive"
        dest = os.path.join(root, NOMBRE_CARPETA_ONEDRIVE)
        if not os.path.exists(dest): os.makedirs(dest)
        try: shutil.copy2(ruta_pdf, os.path.join(dest, os.path.basename(ruta_pdf))); return True, "Sync OK"
        except Exception as e: return False, str(e)

    def guardar_firma_img(trazos):
        if not trazos: return None
        # GUARDAMOS EN TEMP PARA EVITAR PERMISOS EN ANDROID
        temp_dir = tempfile.gettempdir()
        path = os.path.join(temp_dir, "firma_temp.png")
        img = Image.new("RGB", (400, 200), "white"); draw = ImageDraw.Draw(img)
        for t in trazos:
            if len(t) > 1: draw.line(t, fill="black", width=3)
            elif len(t) == 1: draw.point(t[0], fill="black")
        img.save(path); return path

    # --- GENERADOR PDF PREMIUM ---
    def generar_pdf(cliente, tecnico, obs, path_firma, datos_usuarios):
        pdf = PDFReporte(orientation='P', unit='mm', format='A4')
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Bloque Gris Datos
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(10, 48, 190, 28, 'F')
        
        pdf.set_xy(15, 53); pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(100, 100, 100); pdf.cell(25, 6, "CLIENTE:", 0, 0)
        pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(0, 0, 0); pdf.cell(0, 6, cliente, 0, 1)
        pdf.set_x(15); pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(100, 100, 100); pdf.cell(25, 6, "TÉCNICO:", 0, 0)
        pdf.set_font("Helvetica", "", 11); pdf.set_text_color(0, 0, 0); pdf.cell(0, 6, tecnico, 0, 1)
        pdf.set_x(15); pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(100, 100, 100); pdf.cell(25, 6, "FECHA:", 0, 0)
        pdf.set_font("Helvetica", "", 11); pdf.set_text_color(0, 0, 0); 
        pdf.cell(0, 6, obtener_hora_chile().strftime('%d/%m/%Y %H:%M'), 0, 1)

        pdf.ln(15)

        # Título
        pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(5, 131, 242); pdf.cell(0, 8, "BITÁCORA DE ATENCIÓN", 0, 1, 'L'); pdf.ln(2)
        pdf.set_draw_color(200, 200, 200); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)

        for u in datos_usuarios:
            if pdf.get_y() > 220: pdf.add_page()
            pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(0, 0, 0); pdf.cell(140, 8, u['nombre'], 0, 0, 'L')
            pdf.set_font("Helvetica", "B", 9)
            if u['atendido']: pdf.set_fill_color(220, 255, 220); pdf.set_text_color(0, 100, 0); pdf.cell(50, 8, "ATENDIDO", 0, 1, 'C', True)
            else: pdf.set_fill_color(255, 220, 220); pdf.set_text_color(180, 0, 0); pdf.cell(50, 8, "NO ATENDIDO", 0, 1, 'C', True)
            pdf.set_text_color(0, 0, 0); pdf.ln(2); pdf.set_x(10); pdf.set_font("Helvetica", "", 10)
            texto = f"Trabajo: {u['trabajo']}" if u['atendido'] else f"Motivo: {u['motivo']}"
            pdf.multi_cell(0, 5, texto, 0, 'L')

            # FOTOS (IMÁGENES GRANDES)
            if u['fotos'] and u['atendido']:
                pdf.ln(2); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(5, 131, 242); pdf.cell(0, 4, "Evidencias Adjuntas:", 0, 1)
                x_curr, y_curr = 10, pdf.get_y() + 1
                for fp in u['fotos']:
                    if os.path.exists(fp):
                        if x_curr + 45 > 200: x_curr = 10; y_curr += 40
                        if y_curr + 40 > 250: pdf.add_page(); x_curr = 10; y_curr = pdf.get_y()
                        try: pdf.image(fp, x=x_curr, y=y_curr, h=35); x_curr += 48
                        except: pass
                pdf.set_y(y_curr + 40) 

            pdf.ln(5); pdf.set_draw_color(230, 230, 230); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)

        if pdf.get_y() > 220: pdf.add_page()
        pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(5, 131, 242); pdf.cell(0, 8, "OBSERVACIONES ADICIONALES", 0, 1, 'L')
        pdf.set_font("Helvetica", "", 10); pdf.set_text_color(0,0,0); pdf.multi_cell(0, 6, obs if obs else "Sin observaciones adicionales.", 0, 'L'); pdf.ln(10)
        
        if path_firma and os.path.exists(path_firma):
            if pdf.get_y() > 200: pdf.add_page()
            pdf.set_font("Helvetica", "B", 11); pdf.cell(0, 6, "CONFORMIDAD DEL SERVICIO", 0, 1, 'L'); pdf.image(path_firma, w=50)

        # GUARDAR EN TEMP (FIX ANDROID)
        temp_dir = tempfile.gettempdir()
        nombre = f"Reporte_{cliente}_{obtener_hora_chile().strftime('%Y%m%d_%H%M%S')}.pdf"
        ruta = os.path.join(temp_dir, nombre)
        pdf.output(ruta)
        return ruta

    # ==========================================
    # 4. UI HELPERS
    # ==========================================
    def crear_header(c):
        return ft.Container(content=ft.Column([
            ft.Row([
                ft.Row([ft.Icon(ft.Icons.DASHBOARD_ROUNDED, color=COLOR_PRIMARIO, size=28), ft.Text("PANEL DE CONTROL", color=COLOR_PRIMARIO, weight="bold", size=16)]),
                ft.IconButton(icon=ft.Icons.DARK_MODE if app_state["tema"]=="light" else ft.Icons.LIGHT_MODE, icon_color=c["texto"], on_click=cambiar_tema)
            ], alignment="spaceBetween"),
            ft.Divider(height=10, color="transparent"),
            ft.Container(content=ft.Image(src="logo.png", width=200, fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.BROKEN_IMAGE)), bgcolor="white" if app_state["tema"]=="dark" else None, border_radius=10, padding=5 if app_state["tema"]=="dark" else 0, shadow=ft.BoxShadow(blur_radius=20, color=c["sombra"], offset=ft.Offset(0, 5))),
            ft.Divider(height=10, color="transparent"),
            ft.Text("Bienvenido, Técnico", size=26, weight="bold", color=c["texto"]), ft.Text("Gestión de Visitas", size=14, color=c["texto_sec"], weight="w500")
        ], horizontal_alignment="center", spacing=5), bgcolor=c["superficie"], width=float("inf"), padding=ft.padding.only(top=50, bottom=30, left=20, right=20), border_radius=ft.border_radius.only(bottom_left=40, bottom_right=40), shadow=ft.BoxShadow(blur_radius=20, color="#15000000", offset=ft.Offset(0, 10)))

    def crear_stats_card(c):
        return ft.Container(content=ft.Row([ft.Container(content=ft.Icon(ft.Icons.FOLDER_SHARED_ROUNDED, color=COLOR_BLANCO, size=30), bgcolor=COLOR_ACCENTO, padding=12, border_radius=12), ft.Column([ft.Text("Total Reportes", color=c["texto_sec"], size=13, weight="w500"), ft.Text(str(obtener_conteo_reportes()), weight="bold", size=28, color=c["texto"])], spacing=2)], alignment="start", spacing=15), bgcolor=c["superficie"], padding=ft.padding.symmetric(vertical=15, horizontal=20), border_radius=20, width=280, shadow=ft.BoxShadow(blur_radius=20, color="#20000000", offset=ft.Offset(0, 10)), margin=ft.margin.only(top=-30, bottom=25), alignment=ft.alignment.center)

    def crear_boton_menu(c, titulo, subtitulo, icono, on_click_action):
        return ft.Container(content=ft.Row([ft.Column([ft.Text(titulo, size=18, weight="bold", color=COLOR_BLANCO), ft.Text(subtitulo, size=12, color="white70")], expand=True, alignment="center", spacing=3), ft.Icon(icono, size=40, color="white54")], alignment="spaceBetween"), gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=[COLOR_PRIMARIO, COLOR_ACCENTO]), padding=20, border_radius=18, shadow=ft.BoxShadow(blur_radius=10, color=c["sombra"], offset=ft.Offset(0, 5)), on_click=on_click_action, ink=True)

    # ==========================================
    # 5. RUTEADOR
    # ==========================================
    def route_change(route):
        page.views.clear(); c = COLORES[app_state["tema"]]
        
        # DASHBOARD
        page.views.append(ft.View("/", controls=[crear_header(c), ft.Container(content=ft.Column([crear_stats_card(c), crear_boton_menu(c, "Nueva Visita", "Crear reporte y firmar", ft.Icons.ADD_LOCATION_ALT_ROUNDED, lambda _: page.go("/nueva_visita")), ft.Divider(height=15, color="transparent"), ft.Container(content=ft.Row([ft.Column([ft.Text("Historial", size=18, weight="bold", color=COLOR_BLANCO), ft.Text("Ver reportes anteriores", size=12, color="white70")], expand=True, alignment="center", spacing=3), ft.Icon(ft.Icons.HISTORY, size=40, color="white54")], alignment="spaceBetween"), gradient=ft.LinearGradient(colors=["#F2994A", "#F2C94C"]), padding=20, border_radius=18, shadow=ft.BoxShadow(blur_radius=10, color="#33F2994A", offset=ft.Offset(0, 5)), on_click=lambda _: page.go("/historial"), ink=True)], horizontal_alignment="center"), padding=20, expand=True, alignment=ft.alignment.top_center)], bgcolor=c["fondo"], padding=0))

        # FORMULARIO
        if page.route == "/nueva_visita":
            datos_firma = {"trazos": []}
            txt_tec = ft.TextField(label="Técnico", filled=True, bgcolor=c["input_bg"], color=c["texto"], border_radius=10, prefix_icon=ft.Icons.PERSON, border_color="transparent")
            txt_obs = ft.TextField(label="Notas Adicionales (Opcional)", multiline=True, min_lines=2, filled=True, bgcolor=c["input_bg"], color=c["texto"], border_radius=10, text_size=12, border_color="transparent")
            col_usuarios = ft.Column(); state_usuarios = []; usuario_actual_foto = [None] 
            
            # FILE PICKERS
            fp = ft.FilePicker(on_result=lambda e: actualizar_fotos_usuario(e)); page.overlay.append(fp)
            save_file_picker = ft.FilePicker(on_result=lambda e: notif_guardado(e)); page.overlay.append(save_file_picker)

            def notif_guardado(e):
                if e.path:
                    try: shutil.copy2(ultimo_pdf_generado.value, e.path); page.open(ft.SnackBar(ft.Text(f"PDF Guardado"), bgcolor="green"))
                    except Exception as ex: page.open(ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor="red"))

            def actualizar_fotos_usuario(e):
                if e.files and usuario_actual_foto[0] is not None:
                    u = state_usuarios[usuario_actual_foto[0]]
                    for f in e.files: u["lista_fotos"].append(f.path)
                    u["control_galeria"].controls.clear()
                    for p in u["lista_fotos"]: u["control_galeria"].controls.append(ft.Container(content=ft.Image(src=p, width=50, height=50, fit=ft.ImageFit.COVER, border_radius=5), border=ft.border.all(1, c["borde"]), border_radius=5))
                    u["control_galeria"].update()
                    page.open(ft.SnackBar(ft.Text(f"Fotos agregadas"), bgcolor="green"))

            def cargar_usuarios(cliente):
                col_usuarios.controls.clear(); state_usuarios.clear()
                nombres = USUARIOS_POR_CLIENTE.get(cliente, [])
                for i, nombre in enumerate(nombres):
                    chk = ft.Checkbox(label="Atendido", value=True, fill_color=COLOR_PRIMARIO)
                    bg_inp = "#E0F2FF" if app_state["tema"]=="light" else "#333333"
                    col_inp = "#000000" if app_state["tema"]=="light" else "#FFFFFF"
                    txt_trabajo = ft.TextField(label="¿Qué se realizó?", value="", read_only=True, multiline=True, text_size=12, bgcolor=bg_inp, color=col_inp, border_color="transparent", border_radius=8)
                    txt_motivo = ft.TextField(label="Motivo no atención", visible=False, text_size=13, height=45, bgcolor=COLOR_ROJO_SUAVE, color="black", border_color="transparent", border_radius=8)
                    
                    estado_tareas = {t: False for t in TAREAS_MANTENIMIENTO}
                    def actualizar_txt_trabajo(dic, inp):
                        hechos = [f"{k} ({v})" for k, v in dic.items() if v]
                        inp.value = "Mantenimiento: " + ", ".join(hechos) if hechos else ""
                        inp.update()
                    def abrir_checklist(e, nom_u=nombre, dic_u=estado_tareas, inp_u=txt_trabajo):
                        lista_checks = []
                        for t in TAREAS_MANTENIMIENTO:
                            def on_ch(e, tarea=t, d=dic_u, i=inp_u):
                                d[tarea] = obtener_hora_chile().strftime("%H:%M") if e.control.value else False
                                actualizar_txt_trabajo(d, i)
                            lista_checks.append(ft.Checkbox(label=t, value=bool(dic_u[t]), on_change=on_ch))
                        dlg_tareas = ft.AlertDialog(title=ft.Text(f"Tareas: {nom_u}"), content=ft.Column(lista_checks, height=300, scroll="auto"), actions=[ft.TextButton("Listo", on_click=lambda e: page.close(dlg_tareas))])
                        page.open(dlg_tareas)

                    btn_checklist = ft.ElevatedButton("Abrir Checklist", icon=ft.Icons.CHECKLIST, bgcolor=COLOR_SECUNDARIO, color="white", on_click=abrir_checklist)
                    row_galeria = ft.Row(scroll="auto")
                    
                    # BOTONES FOTOS SAMSUNG FIX
                    def pick_camera(e, idx=i):
                        usuario_actual_foto[0] = idx
                        fp.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
                    def pick_gallery(e, idx=i):
                        usuario_actual_foto[0] = idx
                        fp.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE)

                    btn_galeria = ft.IconButton(icon=ft.Icons.PHOTO_LIBRARY, tooltip="Galería", icon_color=COLOR_ACCENTO, on_click=lambda e, idx=i: pick_gallery(e, idx))
                    btn_camara = ft.IconButton(icon=ft.Icons.CAMERA_ALT, tooltip="Cámara", icon_color=COLOR_ACCENTO, on_click=lambda e, idx=i: pick_camera(e, idx))
                    
                    cont_detalles = ft.Column([ft.Divider(), btn_checklist, ft.Divider(), ft.Row([btn_galeria, btn_camara, row_galeria])], visible=True)
                    def on_chk(e, tm=txt_motivo, tt=txt_trabajo, cd=cont_detalles):
                        v = e.control.value; tm.visible = not v; tt.visible = v; cd.visible = v; page.update()
                    chk.on_change = on_chk
                    state_usuarios.append({"nombre": nombre, "check": chk, "motivo": txt_motivo, "trabajo": txt_trabajo, "lista_fotos": [], "control_galeria": row_galeria})
                    col_usuarios.controls.append(ft.Container(content=ft.Column([ft.Row([ft.Icon(ft.Icons.PERSON, size=16, color=COLOR_SECUNDARIO), ft.Text(nombre, weight="bold", color=c["texto"], expand=True), chk], alignment="spaceBetween"), txt_motivo, txt_trabajo, cont_detalles]), padding=10, border=ft.border.all(1, c["borde"]), border_radius=8, margin=ft.margin.only(bottom=10)))
                col_usuarios.update()

            dd_cli = ft.Dropdown(label="Cliente", options=[ft.dropdown.Option(k) for k in USUARIOS_POR_CLIENTE.keys()], filled=True, bgcolor=c["input_bg"], color=c["texto"], border_radius=10, border_color="transparent", on_change=lambda e: cargar_usuarios(e.control.value))

            # FIRMA POPUP
            def pan_start(e): datos_firma["trazos"].append([(e.local_x, e.local_y)]); canvas.shapes.append(cv.Path([cv.Path.MoveTo(e.local_x, e.local_y)], paint=ft.Paint(stroke_width=3, color="black", style=ft.PaintingStyle.STROKE))); canvas.update()
            def pan_update(e): datos_firma["trazos"][-1].append((e.local_x, e.local_y)); canvas.shapes[-1].elements.append(cv.Path.LineTo(e.local_x, e.local_y)); canvas.update()
            canvas = cv.Canvas(shapes=[]); gd = ft.GestureDetector(on_pan_start=pan_start, on_pan_update=pan_update, drag_interval=10)
            def abrir_dialogo_firma(e):
                datos_firma["trazos"] = []; canvas.shapes = []
                def confirmar_click(e): page.close(dlg_firma); guardar(None)
                dlg_firma = ft.AlertDialog(title=ft.Text("Firmar Conformidad"), content=ft.Container(content=ft.Stack([canvas, gd]), border=ft.border.all(1, "grey"), border_radius=10, width=300, height=200, bgcolor="white"), actions=[ft.TextButton("Limpiar", on_click=lambda e: [datos_firma["trazos"].clear(), canvas.shapes.clear(), canvas.update()]), ft.ElevatedButton("Confirmar y Guardar", on_click=confirmar_click, bgcolor=COLOR_PRIMARIO, color="white")])
                page.open(dlg_firma)

            btn_ver = ft.ElevatedButton("Guardar PDF", icon=ft.Icons.DOWNLOAD, visible=False, bgcolor="#FF5722", color="white")
            btn_correo = ft.ElevatedButton("Enviar Correo", icon=ft.Icons.EMAIL, visible=False, bgcolor="#0072C6", color="white")

            def guardar(e):
                try:
                    datos_finales = []; todas_fotos = [] 
                    for u in state_usuarios:
                        fotos = u["lista_fotos"]; todas_fotos.extend(fotos)
                        datos_finales.append({"nombre": u["nombre"], "atendido": u["check"].value, "motivo": u["motivo"].value, "trabajo": u["trabajo"].value, "fotos": fotos})
                    json_usr = json.dumps(datos_finales); firma = guardar_firma_img(datos_firma["trazos"]) if datos_firma["trazos"] else None
                    pdf = generar_pdf(dd_cli.value, txt_tec.value, txt_obs.value, firma, datos_finales); ultimo_pdf_generado.value = pdf
                    con = sqlite3.connect("visitas.db"); cur = con.cursor()
                    cur.execute("INSERT INTO reportes (fecha, cliente, tecnico, observaciones, imagen_path, pdf_path, detalles_usuarios) VALUES (?, ?, ?, ?, ?, ?, ?)", (obtener_hora_chile().strftime('%Y-%m-%d %H:%M:%S'), dd_cli.value, txt_tec.value, txt_obs.value, json.dumps(todas_fotos), pdf, json_usr))
                    con.commit(); con.close()
                    page.open(ft.SnackBar(ft.Text(f"Reporte Generado"), bgcolor="green"))
                    def guardar_pdf_device(e): save_file_picker.save_file(file_name=os.path.basename(pdf))
                    btn_ver.visible = True; btn_ver.on_click = guardar_pdf_device; btn_ver.update()
                    btn_correo.visible = True; btn_correo.on_click = lambda _: [page.open(ft.SnackBar(ft.Text(enviar_correo_smtp(pdf, dd_cli.value, txt_tec.value)[1])))]; btn_correo.update()
                    txt_obs.value = ""; cargar_usuarios(dd_cli.value); page.update()
                except Exception as ex: page.open(ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor="red"))

            btn_main_guardar = ft.ElevatedButton("FIRMAR Y FINALIZAR", on_click=lambda e: abrir_dialogo_firma(e) if dd_cli.value and txt_tec.value else page.open(ft.SnackBar(ft.Text("Faltan datos"), bgcolor="red")), height=55, style=ft.ButtonStyle(bgcolor=COLOR_PRIMARIO, color="white", shape=ft.RoundedRectangleBorder(radius=12), text_style=ft.TextStyle(size=16, weight="bold")))
            page.views.append(ft.View("/nueva_visita", controls=[ft.AppBar(title=ft.Text("Nueva Visita", color=c["texto"]), bgcolor=c["superficie"], color=COLOR_PRIMARIO, elevation=0), ft.Container(content=ft.Column([ft.Container(content=ft.Column([ft.Text("Datos Generales", weight="bold", color=COLOR_PRIMARIO), dd_cli, txt_tec]), padding=15, bgcolor=c["superficie"], border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color=c["sombra"])), ft.Container(content=ft.Column([ft.Text("Bitácora por Usuario", weight="bold", color=COLOR_PRIMARIO), col_usuarios]), padding=15, bgcolor=c["superficie"], border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color=c["sombra"])), ft.Container(content=ft.Column([ft.Text("Notas Adicionales", weight="bold", color=COLOR_PRIMARIO), txt_obs]), padding=15, bgcolor=c["superficie"], border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color=c["sombra"])), btn_main_guardar, ft.Row([btn_ver, btn_correo], alignment="center", wrap=True)], scroll="auto"), padding=10, expand=True)], bgcolor=c["fondo"]))

        if page.route == "/historial":
            lista_items = []; datos = obtener_historial()
            if not datos: lista_items.append(ft.Text("Vacío", color="grey"))
            else:
                for row in datos:
                    id_rep, fecha, cli, tec, obs, pdf = row
                    ex = pdf and os.path.exists(pdf)
                    def descargar_historial(e, p=pdf):
                        if p and os.path.exists(p):
                            ultimo_pdf_generado.value = p 
                            save_file_picker.save_file(file_name=os.path.basename(p))
                        else: page.open(ft.SnackBar(ft.Text("No encontrado"), bgcolor="red"))
                    lista_items.append(ft.Container(content=ft.Column([ft.Row([ft.Icon(ft.Icons.DESCRIPTION, color=COLOR_PRIMARIO if ex else "grey"), ft.Text(f"{cli}", weight="bold", color=c["texto"]), ft.Text(f"{fecha}", size=12, color="grey")], alignment="spaceBetween"), ft.Text(f"Técnico: {tec}", color=c["texto"]), ft.TextButton("Descargar PDF", on_click=descargar_historial, disabled=not ex)]), padding=15, bgcolor=c["superficie"], border_radius=12, shadow=ft.BoxShadow(blur_radius=5, color=c["sombra"]), margin=ft.margin.only(bottom=10)))
            page.views.append(ft.View("/historial", controls=[ft.AppBar(title=ft.Text("Historial", color=c["texto"]), bgcolor=c["superficie"], color=COLOR_PRIMARIO, elevation=0), ft.Container(content=ft.ListView(controls=lista_items, spacing=10, padding=20), expand=True)], bgcolor=c["fondo"]))
        page.update()

    def view_pop(view): page.views.pop(); top_view = page.views[-1]; page.go(top_view.route)
    page.on_route_change = route_change; page.on_view_pop = view_pop; page.go(page.route)

ft.app(target=main)