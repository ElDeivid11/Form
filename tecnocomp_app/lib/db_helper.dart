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
    String path = join(await getDatabasesPath(), 'tecnocomp_offline.db');
    return await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        // Tablas espejo de tu servidor para trabajar Offline
        await db.execute('CREATE TABLE clientes(nombre TEXT PRIMARY KEY, email TEXT)');
        await db.execute('CREATE TABLE tecnicos(nombre TEXT PRIMARY KEY)');
        
        // Tabla de cola de espera (Reportes creados sin internet)
        await db.execute('''
          CREATE TABLE reportes_pendientes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            tecnico TEXT,
            obs TEXT,
            datos_usuarios TEXT, 
            firma_path TEXT,
            fecha_creacion TEXT
          )
        ''');
      },
    );
  }

  // --- MÉTODOS DE SINCRONIZACIÓN ---
  Future<void> guardarConfiguracion(List clientes, List tecnicos) async {
    final db = await database;
    await db.transaction((txn) async {
      await txn.delete('clientes');
      await txn.delete('tecnicos');
      for (var c in clientes) {
        await txn.insert('clientes', {'nombre': c[0], 'email': c[1]});
      }
      for (var t in tecnicos) {
        await txn.insert('tecnicos', {'nombre': t});
      }
    });
  }

  Future<List<String>> getClientes() async {
    final db = await database;
    final res = await db.query('clientes');
    return res.map((e) => e['nombre'] as String).toList();
  }

  Future<List<String>> getTecnicos() async {
    final db = await database;
    final res = await db.query('tecnicos');
    return res.map((e) => e['nombre'] as String).toList();
  }

  // --- MÉTODOS DE REPORTE ---
  Future<int> insertarReporte(Map<String, dynamic> row) async {
    final db = await database;
    return await db.insert('reportes_pendientes', row);
  }

  Future<List<Map<String, dynamic>>> getReportesPendientes() async {
    final db = await database;
    return await db.query('reportes_pendientes');
  }

  Future<void> borrarReporte(int id) async {
    final db = await database;
    await db.delete('reportes_pendientes', where: 'id = ?', whereArgs: [id]);
  }
}