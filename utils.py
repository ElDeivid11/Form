import datetime
import pytz
import requests
import base64
import tempfile
import os
from PIL import Image, ImageDraw
import config

def obtener_hora_chile():
    try:
        return datetime.datetime.now(pytz.timezone('Chile/Continental'))
    except:
        return datetime.datetime.now()

# --- HELPER INTERNO PARA AUTH (Token Único) ---
def _obtener_token_graph():
    url = f"https://login.microsoftonline.com/{config.GRAPH_TENANT_ID}/oauth2/v2.0/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': config.GRAPH_CLIENT_ID,
        'client_secret': config.GRAPH_CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default'
    }
    try:
        r = requests.post(url, data=data)
        js = r.json()
        if 'access_token' in js:
            return js['access_token']
        print(f"Error Token: {js}")
        return None
    except Exception as e:
        print(f"Excepción Token: {e}")
        return None

def _sanitizar_nombre(nombre):
    if not nombre: return "SinNombre"
    for char in ['"', '*', ':', '<', '>', '?', '/', '\\', '|']:
        nombre = nombre.replace(char, '')
    return nombre.strip()

# --- BACKUP BASE DE DATOS ---
def subir_backup_sharepoint(ruta_db):
    """Sube el archivo .db a la carpeta /Backups de SharePoint"""
    if not os.path.exists(ruta_db):
        return False, "No se encontró el archivo de base de datos"

    token = _obtener_token_graph()
    if not token: return False, "Error de autenticación Azure"

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    timestamp = obtener_hora_chile().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_visitas_{timestamp}.db"

    try:
        # 1. Obtener ID Sitio
        site_url = f"https://graph.microsoft.com/v1.0/sites/{config.SHAREPOINT_HOST_NAME}:{config.SHAREPOINT_SITE_PATH}"
        r_site = requests.get(site_url, headers=headers)
        if r_site.status_code != 200: return False, f"Error Sitio: {r_site.text}"
        site_id = r_site.json()['id']

        # 2. Obtener ID Drive
        drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        r_drives = requests.get(drives_url, headers=headers)
        drive_id = None
        for d in r_drives.json().get('value', []):
            if d['name'] == config.SHAREPOINT_DRIVE_NAME or d['name'] == "Documents" or d['name'] == "Documentos":
                drive_id = d['id']
                break
        if not drive_id and r_drives.json().get('value'): drive_id = r_drives.json()['value'][0]['id']
        if not drive_id: return False, "No se encontró Documentos"

        # 3. Subir a carpeta /Backups
        ruta_sharepoint = f"/Backups/{filename}"
        upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{ruta_sharepoint}:/content"

        with open(ruta_db, 'rb') as f_up:
            headers_put = headers.copy()
            headers_put['Content-Type'] = 'application/octet-stream'
            r_up = requests.put(upload_url, headers=headers_put, data=f_up)

        if r_up.status_code in [200, 201]:
            return True, "Backup subido exitosamente"
        else:
            return False, f"Error subida: {r_up.status_code}"

    except Exception as e:
        return False, f"Excepción Backup: {e}"

# --- SHAREPOINT (PDFs) ---
def subir_archivo_sharepoint(ruta_local, cliente):
    if not os.path.exists(ruta_local): return False, "Archivo no existe"
    token = _obtener_token_graph()
    if not token: return False, "No Auth"

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    filename = os.path.basename(ruta_local)
    cliente_limpio = _sanitizar_nombre(cliente)
    fecha_carpeta = obtener_hora_chile().strftime('%Y-%m-%d')

    try:
        site_url = f"https://graph.microsoft.com/v1.0/sites/{config.SHAREPOINT_HOST_NAME}:{config.SHAREPOINT_SITE_PATH}"
        r_site = requests.get(site_url, headers=headers)
        if r_site.status_code != 200: return False, f"Error Sitio: {r_site.text}"
        site_id = r_site.json()['id']

        drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        r_drives = requests.get(drives_url, headers=headers)
        drive_id = None
        for d in r_drives.json().get('value', []):
            if d['name'] == config.SHAREPOINT_DRIVE_NAME or d['name'] == "Documents" or d['name'] == "Documentos":
                drive_id = d['id']; break
        if not drive_id and r_drives.json().get('value'): drive_id = r_drives.json()['value'][0]['id']
        if not drive_id: return False, "No Documentos"

        ruta_sharepoint = f"/{cliente_limpio}/{fecha_carpeta}/{filename}"
        upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{ruta_sharepoint}:/content"

        with open(ruta_local, 'rb') as f_upload:
            headers_put = headers.copy(); headers_put['Content-Type'] = 'application/pdf'
            r_up = requests.put(upload_url, headers=headers_put, data=f_upload)

        if r_up.status_code in [200, 201]: return True, f"Subido a '{cliente_limpio}/{fecha_carpeta}'"
        return False, f"Error SP: {r_up.status_code}"
    except Exception as e: return False, f"Excep SP: {e}"

# --- EMAIL GRAPH (DISEÑO MEJORADO) ---
def enviar_correo_graph(ruta_pdf, cliente, tecnico):
    if not os.path.exists(ruta_pdf): return False, "PDF no existe."
    destinatario = config.CORREOS_POR_CLIENTE.get(cliente, "")
    if not destinatario: return False, f"No hay correo para {cliente}"

    token = _obtener_token_graph()
    if not token: return False, "Error Auth Azure"

    with open(ruta_pdf, "rb") as f:
        pdf_content = base64.b64encode(f.read()).decode("utf-8")
    
    # --- PLANTILLA HTML ESTILIZADA ---
    color_brand = config.COLOR_PRIMARIO
    fecha_hoy = obtener_hora_chile().strftime('%d/%m/%Y')
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ margin: 0; padding: 0; background-color: #f4f4f4; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; }}
            .email-container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .header {{ background-color: {color_brand}; color: #ffffff; padding: 25px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 22px; text-transform: uppercase; letter-spacing: 1px; }}
            .content {{ padding: 30px; line-height: 1.6; }}
            .info-box {{ background-color: #f8f9fa; border-left: 5px solid {color_brand}; padding: 15px; margin: 25px 0; border-radius: 4px; }}
            .info-row {{ margin-bottom: 8px; font-size: 14px; }}
            .info-label {{ font-weight: bold; color: #555; width: 120px; display: inline-block; }}
            .footer {{ background-color: #eeeeee; padding: 15px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #e0e0e0; }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>Reporte de Visita Técnica</h1>
            </div>
            <div class="content">
                <p>Estimados <strong>{cliente}</strong>,</p>
                <p>Junto con saludar, hacemos entrega del informe técnico correspondiente a los servicios realizados el día de hoy en sus instalaciones.</p>
                
                <div class="info-box">
                    <div class="info-row">
                        <span class="info-label">Fecha:</span> {fecha_hoy}
                    </div>
                    <div class="info-row">
                        <span class="info-label">Técnico:</span> {tecnico}
                    </div>
                    <div class="info-row">
                        <span class="info-label">Estado:</span> <strong style="color: #28a745;">Finalizado con Éxito</strong>
                    </div>
                </div>

                <p>El documento PDF adjunto contiene el detalle completo de las labores efectuadas, evidencias fotográficas y las firmas de conformidad.</p>
                
                <p style="margin-top: 30px;">Atentamente,<br><strong>Equipo de Soporte Tecnocomp</strong></p>
            </div>
            <div class="footer">
                <p>&copy; {datetime.datetime.now().year} Tecnocomp Computación Ltda.</p>
                <p>Este correo ha sido generado automáticamente. Por favor no responder a esta dirección.</p>
            </div>
        </div>
    </body>
    </html>
    """

    email_data = {
        "message": {
            "subject": f"📍 Reporte de Visita - {cliente} - {fecha_hoy}",
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": destinatario}}],
            "attachments": [{
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": os.path.basename(ruta_pdf),
                "contentType": "application/pdf",
                "contentBytes": pdf_content
            }]
        },
        "saveToSentItems": "true"
    }

    try:
        r = requests.post(
            f"https://graph.microsoft.com/v1.0/users/{config.GRAPH_USER_EMAIL}/sendMail",
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json=email_data
        )
        if r.status_code == 202: return True, "Correo enviado (Oficial)"
        return False, f"Error Graph: {r.text}"
    except Exception as e:
        return False, f"Error envío: {e}"

def guardar_firma_img(trazos, nombre_archivo="firma_temp.png"):
    if not trazos: return None
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, nombre_archivo)
    img = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(img)
    for t in trazos:
        if len(t) > 1: draw.line(t, fill="black", width=3)
        elif len(t) == 1: draw.point(t[0], fill="black")
    img.save(path); return path