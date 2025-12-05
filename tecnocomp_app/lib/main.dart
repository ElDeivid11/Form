import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:signature/signature.dart';
import 'package:shared_preferences/shared_preferences.dart';
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

// --- EXPRESIÓN REGULAR PARA NOMBRES (Solo letras y espacios) ---
bool _validarTextoSinNumeros(String texto) {
  final regex = RegExp(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$');
  return regex.hasMatch(texto);
}

// --- LISTA DE TAREAS PREDEFINIDAS ---
const List<String> kTareasPredefinidas = [
  "Limpieza Física",
  "Optimización SW",
  "Instalación Office",
  "Respaldo Datos",
  "Configuración Correo",
  "Cambio Pasta Térmica",
  "Diagnóstico HW",
  "Formateo Completo"
];

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
      _mostrarConfigurarIP();
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
                          IconButton(
                            icon: Icon(isDark ? Icons.light_mode : Icons.dark_mode, color: Colors.white),
                            onPressed: () => themeNotifier.value = isDark ? ThemeMode.light : ThemeMode.dark,
                          ),
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
                              icon: Icons.storage, 
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

// --- PANTALLA HISTORIAL (Sin cambios mayores, solo referencias) ---
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
    showDialog(context: context, barrierDismissible: false, builder: (_) => const Center(child: CircularProgressIndicator()));
    bool ok = await ApiService.subirReporte(reporte);
    if(!mounted) return;
    Navigator.pop(context);

    if (ok) {
      await DBHelper().marcarComoEnviado(reporte['id']);
      _cargar();
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Enviado correctamente"), backgroundColor: Colors.green));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al enviar."), backgroundColor: Colors.red));
    }
  }

  void _editarReporte(Map<String, dynamic> reporte) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => FormularioVisita(reporteEditar: reporte, soloLectura: false)));
    _cargar();
  }

  void _verReporte(Map<String, dynamic> reporte) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => FormularioVisita(reporteEditar: reporte, soloLectura: true)));
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
          tabs: const [Tab(text: "Pendientes"), Tab(text: "Enviados")],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [_listaReportes(_pendientes, true), _listaReportes(_enviados, false)],
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
          child: ListTile(
            leading: Icon(esPendiente ? Icons.upload_file : Icons.check_circle, color: esPendiente ? Colors.orange : Colors.green),
            title: Text(rep['cliente'] ?? "Sin Cliente"),
            subtitle: Text("Téc: ${rep['tecnico']}\n${rep['fecha_creacion'].toString().split('.')[0]}"),
            isThreeLine: true,
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (esPendiente) ...[
                  IconButton(icon: const Icon(Icons.edit, color: Colors.blue), onPressed: () => _editarReporte(rep)),
                  IconButton(icon: const Icon(Icons.send, color: Colors.green), onPressed: () => _enviarReporte(rep)),
                ] else
                  IconButton(icon: const Icon(Icons.visibility, color: Colors.grey), onPressed: () => _verReporte(rep)),
                IconButton(
                  icon: const Icon(Icons.delete, color: Colors.grey),
                  onPressed: () { _borrarReporte(rep['id']); },
                ),
              ],
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
    setState(() { _clientes = cls; _tecnicos = tcs; _usuariosPorCliente = usuariosMap; });
  }

  void _borrarCliente(String nombre) async { await DBHelper().eliminarCliente(nombre); _cargarDatos(); }
  void _borrarTecnico(String nombre) async { await DBHelper().eliminarTecnico(nombre); _cargarDatos(); }
  void _borrarUsuario(String nombreUsuario, String cliente) async { await DBHelper().eliminarUsuarioFrecuente(nombreUsuario, cliente); _cargarDatos(); }

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
          title: Text(items[i]),
          trailing: IconButton(
            icon: const Icon(Icons.delete, color: Colors.grey),
            onPressed: () => onBorrar(items[i]),
          ),
        ),
      ),
    );
  }
}

// --- FORMULARIO DE VISITA (MODIFICADO PARA TABLET Y CHECKLIST) ---
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
  
  // Para el modo tablet: índice del usuario seleccionado actualmente
  int _usuarioSeleccionadoIndex = -1;

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
        // Restaurar estado
        _usuarios = usersRaw.map((u) {
          // Asegurar que el mapa de tareas exista si viene de una versión vieja
          if (u['tareas_map'] == null) {
             u['tareas_map'] = <String, dynamic>{}; 
          }
          return Map<String, dynamic>.from(u);
        }).toList();
        
        if (_usuarios.isNotEmpty) _usuarioSeleccionadoIndex = 0;
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
            const SizedBox(height: 10),
            // --- AHORA PIDE EMAIL SIEMPRE (CLIENTE O TÉCNICO) ---
            TextField(
              controller: emailController, 
              decoration: const InputDecoration(labelText: "Email para reportes"), 
              keyboardType: TextInputType.emailAddress
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
          ElevatedButton(
            onPressed: () async {
              final nombre = controller.text.trim();
              if (nombre.isNotEmpty) {
                if (!esCliente && !_validarTextoSinNumeros(nombre)) {
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("El nombre solo puede contener letras."), backgroundColor: Colors.red));
                  return;
                }

                if (esCliente) {
                   await DBHelper().agregarClienteLocal(nombre, emailController.text);
                   _alSeleccionarCliente(nombre);
                } else {
                   // Guardamos también el email del técnico
                   await DBHelper().agregarTecnicoLocal(nombre, emailController.text);
                   setState(() => _selectedTecnico = nombre);
                }
                
                Navigator.pop(ctx);
                await _cargarDatosLocales();
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
    if (_selectedCliente == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Selecciona un cliente primero.")));
      return;
    }
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Nuevo Usuario"),
        content: TextField(controller: controller, decoration: const InputDecoration(labelText: "Nombre (Sin números)")),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
          ElevatedButton(
            onPressed: () async {
              final nombre = controller.text.trim();
              if (nombre.isNotEmpty) {
                // VALIDACIÓN: No permitir números en Usuario
                if (!_validarTextoSinNumeros(nombre)) {
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Nombre inválido. Solo letras."), backgroundColor: Colors.red));
                  return;
                }

                await DBHelper().guardarUsuarioFrecuente(nombre, _selectedCliente!);
                setState(() {
                  _usuarios.add({
                    'nombre': nombre, 
                    'atendido': true, 
                    'trabajo': '', 
                    'motivo': '', 
                    'fotos': [], 
                    'firma': null,
                    'tareas_map': {} // Mapa vacio de tareas
                  });
                  _usuarioSeleccionadoIndex = _usuarios.length - 1; // Seleccionar el nuevo
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
        content: Text("¿Borrar a '$nombreUsuario'?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
          TextButton(onPressed: () async {
              // No lo borramos de la DB de frecuentes, solo del reporte actual
              setState(() {
                 _usuarios.removeAt(index);
                 if (_usuarioSeleccionadoIndex >= _usuarios.length) {
                   _usuarioSeleccionadoIndex = _usuarios.length - 1;
                 }
              });
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
    setState(() { _selectedCliente = cliente; _usuarios = []; _usuarioSeleccionadoIndex = -1; });
    if (cliente != null) {
      var usersGuardados = await DBHelper().getUsuariosPorCliente(cliente);
      if (usersGuardados.isNotEmpty) {
        setState(() {
          _usuarios = usersGuardados.map((nombre) => {
            'nombre': nombre, 'atendido': true, 'trabajo': '', 'motivo': '', 'fotos': [], 'firma': null, 'tareas_map': {}
          }).toList();
          _usuarioSeleccionadoIndex = 0; // Seleccionar el primero por defecto
        });
      }
    }
  }

  // --- LOGICA CHECKLIST ---
  void _toggleTarea(int indexUsuario, String tarea, bool valor) {
    if (widget.soloLectura) return;
    setState(() {
      Map tareasMap = _usuarios[indexUsuario]['tareas_map'] ?? {};
      
      if (valor) {
        // Guardamos la hora actual HH:MM
        String hora = DateTime.now().toString().substring(11, 16);
        tareasMap[tarea] = hora;
      } else {
        tareasMap.remove(tarea);
      }
      _usuarios[indexUsuario]['tareas_map'] = tareasMap;

      // ACTUALIZAR EL STRING 'trabajo' PARA COMPATIBILIDAD CON PDF
      // Ejemplo: "Limpieza (10:00), Formateo (10:30)"
      List<String> partes = [];
      tareasMap.forEach((k, v) {
        partes.add("$k ($v)");
      });
      // Si hay texto manual previo que no esté en tareas, podríamos perderlo, 
      // así que asumimos que el checklist manda. O concatenamos un campo 'extra'.
      _usuarios[indexUsuario]['trabajo'] = partes.join(", ");
    });
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
    
    // DETECCIÓN DE TABLET para ajustar tamaño de firma
    final isTablet = MediaQuery.of(context).size.width > 600;
    final double signatureWidth = isTablet ? 600 : 300;
    final double signatureHeight = isTablet ? 400 : 200;

    final SignatureController _controller = SignatureController(penStrokeWidth: 3, penColor: Colors.black, exportBackgroundColor: Colors.white);
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Firma del Usuario"),
        content: SizedBox(
          width: signatureWidth,
          height: signatureHeight,
          child: Container(
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey.shade400),
              color: Colors.grey[200], // Fondo gris suave para que se vea el área
            ),
            child: Signature(
              controller: _controller, 
              width: signatureWidth,
              height: signatureHeight,
              backgroundColor: Colors.transparent // Importante
            ),
          ),
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

  void _guardarLocalmente() async {
    if (widget.soloLectura) return;
    if (_selectedCliente == null || _selectedTecnico == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Falta seleccionar Cliente o Técnico"), backgroundColor: Colors.orange));
      return;
    }

    Map<String, dynamic> reporte = {
      'cliente': _selectedCliente,
      'tecnico': _selectedTecnico,
      'obs': _obsController.text,
      'datos_usuarios': json.encode(_usuarios), // Aquí va el mapa con 'tareas_map' incluido
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
    
    // DETECTAR ANCHO DE PANTALLA PARA MODO TABLET
    final width = MediaQuery.of(context).size.width;
    final bool esTablet = width > 600;

    return Scaffold(
      appBar: AppBar(title: Text(titulo)),
      body: LayoutBuilder(
        builder: (context, constraints) {
          if (esTablet) {
            // --- DISEÑO TABLET (2 COLUMNAS) ---
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // COLUMNA IZQUIERDA: GENERAL + LISTA USUARIOS
                SizedBox(
                  width: width * 0.4, // 40% del ancho
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      children: [
                        _buildGeneralCard(readOnly, isDark),
                        const SizedBox(height: 20),
                        _buildListaUsuarios(readOnly, isDark, compact: true),
                        const SizedBox(height: 20),
                        _buildBotonGuardar(readOnly),
                      ],
                    ),
                  ),
                ),
                // COLUMNA DERECHA: DETALLE DEL USUARIO SELECCIONADO
                Expanded(
                  child: Container(
                    margin: const EdgeInsets.all(20),
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: isDark ? kCardColorDark : Colors.white,
                      borderRadius: BorderRadius.circular(kRadius),
                      boxShadow: [const BoxShadow(color: Colors.black12, blurRadius: 10)]
                    ),
                    child: _usuarioSeleccionadoIndex >= 0 && _usuarioSeleccionadoIndex < _usuarios.length
                        ? _buildDetalleUsuario(_usuarioSeleccionadoIndex, readOnly, isDark)
                        : const Center(child: Text("Selecciona un usuario para ver detalles", style: TextStyle(color: Colors.grey))),
                  ),
                ),
              ],
            );
          } else {
            // --- DISEÑO MOVIL (1 COLUMNA) ---
            return SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  _buildGeneralCard(readOnly, isDark),
                  const SizedBox(height: 20),
                  // En móvil mostramos la lista completa expandida
                  ..._usuarios.asMap().entries.map((e) {
                    return Container(
                      margin: const EdgeInsets.only(bottom: 15),
                      decoration: BoxDecoration(
                         color: isDark ? kCardColorDark : Colors.white,
                         borderRadius: BorderRadius.circular(kRadius),
                         boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 5)]
                      ),
                      child: Column(
                        children: [
                          _buildHeaderUsuario(e.key, readOnly, isDark), // Header con nombre y X
                          _buildDetalleUsuario(e.key, readOnly, isDark), // Contenido completo
                        ],
                      ),
                    );
                  }),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                       const Text("REGISTRO", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
                       if (!readOnly) TextButton.icon(onPressed: _agregarUsuarioRapido, icon: const Icon(Icons.add), label: const Text("Agregar Usuario"))
                    ],
                  ),
                  const SizedBox(height: 20),
                  _buildBotonGuardar(readOnly),
                ],
              ),
            );
          }
        },
      ),
    );
  }

  // --- WIDGETS REUTILIZABLES ---

  Widget _buildGeneralCard(bool readOnly, bool isDark) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("INFORMACIÓN GENERAL", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: kPrimaryColor)),
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
            const SizedBox(height: 15),
            // --- CAMBIO AQUÍ: CAJA EXTENDIDA ---
            TextField(
              controller: _obsController, 
              decoration: const InputDecoration(
                labelText: "Observaciones Generales", 
                prefixIcon: Icon(Icons.comment_outlined),
                alignLabelWithHint: true, // Alinea el texto arriba
              ), 
              maxLines: 6, // Altura máxima
              minLines: 3, // Altura mínima
              readOnly: readOnly
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildListaUsuarios(bool readOnly, bool isDark, {bool compact = false}) {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text("USUARIOS", style: TextStyle(fontWeight: FontWeight.bold)),
            if (!readOnly) IconButton(icon: const Icon(Icons.add_circle, color: kPrimaryColor), onPressed: _agregarUsuarioRapido)
          ],
        ),
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: _usuarios.length,
          separatorBuilder: (_,__) => const SizedBox(height: 8),
          itemBuilder: (ctx, i) {
            final u = _usuarios[i];
            final bool isSelected = i == _usuarioSeleccionadoIndex;
            return ListTile(
              tileColor: isSelected ? kPrimaryColor.withOpacity(0.1) : (isDark ? kCardColorDark : Colors.white),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10), side: isSelected ? const BorderSide(color: kPrimaryColor) : BorderSide.none),
              title: Text(u['nombre'], style: TextStyle(fontWeight: isSelected ? FontWeight.bold : FontWeight.normal)),
              leading: Icon(Icons.person, color: isSelected ? kPrimaryColor : Colors.grey),
              trailing: !readOnly ? IconButton(icon: const Icon(Icons.close, color: Colors.red, size: 18), onPressed: ()=>_borrarUsuarioConConfirmacion(i)) : null,
              onTap: () => setState(() => _usuarioSeleccionadoIndex = i),
            );
          },
        ),
      ],
    );
  }

  Widget _buildHeaderUsuario(int idx, bool readOnly, bool isDark) {
    final usr = _usuarios[idx];
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(color: (isDark?Colors.white:Colors.black).withOpacity(0.05), borderRadius: const BorderRadius.vertical(top: Radius.circular(kRadius))),
      child: Row(
        children: [
          const Icon(Icons.person, size: 18),
          const SizedBox(width: 10),
          Expanded(child: Text(usr['nombre'] ?? "", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16))),
          if (!readOnly) IconButton(icon: const Icon(Icons.close, color: Colors.red, size: 18), onPressed: () => _borrarUsuarioConConfirmacion(idx))
        ],
      ),
    );
  }

  Widget _buildDetalleUsuario(int idx, bool readOnly, bool isDark) {
    Map usr = _usuarios[idx];
    List fotos = usr['fotos'] ?? [];
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // TITULO SI ESTAMOS EN TABLET
        if (MediaQuery.of(context).size.width > 600) 
           Padding(
             padding: const EdgeInsets.only(bottom: 20),
             child: Text(usr['nombre'], style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: isDark ? kPrimaryColorDark : kPrimaryColor)),
           ),

        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(usr['atendido'] ? "✅ Atendido" : "❌ No Atendido", style: TextStyle(color: usr['atendido'] ? Colors.green : Colors.red, fontWeight: FontWeight.bold)),
          value: usr['atendido'], 
          activeColor: Colors.green,
          onChanged: readOnly ? null : (v) => setState(() => usr['atendido'] = v)
        ),
        
        const Divider(),
        
        if (usr['atendido']) ...[
           const Text("LISTA DE TAREAS", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.grey)),
           const SizedBox(height: 10),
           
           // --- CHECKLIST CON HORA ---
           ...kTareasPredefinidas.map((tarea) {
              Map tareasMap = usr['tareas_map'] ?? {};
              bool isChecked = tareasMap.containsKey(tarea);
              String? hora = tareasMap[tarea];
              
              return CheckboxListTile(
                title: Text(tarea),
                secondary: isChecked ? Text(hora ?? "", style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold)) : null,
                value: isChecked,
                onChanged: readOnly ? null : (val) => _toggleTarea(idx, tarea, val!),
                activeColor: kPrimaryColor,
                dense: true,
                contentPadding: EdgeInsets.zero,
              );
           }),
           
           const SizedBox(height: 15),
           Row(
             children: [
               Expanded(
                 child: _ActionButton(
                   icon: Icons.camera_alt,
                   text: "${fotos.length} Fotos",
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
           ),

           // --- GALERÍA DE FOTOS (NUEVO) ---
           if (fotos.isNotEmpty) ...[
             const SizedBox(height: 20),
             const Text("EVIDENCIA FOTOGRÁFICA:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.grey)),
             const SizedBox(height: 10),
             Wrap(
               spacing: 10,
               runSpacing: 10,
               children: fotos.map<Widget>((path) {
                 return ClipRRect(
                   borderRadius: BorderRadius.circular(8),
                   child: Image.file(
                     File(path), 
                     width: 100, 
                     height: 100, 
                     fit: BoxFit.cover,
                     errorBuilder: (c,e,s) => Container(width: 100, height: 100, color: Colors.grey, child: const Icon(Icons.broken_image)),
                   ),
                 );
               }).toList(),
             )
           ]

        ] else
           TextFormField(
             initialValue: usr['motivo'],
             decoration: const InputDecoration(labelText: "Motivo no atención"),
             readOnly: readOnly,
             onChanged: (v) => usr['motivo'] = v,
           ),
      ],
    );
  }

  Widget _buildBotonGuardar(bool readOnly) {
    if (readOnly) return const SizedBox();
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: _guardarLocalmente,
        child: Text(widget.reporteEditar != null ? "GUARDAR CAMBIOS" : "GUARDAR VISITA", style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
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