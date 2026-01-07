import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'db_helper.dart';

class ApiService {
  
  static const String _defaultUrl = "http://192.168.1.100:8000";

  static Future<String> _getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    String? url = prefs.getString('api_url');
    String finalUrl = url ?? _defaultUrl;
    if (finalUrl.endsWith('/')) {
      finalUrl = finalUrl.substring(0, finalUrl.length - 1);
    }
    return finalUrl;
  }

  // --- MODIFICADO: SOLO VALIDACIÓN DE CONEXIÓN ---
  static Future<bool> sincronizarDatos() async {
    try {
      String baseUrl = await _getBaseUrl();
      print("Probando conexión con $baseUrl...");
      
      // Hacemos peticiones ligeras solo para ver si el servidor responde
      final respClientes = await http.get(Uri.parse('$baseUrl/clientes')).timeout(const Duration(seconds: 5));
      final respTecnicos = await http.get(Uri.parse('$baseUrl/tecnicos')).timeout(const Duration(seconds: 5));

      // Si el servidor responde OK (200)
      if (respClientes.statusCode == 200 && respTecnicos.statusCode == 200) {
        
        print("✅ Conexión Exitosa - NO se han modificado datos locales.");
        
        // AQUÍ ESTABA LA LÍNEA QUE BORRABA TUS DATOS. LA HEMOS QUITADO.
        // await DBHelper().guardarConfiguracion(...); 

        return true; 

      } else {
        print("⚠️ Servidor respondió pero con errores (Status no 200).");
        return false;
      }
    } catch (e) {
      print("Error de Conexión: $e");
      return false; // Retornamos false para que la UI sepa que falló
    }
  }

  // 2. CREACIÓN REMOTA (Se mantiene por si quieres enviar datos individuales al crearlos)
  
  static Future<bool> crearClienteRemoto(String nombre, String email) async {
    try {
      String baseUrl = await _getBaseUrl();
      print("Enviando Cliente a $baseUrl/clientes");
      final response = await http.post(
        Uri.parse('$baseUrl/clientes'),
        headers: {"Content-Type": "application/json"},
        body: json.encode({"nombre": nombre, "email": email}),
      );
      return response.statusCode == 200;
    } catch (e) { print("Error crearCliente: $e"); return false; }
  }

  static Future<bool> crearTecnicoRemoto(String nombre) async {
    try {
      String baseUrl = await _getBaseUrl();
      print("Enviando Técnico a $baseUrl/tecnicos");
      final response = await http.post(
        Uri.parse('$baseUrl/tecnicos'),
        headers: {"Content-Type": "application/json"},
        body: json.encode({"nombre": nombre}),
      );
      return response.statusCode == 200;
    } catch (e) { print("Error crearTecnico: $e"); return false; }
  }

  static Future<bool> crearUsuarioRemoto(String nombre, String cliente) async {
    try {
      String baseUrl = await _getBaseUrl();
      print("Enviando Usuario a $baseUrl/usuarios");
      final response = await http.post(
        Uri.parse('$baseUrl/usuarios'),
        headers: {"Content-Type": "application/json"},
        body: json.encode({"nombre": nombre, "cliente_nombre": cliente}),
      );
      return response.statusCode == 200;
    } catch (e) { print("Error crearUsuario: $e"); return false; }
  }

  // --- SUBIDA DE REPORTES (Se mantiene intacto para enviar los PDFs) ---

  static Future<bool> subirReporte(Map<String, dynamic> reporte) async {
    try {
      String baseUrl = await _getBaseUrl();
      var uri = Uri.parse('$baseUrl/reporte/crear');
      var request = http.MultipartRequest('POST', uri);

      request.fields['cliente'] = reporte['cliente'];
      request.fields['tecnico'] = reporte['tecnico'];
      request.fields['obs'] = reporte['obs'];
      request.fields['datos_usuarios'] = reporte['datos_usuarios'];

      String? emailCliente = await DBHelper().getClientEmail(reporte['cliente']);
      if (emailCliente != null) request.fields['email_cliente'] = emailCliente;
      String? emailTecnico = await DBHelper().getTecnicoEmail(reporte['tecnico']);
      if (emailTecnico != null) request.fields['email_tecnico'] = emailTecnico;

      List<dynamic> usuarios = json.decode(reporte['datos_usuarios']);
      for (var u in usuarios) {
        if (u['fotos'] != null) {
          for (String pathFoto in u['fotos']) {
             if (File(pathFoto).existsSync()) request.files.add(await http.MultipartFile.fromPath('fotos', pathFoto));
          }
        }
        if (u['firma'] != null && File(u['firma']).existsSync()) {
             request.files.add(await http.MultipartFile.fromPath('firmas_usuarios', u['firma']));
        }
      }
      var response = await request.send();
      return response.statusCode == 200;
    } catch (e) { return false; }
  }

  static Future<bool> eliminarReporteRemoto(int serverId) async {
    try {
      String baseUrl = await _getBaseUrl();
      final response = await http.delete(Uri.parse('$baseUrl/reporte/$serverId'));
      return response.statusCode == 200;
    } catch (e) { return false; }
  }

  static Future<bool> eliminarClienteRemoto(String nombre) async {
    try {
      String baseUrl = await _getBaseUrl();
      final url = '$baseUrl/cliente/${Uri.encodeComponent(nombre)}';
      final response = await http.delete(Uri.parse(url));
      return response.statusCode == 200;
    } catch (e) { return false; }
  }

  static Future<bool> eliminarTecnicoRemoto(String nombre) async {
    try {
      String baseUrl = await _getBaseUrl();
      final url = '$baseUrl/tecnico/${Uri.encodeComponent(nombre)}';
      final response = await http.delete(Uri.parse(url));
      return response.statusCode == 200;
    } catch (e) { return false; }
  }

  static Future<bool> eliminarUsuarioRemoto(String nombre, String cliente) async {
    try {
      String baseUrl = await _getBaseUrl();
      final url = '$baseUrl/usuario/${Uri.encodeComponent(cliente)}/${Uri.encodeComponent(nombre)}';
      final response = await http.delete(Uri.parse(url));
      return response.statusCode == 200;
    } catch (e) { return false; }
  }

  // Se mantiene la función pero no la usaremos en el botón "Sincronizar" principal
  static Future<bool> subirDatosLocales({
    required List<Map<String, dynamic>> clientes,
    required List<String> tecnicos,
    required Map<String, List<String>> usuariosPorCliente
  }) async {
    try {
      String baseUrl = await _getBaseUrl();
      print("📤 Subiendo datos locales al servidor...");

      // A. SUBIR CLIENTES
      for (var c in clientes) {
        try {
          await http.post(
            Uri.parse('$baseUrl/clientes'),
            headers: {"Content-Type": "application/json"},
            body: json.encode({
              "nombre": c['nombre'],
              "email": c['email'] ?? ""
            }),
          );
        } catch (e) { print("Error subiendo cliente: $e"); }
      }

      // B. SUBIR TÉCNICOS
      for (var t in tecnicos) {
        try {
          await http.post(
            Uri.parse('$baseUrl/tecnicos'),
            headers: {"Content-Type": "application/json"},
            body: json.encode({"nombre": t}),
          );
        } catch (e) { print("Error subiendo técnico: $e"); }
      }

      // C. SUBIR USUARIOS
      for (var entry in usuariosPorCliente.entries) {
        String cliente = entry.key;
        for (var usuario in entry.value) {
          try {
            await http.post(
              Uri.parse('$baseUrl/usuarios'),
              headers: {"Content-Type": "application/json"},
              body: json.encode({
                "nombre": usuario,
                "cliente": cliente
              }),
            );
          } catch (e) { print("Error subiendo usuario: $e"); }
        }
      }
      return true;
    } catch (e) {
      print("Error General Subida Datos: $e");
      return false;
    }
  }
}