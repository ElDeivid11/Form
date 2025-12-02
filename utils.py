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

def enviar_correo_graph(ruta_pdf, cliente, tecnico):
    """
    Envía el correo usando la API oficial de Microsoft Graph.
    Requiere que la App esté registrada en Azure con permiso Mail.Send
    """
    if not os.path.exists(ruta_pdf):
        return False, "PDF no existe."
    
    # Obtener destinatario
    destinatario = config.CORREOS_POR_CLIENTE.get(cliente, "")
    if not destinatario:
        return False, f"No hay correo para {cliente}"

    # 1. Autenticación (Obtener Token)
    token_url = f"https://login.microsoftonline.com/{config.GRAPH_TENANT_ID}/oauth2/v2.0/token"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': config.GRAPH_CLIENT_ID,
        'client_secret': config.GRAPH_CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    try:
        token_r = requests.post(token_url, data=token_data)
        token_json = token_r.json()
        if 'access_token' not in token_json:
            return False, f"Error Auth Azure: {token_json.get('error_description', 'Desconocido')}"
        access_token = token_json['access_token']
    except Exception as e:
        return False, f"Error conexión Azure: {e}"

    # 2. Preparar PDF en Base64
    with open(ruta_pdf, "rb") as f:
        pdf_content = base64.b64encode(f.read()).decode("utf-8")
    
    nombre_pdf = os.path.basename(ruta_pdf)
    fecha_hoy = obtener_hora_chile().strftime('%d/%m/%Y')
    
    # 3. Construir HTML (Escapado para JSON)
    color_brand = config.COLOR_PRIMARIO
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: 'Segoe UI', sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0;">
            <div style="background-color: {color_brand}; color: #ffffff; padding: 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">Reporte de Visita Técnica</h1>
            </div>
            <div style="padding: 30px; color: #333333; line-height: 1.6;">
                <p>Estimados <strong>{cliente}</strong>,</p>
                <p>Adjuntamos el informe técnico de los servicios realizados hoy.</p>
                <div style="background-color: #f8f9fa; border-left: 4px solid {color_brand}; padding: 15px; margin: 20px 0;">
                    <div><strong>Fecha:</strong> {fecha_hoy}</div>
                    <div><strong>Técnico:</strong> {tecnico}</div>
                    <div><strong>Estado:</strong> Finalizado</div>
                </div>
                <p>El PDF adjunto contiene el detalle completo y las firmas.</p>
                <p style="margin-top: 30px;">Atentamente,<br><strong>Equipo Tecnocomp</strong></p>
            </div>
            <div style="background-color: #eeeeee; padding: 10px; text-align: center; font-size: 12px; color: #777;">
                &copy; {datetime.datetime.now().year} Tecnocomp Computación Ltda.
            </div>
        </div>
    </body>
    </html>
    """

    # 4. Payload para Graph API
    email_url = f"https://graph.microsoft.com/v1.0/users/{config.GRAPH_USER_EMAIL}/sendMail"
    
    email_data = {
        "message": {
            "subject": f"Informe de Visita Técnica - {cliente} [{fecha_hoy}]",
            "body": {
                "contentType": "HTML",
                "content": html_body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": destinatario
                    }
                }
            ],
            "attachments": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": nombre_pdf,
                    "contentType": "application/pdf",
                    "contentBytes": pdf_content
                }
            ]
        },
        "saveToSentItems": "true"
    }

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(email_url, headers=headers, json=email_data)
        if response.status_code == 202:
            return True, f"Enviado a {destinatario} (Oficial)"
        else:
            # Intentar leer error
            try: err = response.json()
            except: err = response.text
            return False, f"Error Graph {response.status_code}: {err}"
    except Exception as e:
        return False, f"Error envío: {e}"

def guardar_firma_img(trazos, nombre_archivo="firma_temp.png"):
    if not trazos: return None
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, nombre_archivo)
    
    # Crear imagen blanca
    img = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(img)
    
    for t in trazos:
        if len(t) > 1:
            draw.line(t, fill="black", width=3)
        elif len(t) == 1:
            draw.point(t[0], fill="black")
            
    img.save(path)
    return path