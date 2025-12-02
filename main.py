import flet as ft
import sqlite3
import datetime
import os
import shutil
import sys
import json
import pytz 
import smtplib 
import tempfile
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
FONT_FAMILY = "Poppins"
NOMBRE_EMPRESA_ONEDRIVE = "Tecnocomp Computacion Ltda" 
NOMBRE_CARPETA_ONEDRIVE = "Visitas Terreno"
CARPETA_LOCAL_INFORMES = "Informes"

TAREAS_MANTENIMIENTO = ["Borrar Temporales", "Actualizaciones Windows", "Revisión Antivirus", "Limpieza Física", "Optimización Disco", "Revisión Cables"]

CORREOS_POR_CLIENTE = {"Intermar": "contacto@intermar.cl", "Las200": "admin@las200.cl"}
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_REMITENTE = "enviodeinformestc1234@gmail.com" 
EMAIL_PASSWORD = "gedc vmtb rjph hyrn" 

USUARIOS_POR_CLIENTE = {
    "Intermar": ["Raimundo Chico", "Raimundo Grande", "Usuario ejemplo"],
    "Las200": ["Nieves Vallejos", "Jennifer No se cuanto", "Benjamin Practicas"]
}

# Paleta de Colores
COLOR_PRIMARIO = "#0583F2"; COLOR_SECUNDARIO = "#2685BF"; COLOR_ACCENTO = "#2BB9D9"
COLOR_ROJO_SUAVE = "#FFE5E5"; COLOR_AZUL_SUAVE = "#E0F2FF"; COLOR_BLANCO = "#FFFFFF"; COLOR_TEXTO_GLOBAL = "#0D0D0D" 

COLORES = {
    "light": {"fondo": "#F5F8FA", "superficie": "#FFFFFF", "texto": "#0D0D0D", "texto_sec": "grey", "sombra": "#1A0583F2", "borde": "#E0E0E0", "input_bg": "#FFFFFF", "card_bg": "#FFFFFF"},
    "dark": {"fondo": "#121212", "superficie": "#1E1E1E", "texto": "#FFFFFF", "texto_sec": "#B0B0B0", "sombra": "#00000000", "borde": "#333333", "input_bg": "#2C2C2C", "card_bg": "#1E1E1E"}
}
COLORES_GRAFICOS = ["blue", "purple", "teal", "orange", "pink", "cyan", "indigo"]

# --- CLASE PDF ---
class PDFReporte(FPDF):
    def header(self):
        self.set_fill_color(5, 131, 242); self.rect(0, 0, 210, 42, 'F')
        logo = "logo.png" if os.path.exists("logo.png") else ("logo2.png" if os.path.exists("logo2.png") else None)
        if logo:
            try: self.image(logo, x=10, y=6, w=50) 
            except: pass
        self.set_font('Helvetica', 'B', 16); self.set_text_color(255, 255, 255); self.set_xy(140, 15)
        self.cell(60, 10, 'INFORME TÉCNICO', 0, 0, 'R'); self.ln(45)
    def footer(self):
        self.set_y(-15); self.set_font('Helvetica', 'I', 8); self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}} - App Visitas Tecnocomp', 0, 0, 'C')

def main(page: ft.Page):
    page.title = "Tecnocomp Mobile"; page.window_width = 400; page.window_height = 850
    page.padding = 0; page.scroll = "adaptive"
    page.fonts = {"Poppins": "https://fonts.gstatic.com/s/poppins/v20/pxiByp8kv8JHgFVrLEj6Z1xlFd2JQEk.woff2"}
    page.theme = ft.Theme(font_family=FONT_FAMILY, use_material3=True)
    app_state = {"tema": "light"}; page.theme_mode = ft.ThemeMode.LIGHT; page.bgcolor = COLORES["light"]["fondo"]
    ultimo_pdf_generado = ft.Text("", visible=False)

    def cambiar_tema(e):
        app_state["tema"] = "dark" if app_state["tema"] == "light" else "light"
        page.theme_mode = ft.ThemeMode.DARK if app_state["tema"] == "dark" else ft.ThemeMode.LIGHT
        page.bgcolor = COLORES[app_state["tema"]]["fondo"]
        page.views.clear(); route_change(page.route); page.update()

    if sys.platform == "win32" and not os.path.exists(CARPETA_LOCAL_INFORMES): os.makedirs(CARPETA_LOCAL_INFORMES)

    # --- BASE DE DATOS ---
    def inicializar_db():
        con = sqlite3.connect("visitas.db"); cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, cliente TEXT, tecnico TEXT, observaciones TEXT, imagen_path TEXT, pdf_path TEXT, detalles_usuarios TEXT, email_enviado INTEGER DEFAULT 0)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS tecnicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)""")
        try: cur.execute("ALTER TABLE reportes ADD COLUMN pdf_path TEXT")
        except: pass
        try: cur.execute("ALTER TABLE reportes ADD COLUMN detalles_usuarios TEXT")
        except: pass
        try: cur.execute("ALTER TABLE reportes ADD COLUMN email_enviado INTEGER DEFAULT 0")
        except: pass
        cur.execute("SELECT COUNT(*) FROM tecnicos")
        if cur.fetchone()[0] == 0: cur.executemany("INSERT OR IGNORE INTO tecnicos (nombre) VALUES (?)", [("Francisco Alfaro",), ("David Quezada",)])
        con.commit(); con.close()
    inicializar_db()

    # --- BACKEND ---
    def obtener_hora_chile():
        try: return datetime.datetime.now(pytz.timezone('Chile/Continental'))
        except: return datetime.datetime.now()

    def obtener_tecnicos():
        con = sqlite3.connect("visitas.db"); cur = con.cursor()
        cur.execute("SELECT nombre FROM tecnicos ORDER BY nombre ASC")
        lista = [row[0] for row in cur.fetchall()]; con.close(); return lista

    def agregar_nuevo_tecnico(nombre):
        if not nombre: return False
        try:
            con = sqlite3.connect("visitas.db"); cur = con.cursor()
            cur.execute("INSERT INTO tecnicos (nombre) VALUES (?)", (nombre,))
            con.commit(); con.close(); return True
        except: return False

    def eliminar_tecnico(nombre):
        if not nombre: return False
        try:
            con = sqlite3.connect("visitas.db"); cur = con.cursor()
            cur.execute("DELETE FROM tecnicos WHERE nombre = ?", (nombre,))
            con.commit(); con.close(); return True
        except: return False

    def obtener_conteo_reportes():
        con = sqlite3.connect("visitas.db"); cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM reportes"); total = cur.fetchone()[0]; con.close(); return total

    def obtener_historial():
        con = sqlite3.connect("visitas.db"); cur = con.cursor()
        cur.execute("SELECT id, fecha, cliente, tecnico, observaciones, pdf_path, email_enviado, detalles_usuarios, imagen_path FROM reportes ORDER BY id DESC")
        datos = cur.fetchall(); con.close(); return datos

    def obtener_datos_clientes():
        con = sqlite3.connect("visitas.db"); cur = con.cursor()
        cur.execute("SELECT cliente, COUNT(*) FROM reportes GROUP BY cliente ORDER BY COUNT(*) DESC")
        datos = cur.fetchall(); con.close(); return datos

    def obtener_datos_tecnicos():
        con = sqlite3.connect("visitas.db"); cur = con.cursor()
        cur.execute("SELECT tecnico, COUNT(*) FROM reportes GROUP BY tecnico ORDER BY COUNT(*) DESC")
        datos = cur.fetchall(); con.close(); return datos

    def actualizar_estado_email(id_reporte, estado):
        con = sqlite3.connect("visitas.db"); cur = con.cursor()
        cur.execute("UPDATE reportes SET email_enviado = ? WHERE id = ?", (estado, id_reporte)); con.commit(); con.close()

    def enviar_correo_smtp(ruta_pdf, cliente, tecnico):
        if not os.path.exists(ruta_pdf): return False, "PDF no existe."
        dest = CORREOS_POR_CLIENTE.get(cliente, "")
        if not dest: return False, f"No hay correo para {cliente}"
        msg = MIMEMultipart(); msg['From'] = EMAIL_REMITENTE; msg['To'] = dest
        msg['Subject'] = f"Reporte - {cliente} - {datetime.datetime.now().strftime('%d/%m')}"
        cuerpo = f"""<html><body><h2 style="color:{COLOR_PRIMARIO};">Reporte de Visita</h2><p>Adjunto informe técnico.</p></body></html>"""
        msg.attach(MIMEText(cuerpo, 'html'))
        try:
            with open(ruta_pdf, "rb") as att: part = MIMEBase("application", "octet-stream"); part.set_payload(att.read())
            encoders.encode_base64(part); part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(ruta_pdf)}")
            msg.attach(part)
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT); server.starttls()
            server.login(EMAIL_REMITENTE, EMAIL_PASSWORD); server.sendmail(EMAIL_REMITENTE, dest, msg.as_string()); server.quit()
            return True, f"Enviado a {dest}"
        except Exception as e: return False, f"Error Envío: {e}"

    def guardar_firma_img(trazos, nombre_archivo="firma_temp.png"):
        if not trazos: return None
        temp_dir = tempfile.gettempdir()
        path = os.path.join(temp_dir, nombre_archivo)
        img = Image.new("RGB", (400, 200), "white"); draw = ImageDraw.Draw(img)
        for t in trazos:
            if len(t) > 1: draw.line(t, fill="black", width=3)
            elif len(t) == 1: draw.point(t[0], fill="black")
        img.save(path); return path

    def generar_pdf(cliente, tecnico, obs, path_firma, datos_usuarios):
        pdf = PDFReporte(orientation='P', unit='mm', format='A4'); pdf.alias_nb_pages(); pdf.add_page()
        pdf.set_fill_color(240, 240, 240); pdf.rect(10, 48, 190, 28, 'F')
        pdf.set_xy(15, 53); pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(100, 100, 100); pdf.cell(25, 6, "CLIENTE:", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(0, 0, 0); pdf.cell(0, 6, cliente, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(15); pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(100, 100, 100); pdf.cell(25, 6, "TÉCNICO:", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 11); pdf.set_text_color(0, 0, 0); pdf.cell(0, 6, tecnico, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(15); pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(100, 100, 100); pdf.cell(25, 6, "FECHA:", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 11); pdf.set_text_color(0, 0, 0); pdf.cell(0, 6, obtener_hora_chile().strftime('%d/%m/%Y %H:%M'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(15); pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(5, 131, 242); pdf.cell(0, 8, "BITÁCORA DE ATENCIÓN", align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(2)
        pdf.set_draw_color(200, 200, 200); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)

        for u in datos_usuarios:
            if pdf.get_y() > 220: pdf.add_page()
            pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(0, 0, 0); pdf.cell(140, 8, u['nombre'], new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
            pdf.set_font("Helvetica", "B", 9)
            if u['atendido']: pdf.set_fill_color(220, 255, 220); pdf.set_text_color(0, 100, 0); pdf.cell(50, 8, "ATENDIDO", align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else: pdf.set_fill_color(255, 220, 220); pdf.set_text_color(180, 0, 0); pdf.cell(50, 8, "NO ATENDIDO", align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0); pdf.ln(2); pdf.set_x(10); pdf.set_font("Helvetica", "", 10)
            texto = f"Trabajo: {u['trabajo']}" if u['atendido'] else f"Motivo: {u['motivo']}"; pdf.multi_cell(0, 5, texto, align='L')
            
            if u['fotos'] and u['atendido']:
                pdf.ln(2); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(5, 131, 242); pdf.cell(0, 4, "Evidencias:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                x_c, y_c = 10, pdf.get_y() + 1
                for fp in u['fotos']:
                    if os.path.exists(fp):
                        if x_c + 45 > 200: x_c = 10; y_c += 40
                        if y_c + 40 > 250: pdf.add_page(); x_c = 10; y_c = pdf.get_y()
                        try: pdf.image(fp, x=x_c, y=y_c, h=35); x_c += 48
                        except: pass
                pdf.set_y(y_c + 40)
            
            firma_usr = u.get('firma')
            if firma_usr and os.path.exists(firma_usr):
                if pdf.get_y() + 30 > 270: pdf.add_page()
                pdf.ln(2); pdf.set_x(10); pdf.set_font("Helvetica", "B", 8); pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 4, f"Firma de conformidad - {u['nombre']}:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                try: pdf.image(firma_usr, w=40); pdf.ln(5)
                except: pass

            pdf.ln(5); pdf.set_draw_color(230, 230, 230); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)

        if pdf.get_y() > 220: pdf.add_page()
        pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(5, 131, 242); pdf.cell(0, 8, "OBSERVACIONES ADICIONALES", align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10); pdf.set_text_color(0,0,0); pdf.multi_cell(0, 6, obs if obs else "Sin observaciones adicionales.", align='L'); pdf.ln(10)
        
        if path_firma and os.path.exists(path_firma):
            if pdf.get_y() > 200: pdf.add_page()
            pdf.set_font("Helvetica", "B", 11); pdf.cell(0, 6, "CONFORMIDAD DEL SERVICIO", align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.image(path_firma, w=50)

        temp_dir = tempfile.gettempdir()
        nombre = f"Reporte_{cliente}_{obtener_hora_chile().strftime('%Y%m%d_%H%M%S')}.pdf"
        ruta = os.path.join(temp_dir, nombre)
        pdf.output(ruta)
        return ruta

    # --- UI HELPERS ---
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

    def crear_boton_menu(c, titulo, subtitulo, icono, on_click_action, grad_colors=[COLOR_PRIMARIO, COLOR_ACCENTO]):
        return ft.Container(content=ft.Row([ft.Column([ft.Text(titulo, size=18, weight="bold", color=COLOR_BLANCO), ft.Text(subtitulo, size=12, color="white70")], expand=True, alignment="center", spacing=3), ft.Icon(icono, size=40, color="white54")], alignment="spaceBetween"), gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=grad_colors), padding=20, border_radius=18, shadow=ft.BoxShadow(blur_radius=10, color=c["sombra"], offset=ft.Offset(0, 5)), on_click=on_click_action, ink=True)

    def crear_seccion(c, titulo, contenido):
        return ft.Container(content=ft.Column([ft.Text(titulo, weight="bold", size=16, color=COLOR_PRIMARIO), ft.Divider(height=15, color="transparent"), contenido]), padding=20, bgcolor=c["card_bg"], border_radius=18, shadow=ft.BoxShadow(blur_radius=15, color=c["sombra"], offset=ft.Offset(0, 5)), margin=ft.margin.only(bottom=20))

    # --- RUTEADOR ---
    def route_change(route):
        page.views.clear(); c = COLORES[app_state["tema"]]
        
        page.views.append(ft.View("/", controls=[
            crear_header(c), 
            ft.Container(content=ft.Column([
                crear_stats_card(c), 
                crear_boton_menu(c, "Nueva Visita", "Crear reporte y firmar", ft.Icons.ADD_LOCATION_ALT_ROUNDED, lambda _: page.go("/nueva_visita")),
                ft.Divider(height=15, color="transparent"), 
                crear_boton_menu(c, "Historial", "Ver reportes anteriores", ft.Icons.HISTORY, lambda _: page.go("/historial"), grad_colors=["#F2994A", "#F2C94C"]),
                ft.Divider(height=15, color="transparent"),
                crear_boton_menu(c, "Métricas", "Estadísticas y gráficos", ft.Icons.BAR_CHART, lambda _: page.go("/metricas"), grad_colors=["#9C27B0", "#E040FB"])
            ], horizontal_alignment="center", scroll="auto"), padding=ft.padding.symmetric(horizontal=25, vertical=10), expand=True, alignment=ft.alignment.top_center)
        ], bgcolor=c["fondo"], padding=0))

        if page.route == "/metricas":
            data_cli = obtener_datos_clientes(); data_tec = obtener_datos_tecnicos()
            pie_sections = [ft.PieChartSection(value=val, title=f"{key}\n{val}", color=COLORES_GRAFICOS[i%len(COLORES_GRAFICOS)], radius=60) for i, (key, val) in enumerate(data_cli)]
            chart_pie = ft.PieChart(sections=pie_sections, sections_space=2, center_space_radius=40, height=200) if pie_sections else ft.Text("Sin datos", color=c["texto_sec"])
            bar_groups = [ft.BarChartGroup(x=i, bar_rods=[ft.BarChartRod(from_y=0, to_y=val, width=30, color=COLOR_ACCENTO, tooltip=f"{key}: {val}", border_radius=5)]) for i, (key, val) in enumerate(data_tec)]
            chart_bar = ft.BarChart(bar_groups=bar_groups, border=ft.border.all(0, "transparent"), left_axis=ft.ChartAxis(labels_size=35), bottom_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=i, label=ft.Text(key[:3], size=10)) for i, (key, val) in enumerate(data_tec)]), height=250) if bar_groups else ft.Text("Sin datos", color=c["texto_sec"])
            card_pie = ft.Container(content=ft.Column([ft.Text("Visitas por Cliente", size=17, weight="bold", color=c["texto"]), ft.Divider(color="transparent", height=15), chart_pie], horizontal_alignment="center"), bgcolor=c["card_bg"], padding=25, border_radius=20, shadow=ft.BoxShadow(blur_radius=15, color=c["sombra"], offset=ft.Offset(0, 5)))
            card_bar = ft.Container(content=ft.Column([ft.Text("Visitas por Técnico", size=17, weight="bold", color=c["texto"]), ft.Divider(color="transparent", height=15), chart_bar], horizontal_alignment="center"), bgcolor=c["card_bg"], padding=25, border_radius=20, shadow=ft.BoxShadow(blur_radius=15, color=c["sombra"], offset=ft.Offset(0, 5)))
            page.views.append(ft.View("/metricas", controls=[ft.AppBar(title=ft.Text("Métricas", color=c["texto"], weight="bold"), bgcolor=c["superficie"], color=COLOR_PRIMARIO, elevation=0, center_title=True), ft.Container(content=ft.Column([card_pie, ft.Divider(height=20, color="transparent"), card_bar], scroll="auto"), padding=25, expand=True)], bgcolor=c["fondo"]))

        if page.route == "/nueva_visita":
            datos_firma = {"trazos": []}; datos_firma_individual = {"trazos": []}
            txt_obs = ft.TextField(label="Notas Adicionales (Opcional)", multiline=True, min_lines=3, filled=True, bgcolor=c["input_bg"], color=c["texto"], border_radius=12, text_size=14, border_color="transparent", prefix_icon=ft.Icons.NOTE_ALT_OUTLINED)
            col_usuarios = ft.Column(spacing=15); state_usuarios = []; usuario_actual_foto = [None] 
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
                    for p in u["lista_fotos"]: u["control_galeria"].controls.append(ft.Container(content=ft.Image(src=p, width=60, height=60, fit=ft.ImageFit.COVER, border_radius=8), border=ft.border.all(1, c["borde"]), border_radius=8, shadow=ft.BoxShadow(blur_radius=5, color=c["sombra"])))
                    u["control_galeria"].update(); page.open(ft.SnackBar(ft.Text(f"Fotos agregadas"), bgcolor="green"))

            lista_tecnicos = obtener_tecnicos()
            dd_tec = ft.Dropdown(label="Técnico Responsable", options=[ft.dropdown.Option(t) for t in lista_tecnicos], filled=True, bgcolor=c["input_bg"], color=c["texto"], border_radius=12, border_color="transparent", text_size=14, expand=True)
            
            # GESTIÓN DE TÉCNICOS (V48)
            def gestionar_tecnicos_dialog(e):
                def refrescar_lista():
                    col_lista_tecs.controls.clear()
                    tecs = obtener_tecnicos()
                    for t_nombre in tecs:
                        col_lista_tecs.controls.append(ft.Row([ft.Text(t_nombre, size=14, weight="bold", expand=True), ft.IconButton(icon=ft.Icons.DELETE_ROUNDED, icon_color="red", on_click=lambda e, n=t_nombre: eliminar_tec(n))], alignment="spaceBetween"))
                    col_lista_tecs.update()
                def eliminar_tec(nombre_t):
                    if eliminar_tecnico(nombre_t):
                        refrescar_lista(); dd_tec.options = [ft.dropdown.Option(t) for t in obtener_tecnicos()]; dd_tec.value = None; dd_tec.update()
                def agregar_tec(e):
                    if txt_new_tec.value:
                        if agregar_nuevo_tecnico(txt_new_tec.value):
                            txt_new_tec.value = ""; refrescar_lista(); dd_tec.options = [ft.dropdown.Option(t) for t in obtener_tecnicos()]; dd_tec.update()
                
                txt_new_tec = ft.TextField(label="Nuevo Técnico", expand=True, height=40, text_size=12)
                col_lista_tecs = ft.Column(height=200, scroll="auto")
                dlg_gestion = ft.AlertDialog(title=ft.Text("Gestionar Técnicos"), content=ft.Container(content=ft.Column([ft.Row([txt_new_tec, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=COLOR_PRIMARIO, on_click=agregar_tec)]), ft.Divider(), col_lista_tecs]), width=300, height=300), actions=[ft.TextButton("Cerrar", on_click=lambda e: page.close(dlg_gestion))])
                page.open(dlg_gestion); refrescar_lista()

            btn_add_tec = ft.IconButton(icon=ft.Icons.MANAGE_ACCOUNTS, icon_color=COLOR_ACCENTO, tooltip="Gestionar", on_click=gestionar_tecnicos_dialog)

            def cargar_usuarios(cliente):
                col_usuarios.controls.clear(); state_usuarios.clear()
                nombres = USUARIOS_POR_CLIENTE.get(cliente, [])
                for i, nombre in enumerate(nombres):
                    chk = ft.Switch(label="Atendido", value=True, active_color=COLOR_PRIMARIO)
                    bg_inp = "#E0F2FF" if app_state["tema"]=="light" else "#333333"
                    col_inp = "#000000" if app_state["tema"]=="light" else "#FFFFFF"
                    txt_trabajo = ft.TextField(label="Detalle del trabajo", value="", read_only=True, multiline=True, text_size=12, bgcolor=bg_inp, color=col_inp, border_color="transparent", border_radius=8)
                    txt_motivo = ft.TextField(label="Motivo de no atención", visible=False, text_size=13, bgcolor=COLOR_ROJO_SUAVE, color="black", border_color="transparent", border_radius=8)
                    
                    row_galeria = ft.Row(scroll="auto", spacing=10)
                    usr_state = {"nombre": nombre, "check": chk, "motivo": txt_motivo, "trabajo": txt_trabajo, "lista_fotos": [], "control_galeria": row_galeria, "firma": None}

                    estado_tareas = {t: False for t in TAREAS_MANTENIMIENTO}
                    def actualizar_txt_trabajo(dic, inp):
                        hechos = [f"{k} ({v})" for k, v in dic.items() if v]; inp.value = "Mantenimiento: " + ", ".join(hechos) if hechos else ""; inp.update()
                    def abrir_checklist(e, nom_u=nombre, dic_u=estado_tareas, inp_u=txt_trabajo):
                        lista_checks = []
                        for t in TAREAS_MANTENIMIENTO:
                            def on_ch(e, tarea=t, d=dic_u, i=inp_u):
                                d[tarea] = obtener_hora_chile().strftime("%H:%M") if e.control.value else False
                                actualizar_txt_trabajo(d, i)
                            lista_checks.append(ft.Checkbox(label=t, value=bool(dic_u[t]), on_change=on_ch))
                        dlg_tareas = ft.AlertDialog(title=ft.Text(f"Checklist: {nom_u}"), content=ft.Container(content=ft.Column(lista_checks, height=300, scroll="auto"), padding=10), actions=[ft.TextButton("Listo", on_click=lambda e: page.close(dlg_tareas))]); page.open(dlg_tareas)
                    
                    btn_checklist = ft.ElevatedButton("Checklist", icon=ft.Icons.CHECKLIST, bgcolor=COLOR_SECUNDARIO, color="white", on_click=abrir_checklist)
                    
                    # FIRMA INDIVIDUAL
                    canvas_ind = cv.Canvas(shapes=[]); gd_ind = ft.GestureDetector(on_pan_start=lambda e: [datos_firma_individual["trazos"].append([(e.local_x, e.local_y)]), canvas_ind.shapes.append(cv.Path([cv.Path.MoveTo(e.local_x, e.local_y)], paint=ft.Paint(stroke_width=3, color="black", style=ft.PaintingStyle.STROKE))), canvas_ind.update()], on_pan_update=lambda e: [datos_firma_individual["trazos"][-1].append((e.local_x, e.local_y)), canvas_ind.shapes[-1].elements.append(cv.Path.LineTo(e.local_x, e.local_y)), canvas_ind.update()])
                    def abrir_firma_ind(e, u_st=usr_state):
                        datos_firma_individual["trazos"] = []; canvas_ind.shapes = []
                        def guardar_f(e):
                            path = guardar_firma_img(datos_firma_individual["trazos"], f"firma_{nombre}_{datetime.datetime.now().timestamp()}.png")
                            u_st["firma"] = path; page.close(d_f); page.open(ft.SnackBar(ft.Text("Firma guardada"), bgcolor="green"))
                        d_f = ft.AlertDialog(title=ft.Text(f"Firma: {nombre}"), content=ft.Container(content=ft.Stack([canvas_ind, gd_ind]), border=ft.border.all(1, "grey"), width=300, height=200, bgcolor="white"), actions=[ft.TextButton("Borrar", on_click=lambda e: [datos_firma_individual["trazos"].clear(), canvas_ind.shapes.clear(), canvas_ind.update()]), ft.ElevatedButton("Guardar", on_click=guardar_f, bgcolor=COLOR_PRIMARIO, color="white")]); page.open(d_f)
                    btn_firma_ind = ft.ElevatedButton("Firmar", icon=ft.Icons.DRAW, bgcolor=COLOR_ACCENTO, color="white", on_click=abrir_firma_ind)

                    def pick_evidence(e, idx=i): usuario_actual_foto[0] = idx; fp.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.ANY)
                    btn_galeria = ft.IconButton(icon=ft.Icons.ADD_PHOTO_ALTERNATE, icon_color=COLOR_ACCENTO, on_click=pick_evidence)
                    btn_camara = ft.IconButton(icon=ft.Icons.CAMERA_ALT, icon_color=COLOR_ACCENTO, on_click=pick_evidence)
                    cont_detalles = ft.Column([ft.Divider(color=c["borde"]), ft.Row([btn_checklist, btn_firma_ind], alignment="spaceBetween"), ft.Row([btn_galeria, btn_camara, row_galeria], alignment="start")], visible=True)
                    
                    def on_chk(e, tm=txt_motivo, tt=txt_trabajo, cd=cont_detalles):
                        v = e.control.value; tm.visible = not v; tt.visible = v; cd.visible = v; page.update()
                    chk.on_change = on_chk
                    
                    state_usuarios.append(usr_state)
                    col_usuarios.controls.append(ft.Container(content=ft.Column([ft.Row([ft.Row([ft.Icon(ft.Icons.PERSON, color=COLOR_SECUNDARIO), ft.Text(nombre, weight="bold", color=c["texto"], expand=True)]), chk], alignment="spaceBetween"), txt_motivo, txt_trabajo, cont_detalles]), padding=10, border=ft.border.all(1, c["borde"]), border_radius=8, margin=ft.margin.only(bottom=10)))
                col_usuarios.update()

            dd_cli = ft.Dropdown(label="Cliente", options=[ft.dropdown.Option(k) for k in USUARIOS_POR_CLIENTE.keys()], filled=True, bgcolor=c["input_bg"], color=c["texto"], border_radius=12, border_color="transparent", text_size=14, on_change=lambda e: cargar_usuarios(e.control.value))

            def pan_start(e): datos_firma["trazos"].append([(e.local_x, e.local_y)]); canvas.shapes.append(cv.Path([cv.Path.MoveTo(e.local_x, e.local_y)], paint=ft.Paint(stroke_width=3, color="black", style=ft.PaintingStyle.STROKE))); canvas.update()
            def pan_update(e): datos_firma["trazos"][-1].append((e.local_x, e.local_y)); canvas.shapes[-1].elements.append(cv.Path.LineTo(e.local_x, e.local_y)); canvas.update()
            canvas = cv.Canvas(shapes=[]); gd = ft.GestureDetector(on_pan_start=pan_start, on_pan_update=pan_update, drag_interval=10)
            def abrir_dialogo_firma(e):
                datos_firma["trazos"] = []; canvas.shapes = []
                def confirmar_click(e): page.close(dlg_firma); guardar(None)
                dlg_firma = ft.AlertDialog(title=ft.Text("Firma Global (Opcional)"), content=ft.Container(content=ft.Stack([canvas, gd]), border=ft.border.all(1, "grey"), border_radius=10, width=300, height=200, bgcolor="white"), actions=[ft.TextButton("Limpiar", on_click=lambda e: [datos_firma["trazos"].clear(), canvas.shapes.clear(), canvas.update()]), ft.ElevatedButton("Finalizar", on_click=confirmar_click, bgcolor=COLOR_PRIMARIO, color="white")])
                page.open(dlg_firma)

            btn_ver = ft.ElevatedButton("Guardar PDF", icon=ft.Icons.DOWNLOAD, visible=False, bgcolor=COLOR_ACCENTO, color="white")
            btn_correo = ft.ElevatedButton("Enviar Correo", icon=ft.Icons.EMAIL, visible=False, bgcolor=COLOR_SECUNDARIO, color="white")

            def guardar(e):
                try:
                    datos_finales = []; todas_fotos = [] 
                    for u in state_usuarios:
                        fotos = u["lista_fotos"]; todas_fotos.extend(fotos)
                        datos_finales.append({"nombre": u["nombre"], "atendido": u["check"].value, "motivo": u["motivo"].value, "trabajo": u["trabajo"].value, "fotos": fotos, "firma": u["firma"]})
                    json_usr = json.dumps(datos_finales); firma = guardar_firma_img(datos_firma["trazos"]) if datos_firma["trazos"] else None
                    pdf = generar_pdf(dd_cli.value, dd_tec.value, txt_obs.value, firma, datos_finales); ultimo_pdf_generado.value = pdf
                    con = sqlite3.connect("visitas.db"); cur = con.cursor()
                    envio_ok, msg_envio = enviar_correo_smtp(pdf, dd_cli.value, dd_tec.value)
                    estado_envio = 1 if envio_ok else 0
                    cur.execute("INSERT INTO reportes (fecha, cliente, tecnico, observaciones, imagen_path, pdf_path, detalles_usuarios, email_enviado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (obtener_hora_chile().strftime('%Y-%m-%d %H:%M:%S'), dd_cli.value, dd_tec.value, txt_obs.value, json.dumps(todas_fotos), pdf, json_usr, estado_envio))
                    con.commit(); con.close()
                    page.open(ft.SnackBar(ft.Text(f"Guardado. {msg_envio}"), bgcolor="green" if envio_ok else "orange"))
                    def guardar_pdf_device(e): save_file_picker.save_file(file_name=os.path.basename(pdf))
                    btn_ver.visible = True; btn_ver.on_click = guardar_pdf_device; btn_ver.update()
                    btn_correo.visible = True; btn_correo.on_click = lambda _: [page.open(ft.SnackBar(ft.Text(enviar_correo_smtp(pdf, dd_cli.value, dd_tec.value)[1]), bgcolor="blue"))]; btn_correo.update()
                    txt_obs.value = ""; cargar_usuarios(dd_cli.value); page.update()
                except Exception as ex: page.open(ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor="red"))

            btn_main_guardar = ft.ElevatedButton("FINALIZAR VISITA", on_click=lambda e: abrir_dialogo_firma(e) if dd_cli.value and dd_tec.value else page.open(ft.SnackBar(ft.Text("Faltan datos"), bgcolor="red")), height=60, style=ft.ButtonStyle(bgcolor=COLOR_PRIMARIO, color="white", shape=ft.RoundedRectangleBorder(radius=15)))
            page.views.append(ft.View("/nueva_visita", controls=[
                ft.AppBar(title=ft.Text("Nueva Visita", color=c["texto"]), bgcolor=c["superficie"], color=COLOR_PRIMARIO, elevation=0),
                ft.Container(content=ft.Column([
                    crear_seccion(c, "Información", ft.Column([dd_cli, ft.Row([dd_tec, btn_add_tec])], spacing=15)),
                    crear_seccion(c, "Bitácora", col_usuarios),
                    crear_seccion(c, "Cierre", ft.Column([txt_obs, btn_main_guardar, ft.Row([btn_ver, btn_correo], alignment="center", wrap=True)], spacing=10))
                ], scroll="auto"), padding=20, expand=True)
            ], bgcolor=c["fondo"]))

        if page.route == "/historial":
            lista_items = []; datos = obtener_historial()
            if not datos: lista_items.append(ft.Text("Vacío", color="grey"))
            else:
                for row in datos:
                    id_rep, fecha, cli, tec, obs, pdf, enviado, detalles, imgs = row
                    ex = pdf and os.path.exists(pdf)
                    icon_env = ft.Icon(ft.Icons.CHECK_CIRCLE, color="green") if enviado else ft.Icon(ft.Icons.ERROR, color="red")
                    
                    # VISOR "PREMIUM" V49
                    def ver_detalle_modal(e, r_data=row):
                        _id, _fe, _cl, _te, _ob, _pd, _en, _det, _im = r_data
                        header_modal = ft.Container(content=ft.Column([ft.Image(src="logo.png", height=40), ft.Text("REPORTE DE VISITA", weight="bold", size=18, color=COLOR_PRIMARIO), ft.Text(f"{_cl} - {_fe}", size=12, color="grey")], horizontal_alignment="center"), bgcolor=c["card_bg"], padding=10, border_radius=10)
                        usuarios_ui = []
                        if _det:
                            try:
                                usrs = json.loads(_det)
                                for u in usrs:
                                    st = "✅" if u['atendido'] else "❌"; desc = u['trabajo'] if u['atendido'] else u['motivo']
                                    fotos_ui = ft.Row(scroll="auto")
                                    if u.get('fotos'):
                                        for f in u['fotos']: fotos_ui.controls.append(ft.Image(src=f, width=100, height=100, fit="cover", border_radius=8))
                                    firma_ui = ft.Image(src=u['firma'], width=150) if u.get('firma') else ft.Container()
                                    usuarios_ui.append(ft.Container(content=ft.Column([ft.Text(f"{st} {u['nombre']}", weight="bold", color=c["texto"]), ft.Text(desc, size=12, color=c["texto_sec"]), fotos_ui, ft.Text("Firma:", size=10) if u.get('firma') else ft.Container(), firma_ui, ft.Divider()]), padding=10, border=ft.border.all(1, "grey300"), border_radius=8, bgcolor=c["input_bg"]))
                            except: pass
                        dlg = ft.AlertDialog(content=ft.Container(content=ft.Column([header_modal, ft.Text(f"Tec: {_te}", color=c["texto"], weight="bold"), ft.Divider(), ft.Column(usuarios_ui, scroll="auto", expand=True), ft.Text(f"Nota: {_ob}", italic=True, color=c["texto_sec"])], scroll="auto"), width=600, height=700), actions=[ft.TextButton("Cerrar", on_click=lambda e: page.close(dlg)), ft.TextButton("Reenviar", icon=ft.Icons.SEND, on_click=lambda e: [page.open(ft.SnackBar(ft.Text(enviar_correo_smtp(_pd, _cl, _te)[1]), bgcolor="blue")), actualizar_estado_email(_id, 1)])], inset_padding=10)
                        page.open(dlg)

                    lista_items.append(ft.Container(content=ft.Column([ft.Row([ft.Row([ft.Container(content=ft.Icon(ft.Icons.DESCRIPTION, color=COLOR_BLANCO), bgcolor=COLOR_PRIMARIO if ex else "grey", padding=10, border_radius=12), ft.Column([ft.Text(cli, weight="bold", color=c["texto"]), ft.Text(fecha, size=12, color=c["texto_sec"])], spacing=0)]), icon_env], alignment="spaceBetween"), ft.Divider(color=c["borde"]), ft.Row([ft.Text(f"Tec: {tec}", color=c["texto"]), ft.IconButton(icon=ft.Icons.VISIBILITY, icon_color=COLOR_PRIMARIO, on_click=ver_detalle_modal), ft.TextButton("Descargar PDF", on_click=lambda e, p=pdf: save_file_picker.save_file(file_name=os.path.basename(p)), disabled=not ex)], alignment="end")]), padding=15, bgcolor=c["card_bg"], border_radius=12, shadow=ft.BoxShadow(blur_radius=5, color=c["sombra"]), margin=ft.margin.only(bottom=10)))
            page.views.append(ft.View("/historial", controls=[ft.AppBar(title=ft.Text("Historial", color=c["texto"]), bgcolor=c["superficie"], color=COLOR_PRIMARIO, elevation=0), ft.Container(content=ft.ListView(controls=lista_items, spacing=5, padding=20), expand=True)], bgcolor=c["fondo"]))
        page.update()

    def view_pop(view): page.views.pop(); top_view = page.views[-1]; page.go(top_view.route)
    page.on_route_change = route_change; page.on_view_pop = view_pop; page.go(page.route)

ft.app(target=main)