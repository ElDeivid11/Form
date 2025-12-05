import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:signature/signature.dart';
import 'package:shared_preferences/shared_preferences.dart'; // IMPORTANTE
import 'db_helper.dart';
import 'api_service.dart';

// --- CONTROLADOR DE TEMA GLOBAL ---
final ValueNotifier<ThemeMode> themeNotifier = ValueNotifier(ThemeMode.system);

// --- PALETA DE COLORES ---
const Color kPrimaryColor = Color(0xFF0583F2);
const Color kSecondaryColor = Color(0xFF0056A3);
const Color kBackgroundColor = Color(0xFFF5F7FA);
const Color kCardColor = Colors.white;

const Color kPrimaryColorDark = Color(0xFFFF9800); 
const Color kSecondaryColorDark = Color(0xFFF57C00); 
const Color kBackgroundColorDark = Color(0xFF121212); 
const Color kCardColorDark = Color(0xFF1E1E1E); 
const double kRadius = 16.0;

void main() {
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(statusBarColor: Colors.transparent));
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: themeNotifier,
      builder: (context, currentMode, child) {
        return MaterialApp(
          title: 'Tecnocomp',
          debugShowCheckedModeBanner: false,
          themeMode: currentMode,
          theme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.light,
            scaffoldBackgroundColor: kBackgroundColor,
            colorScheme: ColorScheme.fromSeed(seedColor: kPrimaryColor, primary: kPrimaryColor, brightness: Brightness.light),
            appBarTheme: const AppBarTheme(
              backgroundColor: kPrimaryColor,
              foregroundColor: Colors.white,
              elevation: 0,
              centerTitle: true,
              titleTextStyle: TextStyle(fontWeight: FontWeight.bold, fontSize: 20),
            ),
            cardTheme: CardTheme(
              color: kCardColor,
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(kRadius)),
              margin: EdgeInsets.zero,
            ).data, 
            inputDecorationTheme: InputDecorationTheme(
              filled: true,
              fillColor: Colors.grey[50],
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Colors.grey, width: 0.5)),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: kPrimaryColor, width: 1.5)),
              labelStyle: TextStyle(color: Colors.grey[600]),
            ),
            elevatedButtonTheme: ElevatedButtonThemeData(
              style: ElevatedButton.styleFrom(
                backgroundColor: kPrimaryColor,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
                elevation: 3,
              ),
            ),
          ),
          darkTheme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.dark,
            scaffoldBackgroundColor: kBackgroundColorDark,
            colorScheme: ColorScheme.fromSeed(seedColor: kPrimaryColorDark, primary: kPrimaryColorDark, brightness: Brightness.dark),
            appBarTheme: const AppBarTheme(
              backgroundColor: kCardColorDark,
              foregroundColor: kPrimaryColorDark,
              elevation: 0,
              centerTitle: true,
              titleTextStyle: TextStyle(fontWeight: FontWeight.bold, fontSize: 20),
            ),
            cardTheme: CardTheme(
              color: kCardColorDark,
              elevation: 4,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(kRadius)),
              margin: EdgeInsets.zero,
            ).data,
            inputDecorationTheme: InputDecorationTheme(
              filled: true,
              fillColor: const Color(0xFF2C2C2C),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Colors.grey, width: 0.2)),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: kPrimaryColorDark, width: 1.5)),
              labelStyle: const TextStyle(color: Colors.white70),
            ),
            elevatedButtonTheme: ElevatedButtonThemeData(
              style: ElevatedButton.styleFrom(
                backgroundColor: kPrimaryColorDark,
                foregroundColor: Colors.black,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
                elevation: 3,
              ),
            ),
            iconTheme: const IconThemeData(color: kPrimaryColorDark),
            textSelectionTheme: const TextSelectionThemeData(cursorColor: kPrimaryColorDark, selectionHandleColor: kPrimaryColorDark),
          ),
          home: const HomeScreen(),
        );
      },
    );
  }
}

// --- PANTALLA DASHBOARD ---
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
    _mostrarLoading("Sincronizando...");
    bool ok = await ApiService.sincronizarDatos();
    if (!mounted) return;
    Navigator.pop(context);
    if (ok) {
      _mostrarSnack("Datos actualizados correctamente", Colors.green);
    } else {
      _mostrarConfigurarIP(); // Si falla, sugerimos configurar IP
    }
  }

  void _mostrarConfigurarIP() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text("Error de conexión. Verifica la IP."),
        backgroundColor: Colors.red,
        action: SnackBarAction(
          label: "CONFIGURAR",
          textColor: Colors.white,
          onPressed: _abrirConfiguracion,
        ),
      ),
    );
  }

  void _subirPendientes() async {
    final list = await DBHelper().getReportesPendientes();
    if (list.isEmpty) return;
    
    _mostrarLoading("Subiendo ${list.length} reportes...");
    int subidos = 0;
    for (var rep in list) {
      bool ok = await ApiService.subirReporte(rep);
      if (ok) {
        await DBHelper().marcarComoEnviado(rep['id']);
        subidos++;
      }
    }
    Navigator.pop(context);
    _cargarPendientes();
    _mostrarSnack("Proceso finalizado. Subidos: $subidos", Colors.blue);
  }

  void _mostrarLoading(String texto) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(kRadius)),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [const CircularProgressIndicator(), const SizedBox(width: 20), Text(texto)],
          ),
        ),
      ),
    );
  }

  void _mostrarSnack(String texto, Color color) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: color, content: Text(texto), behavior: SnackBarBehavior.floating));
  }

  // --- NUEVO: DIÁLOGO DE CONFIGURACIÓN ---
  void _abrirConfiguracion() async {
    final prefs = await SharedPreferences.getInstance();
    final controller = TextEditingController(text: prefs.getString('api_url') ?? "http://192.168.1.X:8000");

    if (!mounted) return;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Configuración de Red"),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text("Ingresa la IP del servidor Python (Back-office):"),
            const SizedBox(height: 10),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: "URL del Servidor",
                hintText: "Ej: http://192.168.1.50:8000",
                prefixIcon: Icon(Icons.wifi)
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
          ElevatedButton(
            onPressed: () async {
              await prefs.setString('api_url', controller.text.trim());
              if (!mounted) return;
              Navigator.pop(ctx);
              _mostrarSnack("Configuración guardada", Colors.green);
            },
            child: const Text("Guardar"),
          )
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primaryColor = isDark ? kPrimaryColorDark : kPrimaryColor;
    
    return Scaffold(
      body: Stack(
        children: [
          // Fondo
          Container(
            height: 250,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft, 
                end: Alignment.bottomRight, 
                colors: isDark 
                  ? [const Color(0xFF2C2C2C), Colors.black] 
                  : [kPrimaryColor, kSecondaryColor], 
              ),
              borderRadius: const BorderRadius.only(bottomLeft: Radius.circular(40), bottomRight: Radius.circular(40)),
            ),
          ),
          SafeArea(
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Bienvenido,", style: TextStyle(color: Colors.white70, fontSize: 14)),
                          Text("Panel Técnico", style: TextStyle(color: isDark ? kPrimaryColorDark : Colors.white, fontSize: 24, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      Row(
                        children: [
                          // BOTÓN TEMA
                          IconButton(
                            icon: Icon(isDark ? Icons.light_mode : Icons.dark_mode, color: Colors.white),
                            onPressed: () => themeNotifier.value = isDark ? ThemeMode.light : ThemeMode.dark,
                          ),
                          // NUEVO: BOTÓN CONFIGURACIÓN
                          IconButton(
                            icon: const Icon(Icons.settings, color: Colors.white),
                            onPressed: _abrirConfiguracion,
                            tooltip: "Configurar IP",
                          ),
                        ],
                      )
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    children: [
                      _DashboardCard(
                        icon: Icons.add_location_alt_rounded, 
                        title: "Nueva Visita", 
                        subtitle: "Crear reporte offline", 
                        color: isDark ? kCardColorDark : Colors.white,
                        textColor: isDark ? Colors.white : Colors.black87,
                        iconColor: primaryColor,
                        onTap: () async {
                          await Navigator.push(context, MaterialPageRoute(builder: (_) => const FormularioVisita()));
                          _cargarPendientes();
                        }
                      ),
                      const SizedBox(height: 15),
                      _DashboardCard(
                        icon: Icons.history_edu_rounded, 
                        title: "Historial", 
                        subtitle: "$pendientes pendientes de envío", 
                        color: pendientes > 0 
                            ? (isDark ? const Color(0xFFEF6C00) : const Color(0xFFFF9800)) 
                            : (isDark ? kCardColorDark : Colors.white),
                        textColor: pendientes > 0 ? Colors.white : (isDark ? Colors.white : Colors.black87),
                        iconColor: pendientes > 0 ? Colors.white : primaryColor,
                        isPrimary: pendientes > 0,
                        onTap: () async {
                          await Navigator.push(context, MaterialPageRoute(builder: (_) => const PantallaHistorial()));
                          _cargarPendientes();
                        }
                      ),
                      const SizedBox(height: 15),
                      Row(
                        children: [
                          Expanded(
                            child: _DashboardSmallCard(
                              icon: Icons.sync, 
                              title: "Sincronizar", 
                              color: isDark ? kCardColorDark : Colors.blueGrey.shade50,
                              iconColor: isDark ? Colors.grey : Colors.blueGrey,
                              onTap: _sincronizar
                            ),
                          ),
                          const SizedBox(width: 15),
                          Expanded(
                            child: _DashboardSmallCard(
                              icon: Icons.storage, // Icono cambiado para reflejar gestión de datos
                              title: "Gestión Datos", 
                              color: isDark ? kCardColorDark : Colors.blueGrey.shade50,
                              iconColor: isDark ? Colors.grey : Colors.blueGrey,
                              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PantallaGestionDatos())),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DashboardCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final Color textColor;
  final Color iconColor;
  final bool isPrimary;
  final VoidCallback? onTap;

  const _DashboardCard({
    required this.icon, required this.title, required this.subtitle, 
    required this.color, required this.textColor, required this.iconColor, 
    this.isPrimary = false, this.onTap
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(kRadius),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(kRadius),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, 4))],
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isPrimary ? Colors.white24 : iconColor.withOpacity(0.1), 
                borderRadius: BorderRadius.circular(12)
              ),
              child: Icon(icon, color: iconColor, size: 30),
            ),
            const SizedBox(width: 20),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: textColor)),
                Text(subtitle, style: TextStyle(fontSize: 12, color: textColor.withOpacity(0.7))),
              ],
            ),
            const Spacer(),
            Icon(Icons.arrow_forward_ios_rounded, size: 16, color: textColor.withOpacity(0.3))
          ],
        ),
      ),
    );
  }
}

class _DashboardSmallCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final Color color;
  final Color iconColor;
  final VoidCallback onTap;

  const _DashboardSmallCard({required this.icon, required this.title, required this.color, required this.iconColor, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(kRadius),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(kRadius),
          border: isDark ? null : Border.all(color: Colors.black.withOpacity(0.05)),
        ),
        child: Column(
          children: [
            Icon(icon, color: iconColor, size: 28),
            const SizedBox(height: 8),
            Text(title, style: TextStyle(fontWeight: FontWeight.bold, color: iconColor)),
          ],
        ),
      ),
    );
  }
}

// --- PANTALLA HISTORIAL ---
class PantallaHistorial extends StatefulWidget {
  const PantallaHistorial({super.key});
  @override
  State<PantallaHistorial> createState() => _PantallaHistorialState();
}

class _PantallaHistorialState extends State<PantallaHistorial> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<Map<String, dynamic>> _pendientes = [];
  List<Map<String, dynamic>> _enviados = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _cargar();
  }

  void _cargar() async {
    final p = await DBHelper().getReportesPendientes();
    final e = await DBHelper().getReportesEnviados();
    setState(() {
      _pendientes = p;
      _enviados = e;
    });
  }

  void _enviarReporte(Map<String, dynamic> reporte) async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );

    bool ok = await ApiService.subirReporte(reporte);
    
    if(!mounted) return;
    Navigator.pop(context);

    if (ok) {
      await DBHelper().marcarComoEnviado(reporte['id']);
      _cargar();
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Enviado correctamente"), backgroundColor: Colors.green));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al enviar. Revisa la IP en Configuración."), backgroundColor: Colors.red));
    }
  }

  void _editarReporte(Map<String, dynamic> reporte) async {
    await Navigator.push(
      context, 
      MaterialPageRoute(builder: (_) => FormularioVisita(reporteEditar: reporte, soloLectura: false))
    );
    _cargar();
  }

  void _verReporte(Map<String, dynamic> reporte) async {
    await Navigator.push(
      context, 
      MaterialPageRoute(builder: (_) => FormularioVisita(reporteEditar: reporte, soloLectura: true))
    );
  }

  void _borrarReporte(int id) async {
    await DBHelper().borrarReporteFisico(id);
    _cargar();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    return Scaffold(
      appBar: AppBar(
        title: const Text("Historial"),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: isDark ? kPrimaryColorDark : Colors.white,
          labelColor: isDark ? kPrimaryColorDark : Colors.white,
          unselectedLabelColor: isDark ? Colors.grey : Colors.white60,
          tabs: const [Tab(text: "Pendientes"), Tab(text: "Enviados")],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _listaReportes(_pendientes, true),
          _listaReportes(_enviados, false),
        ],
      ),
    );
  }

  Widget _listaReportes(List<Map<String, dynamic>> lista, bool esPendiente) {
    if (lista.isEmpty) return const Center(child: Text("No hay reportes", style: TextStyle(color: Colors.grey)));
    
    return ListView.separated(
      padding: const EdgeInsets.all(15),
      itemCount: lista.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (ctx, i) {
        final rep = lista[i];
        return Card(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8.0),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: esPendiente ? Colors.orange.withOpacity(0.2) : Colors.green.withOpacity(0.2),
                child: Icon(esPendiente ? Icons.upload_file : Icons.check_circle, color: esPendiente ? Colors.orange : Colors.green),
              ),
              title: Text(rep['cliente'] ?? "Sin Cliente", style: const TextStyle(fontWeight: FontWeight.bold)),
              subtitle: Text("Téc: ${rep['tecnico']}\n${rep['fecha_creacion'].toString().split('.')[0]}"),
              isThreeLine: true,
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (esPendiente) ...[
                    IconButton(icon: const Icon(Icons.edit, color: Colors.blue), onPressed: () => _editarReporte(rep)),
                    IconButton(icon: const Icon(Icons.send, color: Colors.green), onPressed: () => _enviarReporte(rep)),
                  ] else ...[
                    IconButton(icon: const Icon(Icons.visibility, color: Colors.grey), onPressed: () => _verReporte(rep)),
                  ],
                  IconButton(
                    icon: const Icon(Icons.delete, color: Colors.grey),
                    onPressed: () => showDialog(
                      context: context,
                      builder: (c) => AlertDialog(
                        title: const Text("¿Borrar?"),
                        content: const Text("Se eliminará este reporte del dispositivo."),
                        actions: [
                          TextButton(onPressed: ()=>Navigator.pop(c), child: const Text("Cancelar")),
                          TextButton(onPressed: (){ _borrarReporte(rep['id']); Navigator.pop(c); }, child: const Text("Borrar", style: TextStyle(color: Colors.red))),
                        ],
                      )
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

// --- PANTALLA GESTIÓN DE DATOS ---
class PantallaGestionDatos extends StatefulWidget {
  const PantallaGestionDatos({super.key});
  @override
  State<PantallaGestionDatos> createState() => _PantallaGestionDatosState();
}

class _PantallaGestionDatosState extends State<PantallaGestionDatos> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<Map<String, dynamic>> _clientes = [];
  List<String> _tecnicos = [];
  Map<String, List<String>> _usuariosPorCliente = {};

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _cargarDatos();
  }

  Future<void> _cargarDatos() async {
    final cls = await DBHelper().getClientesMap();
    final tcs = await DBHelper().getTecnicos();
    Map<String, List<String>> usuariosMap = {};
    for (var c in cls) {
      String nombreCli = c['nombre'];
      usuariosMap[nombreCli] = await DBHelper().getUsuariosPorCliente(nombreCli);
    }
    setState(() {
      _clientes = cls;
      _tecnicos = tcs;
      _usuariosPorCliente = usuariosMap;
    });
  }

  void _borrarCliente(String nombre) async {
    await DBHelper().eliminarCliente(nombre);
    _cargarDatos();
  }

  void _borrarTecnico(String nombre) async {
    await DBHelper().eliminarTecnico(nombre);
    _cargarDatos();
  }

  void _borrarUsuario(String nombreUsuario, String cliente) async {
    await DBHelper().eliminarUsuarioFrecuente(nombreUsuario, cliente);
    _cargarDatos();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primary = isDark ? kPrimaryColorDark : kPrimaryColor;

    return Scaffold(
      appBar: AppBar(
        title: const Text("Gestión de Datos"),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: isDark ? primary : Colors.white,
          labelColor: isDark ? primary : Colors.white,
          unselectedLabelColor: isDark ? Colors.grey : Colors.white60,
          tabs: const [Tab(text: "Clientes"), Tab(text: "Técnicos"), Tab(text: "Usuarios")],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _listaSimple(_clientes.map((c) => c['nombre'] as String).toList(), (item) => _borrarCliente(item), icono: Icons.business, color: primary),
          _listaSimple(_tecnicos, (item) => _borrarTecnico(item), icono: Icons.person_outline, color: primary),
          ListView.builder(
            padding: const EdgeInsets.all(10),
            itemCount: _clientes.length,
            itemBuilder: (ctx, i) {
              String cli = _clientes[i]['nombre'];
              List<String> users = _usuariosPorCliente[cli] ?? [];
              if (users.isEmpty) return const SizedBox();
              return Card(
                margin: const EdgeInsets.only(bottom: 15),
                child: ExpansionTile(
                  title: Text(cli, style: TextStyle(fontWeight: FontWeight.bold, color: primary)),
                  leading: Icon(Icons.group, color: primary),
                  children: users.map((u) => ListTile(
                    title: Text(u),
                    trailing: IconButton(icon: const Icon(Icons.delete, color: Colors.redAccent, size: 20), onPressed: () => _borrarUsuario(u, cli)),
                  )).toList(),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _listaSimple(List<String> items, Function(String) onBorrar, {required IconData icono, required Color color}) {
    if (items.isEmpty) return const Center(child: Text("No hay datos", style: TextStyle(color: Colors.grey)));
    return ListView.separated(
      padding: const EdgeInsets.all(15),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (ctx, i) => Card(
        child: ListTile(
          leading: CircleAvatar(backgroundColor: color.withOpacity(0.1), child: Icon(icono, color: color, size: 20)),
          title: Text(items[i], style: const TextStyle(fontWeight: FontWeight.w500)),
          trailing: IconButton(
            icon: const Icon(Icons.delete, color: Colors.grey),
            onPressed: () => showDialog(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Text("¿Eliminar?"),
                content: Text("Se borrará ${items[i]} de la base de datos local."),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
                  TextButton(onPressed: () { onBorrar(items[i]); Navigator.pop(ctx); }, child: const Text("Eliminar", style: TextStyle(color: Colors.red))),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// --- FORMULARIO DE VISITA ---
class FormularioVisita extends StatefulWidget {
  final Map<String, dynamic>? reporteEditar;
  final bool soloLectura; 

  const FormularioVisita({super.key, this.reporteEditar, this.soloLectura = false});
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

  Future<void> _cargarDatosLocales() async {
    var c = await DBHelper().getClientes();
    var t = await DBHelper().getTecnicos();
    setState(() { _clientes = c; _tecnicos = t; });

    if (widget.reporteEditar != null) {
      final rep = widget.reporteEditar!;
      setState(() {
        _selectedCliente = rep['cliente'];
        _selectedTecnico = rep['tecnico'];
        _obsController.text = rep['obs'];
        List<dynamic> usersRaw = json.decode(rep['datos_usuarios']);
        _usuarios = List<Map<String, dynamic>>.from(usersRaw);
      });
    }
  }

  void _agregarItemRapido(bool esCliente) {
    if (widget.soloLectura) return;
    final controller = TextEditingController();
    final emailController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(esCliente ? "Nuevo Cliente" : "Nuevo Técnico"),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: controller, decoration: const InputDecoration(labelText: "Nombre"), textCapitalization: TextCapitalization.words),
            if (esCliente) ...[const SizedBox(height: 10), TextField(controller: emailController, decoration: const InputDecoration(labelText: "Email Reportes"), keyboardType: TextInputType.emailAddress)],
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
          ElevatedButton(
            onPressed: () async {
              if (controller.text.isNotEmpty) {
                if (esCliente) await DBHelper().agregarClienteLocal(controller.text, emailController.text);
                else await DBHelper().agregarTecnicoLocal(controller.text);
                Navigator.pop(ctx);
                await _cargarDatosLocales();
                setState(() {
                  if (esCliente) _alSeleccionarCliente(controller.text);
                  else _selectedTecnico = controller.text;
                });
              }
            },
            child: const Text("Guardar"),
          )
        ],
      ),
    );
  }

  void _agregarUsuarioRapido() {
    if (widget.soloLectura) return;
    if (_selectedCliente == null) return;
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Nuevo Usuario"),
        content: TextField(controller: controller, decoration: const InputDecoration(labelText: "Nombre")),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
          ElevatedButton(
            onPressed: () async {
              if (controller.text.isNotEmpty) {
                await DBHelper().guardarUsuarioFrecuente(controller.text, _selectedCliente!);
                setState(() {
                  _usuarios.add({'nombre': controller.text, 'atendido': true, 'trabajo': '', 'motivo': '', 'fotos': [], 'firma': null});
                });
                Navigator.pop(ctx);
              }
            },
            child: const Text("Guardar"),
          )
        ],
      ),
    );
  }

  void _borrarUsuarioConConfirmacion(int index) {
    if (widget.soloLectura) return;
    final nombreUsuario = _usuarios[index]['nombre'];
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("¿Eliminar?"),
        content: Text("¿Borrar a '$nombreUsuario' de la lista de frecuentes?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
          TextButton(onPressed: () async {
              if (_selectedCliente != null) await DBHelper().eliminarUsuarioFrecuente(nombreUsuario, _selectedCliente!);
              setState(() => _usuarios.removeAt(index));
              Navigator.pop(ctx);
            },
            child: const Text("Eliminar", style: TextStyle(color: Colors.red)),
          )
        ],
      ),
    );
  }

  void _alSeleccionarCliente(String? cliente) async {
    if (widget.soloLectura) return;
    if (widget.reporteEditar != null && cliente == widget.reporteEditar!['cliente'] && _usuarios.isNotEmpty) {
       setState(() => _selectedCliente = cliente);
       return;
    }
    setState(() { _selectedCliente = cliente; _usuarios = []; });
    if (cliente != null) {
      var usersGuardados = await DBHelper().getUsuariosPorCliente(cliente);
      if (usersGuardados.isNotEmpty) {
        setState(() {
          _usuarios = usersGuardados.map((nombre) => {
            'nombre': nombre, 'atendido': true, 'trabajo': '', 'motivo': '', 'fotos': [], 'firma': null
          }).toList();
        });
      }
    }
  }

  Future<void> _tomarFoto(int indexUsuario) async {
    if (widget.soloLectura) return;
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

  void _abrirFirma(int index) {
    if (widget.soloLectura) return;
    final SignatureController _controller = SignatureController(penStrokeWidth: 3, penColor: Colors.black, exportBackgroundColor: Colors.white);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Firma del Usuario"),
        content: Container(
          decoration: BoxDecoration(border: Border.all(color: Colors.grey.shade300)),
          child: Signature(controller: _controller, height: 200, width: 300, backgroundColor: Colors.white),
        ),
        actions: [
          TextButton(onPressed: () => _controller.clear(), child: const Text("Borrar")),
          ElevatedButton(onPressed: () async {
            if (_controller.isNotEmpty) {
              final Uint8List? data = await _controller.toPngBytes();
              if (data != null) {
                final directory = await getApplicationDocumentsDirectory();
                final String path = '${directory.path}/firma_${DateTime.now().millisecondsSinceEpoch}.png';
                await File(path).writeAsBytes(data);
                setState(() => _usuarios[index]['firma'] = path);
                Navigator.pop(context);
              }
            }
          }, child: const Text("Guardar")),
        ],
      ),
    );
  }

  void _agregarUsuarioManual() {
    if (widget.soloLectura) return;
    setState(() {
      _usuarios.add({'nombre': '', 'atendido': true, 'trabajo': '', 'motivo': '', 'fotos': [], 'firma': null});
    });
  }

  void _guardarLocalmente() async {
    if (widget.soloLectura) return;
    if (_selectedCliente == null || _selectedTecnico == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Falta seleccionar Cliente o Técnico"), backgroundColor: Colors.orange));
      return;
    }

    for (var u in _usuarios) {
      if (u['nombre'] != null && u['nombre'].toString().trim().isNotEmpty) {
        await DBHelper().guardarUsuarioFrecuente(u['nombre'].toString().trim(), _selectedCliente!);
      }
    }

    Map<String, dynamic> reporte = {
      'cliente': _selectedCliente,
      'tecnico': _selectedTecnico,
      'obs': _obsController.text,
      'datos_usuarios': json.encode(_usuarios),
      'fecha_creacion': DateTime.now().toString(),
      'firma_path': null 
    };

    if (widget.reporteEditar != null) {
      await DBHelper().updateReporte(widget.reporteEditar!['id'], reporte);
      if(!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(backgroundColor: Colors.blue, content: Text("Cambios guardados")));
    } else {
      await DBHelper().insertarReporte(reporte);
      if(!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(backgroundColor: Colors.green, content: Text("Visita creada correctamente")));
    }
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final bool readOnly = widget.soloLectura;
    final String titulo = readOnly ? "Detalle Reporte" : (widget.reporteEditar != null ? "Editar Visita" : "Nueva Visita");
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primary = isDark ? kPrimaryColorDark : kPrimaryColor;

    return Scaffold(
      appBar: AppBar(title: Text(titulo)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("INFORMACIÓN GENERAL", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: primary)),
                    const SizedBox(height: 15),
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            isExpanded: true,
                            decoration: const InputDecoration(labelText: "Cliente", prefixIcon: Icon(Icons.business_outlined)),
                            value: _selectedCliente,
                            items: _clientes.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                            onChanged: readOnly ? null : _alSeleccionarCliente,
                          ),
                        ),
                        if (!readOnly) ...[
                          const SizedBox(width: 8),
                          _botonAddMini(() => _agregarItemRapido(true), Colors.green),
                        ]
                      ],
                    ),
                    const SizedBox(height: 15),
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            isExpanded: true,
                            decoration: const InputDecoration(labelText: "Técnico", prefixIcon: Icon(Icons.person_outline)),
                            value: _selectedTecnico,
                            items: _tecnicos.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                            onChanged: readOnly ? null : (v) => setState(() => _selectedTecnico = v),
                          ),
                        ),
                        if (!readOnly) ...[
                          const SizedBox(width: 8),
                          _botonAddMini(() => _agregarItemRapido(false), Colors.orange),
                        ]
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text("REGISTRO DE USUARIOS", style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.grey)),
                if (!readOnly) TextButton.icon(onPressed: _agregarUsuarioRapido, icon: const Icon(Icons.add_circle), label: const Text("Agregar"))
              ],
            ),
            
            ..._usuarios.asMap().entries.map((entry) {
              int idx = entry.key;
              Map usr = entry.value;
              return Container(
                margin: const EdgeInsets.only(bottom: 15),
                decoration: BoxDecoration(
                  color: isDark ? kCardColorDark : Colors.white, 
                  borderRadius: BorderRadius.circular(kRadius), 
                  boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 5, offset: const Offset(0, 2))]
                ),
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(color: primary.withOpacity(0.1), borderRadius: const BorderRadius.vertical(top: Radius.circular(kRadius))),
                      child: Row(
                        children: [
                          Icon(Icons.person, size: 18, color: primary),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              usr['nombre'] ?? "",
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                            ),
                          ),
                          if (!readOnly) IconButton(
                            icon: const Icon(Icons.close, color: Colors.red, size: 18), 
                            onPressed: () => _borrarUsuarioConConfirmacion(idx)
                          )
                        ],
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        children: [
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(usr['atendido'] ? "✅ Atendido" : "❌ No Atendido", style: TextStyle(color: usr['atendido'] ? Colors.green : Colors.red, fontWeight: FontWeight.bold)),
                            value: usr['atendido'], 
                            activeColor: Colors.green,
                            onChanged: readOnly ? null : (v) => setState(() => usr['atendido'] = v)
                          ),
                          
                          if (usr['atendido']) ...[
                             TextFormField(
                               initialValue: usr['trabajo'],
                               decoration: const InputDecoration(labelText: "Trabajo realizado", alignLabelWithHint: true),
                               maxLines: 2,
                               readOnly: readOnly,
                               onChanged: (v) => usr['trabajo'] = v,
                             ),
                             const SizedBox(height: 15),
                             Row(
                               children: [
                                 Expanded(
                                   child: _ActionButton(
                                     icon: Icons.camera_alt,
                                     text: "${(usr['fotos']??[]).length} Fotos",
                                     color: isDark ? Colors.blueGrey.shade900 : Colors.blue.shade50,
                                     textColor: Colors.blue,
                                     onTap: () => _tomarFoto(idx),
                                   ),
                                 ),
                                 const SizedBox(width: 10),
                                 Expanded(
                                   child: _ActionButton(
                                     icon: Icons.draw,
                                     text: usr['firma'] != null ? "Firmado" : "Firmar",
                                     color: usr['firma'] != null 
                                        ? (isDark ? Colors.green.shade900 : Colors.green.shade50) 
                                        : (isDark ? Colors.orange.shade900 : Colors.orange.shade50),
                                     textColor: usr['firma'] != null ? Colors.green : Colors.orange,
                                     onTap: () => _abrirFirma(idx),
                                   ),
                                 ),
                               ],
                             )
                          ] else
                             TextFormField(
                               initialValue: usr['motivo'],
                               decoration: const InputDecoration(labelText: "Motivo no atención"),
                               readOnly: readOnly,
                               onChanged: (v) => usr['motivo'] = v,
                             ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }),
            
            const SizedBox(height: 20),
            
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("CIERRE DE VISITA", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: primary)),
                    const SizedBox(height: 15),
                    TextField(controller: _obsController, decoration: const InputDecoration(labelText: "Observaciones Generales", prefixIcon: Icon(Icons.comment_outlined)), maxLines: 3, readOnly: readOnly),
                    if (!readOnly) ...[
                      const SizedBox(height: 20),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _guardarLocalmente,
                          child: Text(widget.reporteEditar != null ? "GUARDAR CAMBIOS" : "GUARDAR VISITA", style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ]
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _botonAddMini(VoidCallback onTap, Color color) {
    return InkWell(
      onTap: onTap,
      child: Container(
        width: 50, height: 50,
        decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(12), border: Border.all(color: color.withOpacity(0.3))),
        child: Icon(Icons.add, color: color),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color color;
  final Color textColor;
  final VoidCallback onTap;

  const _ActionButton({required this.icon, required this.text, required this.color, required this.textColor, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(10)),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 18, color: textColor),
            const SizedBox(width: 8),
            Text(text, style: TextStyle(color: textColor, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}