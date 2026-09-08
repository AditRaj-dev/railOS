import 'dart:convert';

import 'package:sqflite/sqflite.dart';

/// A possession transition waiting for an online replay.
///
/// The queue deliberately stores the request envelope rather than only the
/// action. That keeps the server's audit fields (idempotency key, field clock,
/// and replay marker) intact across a process restart.
class QueuedTransition {
  final String id;
  final String possessionId;
  final String action;
  final Map<String, dynamic> payload;
  final String idempotencyKey;
  final String clientEventAtUtc;
  final bool offlineReplay;
  int attempts;
  DateTime? nextAttemptAt;
  String? lastError;

  QueuedTransition({
    required this.id,
    required this.possessionId,
    required this.action,
    required this.payload,
    required this.idempotencyKey,
    required this.clientEventAtUtc,
    this.offlineReplay = true,
    this.attempts = 0,
    this.nextAttemptAt,
    this.lastError,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'possessionId': possessionId,
    'action': action,
    'payload': payload,
    'idempotencyKey': idempotencyKey,
    'clientEventAtUtc': clientEventAtUtc,
    'offlineReplay': offlineReplay,
    'attempts': attempts,
    'nextAttemptAt': nextAttemptAt?.toUtc().toIso8601String(),
    'lastError': lastError,
  };

  factory QueuedTransition.fromJson(Map<String, dynamic> json) {
    final payload = json['payload'];
    return QueuedTransition(
      id: json['id'] as String,
      possessionId: json['possessionId'] as String? ?? '',
      action: json['action'] as String,
      payload: payload is Map
          ? Map<String, dynamic>.from(payload)
          : <String, dynamic>{},
      idempotencyKey: json['idempotencyKey'] as String,
      clientEventAtUtc: json['clientEventAtUtc'] as String,
      offlineReplay: json['offlineReplay'] as bool? ?? true,
      attempts: (json['attempts'] as num?)?.toInt() ?? 0,
      nextAttemptAt: _parseDate(json['nextAttemptAt'] as String?),
      lastError: json['lastError'] as String?,
    );
  }

  static DateTime? _parseDate(String? value) {
    if (value == null || value.isEmpty) return null;
    return DateTime.tryParse(value)?.toUtc();
  }
}

/// Local persistence for the field surface.
///
/// Android/iOS use sqflite. Flutter widget tests and desktop previews do not
/// register the native sqflite plugin, so opening the database falls back to a
/// process-local store. The explicit [inMemory] option makes that fallback
/// deterministic for tests without changing the production path.
class LocalStore {
  static const _databaseName = 'railos_field.db';
  static const _databaseVersion = 1;

  final bool _forceMemory;
  final String _databaseNameOverride;
  final Map<String, Map<String, String>> _memory = {
    'queued_evidence': <String, String>{},
    'queued_transitions': <String, String>{},
    'cached_tasks': <String, String>{},
    'cached_possessions': <String, String>{},
    'session': <String, String>{},
  };

  Database? _database;
  Future<void>? _initialization;
  bool _memoryMode = false;

  LocalStore({bool inMemory = false, String? databaseName})
    : _forceMemory = inMemory,
      _databaseNameOverride = databaseName ?? _databaseName {
    _memoryMode = inMemory;
  }

  bool get isMemoryMode => _memoryMode;

  Future<void> initialize() => _initialization ??= _open();

  Future<void> _open() async {
    if (_forceMemory) return;
    try {
      final path = await getDatabasesPath();
      _database = await openDatabase(
        '$path/$_databaseNameOverride',
        version: _databaseVersion,
        onCreate: (db, version) async {
          await db.execute('''
            CREATE TABLE queued_evidence (
              id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
          ''');
          await db.execute('''
            CREATE TABLE queued_transitions (
              id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              attempts INTEGER NOT NULL DEFAULT 0,
              next_attempt_at TEXT,
              last_error TEXT,
              updated_at TEXT NOT NULL
            )
          ''');
          await db.execute('''
            CREATE TABLE cached_tasks (
              id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
          ''');
          await db.execute('''
            CREATE TABLE cached_possessions (
              id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
          ''');
          await db.execute('''
            CREATE TABLE session (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              payload TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
          ''');
        },
      );
    } catch (_) {
      // A native plugin is unavailable in widget tests/desktop previews. The
      // app remains usable and callers can still exercise the queue contract.
      _database = null;
      _memoryMode = true;
    }
  }

  Future<void> saveSession(Map<String, dynamic> payload) async {
    await initialize();
    await _writeJson(
      table: 'session',
      id: '1',
      payload: payload,
      singleRow: true,
    );
  }

  Future<Map<String, dynamic>?> loadSession() async {
    await initialize();
    final payload = await _readJson(table: 'session', id: '1');
    return payload;
  }

  Future<void> clearSession() async {
    await initialize();
    await _delete(table: 'session', id: '1');
  }

  Future<void> saveEvidence(Map<String, dynamic> payload) async {
    await initialize();
    final id = payload['evidenceId'] as String?;
    if (id == null || id.isEmpty) return;
    await _writeJson(table: 'queued_evidence', id: id, payload: payload);
  }

  Future<List<Map<String, dynamic>>> loadEvidence() async {
    await initialize();
    return _readAllJson(table: 'queued_evidence');
  }

  Future<void> deleteEvidence(String evidenceId) async {
    await initialize();
    await _delete(table: 'queued_evidence', id: evidenceId);
  }

  Future<void> saveTransition(QueuedTransition transition) async {
    await initialize();
    await _writeJson(
      table: 'queued_transitions',
      id: transition.id,
      payload: transition.toJson(),
      attempts: transition.attempts,
      nextAttemptAt: transition.nextAttemptAt,
      lastError: transition.lastError,
    );
  }

  Future<List<QueuedTransition>> loadTransitions() async {
    await initialize();
    final rows = await _readAllJson(table: 'queued_transitions');
    return rows.map(QueuedTransition.fromJson).toList();
  }

  Future<void> deleteTransition(String transitionId) async {
    await initialize();
    await _delete(table: 'queued_transitions', id: transitionId);
  }

  Future<void> saveTasks(List<Map<String, dynamic>> tasks) async {
    await initialize();
    await _replaceJsonCollection('cached_tasks', tasks, 'taskId');
  }

  Future<List<Map<String, dynamic>>> loadTasks() async {
    await initialize();
    return _readAllJson(table: 'cached_tasks');
  }

  Future<void> savePossessions(List<Map<String, dynamic>> possessions) async {
    await initialize();
    await _replaceJsonCollection(
      'cached_possessions',
      possessions,
      'possessionId',
    );
  }

  Future<List<Map<String, dynamic>>> loadPossessions() async {
    await initialize();
    return _readAllJson(table: 'cached_possessions');
  }

  Future<void> _replaceJsonCollection(
    String table,
    List<Map<String, dynamic>> payloads,
    String idKey,
  ) async {
    if (_database == null) {
      final memoryTable = _memory[table]!;
      memoryTable.clear();
      for (var index = 0; index < payloads.length; index++) {
        final payload = payloads[index];
        final id = payload[idKey]?.toString() ?? '$index';
        memoryTable[id] = jsonEncode(payload);
      }
      return;
    }

    try {
      await _database!.transaction((txn) async {
        await txn.delete(table);
        final batch = txn.batch();
        for (var index = 0; index < payloads.length; index++) {
          final payload = payloads[index];
          final id = payload[idKey]?.toString() ?? '$index';
          batch.insert(table, {
            'id': id,
            'payload': jsonEncode(payload),
            'updated_at': DateTime.now().toUtc().toIso8601String(),
          }, conflictAlgorithm: ConflictAlgorithm.replace);
        }
        await batch.commit(noResult: true);
      });
    } catch (_) {
      _database = null;
      _memoryMode = true;
      await _replaceJsonCollection(table, payloads, idKey);
    }
  }

  Future<void> _writeJson({
    required String table,
    required String id,
    required Map<String, dynamic> payload,
    bool singleRow = false,
    int attempts = 0,
    DateTime? nextAttemptAt,
    String? lastError,
  }) async {
    if (_database == null) {
      if (singleRow) _memory[table]!.clear();
      _memory[table]![id] = jsonEncode(payload);
      return;
    }

    try {
      final values = <String, Object?>{
        'id': singleRow ? 1 : id,
        'payload': jsonEncode(payload),
        'updated_at': DateTime.now().toUtc().toIso8601String(),
      };
      if (table == 'queued_transitions') {
        values['attempts'] = attempts;
        values['next_attempt_at'] = nextAttemptAt?.toUtc().toIso8601String();
        values['last_error'] = lastError;
      }
      await _database!.insert(
        table,
        values,
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    } catch (_) {
      _database = null;
      _memoryMode = true;
      if (singleRow) _memory[table]!.clear();
      _memory[table]![id] = jsonEncode(payload);
    }
  }

  Future<Map<String, dynamic>?> _readJson({
    required String table,
    required String id,
  }) async {
    if (_database == null) {
      final raw = _memory[table]![id];
      if (raw == null) return null;
      return Map<String, dynamic>.from(jsonDecode(raw) as Map);
    }

    try {
      final rows = await _database!.query(
        table,
        where: 'id = ?',
        whereArgs: [table == 'session' ? 1 : id],
        limit: 1,
      );
      if (rows.isEmpty) return null;
      return Map<String, dynamic>.from(
        jsonDecode(rows.first['payload'] as String) as Map,
      );
    } catch (_) {
      _database = null;
      _memoryMode = true;
      return null;
    }
  }

  Future<List<Map<String, dynamic>>> _readAllJson({
    required String table,
  }) async {
    if (_database == null) {
      return _memory[table]!.values
          .map((raw) => Map<String, dynamic>.from(jsonDecode(raw) as Map))
          .toList();
    }

    try {
      final rows = await _database!.query(table, orderBy: 'updated_at ASC');
      return rows
          .map(
            (row) => Map<String, dynamic>.from(
              jsonDecode(row['payload'] as String) as Map,
            ),
          )
          .toList();
    } catch (_) {
      _database = null;
      _memoryMode = true;
      return <Map<String, dynamic>>[];
    }
  }

  Future<void> _delete({required String table, required String id}) async {
    if (_database == null) {
      _memory[table]!.remove(id);
      return;
    }

    try {
      await _database!.delete(
        table,
        where: 'id = ?',
        whereArgs: [table == 'session' ? 1 : id],
      );
    } catch (_) {
      _database = null;
      _memoryMode = true;
      _memory[table]!.remove(id);
    }
  }
}
