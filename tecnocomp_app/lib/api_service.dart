import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'db_helper.dart';

// CAMBIA ESTO POR TU IP LOCAL (Ej: 192.168.1.15)
// No uses localhost porque el celular no entenderá.
const String BASE_URL = "http://10.101.0.112:8000"; 

class ApiService {
  
  // Descarga clientes y técnicos del Python
  static Future<bool> sincronizarDatos() async {
    try {
      print("Intentando conectar a $BASE_URL...");
      final respClientes = await http.get(Uri.parse('$BASE_URL/clientes')).timeout(const Duration(seconds: 5));
      final respTecnicos = await http.get(Uri.parse('$BASE_URL/tecnicos')).timeout(const Duration(seconds: 5));

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

  // Sube reporte + fotos al Python
  static Future<bool> subirReporte(Map<String, dynamic> reporte) async {
    try {
      var uri = Uri.parse('$BASE_URL/reporte/crear');
      var request = http.MultipartRequest('POST', uri);

      request.fields['cliente'] = reporte['cliente'];
      request.fields['tecnico'] = reporte['tecnico'];
      request.fields['obs'] = reporte['obs'];
      request.fields['datos_usuarios'] = reporte['datos_usuarios'];

      // Adjuntar fotos si existen
      List<dynamic> usuarios = json.decode(reporte['datos_usuarios']);
      for (var u in usuarios) {
        if (u['fotos'] != null) {
          for (String pathFoto in u['fotos']) {
             if (File(pathFoto).existsSync()) {
               request.files.add(await http.MultipartFile.fromPath('fotos', pathFoto));
             }
          }
        }
      }

      var response = await request.send();
      if (response.statusCode == 200) {
        return true;
      } else {
        print("Error Servidor: ${response.statusCode}");
        return false;
      }
    } catch (e) {
      print("Error Subida: $e");
      return false;
    }
  }
}