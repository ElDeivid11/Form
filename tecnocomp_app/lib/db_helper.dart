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
    // CAMBIO IMPORTANTE: Cambié el nombre a 'tecnocomp_v7.db' para forzar 
    // a que la app cree una base de datos nueva y limpia con todas las tablas.
    String path = join(await getDatabasesPath(), 'tecnocomp_v7.db');
    
    return await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        // --- 1. TABLA CLIENTES (Esta era la que faltaba y daba error) ---
        await db.execute('''
          CREATE TABLE clientes(
            nombre TEXT PRIMARY KEY, 
            email TEXT
          )
        ''');

        // --- 2. TABLA TÉCNICOS ---
        await db.execute('''
          CREATE TABLE tecnicos(
            nombre TEXT PRIMARY KEY, 
            email TEXT
          )
        ''');

        // --- 3. TABLA USUARIOS FRECUENTES ---
        await db.execute('''
          CREATE TABLE usuarios_frecuentes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nombre TEXT, 
            cliente TEXT
          )
        ''');
        
        // --- 4. TABLA REPORTES ---
        await db.execute('''
          CREATE TABLE reportes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
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

  // --- REPORTES ---
  Future<int> insertarReporte(Map<String, dynamic> row) async {
    final db = await database;
    return await db.insert('reportes', row);
  }

  Future<void> actualizarServerId(int localId, int serverId) async {
    final db = await database;
    await db.update('reportes', {'server_id': serverId, 'enviado': 1}, where: 'id = ?', whereArgs: [localId]);
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
  Future<void> agregarTecnicoLocal(String nombre, String email) async {
    final db = await database;
    await db.insert('tecnicos', {'nombre': nombre, 'email': email}, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<String>> getTecnicos() async {
    final db = await database;
    final res = await db.query('tecnicos', orderBy: 'nombre ASC');
    return res.map((e) => e['nombre'] as String).toList();
  }

  Future<String?> getTecnicoEmail(String nombre) async {
    final db = await database;
    final res = await db.query('tecnicos', columns: ['email'], where: 'nombre = ?', whereArgs: [nombre]);
    if (res.isNotEmpty) return res.first['email'] as String?;
    return null;
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

  // --- SINCRONIZACIÓN (ROBUSTA) ---
  Future<void> guardarConfiguracion(List clientes, List tecnicos) async {
    final db = await database;
    await db.transaction((txn) async {
      // 1. Guardar Clientes
      for (var c in clientes) {
        String nombre = "";
        String email = "";

        if (c is List && c.isNotEmpty) {
          nombre = c[0].toString();
          if (c.length > 1) email = c[1].toString();
        } 
        else if (c is Map) {
          nombre = c['nombre'] ?? "";
          email = c['email'] ?? "";
        }

        if (nombre.isNotEmpty) {
          await txn.rawInsert(
            'INSERT OR REPLACE INTO clientes(nombre, email) VALUES(?, ?)', 
            [nombre, email]
          );
        }
      }

      // 2. Guardar Técnicos
      for (var t in tecnicos) {
        String nombre = "";
        String email = ""; // Si viniera email en el futuro
        
        if (t is String) {
          nombre = t;
        }
        else if (t is List && t.isNotEmpty) {
          nombre = t[0].toString();
          // if (t.length > 1) email = t[1].toString();
        }
        else if (t is Map) {
            nombre = t['nombre'] ?? "";
            email = t['email'] ?? "";
        }

        if (nombre.isNotEmpty) {
           await txn.rawInsert(
             'INSERT OR REPLACE INTO tecnicos(nombre, email) VALUES(?, ?)', 
             [nombre, email]
           );
        }
      }
    });
  }

  // --- FUNCIONES DE UPDATE Y DELETE ---
  Future<int> updateReporte(int id, Map<String, dynamic> row) async {
    final db = await database;
    return await db.update('reportes', row, where: 'id = ?', whereArgs: [id]);
  }

  Future<void> marcarComoEnviado(int id) async {
    final db = await database;
    await db.update('reportes', {'enviado': 1}, where: 'id = ?', whereArgs: [id]);
  }

  Future<List<Map<String, dynamic>>> getReportesPendientes() async {
    final db = await database;
    return await db.query('reportes', where: 'enviado = 0', orderBy: "id DESC");
  }

  Future<List<Map<String, dynamic>>> getReportesEnviados() async {
    final db = await database;
    return await db.query('reportes', where: 'enviado = 1', orderBy: "id DESC");
  }

  Future<void> borrarReporteFisico(int id) async {
    final db = await database;
    await db.delete('reportes', where: 'id = ?', whereArgs: [id]);
  }
}