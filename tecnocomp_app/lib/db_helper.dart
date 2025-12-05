import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class DBHelper {
  static final DBHelper _instance = DBHelper._internal();
  static Database? _database;

  DBHelper._internal();

  factory DBHelper() => _instance;

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB();
    return _database!;
  }

  Future<Database> _initDB() async {
    // CAMBIO V4: Para limpiar estructura y agregar campo 'enviado'
    String path = join(await getDatabasesPath(), 'tecnocomp_v4.db');
    return await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('CREATE TABLE clientes(nombre TEXT PRIMARY KEY, email TEXT)');
        await db.execute('CREATE TABLE tecnicos(nombre TEXT PRIMARY KEY)');
        
        await db.execute('''
          CREATE TABLE usuarios_frecuentes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cliente TEXT,
            UNIQUE(nombre, cliente)
          )
        ''');

        // NUEVO CAMPO: enviado (0=Pendiente, 1=Enviado)
        await db.execute('''
          CREATE TABLE reportes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            tecnico TEXT,
            obs TEXT,
            datos_usuarios TEXT, 
            firma_path TEXT,
            fecha_creacion TEXT,
            enviado INTEGER DEFAULT 0 
          )
        ''');
      },
    );
  }

  // --- CLIENTES ---
  Future<void> agregarClienteLocal(String nombre, String email) async {
    final db = await database;
    await db.insert('clientes', {'nombre': nombre, 'email': email}, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Map<String, dynamic>>> getClientesMap() async {
    final db = await database;
    return await db.query('clientes', orderBy: 'nombre ASC');
  }

  Future<List<String>> getClientes() async {
    final list = await getClientesMap();
    return list.map((e) => e['nombre'] as String).toList();
  }

  Future<void> eliminarCliente(String nombre) async {
    final db = await database;
    await db.delete('clientes', where: 'nombre = ?', whereArgs: [nombre]);
    await db.delete('usuarios_frecuentes', where: 'cliente = ?', whereArgs: [nombre]);
  }

  Future<String?> getClientEmail(String nombre) async {
    final db = await database;
    final res = await db.query('clientes', columns: ['email'], where: 'nombre = ?', whereArgs: [nombre]);
    if (res.isNotEmpty) return res.first['email'] as String?;
    return null;
  }

  // --- TÉCNICOS ---
  Future<void> agregarTecnicoLocal(String nombre) async {
    final db = await database;
    await db.insert('tecnicos', {'nombre': nombre}, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<String>> getTecnicos() async {
    final db = await database;
    final res = await db.query('tecnicos', orderBy: 'nombre ASC');
    return res.map((e) => e['nombre'] as String).toList();
  }

  Future<void> eliminarTecnico(String nombre) async {
    final db = await database;
    await db.delete('tecnicos', where: 'nombre = ?', whereArgs: [nombre]);
  }

  // --- USUARIOS FRECUENTES ---
  Future<void> guardarUsuarioFrecuente(String nombre, String cliente) async {
    final db = await database;
    await db.rawInsert('INSERT OR IGNORE INTO usuarios_frecuentes(nombre, cliente) VALUES(?, ?)', [nombre, cliente]);
  }

  Future<List<String>> getUsuariosPorCliente(String cliente) async {
    final db = await database;
    final res = await db.query('usuarios_frecuentes', where: 'cliente = ?', whereArgs: [cliente], orderBy: 'nombre ASC');
    return res.map((e) => e['nombre'] as String).toList();
  }

  Future<void> eliminarUsuarioFrecuente(String nombre, String cliente) async {
    final db = await database;
    await db.delete('usuarios_frecuentes', where: 'nombre = ? AND cliente = ?', whereArgs: [nombre, cliente]);
  }

  // --- SINCRONIZACIÓN ---
  Future<void> guardarConfiguracion(List clientes, List tecnicos) async {
    final db = await database;
    await db.transaction((txn) async {
      for (var c in clientes) {
        await txn.rawInsert('INSERT OR IGNORE INTO clientes(nombre, email) VALUES(?, ?)', [c[0], c[1]]);
      }
      for (var t in tecnicos) {
        await txn.rawInsert('INSERT OR IGNORE INTO tecnicos(nombre) VALUES(?)', [t]);
      }
    });
  }

  // --- REPORTES ---
  Future<int> insertarReporte(Map<String, dynamic> row) async {
    final db = await database;
    return await db.insert('reportes', row);
  }

  Future<int> updateReporte(int id, Map<String, dynamic> row) async {
    final db = await database;
    return await db.update('reportes', row, where: 'id = ?', whereArgs: [id]);
  }

  // NUEVO: Marcar como enviado en lugar de borrar
  Future<void> marcarComoEnviado(int id) async {
    final db = await database;
    await db.update('reportes', {'enviado': 1}, where: 'id = ?', whereArgs: [id]);
  }

  // NUEVO: Obtener solo pendientes
  Future<List<Map<String, dynamic>>> getReportesPendientes() async {
    final db = await database;
    return await db.query('reportes', where: 'enviado = 0', orderBy: "id DESC");
  }

  // NUEVO: Obtener solo enviados (historial)
  Future<List<Map<String, dynamic>>> getReportesEnviados() async {
    final db = await database;
    return await db.query('reportes', where: 'enviado = 1', orderBy: "id DESC");
  }

  // Borrado físico (solo si el usuario quiere limpiar el historial)
  Future<void> borrarReporteFisico(int id) async {
    final db = await database;
    await db.delete('reportes', where: 'id = ?', whereArgs: [id]);
  }
}