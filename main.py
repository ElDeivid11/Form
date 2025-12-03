import flet as f
import flet.canvas as cv
import shutil
import os
import json
import datetime
import config
import database
import utils
import pdf_generator

# --- IMPORTACIÓN SEGURA DE PLYER ---
# Esto evita que la app se rompa en Windows donde no existe cámara nativa
camera = None
try:
    from plyer import camera
except Exception as e:
    print(f"Advertencia: Plyer no está disponible o no soporta esta plataforma ({e}). Se usará modo compatibilidad.")
    camera = None

def main(page: f.Page):
    page.title = "Tecnocomp Mobile"
    page.window_width = 400
    page.window_height = 850
    page.padding = 0
    page.scroll = "adaptive"
    page.fonts = {"Poppins": "https://fonts.gstatic.com/s/poppins/v20/pxiByp8kv8JHgFVrLEj6Z1xlFd2JQEk.woff2"}
    page.theme = f.Theme(font_family=config.FONT_FAMILY, use_material3=True)
    
    # --- ESTADO GLOBAL ---
    app_state = {
        "tema": "light",
        "id_editar": None
    }
    
    page.theme_mode = f.ThemeMode.LIGHT
    page.bgcolor = config.COLORES["light"]["fondo"]
    ultimo_pdf_generado = f.Text("", visible=False)

    database.inicializar_db()

    def cambiar_tema(e):
        app_state["tema"] = "dark" if app_state["tema"] == "light" else "light"
        page.theme_mode = f.ThemeMode.DARK if app_state["tema"] == "dark" else f.ThemeMode.LIGHT
        page.bgcolor = config.COLORES[app_state["tema"]]["fondo"]
        page.views.clear()
        route_change(page.route)
        page.update()

    def crear_header(c):
        return f.Container(
            content=f.Column([
                f.Row([
                    f.Row([f.Icon(f.Icons.DASHBOARD_ROUNDED, color=config.COLOR_PRIMARIO, size=28), 
                           f.Text("PANEL DE CONTROL", color=config.COLOR_PRIMARIO, weight="bold", size=16)]),
                    f.IconButton(icon=f.Icons.DARK_MODE if app_state["tema"]=="light" else f.Icons.LIGHT_MODE, icon_color=c["texto"], on_click=cambiar_tema)
                ], alignment="spaceBetween"),
                f.Divider(height=10, color="transparent"),
                f.Container(
                    content=f.Image(src="logo2.png", width=200, fit=f.ImageFit.CONTAIN, error_content=f.Icon(f.Icons.BROKEN_IMAGE)), 
                    bgcolor="white" if app_state["tema"]=="dark" else None, 
                    border_radius=10, padding=5 if app_state["tema"]=="dark" else 0,
                    shadow=f.BoxShadow(blur_radius=20, color=c["sombra"], offset=f.Offset(0, 5))
                ),
                f.Divider(height=10, color="transparent"),
                f.Text("Bienvenido, Técnico", size=26, weight="bold", color=c["texto"]), 
                f.Text("Gestión de Visitas", size=14, color=c["texto_sec"], weight="w500")
            ], horizontal_alignment="center", spacing=5),
            bgcolor=c["superficie"], width=float("inf"), padding=f.padding.only(top=50, bottom=30, left=20, right=20),
            border_radius=f.border_radius.only(bottom_left=40, bottom_right=40),
            shadow=f.BoxShadow(blur_radius=20, color="#15000000", offset=f.Offset(0, 10))
        )

    def crear_stats_card(c):
        count = database.obtener_conteo_reportes()
        return f.Container(
            content=f.Row([
                f.Container(content=f.Icon(f.Icons.FOLDER_SHARED_ROUNDED, color=config.COLOR_BLANCO, size=30), bgcolor=config.COLOR_ACCENTO, padding=12, border_radius=12),
                f.Column([f.Text("Total Reportes", color=c["texto_sec"], size=13, weight="w500"), f.Text(str(count), weight="bold", size=28, color=c["texto"])], spacing=2)
            ], alignment="start", spacing=15),
            bgcolor=c["superficie"], padding=f.padding.symmetric(vertical=15, horizontal=20),
            border_radius=20, width=280, shadow=f.BoxShadow(blur_radius=20, color="#20000000", offset=f.Offset(0, 10)), margin=f.margin.only(top=-30, bottom=25), alignment=f.alignment.center
        )

    def crear_boton_menu(c, titulo, subtitulo, icono, on_click_action, grad_colors=[config.COLOR_PRIMARIO, config.COLOR_ACCENTO]):
        return f.Container(
            content=f.Row([
                f.Column([f.Text(titulo, size=18, weight="bold", color=config.COLOR_BLANCO), f.Text(subtitulo, size=12, color="white70")], expand=True, alignment="center", spacing=3), 
                f.Icon(icono, size=40, color="white54")
            ], alignment="spaceBetween"),
            gradient=f.LinearGradient(begin=f.alignment.top_left, end=f.alignment.bottom_right, colors=grad_colors),
            padding=20, border_radius=18, shadow=f.BoxShadow(blur_radius=10, color=c["sombra"], offset=f.Offset(0, 5)), on_click=on_click_action, ink=True
        )

    def crear_seccion(c, titulo, contenido):
        return f.Container(content=f.Column([f.Text(titulo, weight="bold", size=16, color=config.COLOR_PRIMARIO), f.Divider(height=15, color="transparent"), contenido]), padding=20, bgcolor=c["card_bg"], border_radius=18, shadow=f.BoxShadow(blur_radius=15, color=c["sombra"], offset=f.Offset(0, 5)), margin=f.margin.only(bottom=20))

    # --- BACKUP ---
    def mostrar_dialogo_backup(e):
        pass_input = f.TextField(label="Contraseña de Administrador", password=True, can_reveal_password=True, text_align="center")
        
        def confirmar_backup(e):
            if pass_input.value == config.ADMIN_PASSWORD:
                page.close(dlg_pass)
                pass_input.value = "" 
                page.open(f.SnackBar(f.Text("Iniciando respaldo en la nube..."), bgcolor="blue"))
                page.update()
                
                ok, msg = utils.subir_backup_database()
                color = "green" if ok else "red"
                page.open(f.SnackBar(f.Text(msg), bgcolor=color))
            else:
                pass_input.error_text = "Contraseña incorrecta"
                pass_input.update()

        dlg_pass = f.AlertDialog(
            title=f.Text("Acceso Restringido"),
            content=f.Container(
                content=f.Column([
                    f.Icon(f.Icons.SECURITY, size=50, color=config.COLOR_SECUNDARIO),
                    f.Text("Esta acción subirá una copia completa de la base de datos al SharePoint."),
                    pass_input
                ], tight=True, horizontal_alignment="center"),
                height=150
            ),
            actions=[
                f.TextButton("Cancelar", on_click=lambda e: page.close(dlg_pass)),
                f.ElevatedButton("Autorizar Backup", on_click=confirmar_backup, bgcolor=config.COLOR_PRIMARIO, color="white")
            ],
            actions_alignment="center"
        )
        page.open(dlg_pass)

    def route_change(route):
        page.views.clear()
        c = config.COLORES[app_state["tema"]]
        
        # Helper para opacidad (Arregla 'with_opacity')
        def obtener_color_opacidad(color_hex, opacity):
            if not color_hex: return None
            color_hex = color_hex.lstrip('#')
            alpha = int(opacity * 255)
            return f"#{alpha:02x}{color_hex}"

        # --- DASHBOARD ---
        if page.route == "/":
            app_state["id_editar"] = None
            page.views.append(f.View("/", controls=[
                crear_header(c), 
                f.Container(content=f.Column([
                    crear_stats_card(c), 
                    crear_boton_menu(c, "Nueva Visita", "Crear reporte y firmar", f.Icons.ADD_LOCATION_ALT_ROUNDED, lambda _: page.go("/nueva_visita")),
                    f.Divider(height=15, color="transparent"), 
                    crear_boton_menu(c, "Historial", "Ver y editar reportes", f.Icons.HISTORY, lambda _: page.go("/historial"), grad_colors=["#F2994A", "#F2C94C"]),
                    f.Divider(height=15, color="transparent"),
                    crear_boton_menu(c, "Métricas", "Estadísticas y gráficos", f.Icons.BAR_CHART, lambda _: page.go("/metricas"), grad_colors=["#9C27B0", "#E040FB"]),
                    f.Divider(height=15, color="transparent"),
                    crear_boton_menu(c, "Respaldo Cloud", "Subir DB a SharePoint", f.Icons.CLOUD_UPLOAD, mostrar_dialogo_backup, grad_colors=["#455A64", "#607D8B"])
                ], horizontal_alignment="center", scroll="auto"), padding=f.padding.symmetric(horizontal=25, vertical=10), expand=True, alignment=f.alignment.top_center)
            ], bgcolor=c["fondo"], padding=0))

        # --- METRICAS PROFESIONALES ---
        if page.route == "/metricas":
            data_cli = database.obtener_datos_clientes()
            data_tec = database.obtener_datos_tecnicos()
            total, pendientes, top_cliente = database.obtener_kpis_generales()
            data_mes = database.obtener_evolucion_mensual()

            def crear_kpi_card(titulo, valor, icono, color_bg, color_ico):
                return f.Container(
                    content=f.Column([
                        f.Row([f.Icon(icono, color=color_ico, size=20), f.Text(titulo, size=12, color=c["texto_sec"], weight="w500")], spacing=5),
                        f.Text(str(valor), size=22, weight="bold", color=c["texto"])
                    ], spacing=2),
                    bgcolor=c["card_bg"], padding=15, border_radius=12, 
                    shadow=f.BoxShadow(blur_radius=5, color=c["sombra"], offset=f.Offset(0, 3)),
                    expand=True
                )

            row_kpis = f.Row([
                crear_kpi_card("Total Visitas", total, f.Icons.NUMBERS, c["card_bg"], config.COLOR_PRIMARIO),
                crear_kpi_card("Pendientes", pendientes, f.Icons.PENDING_ACTIONS, c["card_bg"], "orange"),
                crear_kpi_card("Top Cliente", top_cliente.split('(')[0][:10], f.Icons.STAR, c["card_bg"], "purple"),
            ], spacing=10)

            if data_mes:
                puntos_linea = [f.LineChartDataPoint(i, count) for i, (mes, count) in enumerate(data_mes)]
                etiquetas_x = [f.ChartAxisLabel(value=i, label=f.Text(mes[5:], size=10, weight="bold")) for i, (mes, count) in enumerate(data_mes)]
                max_y = max([x[1] for x in data_mes]) + 2
                color_sombreado = obtener_color_opacidad(config.COLOR_ACCENTO, 0.2)
                
                chart_line = f.LineChart(
                    data_series=[f.LineChartData(data_points=puntos_linea, stroke_width=4, color=config.COLOR_ACCENTO, curved=True, stroke_cap_round=True, below_line_bgcolor=color_sombreado)],
                    border=f.border.all(0),
                    left_axis=f.ChartAxis(labels_size=30),
                    bottom_axis=f.ChartAxis(labels=etiquetas_x, labels_size=20),
                    tooltip_bgcolor=c["input_bg"],
                    min_y=0, max_y=max_y, height=200
                )
            else:
                chart_line = f.Text("Sin datos históricos", color="grey")

            container_linea = f.Container(content=f.Column([f.Text("Tendencia Mensual", size=16, weight="bold", color=c["texto"]), f.Divider(height=10, color="transparent"), chart_line]), bgcolor=c["card_bg"], padding=20, border_radius=16, shadow=f.BoxShadow(blur_radius=10, color=c["sombra"]))

            pie_sections = [f.PieChartSection(value=val, title=f"{val}", color=config.COLORES_GRAFICOS[i%len(config.COLORES_GRAFICOS)], radius=50, title_style=f.TextStyle(size=12, color="white", weight="bold")) for i, (key, val) in enumerate(data_cli)]
            chart_pie = f.PieChart(sections=pie_sections, sections_space=2, center_space_radius=30, height=200) if pie_sections else f.Text("Sin datos")
            
            legend_items = []
            for i, (key, val) in enumerate(data_cli[:4]): 
                legend_items.append(f.Row([f.Container(width=10, height=10, bgcolor=config.COLORES_GRAFICOS[i%len(config.COLORES_GRAFICOS)], border_radius=2), f.Text(key, size=10, color=c["texto_sec"], no_wrap=True)], spacing=5))
            
            col_pie = f.Column([f.Text("Por Cliente", weight="bold", color=c["texto"]), chart_pie, f.Column(legend_items, spacing=2)], horizontal_alignment="center", spacing=10)
            container_pie = f.Container(content=col_pie, bgcolor=c["card_bg"], padding=15, border_radius=16, shadow=f.BoxShadow(blur_radius=10, color=c["sombra"]), expand=True)

            bar_groups = [f.BarChartGroup(x=i, bar_rods=[f.BarChartRod(from_y=0, to_y=val, width=20, color=config.COLOR_PRIMARIO, border_radius=4)]) for i, (key, val) in enumerate(data_tec)]
            chart_bar = f.BarChart(bar_groups=bar_groups, border=f.border.all(0), left_axis=f.ChartAxis(labels_size=25), bottom_axis=f.ChartAxis(labels=[f.ChartAxisLabel(value=i, label=f.Text(key[:3], size=10)) for i, (key, val) in enumerate(data_tec)]), height=180) if bar_groups else f.Text("Sin datos")
            col_bar = f.Column([f.Text("Por Técnico", weight="bold", color=c["texto"]), chart_bar], horizontal_alignment="center", spacing=20)
            container_bar = f.Container(content=col_bar, bgcolor=c["card_bg"], padding=15, border_radius=16, shadow=f.BoxShadow(blur_radius=10, color=c["sombra"]), expand=True)

            page.views.append(f.View("/metricas", controls=[
                f.AppBar(leading=f.IconButton(icon=f.Icons.ARROW_BACK, icon_color=config.COLOR_PRIMARIO, on_click=lambda _: page.go("/")), title=f.Text("Dashboard", color=c["texto"], weight="bold"), bgcolor=c["superficie"], color=config.COLOR_PRIMARIO, elevation=0, center_title=True), 
                f.Container(content=f.Column([row_kpis, f.Divider(height=10, color="transparent"), container_linea, f.Divider(height=10, color="transparent"), f.Row([container_pie, container_bar], spacing=10)], scroll="auto"), padding=20, expand=True)
            ], bgcolor=c["fondo"]))

        # --- NUEVA VISITA / EDICIÓN ---
        if page.route == "/nueva_visita":
            datos_firma = {"trazos": []}
            datos_firma_individual = {"trazos": []}
            state_usuarios = []
            usuario_actual_foto = [None] 
            
            fp = f.FilePicker(on_result=lambda e: actualizar_fotos_usuario(e))
            page.overlay.append(fp)

            def actualizar_fotos_usuario(e):
                if e.files and usuario_actual_foto[0] is not None:
                    u = state_usuarios[usuario_actual_foto[0]]
                    for file in e.files: u["lista_fotos"].append(file.path)
                    u["control_galeria"].controls.clear()
                    for p in u["lista_fotos"]: 
                        u["control_galeria"].controls.append(f.Container(content=f.Image(src=p, width=60, height=60, fit=f.ImageFit.COVER, border_radius=8), border=f.border.all(1, c["borde"]), border_radius=8, shadow=f.BoxShadow(blur_radius=5, color=c["sombra"])))
                    u["control_galeria"].update()
                    page.open(f.SnackBar(f.Text(f"Fotos agregadas"), bgcolor="green"))

            # --- INTEGRACIÓN CÁMARA PLYER ---
            def on_camera_complete(path):
                if usuario_actual_foto[0] is not None:
                    if os.path.exists(path):
                        u = state_usuarios[usuario_actual_foto[0]]
                        u["lista_fotos"].append(path)
                        img_widget = f.Container(content=f.Image(src=path, width=60, height=60, fit=f.ImageFit.COVER, border_radius=8), border=f.border.all(1, c["borde"]), border_radius=8)
                        u["control_galeria"].controls.append(img_widget)
                        u["control_galeria"].update()
                        page.open(f.SnackBar(f.Text("Foto nativa guardada"), bgcolor="green"))
                        page.update()

            def abrir_camara_nativa(e, idx):
                usuario_actual_foto[0] = idx
                try:
                    if camera:
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = os.path.join(os.getcwd(), f"foto_{timestamp}.jpg")
                        camera.take_picture(filename, on_complete=on_camera_complete)
                        page.open(f.SnackBar(f.Text("Abriendo cámara nativa..."), bgcolor="blue"))
                    else:
                        page.open(f.SnackBar(f.Text("Cámara nativa no disponible en Windows. Usa 'Galería'."), bgcolor="orange"))
                    page.update()
                except Exception as ex:
                    page.open(f.SnackBar(f.Text(f"Error cámara: {ex}"), bgcolor="red"))
                    page.update()

            lista_tecnicos = database.obtener_tecnicos()
            dd_tec = f.Dropdown(label="Técnico Responsable", options=[f.dropdown.Option(t) for t in lista_tecnicos], filled=True, bgcolor=c["input_bg"], color=c["texto"], border_radius=12, border_color="transparent", text_size=14, expand=True)
            
            def gestionar_tecnicos_dialog(e):
                def refrescar_lista_t():
                    col_lista_tecs.controls.clear()
                    tecs = database.obtener_tecnicos()
                    for t_nombre in tecs:
                        col_lista_tecs.controls.append(f.Row([f.Text(t_nombre, size=14, weight="bold", expand=True), f.IconButton(icon=f.Icons.DELETE_ROUNDED, icon_color="red", on_click=lambda e, n=t_nombre: eliminar_tec(n))], alignment="spaceBetween"))
                    col_lista_tecs.update()
                def eliminar_tec(nombre_t):
                    if database.eliminar_tecnico(nombre_t):
                        refrescar_lista_t(); dd_tec.options = [f.dropdown.Option(t) for t in database.obtener_tecnicos()]; dd_tec.value = None; dd_tec.update()
                def agregar_tec(e):
                    if txt_new_tec.value:
                        if database.agregar_nuevo_tecnico(txt_new_tec.value):
                            txt_new_tec.value = ""; refrescar_lista_t(); dd_tec.options = [f.dropdown.Option(t) for t in database.obtener_tecnicos()]; dd_tec.update()
                txt_new_tec = f.TextField(label="Nuevo Técnico", expand=True, height=40, text_size=12)
                col_lista_tecs = f.Column(height=200, scroll="auto")
                dlg_gestion = f.AlertDialog(title=f.Text("Gestionar Técnicos"), content=f.Container(content=f.Column([f.Row([txt_new_tec, f.IconButton(icon=f.Icons.ADD_CIRCLE, icon_color=config.COLOR_PRIMARIO, on_click=agregar_tec)]), f.Divider(), col_lista_tecs]), width=300, height=300), actions=[f.TextButton("Cerrar", on_click=lambda e: page.close(dlg_gestion))])
                page.open(dlg_gestion); refrescar_lista_t()
            btn_add_tec = f.IconButton(icon=f.Icons.MANAGE_ACCOUNTS, icon_color=config.COLOR_ACCENTO, tooltip="Gestionar Técnicos", on_click=gestionar_tecnicos_dialog)

            lista_clientes = database.obtener_nombres_clientes()
            dd_cli = f.Dropdown(label="Cliente", options=[f.dropdown.Option(k) for k in lista_clientes], filled=True, bgcolor=c["input_bg"], color=c["texto"], border_radius=12, border_color="transparent", text_size=14, expand=True)
            
            def gestionar_clientes_dialog(e):
                def refrescar_lista_c():
                    col_lista_clis.controls.clear()
                    clis = database.obtener_clientes()
                    for cl_nombre, cl_email in clis:
                        col_lista_clis.controls.append(f.Row([f.Column([f.Text(cl_nombre, weight="bold", size=14), f.Text(cl_email, size=10, color="grey")], expand=True), f.IconButton(icon=f.Icons.DELETE_ROUNDED, icon_color="red", on_click=lambda e, n=cl_nombre: eliminar_cli(n))], alignment="spaceBetween"))
                    col_lista_clis.update()
                def eliminar_cli(nombre_c):
                    if database.eliminar_cliente(nombre_c):
                        refrescar_lista_c(); dd_cli.options = [f.dropdown.Option(k) for k in database.obtener_nombres_clientes()]; dd_cli.value = None; dd_cli.update(); col_usuarios.controls.clear(); col_usuarios.update()
                def agregar_cli(e):
                    if txt_new_cli_nombre.value and txt_new_cli_email.value:
                        if database.agregar_cliente(txt_new_cli_nombre.value, txt_new_cli_email.value):
                            txt_new_cli_nombre.value = ""; txt_new_cli_email.value = ""; refrescar_lista_c(); dd_cli.options = [f.dropdown.Option(k) for k in database.obtener_nombres_clientes()]; dd_cli.update()
                txt_new_cli_nombre = f.TextField(label="Nombre Cliente", expand=True, height=40, text_size=12)
                txt_new_cli_email = f.TextField(label="Email Reportes", expand=True, height=40, text_size=12)
                col_lista_clis = f.Column(height=200, scroll="auto")
                dlg_gestion_c = f.AlertDialog(title=f.Text("Gestionar Clientes"), content=f.Container(content=f.Column([f.Text("Nuevo Cliente:", size=12), txt_new_cli_nombre, txt_new_cli_email, f.ElevatedButton("Agregar Cliente", on_click=agregar_cli, bgcolor=config.COLOR_PRIMARIO, color="white"), f.Divider(), f.Text("Existentes:", size=12), col_lista_clis]), width=300, height=400), actions=[f.TextButton("Cerrar", on_click=lambda e: page.close(dlg_gestion_c))])
                page.open(dlg_gestion_c); refrescar_lista_c()
            btn_add_cli = f.IconButton(icon=f.Icons.SETTINGS, icon_color=config.COLOR_SECUNDARIO, tooltip="Gestionar Clientes", on_click=gestionar_clientes_dialog)

            col_usuarios = f.Column(spacing=15)
            
            def cargar_usuarios(cliente, datos_edicion=None, actualizar_vista=True):
                col_usuarios.controls.clear(); state_usuarios.clear()
                if not cliente:
                    if actualizar_vista: col_usuarios.update()
                    return
                
                def agregar_usuario_dialog(e):
                    def guardar_nuevo_user(e):
                        if txt_n_user.value:
                            if database.agregar_usuario(txt_n_user.value, cliente):
                                page.close(d_u); cargar_usuarios(cliente); page.open(f.SnackBar(f.Text("Usuario agregado"), bgcolor="green"))
                    txt_n_user = f.TextField(label="Nombre del Usuario", autofocus=True)
                    d_u = f.AlertDialog(title=f.Text(f"Nuevo usuario para {cliente}"), content=txt_n_user, actions=[f.TextButton("Cancelar", on_click=lambda e: page.close(d_u)), f.ElevatedButton("Guardar", on_click=guardar_nuevo_user)])
                    page.open(d_u)
                
                btn_crear_user = f.ElevatedButton("Agregar Usuario", icon=f.Icons.PERSON_ADD, on_click=agregar_usuario_dialog, bgcolor=config.COLOR_AZUL_SUAVE, color=config.COLOR_PRIMARIO, width=float("inf"))
                col_usuarios.controls.append(btn_crear_user)
                
                nombres = database.obtener_usuarios_por_cliente(cliente)
                
                for i, nombre in enumerate(nombres):
                    val_atendido = True
                    val_trabajo = ""
                    val_motivo = ""
                    val_fotos = []
                    val_firma = None
                    
                    if datos_edicion:
                        for u_prev in datos_edicion:
                            if u_prev["nombre"] == nombre:
                                val_atendido = u_prev["atendido"]
                                val_trabajo = u_prev["trabajo"]
                                val_motivo = u_prev["motivo"]
                                val_fotos = u_prev["fotos"]
                                val_firma = u_prev.get("firma")
                                break
                    
                    chk = f.Switch(label="Atendido", value=val_atendido, active_color=config.COLOR_PRIMARIO)
                    bg_inp = "#E0F2FF" if app_state["tema"]=="light" else "#333333"; col_inp = "#000000" if app_state["tema"]=="light" else "#FFFFFF"
                    
                    txt_trabajo = f.TextField(label="Detalle del trabajo", value=val_trabajo, read_only=True, multiline=True, text_size=12, bgcolor=bg_inp, color=col_inp, border_color="transparent", border_radius=8, visible=val_atendido)
                    txt_motivo = f.TextField(label="Motivo de no atención", value=val_motivo, visible=not val_atendido, text_size=13, bgcolor=config.COLOR_ROJO_SUAVE, color="black", border_color="transparent", border_radius=8)
                    
                    row_galeria = f.Row(scroll="auto", spacing=10)
                    for p in val_fotos:
                        row_galeria.controls.append(f.Container(content=f.Image(src=p, width=60, height=60, fit=f.ImageFit.COVER, border_radius=8), border=f.border.all(1, c["borde"]), border_radius=8))

                    usr_state = {"nombre": nombre, "check": chk, "motivo": txt_motivo, "trabajo": txt_trabajo, "lista_fotos": list(val_fotos), "control_galeria": row_galeria, "firma": val_firma}
                    
                    estado_tareas = {t: False for t in config.TAREAS_MANTENIMIENTO}
                    if val_trabajo.startswith("Mantenimiento: "):
                        tareas_texto = val_trabajo.replace("Mantenimiento: ", "")
                        partes = tareas_texto.split(", ")
                        for p in partes:
                            if " (" in p and p.endswith(")"):
                                parts = p.rsplit(" (", 1)
                                if len(parts) == 2:
                                    nombre_tarea = parts[0]
                                    hora_tarea = parts[1][:-1]
                                    if nombre_tarea in estado_tareas:
                                        estado_tareas[nombre_tarea] = hora_tarea
                            else:
                                if p in estado_tareas: estado_tareas[p] = "OK"

                    def actualizar_txt_trabajo(dic, inp):
                        hechos = [f"{k} ({v})" for k, v in dic.items() if v]
                        inp.value = "Mantenimiento: " + ", ".join(hechos) if hechos else ""; inp.update()
                        
                    def abrir_checklist(e, nom_u=nombre, dic_u=estado_tareas, inp_u=txt_trabajo):
                        lista_checks = []
                        for t in config.TAREAS_MANTENIMIENTO:
                            def on_ch(e, tarea=t, d=dic_u, i=inp_u):
                                d[tarea] = utils.obtener_hora_chile().strftime("%H:%M") if e.control.value else False; actualizar_txt_trabajo(d, i)
                            lista_checks.append(f.Checkbox(label=t, value=bool(dic_u[t]), on_change=on_ch))
                        dlg_tareas = f.AlertDialog(title=f.Text(f"Checklist: {nom_u}"), content=f.Container(content=f.Column(lista_checks, height=300, scroll="auto"), padding=10), actions=[f.TextButton("Listo", on_click=lambda e: page.close(dlg_tareas))]); page.open(dlg_tareas)
                    
                    btn_checklist = f.ElevatedButton("Checklist", icon=f.Icons.CHECKLIST, bgcolor=config.COLOR_SECUNDARIO, color="white", on_click=abrir_checklist)
                    
                    icon_check_firma = f.Icon(f.Icons.CHECK_CIRCLE, color="green", visible=bool(val_firma), tooltip="Firma capturada")

                    canvas_ind = cv.Canvas(shapes=[]); gd_ind = f.GestureDetector(on_pan_start=lambda e: [datos_firma_individual["trazos"].append([(e.local_x, e.local_y)]), canvas_ind.shapes.append(cv.Path([cv.Path.MoveTo(e.local_x, e.local_y)], paint=f.Paint(stroke_width=3, color="black", style=f.PaintingStyle.STROKE))), canvas_ind.update()], on_pan_update=lambda e: [datos_firma_individual["trazos"][-1].append((e.local_x, e.local_y)), canvas_ind.shapes[-1].elements.append(cv.Path.LineTo(e.local_x, e.local_y)), canvas_ind.update()])
                    
                    def abrir_firma_ind(e, u_st=usr_state, icon_ref=icon_check_firma):
                        datos_firma_individual["trazos"] = []; canvas_ind.shapes = []
                        def guardar_f(e):
                            path = utils.guardar_firma_img(datos_firma_individual["trazos"], f"firma_{nombre}_{datetime.datetime.now().timestamp()}.png")
                            u_st["firma"] = path
                            icon_ref.visible = True
                            icon_ref.update()
                            page.close(d_f); page.open(f.SnackBar(f.Text("Firma guardada"), bgcolor="green"))
                        d_f = f.AlertDialog(title=f.Text(f"Firma: {nombre}"), content=f.Container(content=f.Stack([canvas_ind, gd_ind]), border=f.border.all(1, "grey"), width=300, height=200, bgcolor="white"), actions=[f.TextButton("Borrar", on_click=lambda e: [datos_firma_individual["trazos"].clear(), canvas_ind.shapes.clear(), canvas_ind.update()]), f.ElevatedButton("Guardar", on_click=guardar_f, bgcolor=config.COLOR_PRIMARIO, color="white")]); page.open(d_f)
                    
                    btn_firma_ind = f.ElevatedButton("Firmar", icon=f.Icons.DRAW, bgcolor=config.COLOR_ACCENTO, color="white", on_click=abrir_firma_ind)
                    
                    # Logica de Fotos (Galeria / Cámara Nativa)
                    def pick_evidence(e, idx=i): usuario_actual_foto[0] = idx; fp.pick_files(allow_multiple=True, file_type=f.FilePickerFileType.ANY)
                    def click_camara(e, idx=i): abrir_camara_nativa(e, idx)

                    btn_galeria = f.IconButton(icon=f.Icons.ADD_PHOTO_ALTERNATE, icon_color=config.COLOR_ACCENTO, tooltip="Galería", on_click=pick_evidence)
                    btn_camara = f.IconButton(icon=f.Icons.CAMERA_ALT, icon_color=config.COLOR_ACCENTO, tooltip="Cámara Nativa", on_click=click_camara)
                    
                    cont_detalles = f.Column([
                        f.Divider(color=c["borde"]), 
                        f.Row([btn_checklist, f.Row([btn_firma_ind, icon_check_firma], spacing=5)], alignment="spaceBetween"), 
                        f.Row([btn_galeria, btn_camara, row_galeria], alignment="start")
                    ], visible=val_atendido)
                    
                    def on_chk(e, tm=txt_motivo, tt=txt_trabajo, cd=cont_detalles):
                        v = e.control.value; tm.visible = not v; tt.visible = v; cd.visible = v; page.update()
                    chk.on_change = on_chk
                    def borrar_usuario_click(e, nom_u=nombre, cli_n=cliente):
                        if database.eliminar_usuario(nom_u, cli_n): cargar_usuarios(cli_n)
                    
                    header_user = f.Row([f.Row([f.Icon(f.Icons.PERSON, color=config.COLOR_SECUNDARIO), f.Text(nombre, weight="bold", color=c["texto"], expand=True)]), f.Row([chk, f.IconButton(icon=f.Icons.DELETE_FOREVER, icon_color="red", icon_size=20, tooltip="Borrar Usuario", on_click=borrar_usuario_click)])], alignment="spaceBetween")
                    state_usuarios.append(usr_state)
                    col_usuarios.controls.append(f.Container(content=f.Column([header_user, txt_motivo, txt_trabajo, cont_detalles]), padding=10, border=f.border.all(1, c["borde"]), border_radius=8, margin=f.margin.only(bottom=10)))
                
                if actualizar_vista: col_usuarios.update()
            
            dd_cli.on_change = lambda e: cargar_usuarios(e.control.value)

            txt_obs = f.TextField(label="Notas Adicionales (Opcional)", multiline=True, min_lines=3, filled=True, bgcolor=c["input_bg"], color=c["texto"], border_radius=12, text_size=14, border_color="transparent", prefix_icon=f.Icons.NOTE_ALT_OUTLINED)
            def pan_start(e): datos_firma["trazos"].append([(e.local_x, e.local_y)]); canvas.shapes.append(cv.Path([cv.Path.MoveTo(e.local_x, e.local_y)], paint=f.Paint(stroke_width=3, color="black", style=f.PaintingStyle.STROKE))); canvas.update()
            def pan_update(e): datos_firma["trazos"][-1].append((e.local_x, e.local_y)); canvas.shapes[-1].elements.append(cv.Path.LineTo(e.local_x, e.local_y)); canvas.update()
            canvas = cv.Canvas(shapes=[]); gd = f.GestureDetector(on_pan_start=pan_start, on_pan_update=pan_update, drag_interval=10)
            def abrir_dialogo_firma(e):
                datos_firma["trazos"] = []; canvas.shapes = []
                def confirmar_click(e): page.close(dlg_firma); guardar(None)
                dlg_firma = f.AlertDialog(title=f.Text("Firma Global (Opcional)"), content=f.Container(content=f.Stack([canvas, gd]), border=f.border.all(1, "grey"), border_radius=10, width=300, height=200, bgcolor="white"), actions=[f.TextButton("Limpiar", on_click=lambda e: [datos_firma["trazos"].clear(), canvas.shapes.clear(), canvas.update()]), f.ElevatedButton("Finalizar", on_click=confirmar_click, bgcolor=config.COLOR_PRIMARIO, color="white")])
                page.open(dlg_firma)

            # --- FEEDBACK VISUAL ---
            progress_ring = f.ProgressRing(visible=False, width=20, height=20, color=config.COLOR_BLANCO)
            
            def guardar(e):
                if not dd_cli.value or not dd_tec.value:
                    page.open(f.SnackBar(f.Text("Faltan datos clave"), bgcolor="red")); return
                
                btn_main_guardar.disabled = True
                texto_btn = "ACTUALIZANDO..." if app_state["id_editar"] else "GUARDANDO..."
                btn_main_guardar.text = texto_btn
                btn_main_guardar.content = f.Row([progress_ring, f.Text(texto_btn)], alignment="center")
                progress_ring.visible = True
                page.update()

                try:
                    datos_finales = []; todas_fotos = [] 
                    for u in state_usuarios:
                        fotos = u["lista_fotos"]; todas_fotos.extend(fotos)
                        datos_finales.append({"nombre": u["nombre"], "atendido": u["check"].value, "motivo": u["motivo"].value, "trabajo": u["trabajo"].value, "fotos": fotos, "firma": u["firma"]})
                    json_usr = json.dumps(datos_finales)
                    firma = utils.guardar_firma_img(datos_firma["trazos"]) if datos_firma["trazos"] else None
                    
                    # Generar PDF
                    pdf_path = pdf_generator.generar_pdf(dd_cli.value, dd_tec.value, txt_obs.value, firma, datos_finales)
                    ultimo_pdf_generado.value = pdf_path
                    
                    # Guardar en DB (SIN ENVIAR CORREO)
                    fecha_actual = utils.obtener_hora_chile().strftime('%Y-%m-%d %H:%M:%S')
                    
                    if app_state["id_editar"]:
                        # UPDATE
                        database.actualizar_reporte(app_state["id_editar"], fecha_actual, dd_cli.value, dd_tec.value, txt_obs.value, json.dumps(todas_fotos), pdf_path, json_usr, 0) # 0 = Pendiente
                        msg_exito = "Reporte actualizado. Pendiente de envío."
                    else:
                        # INSERT
                        database.guardar_reporte(fecha_actual, dd_cli.value, dd_tec.value, txt_obs.value, json.dumps(todas_fotos), pdf_path, json_usr, 0)
                        msg_exito = "Guardado localmente. Pendiente de envío."

                    page.open(f.SnackBar(f.Text(msg_exito), bgcolor="green"))
                    
                    # Redirigir al historial tras guardar
                    page.go("/historial")

                except Exception as ex:
                    page.open(f.SnackBar(f.Text(f"Error Crítico: {ex}"), bgcolor="red"))
                    btn_main_guardar.content = None
                    btn_main_guardar.text = "FINALIZAR VISITA"
                    btn_main_guardar.disabled = False
                
                progress_ring.visible = False
                page.update()

            txt_btn_main = "GUARDAR CAMBIOS" if app_state["id_editar"] else "FINALIZAR VISITA"
            btn_main_guardar = f.ElevatedButton(txt_btn_main, on_click=lambda e: abrir_dialogo_firma(e), height=60, style=f.ButtonStyle(bgcolor=config.COLOR_PRIMARIO, color="white", shape=f.RoundedRectangleBorder(radius=15)))
            
            # --- CARGAR DATOS SI ES EDICIÓN ---
            titulo_vista = "Nueva Visita"
            if app_state["id_editar"]:
                titulo_vista = "Editar Visita"
                datos_existentes = database.obtener_reporte_por_id(app_state["id_editar"])
                if datos_existentes:
                    _, _, cli_db, tec_db, obs_db, _, _, detalles_db, _ = datos_existentes
                    dd_cli.value = cli_db
                    dd_tec.value = tec_db
                    txt_obs.value = obs_db
                    
                    try:
                        detalles_json = json.loads(detalles_db)
                        cargar_usuarios(cli_db, detalles_json, actualizar_vista=False)
                    except:
                        cargar_usuarios(cli_db, actualizar_vista=False)

            page.views.append(f.View("/nueva_visita", controls=[
                f.AppBar(
                    leading=f.IconButton(icon=f.Icons.ARROW_BACK, icon_color=config.COLOR_PRIMARIO, on_click=lambda _: page.go("/")),
                    title=f.Text(titulo_vista, color=c["texto"]), 
                    bgcolor=c["superficie"], 
                    color=config.COLOR_PRIMARIO, 
                    elevation=0
                ),
                f.Container(content=f.Column([
                    crear_seccion(c, "Información", f.Column([f.Row([dd_cli, btn_add_cli]), f.Row([dd_tec, btn_add_tec])], spacing=15)),
                    crear_seccion(c, "Bitácora", col_usuarios),
                    crear_seccion(c, "Cierre", f.Column([txt_obs, btn_main_guardar], spacing=10))
                ], scroll="auto"), padding=20, expand=True)
            ], bgcolor=c["fondo"]))

        # --- HISTORIAL ---
        if page.route == "/historial":
            lista_items = []
            
            def sincronizar_pendientes(e):
                pendientes = database.obtener_reportes_pendientes()
                if not pendientes:
                    page.open(f.SnackBar(f.Text("No hay correos pendientes"), bgcolor="grey"))
                    return
                
                enviados = 0
                total = len(pendientes)
                page.open(f.SnackBar(f.Text(f"Sincronizando {total} reportes..."), bgcolor="blue"))
                
                for p_id, p_pdf, p_cli, p_tec in pendientes:
                    try:
                        email_dest = database.obtener_correo_cliente(p_cli)
                        config.CORREOS_POR_CLIENTE[p_cli] = email_dest
                        ok, msg = utils.enviar_correo_graph(p_pdf, p_cli, p_tec)
                        utils.subir_archivo_sharepoint(p_pdf, p_cli)
                        if ok:
                            database.actualizar_estado_email(p_id, 1)
                            enviados += 1
                    except: pass
                
                page.open(f.SnackBar(f.Text(f"Sincronización completa: {enviados}/{total} enviados"), bgcolor="green" if enviados==total else "orange"))
                page.go("/dummy"); page.go("/historial")

            btn_sync = f.IconButton(icon=f.Icons.SYNC, tooltip="Enviar pendientes", on_click=sincronizar_pendientes, icon_color=config.COLOR_PRIMARIO)

            datos = database.obtener_historial()
            if not datos: lista_items.append(f.Text("Vacío", color="grey"))
            else:
                for row in datos:
                    id_rep, fecha, cli, tec, obs, pdf_p, enviado, detalles, imgs = row
                    ex = pdf_p and os.path.exists(pdf_p)
                    icon_env = f.Icon(f.Icons.CHECK_CIRCLE, color="green") if enviado else f.Icon(f.Icons.ACCESS_TIME_FILLED, color="orange", tooltip="Pendiente de envío")
                    
                    def editar_click(e, id_r=id_rep):
                        app_state["id_editar"] = id_r
                        page.go("/nueva_visita")

                    def accion_reenviar(e, r_data=row, id_r=id_rep, cli_r=cli, tec_r=tec, pdf_r=pdf_p, dlg_ref=None):
                        if dlg_ref: page.close(dlg_ref)
                        page.open(f.SnackBar(f.Text("Enviando correo..."), bgcolor="blue"))
                        page.update()
                        ok, msg_env = utils.enviar_correo_graph(pdf_r, cli_r, tec_r)
                        if ok: database.actualizar_estado_email(id_r, 1)
                        page.open(f.SnackBar(f.Text(msg_env), bgcolor="green" if ok else "red"))
                        page.go("/dummy")
                        page.go("/historial")

                    def ver_detalle_modal(e, r_data=row):
                        _id, _fe, _cl, _te, _ob, _pd, _en, _det, _im = r_data
                        header_modal = f.Container(content=f.Column([f.Image(src="logo2.png", height=40), f.Text("REPORTE DE VISITA", weight="bold", size=18, color=config.COLOR_PRIMARIO), f.Text(f"{_cl} - {_fe}", size=12, color="grey")], horizontal_alignment="center"), bgcolor=c["card_bg"], padding=10, border_radius=10)
                        usuarios_ui = []
                        if _det:
                            try:
                                usrs = json.loads(_det)
                                for u in usrs:
                                    st = "✅" if u['atendido'] else "❌"; desc = u['trabajo'] if u['atendido'] else u['motivo']
                                    fotos_ui = f.Row(scroll="auto")
                                    if u.get('fotos'):
                                        for fot in u['fotos']: fotos_ui.controls.append(f.Image(src=fot, width=100, height=100, fit="cover", border_radius=8))
                                    firma_ui = f.Image(src=u['firma'], width=150) if u.get('firma') else f.Container()
                                    usuarios_ui.append(f.Container(content=f.Column([f.Text(f"{st} {u['nombre']}", weight="bold", color=c["texto"]), f.Text(desc, size=12, color=c["texto_sec"]), fotos_ui, f.Text("Firma:", size=10) if u.get('firma') else f.Container(), firma_ui, f.Divider()]), padding=10, border=f.border.all(1, "grey300"), border_radius=8, bgcolor=c["input_bg"]))
                            except: pass
                        
                        dlg = f.AlertDialog()
                        btn_reenviar = f.TextButton("Enviar Email", icon=f.Icons.SEND, on_click=lambda e: accion_reenviar(e, row, _id, _cl, _te, _pd, dlg))
                        
                        dlg.content = f.Container(content=f.Column([header_modal, f.Text(f"Tec: {_te}", color=c["texto"], weight="bold"), f.Divider(), f.Column(usuarios_ui, scroll="auto", expand=True), f.Text(f"Nota: {_ob}", italic=True, color=c["texto_sec"])], scroll="auto"), width=600, height=700)
                        dlg.actions = [f.TextButton("Cerrar", on_click=lambda e: page.close(dlg)), btn_reenviar]
                        dlg.inset_padding = 10
                        page.open(dlg)
                    
                    lista_items.append(f.Container(content=f.Column([
                        f.Row([
                            f.Row([f.Container(content=f.Icon(f.Icons.DESCRIPTION, color=config.COLOR_BLANCO), bgcolor=config.COLOR_PRIMARIO if ex else "grey", padding=10, border_radius=12), 
                                   f.Column([f.Text(cli, weight="bold", color=c["texto"]), f.Text(fecha, size=12, color=c["texto_sec"])], spacing=0)]), 
                            icon_env
                        ], alignment="spaceBetween"), 
                        f.Divider(color=c["borde"]), 
                        f.Row([
                            f.Text(f"Tec: {tec}", color=c["texto"]), 
                            f.Row([
                                f.IconButton(icon=f.Icons.EDIT, icon_color="orange", tooltip="Editar", on_click=editar_click),
                                f.IconButton(icon=f.Icons.VISIBILITY, icon_color=config.COLOR_PRIMARIO, tooltip="Ver detalle", on_click=ver_detalle_modal)
                            ])
                        ], alignment="spaceBetween")
                    ]), padding=15, bgcolor=c["card_bg"], border_radius=12, shadow=f.BoxShadow(blur_radius=5, color=c["sombra"]), margin=f.margin.only(bottom=10)))
            
            page.views.append(f.View("/historial", controls=[
                f.AppBar(
                    leading=f.IconButton(icon=f.Icons.ARROW_BACK, icon_color=config.COLOR_PRIMARIO, on_click=lambda _: page.go("/")),
                    title=f.Text("Historial", color=c["texto"]), 
                    bgcolor=c["superficie"], 
                    color=config.COLOR_PRIMARIO, 
                    elevation=0, 
                    actions=[btn_sync]
                ),
                f.Container(content=f.ListView(controls=lista_items, spacing=5, padding=20), expand=True)
            ], bgcolor=c["fondo"]))
        
        page.update()

    def view_pop(view):
        if len(page.views) > 0:
            page.views.pop()
        
        if len(page.views) > 0:
            top_view = page.views[-1]
            page.go(top_view.route)
        else:
            page.go("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)

f.app(target=main)