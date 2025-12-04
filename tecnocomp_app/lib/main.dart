import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart'; // Cámara Nativa
import 'package:path_provider/path_provider.dart';
import 'db_helper.dart';
import 'api_service.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Tecnocomp',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0583F2)),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int pendientes = 0;

  @override
  void initState() {
    super.initState();
    _cargarPendientes();
  }

  void _cargarPendientes() async {
    final list = await DBHelper().getReportesPendientes();
    setState(() => pendientes = list.length);
  }

  void _sincronizar() async {
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Conectando con servidor...")));
    bool ok = await ApiService.sincronizarDatos();
    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(backgroundColor: Colors.green, content: Text("Datos actualizados correctamente")));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(backgroundColor: Colors.red, content: Text("Error de conexión. Revisa la IP.")));
    }
  }

  void _subirPendientes() async {
    final list = await DBHelper().getReportesPendientes();
    if (list.isEmpty) return;

    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Subiendo ${list.length} reportes...")));
    
    int subidos = 0;
    for (var rep in list) {
      bool ok = await ApiService.subirReporte(rep);
      if (ok) {
        await DBHelper().borrarReporte(rep['id']);
        subidos++;
      }
    }
    _cargarPendientes();
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: Colors.blue, content: Text("Proceso finalizado. Subidos: $subidos")));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Tecnocomp Mobile"), backgroundColor: const Color(0xFF0583F2), foregroundColor: Colors.white),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // LOGO
            Image.asset('assets/logo2.png', width: 250, errorBuilder: (c,o,s)=>const Icon(Icons.broken_image, size: 50)),
            const SizedBox(height: 40),
            
            // BOTÓN 1: SYNC
            _botonMenu(Icons.sync, "1. Sincronizar Datos", Colors.blueGrey, _sincronizar),
            const SizedBox(height: 15),
            
            // BOTÓN 2: NUEVA VISITA
            _botonMenu(Icons.add_circle, "2. Nueva Visita (Offline)", const Color(0xFF0583F2), () async {
                 await Navigator.push(context, MaterialPageRoute(builder: (_) => const FormularioVisita()));
                 _cargarPendientes();
            }),
            const SizedBox(height: 15),
            
            // BOTÓN 3: SUBIR
            _botonMenu(Icons.cloud_upload, "3. Subir Pendientes ($pendientes)", pendientes > 0 ? Colors.orange : Colors.grey, pendientes > 0 ? _subirPendientes : null),
          ],
        ),
      ),
    );
  }

  Widget _botonMenu(IconData icon, String text, Color color, VoidCallback? onTap) {
    return SizedBox(
      width: double.infinity,
      height: 60,
      child: ElevatedButton.icon(
        icon: Icon(icon, color: Colors.white),
        style: ElevatedButton.styleFrom(backgroundColor: color, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15))),
        label: Text(text, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
        onPressed: onTap,
      ),
    );
  }
}

// --- PANTALLA DE FORMULARIO ---
class FormularioVisita extends StatefulWidget {
  const FormularioVisita({super.key});
  @override
  State<FormularioVisita> createState() => _FormularioVisitaState();
}

class _FormularioVisitaState extends State<FormularioVisita> {
  final _picker = ImagePicker();
  List<String> _clientes = [];
  List<String> _tecnicos = [];
  
  String? _selectedCliente;
  String? _selectedTecnico;
  final TextEditingController _obsController = TextEditingController();
  List<Map<String, dynamic>> _usuarios = [];

  @override
  void initState() {
    super.initState();
    _cargarDatosLocales();
  }

  void _cargarDatosLocales() async {
    var c = await DBHelper().getClientes();
    var t = await DBHelper().getTecnicos();
    setState(() { _clientes = c; _tecnicos = t; });
  }

  Future<void> _tomarFoto(int indexUsuario) async {
    // AQUÍ ESTÁ LA MAGIA: Llamada nativa a la cámara
    final XFile? photo = await _picker.pickImage(source: ImageSource.camera, imageQuality: 50);
    if (photo != null) {
      final directory = await getApplicationDocumentsDirectory();
      final String path = '${directory.path}/${DateTime.now().millisecondsSinceEpoch}.jpg';
      await File(photo.path).copy(path);

      setState(() {
        if (_usuarios[indexUsuario]['fotos'] == null) _usuarios[indexUsuario]['fotos'] = [];
        _usuarios[indexUsuario]['fotos'].add(path);
      });
    }
  }

  void _agregarUsuario() {
    setState(() {
      _usuarios.add({'nombre': '', 'atendido': true, 'trabajo': '', 'motivo': '', 'fotos': []});
    });
  }

  void _guardarLocalmente() async {
    if (_selectedCliente == null || _selectedTecnico == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Falta Cliente o Técnico")));
      return;
    }

    Map<String, dynamic> reporte = {
      'cliente': _selectedCliente,
      'tecnico': _selectedTecnico,
      'obs': _obsController.text,
      'datos_usuarios': json.encode(_usuarios),
      'fecha_creacion': DateTime.now().toString(),
      'firma_path': null 
    };

    await DBHelper().insertarReporte(reporte);
    if(!mounted) return;
    Navigator.pop(context);
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(backgroundColor: Colors.green, content: Text("Visita guardada en el celular")));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Nueva Visita"), backgroundColor: const Color(0xFF0583F2), foregroundColor: Colors.white),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            DropdownButtonFormField(
              decoration: const InputDecoration(labelText: "Cliente", border: OutlineInputBorder()),
              items: _clientes.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
              onChanged: (v) => setState(() => _selectedCliente = v as String?),
            ),
            const SizedBox(height: 15),
            DropdownButtonFormField(
              decoration: const InputDecoration(labelText: "Técnico", border: OutlineInputBorder()),
              items: _tecnicos.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
              onChanged: (v) => setState(() => _selectedTecnico = v as String?),
            ),
            const SizedBox(height: 25),
            
            // LISTA DE USUARIOS
            const Align(alignment: Alignment.centerLeft, child: Text("Usuarios Atendidos", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.grey))),
            ..._usuarios.asMap().entries.map((entry) {
              int idx = entry.key;
              Map usr = entry.value;
              return Card(
                margin: const EdgeInsets.symmetric(vertical: 8),
                elevation: 3,
                child: Padding(
                  padding: const EdgeInsets.all(10.0),
                  child: Column(
                    children: [
                      TextFormField(
                        decoration: const InputDecoration(labelText: "Nombre Usuario", icon: Icon(Icons.person)),
                        onChanged: (v) => usr['nombre'] = v,
                      ),
                      SwitchListTile(
                        title: Text(usr['atendido'] ? "Atendido" : "No Atendido", style: TextStyle(color: usr['atendido'] ? Colors.green : Colors.red, fontWeight: FontWeight.bold)),
                        value: usr['atendido'], 
                        onChanged: (v) => setState(() => usr['atendido'] = v)
                      ),
                      if (usr['atendido']) 
                         TextFormField(
                           decoration: const InputDecoration(labelText: "Trabajo realizado"),
                           maxLines: 2,
                           onChanged: (v) => usr['trabajo'] = v,
                         )
                      else
                         TextFormField(
                           decoration: const InputDecoration(labelText: "Motivo no atención"),
                           onChanged: (v) => usr['motivo'] = v,
                         ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          ElevatedButton.icon(
                            icon: const Icon(Icons.camera_alt),
                            label: const Text("FOTO"),
                            onPressed: () => _tomarFoto(idx),
                          ),
                          const SizedBox(width: 10),
                          Text("${(usr['fotos'] ?? []).length} Fotos tomadas", style: const TextStyle(color: Colors.grey)),
                        ],
                      )
                    ],
                  ),
                ),
              );
            }),
            const SizedBox(height: 10),
            OutlinedButton.icon(onPressed: _agregarUsuario, icon: const Icon(Icons.add), label: const Text("Agregar Usuario")),
            const SizedBox(height: 20),
            TextField(controller: _obsController, decoration: const InputDecoration(labelText: "Observaciones Generales", border: OutlineInputBorder()), maxLines: 3),
            const SizedBox(height: 30),
            
            SizedBox(
              width: double.infinity,
              height: 55,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0583F2), foregroundColor: Colors.white),
                onPressed: _guardarLocalmente,
                child: const Text("GUARDAR VISITA", style: TextStyle(fontSize: 18)),
              ),
            )
          ],
        ),
      ),
    );
  }
}