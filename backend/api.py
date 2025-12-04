import shutil
import os
import json
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Importamos tus módulos existentes
import database
import utils
import pdf_generator
import config

app = FastAPI(title="Tecnocomp API")

# Inicializamos la DB al arrancar
database.inicializar_db()

# Modelos de datos para recibir JSON (Pydantic)
class ClienteBase(BaseModel):
    nombre: str
    email: str

class TecnicoBase(BaseModel):
    nombre: str

# --- ENDPOINTS DE CONFIGURACIÓN ---

@app.get("/clientes")
def get_clientes():
    return database.obtener_clientes()

@app.get("/tecnicos")
def get_tecnicos():
    return database.obtener_tecnicos()

@app.post("/clientes")
def create_cliente(cliente: ClienteBase):
    exito = database.agregar_cliente(cliente.nombre, cliente.email)
    if not exito: raise HTTPException(status_code=400, detail="Error al crear cliente")
    return {"status": "ok"}

@app.get("/usuarios/{cliente_nombre}")
def get_usuarios(cliente_nombre: str):
    return database.obtener_usuarios_por_cliente(cliente_nombre)

# --- ENDPOINT PRINCIPAL: CREAR REPORTE ---
# Este endpoint recibe los datos del formulario Y las fotos al mismo tiempo
@app.post("/reporte/crear")
async def crear_reporte(
    cliente: str = Form(...),
    tecnico: str = Form(...),
    obs: str = Form(""),
    datos_usuarios: str = Form(...), # Recibiremos el JSON como string
    firma_tecnico: UploadFile = File(None),
    fotos: List[UploadFile] = File(None)
):
    try:
        # 1. Procesar Datos
        usuarios_parsed = json.loads(datos_usuarios)
        
        # 2. Guardar Imágenes Temporales
        # Necesitamos mapear qué foto pertenece a qué usuario/evidencia.
        # Para simplificar esta migración inicial, guardaremos todas en una carpeta temp
        # y actualizaremos las rutas en el JSON.
        
        temp_dir = "temp_uploads"
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)

        rutas_fotos_finales = []
        
        # Guardar firma técnico si existe
        path_firma_tec = None
        if firma_tecnico:
            path_firma_tec = f"{temp_dir}/firma_tec_{firma_tecnico.filename}"
            with open(path_firma_tec, "wb") as buffer:
                shutil.copyfileobj(firma_tecnico.file, buffer)

        # Procesar fotos de evidencia
        # Nota: En una implementación real, deberías enviar IDs para relacionar 
        # cada foto con su usuario específico. Por ahora, asumiremos que el frontend
        # envía las rutas o nombres correctos en el JSON y aquí solo subimos los archivos.
        if fotos:
            for foto in fotos:
                ruta_dest = f"{temp_dir}/{foto.filename}"
                with open(ruta_dest, "wb") as buffer:
                    shutil.copyfileobj(foto.file, buffer)
                rutas_fotos_finales.append(ruta_dest)

        # 3. Generar PDF (Reutilizando tu lógica)
        # Tu pdf_generator espera rutas locales, así que usamos las que acabamos de guardar.
        pdf_path = pdf_generator.generar_pdf(
            cliente=cliente,
            tecnico=tecnico,
            obs=obs,
            path_firma=path_firma_tec,
            datos_usuarios=usuarios_parsed 
        )

        # 4. Guardar en Base de Datos
        fecha_actual = utils.obtener_hora_chile().strftime('%Y-%m-%d %H:%M:%S')
        database.guardar_reporte(
            fecha=fecha_actual,
            cliente=cliente,
            tecnico=tecnico,
            obs=obs,
            fotos_json=json.dumps(rutas_fotos_finales),
            pdf_path=pdf_path,
            detalles_json=json.dumps(usuarios_parsed),
            estado_envio=0
        )

        # 5. Enviar Correo y Subir a SharePoint (Tu lógica de utils.py)
        # Obtenemos el ID del reporte recién creado (el último)
        # Ojo: esto es una simplificación. Lo ideal es que guardar_reporte retorne el ID.
        
        # Ejecutamos la lógica de envío
        email_dest = database.obtener_correo_cliente(cliente)
        config.CORREOS_POR_CLIENTE[cliente] = email_dest # Actualizar config runtime
        
        ok_email, msg_email = utils.enviar_correo_graph(pdf_path, cliente, tecnico)
        ok_sp, msg_sp = utils.subir_archivo_sharepoint(pdf_path, cliente)

        return {
            "status": "success",
            "pdf_generated": pdf_path,
            "email_sent": ok_email,
            "sharepoint_upload": ok_sp,
            "message": f"Email: {msg_email} | SP: {msg_sp}"
        }

    except Exception as e:
        print(f"Error procesando reporte: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Escucha en todas las interfaces para que tu celular pueda conectar
    uvicorn.run(app, host="0.0.0.0", port=8000)