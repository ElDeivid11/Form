# utils.py
import datetime
import pytz
import smtplib
import tempfile
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from PIL import Image, ImageDraw
import config

def obtener_hora_chile():
    try:
        return datetime.datetime.now(pytz.timezone('Chile/Continental'))
    except:
        return datetime.datetime.now()

def enviar_correo_smtp(ruta_pdf, cliente, tecnico):
    if not os.path.exists(ruta_pdf):
        return False, "PDF no existe."
    
    dest = config.CORREOS_POR_CLIENTE.get(cliente, "")
    if not dest:
        return False, f"No hay correo para {cliente}"
    
    msg = MIMEMultipart()
    msg['From'] = config.EMAIL_REMITENTE
    msg['To'] = dest
    msg['Subject'] = f"Reporte - {cliente} - {obtener_hora_chile().strftime('%d/%m')}"
    
    cuerpo = f"""
    <html>
        <body>
            <h2 style="color:{config.COLOR_PRIMARIO};">Reporte de Visita</h2>
            <p>Se adjunta el informe técnico realizado por {tecnico}.</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(cuerpo, 'html'))
    
    try:
        with open(ruta_pdf, "rb") as att:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(att.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(ruta_pdf)}")
        msg.attach(part)
        
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.EMAIL_REMITENTE, config.EMAIL_PASSWORD)
        server.sendmail(config.EMAIL_REMITENTE, dest, msg.as_string())
        server.quit()
        return True, f"Enviado a {dest}"
    except Exception as e:
        return False, f"Error Envío: {e}"

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