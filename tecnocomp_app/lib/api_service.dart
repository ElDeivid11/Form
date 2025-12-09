import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart'; // IMPORTANTE
import 'db_helper.dart';

class ApiService {
  
  // IP por defecto (puedes cambiarla si quieres)
  static const String _defaultUrl = "http://192.168.1.100:8000";

  // Función auxiliar para obtener la URL guardada
  static Future<String> _getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    String? url = prefs.getString('api_url');
    // Si no hay nada guardado, usamos la default.
    // Nos aseguramos que no termine en '/' para evitar errores de ruta.
    String finalUrl = url ?? _defaultUrl;
    if (finalUrl.endsWith('/')) {
      finalUrl = finalUrl.substring(0, finalUrl.length - 1);
    }
    return finalUrl;
  }

  // 1. SINCRONIZAR DATOS
  static Future<bool> sincronizarDatos() async {
    try {
      String baseUrl = await _getBaseUrl();
      print("Intentando conectar a $baseUrl...");
      
      final respClientes = await http.get(Uri.parse('$baseUrl/clientes')).timeout(const Duration(seconds: 90));
      final respTecnicos = await http.get(Uri.parse('$baseUrl/tecnicos')).timeout(const Duration(seconds: 90));

      if (respClientes.statusCode == 200 && respTecnicos.statusCode == 200) {
        List cli = json.decode(respClientes.body);
        List tec = json.decode(respTecnicos.body);
        
        await DBHelper().guardarConfiguracion(cli, tec);
        return true;
      }
      return false;
    } catch (e) {
      print("Error Sync: $e");
      return false;
    }
  }

  // 2. SUBIR REPORTE (ACTUALIZADO CON EMAIL TÉCNICO)
  static Future<bool> subirReporte(Map<String, dynamic> reporte) async {
    try {
      String baseUrl = await _getBaseUrl();
      var uri = Uri.parse('$baseUrl/reporte/crear');
      var request = http.MultipartRequest('POST', uri);

      // --- CAMPOS BÁSICOS ---
      request.fields['cliente'] = reporte['cliente'];
      request.fields['tecnico'] = reporte['tecnico'];
      request.fields['obs'] = reporte['obs'];
      request.fields['datos_usuarios'] = reporte['datos_usuarios'];

      // --- 1. EMAIL DEL CLIENTE (Si existe) ---
      String? emailCliente = await DBHelper().getClientEmail(reporte['cliente']);
      if (emailCliente != null && emailCliente.isNotEmpty) {
        request.fields['email_cliente'] = emailCliente;
      }

      // --- 2. EMAIL DEL TÉCNICO (NUEVO) ---
      // Buscamos el correo del técnico en la BD local para enviarlo al servidor
      String? emailTecnico = await DBHelper().getTecnicoEmail(reporte['tecnico']);
      if (emailTecnico != null && emailTecnico.isNotEmpty) {
        request.fields['email_tecnico'] = emailTecnico;
      }

      // --- ARCHIVOS (FOTOS Y FIRMAS) ---
      List<dynamic> usuarios = json.decode(reporte['datos_usuarios']);
      
      for (var u in usuarios) {
        // Fotos
        if (u['fotos'] != null) {
          for (String pathFoto in u['fotos']) {
             if (File(pathFoto).existsSync()) {
               request.files.add(await http.MultipartFile.fromPath('fotos', pathFoto));
             }
          }
        }
        // Firmas
        if (u['firma'] != null) {
          String pathFirma = u['firma'];
          if (File(pathFirma).existsSync()) {
             request.files.add(await http.MultipartFile.fromPath('firmas_usuarios', pathFirma));
          }
        }
      }

      // --- ENVIAR SOLICITUD ---
      var response = await request.send();
      
      if (response.statusCode == 200) {
        // Intentar leer server_id si viene en la respuesta (opcional para futuras mejoras)
        return true;
      } else {
        final respStr = await response.stream.bytesToString();
        print("Error Servidor (${response.statusCode}): $respStr");
        return false;
      }
    } catch (e) {
      print("Error Subida: $e");
      return false;
    }
  }

  // 3. ELIMINAR REPORTE DEL SERVIDOR (NUEVO)
  static Future<bool> eliminarReporteRemoto(int serverId) async {
    try {
      String baseUrl = await _getBaseUrl();
      // Asume que tu API tiene DELETE /reporte/{id}
      final response = await http.delete(Uri.parse('$baseUrl/reporte/$serverId'));
      return response.statusCode == 200;
    } catch (e) {
      print("Error eliminando: $e");
      return false;
    }
  }
  // ... (código anterior igual)

  // 4. ELIMINAR CLIENTE REMOTO
  static Future<bool> eliminarClienteRemoto(String nombre) async {
    try {
      String baseUrl = await _getBaseUrl();
      // Usamos Uri.encodeComponent para manejar espacios en nombres (ej: "Juan Perez")
      final url = '$baseUrl/cliente/${Uri.encodeComponent(nombre)}';
      final response = await http.delete(Uri.parse(url));
      return response.statusCode == 200;
    } catch (e) {
      print("Error borrando cliente remoto: $e");
      return false;
    }
  }

  // 5. ELIMINAR TÉCNICO REMOTO
  static Future<bool> eliminarTecnicoRemoto(String nombre) async {
    try {
      String baseUrl = await _getBaseUrl();
      final url = '$baseUrl/tecnico/${Uri.encodeComponent(nombre)}';
      final response = await http.delete(Uri.parse(url));
      return response.statusCode == 200;
    } catch (e) {
      print("Error borrando técnico remoto: $e");
      return false;
    }
  }

  // 6. ELIMINAR USUARIO REMOTO
  static Future<bool> eliminarUsuarioRemoto(String nombre, String cliente) async {
    try {
      String baseUrl = await _getBaseUrl();
      final url = '$baseUrl/usuario/${Uri.encodeComponent(cliente)}/${Uri.encodeComponent(nombre)}';
      final response = await http.delete(Uri.parse(url));
      return response.statusCode == 200;
    } catch (e) {
      print("Error borrando usuario remoto: $e");
      return false;
    }
  }
}
