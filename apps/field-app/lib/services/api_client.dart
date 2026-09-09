import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../models/evidence_models.dart';
import '../storage/local_store.dart';
import '../storage/offline_evidence_queue.dart';

class RailOSApiException implements Exception {
  final int statusCode;
  final String code;
  final String message;
  final Map<String, dynamic> details;

  const RailOSApiException({
    required this.statusCode,
    required this.code,
    required this.message,
    this.details = const <String, dynamic>{},
  });

  @override
  String toString() => '$code ($statusCode): $message';
}

class RailOSNetworkException implements Exception {
  final String message;

  const RailOSNetworkException(this.message);

  @override
  String toString() => message;
}

class OfflineEntitlementExpiredException implements Exception {
  const OfflineEntitlementExpiredException();

  @override
  String toString() =>
      'Your 24-hour offline entitlement has expired. Reconnect and authenticate before recording field actions.';
}

class RailOSApiClient {
  final String baseUrl;
  final OfflineEvidenceQueue queue;

  // Points at the deployed Render backend by default. For local dev against
  // an emulator, override with --dart-define=RAILOS_API_BASE=http://10.0.2.2:8000
  // (10.0.2.2 = emulator host loopback); a physical device on the same LAN as
  // a local server can use --dart-define=RAILOS_API_BASE=http://127.0.0.1:8000
  // with adb reverse.
  static const _defaultBase = String.fromEnvironment(
    'RAILOS_API_BASE',
    defaultValue: 'https://railos-api.onrender.com',
  );

  RailOSApiClient({String? baseUrl, OfflineEvidenceQueue? queue})
    : baseUrl = (baseUrl ?? _defaultBase).replaceFirst(RegExp(r'/$'), ''),
      queue = queue ?? OfflineEvidenceQueue() {
    this.queue.attachSyncHandlers(
      evidenceSync: syncEvidence,
      transitionSync: _syncQueuedTransition,
    );
  }

  String? get _token => queue.currentSession?.accessToken;

  Map<String, String> _headers({
    String? idempotencyKey,
    String? clientEventAtUtc,
    bool offlineReplay = false,
  }) {
    final session = queue.currentSession;
    return {
      'Content-Type': 'application/json',
      if (_token != null && _token!.isNotEmpty)
        'Authorization': 'Bearer $_token',
      if (session != null && session.userId.isNotEmpty)
        'X-RailOS-User': session.userId,
      // The role comes from the authenticated session so the same binary can
      // be used by FIELD_SUPERVISOR, STATION_MASTER, TPC, or SSE staff.
      'X-RailOS-Role': session?.normalizedRole ?? 'FIELD_SUPERVISOR',
      if (idempotencyKey != null) 'Idempotency-Key': idempotencyKey,
      if (clientEventAtUtc != null)
        'X-RailOS-Client-Event-At': clientEventAtUtc,
      if (offlineReplay) 'X-RailOS-Offline-Replay': 'true',
    };
  }

  Future<dynamic> _request(
    String method,
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
  }) async {
    final client = HttpClient();
    try {
      final request = await client.openUrl(method, Uri.parse('$baseUrl$path'));
      (headers ?? const <String, String>{}).forEach(request.headers.set);
      if (body != null) request.write(jsonEncode(body));
      final response = await request.close();
      final raw = await response.transform(utf8.decoder).join();
      dynamic decoded;
      if (raw.trim().isNotEmpty) {
        try {
          decoded = jsonDecode(raw);
        } catch (_) {
          decoded = <String, dynamic>{'message': raw};
        }
      } else {
        decoded = <String, dynamic>{};
      }

      if (response.statusCode < 200 || response.statusCode >= 300) {
        final error = decoded is Map
            ? Map<String, dynamic>.from(decoded)
            : <String, dynamic>{};
        final detail = error['detail'];
        final envelope = detail is Map
            ? Map<String, dynamic>.from(detail)
            : error;
        throw RailOSApiException(
          statusCode: response.statusCode,
          code: envelope['code'] as String? ?? 'HTTP_${response.statusCode}',
          message:
              envelope['message'] as String? ??
              'The server rejected this request.',
          details: envelope['details'] is Map
              ? Map<String, dynamic>.from(envelope['details'] as Map)
              : const <String, dynamic>{},
        );
      }
      return decoded;
    } on RailOSApiException {
      rethrow;
    } on SocketException catch (error) {
      throw RailOSNetworkException(
        'RailOS server is unreachable: ${error.message}',
      );
    } on TimeoutException catch (error) {
      throw RailOSNetworkException('RailOS request timed out: $error');
    } on HandshakeException catch (error) {
      throw RailOSNetworkException(
        'Secure connection to RailOS failed: $error',
      );
    } catch (error) {
      // HttpClient reports DNS and platform transport failures through several
      // different exception types. Keep them queueable as network failures.
      if (error is FormatException) rethrow;
      throw RailOSNetworkException('RailOS request failed: $error');
    } finally {
      client.close(force: true);
    }
  }

  Future<SupervisorSession> login(String employeeId, String password) async {
    final data = _asMap(
      await _request(
        'POST',
        '/api/v1/auth/login',
        body: {'employeeId': employeeId, 'password': password},
        headers: const {'Content-Type': 'application/json'},
      ),
    );
    final now = DateTime.now().toUtc();
    final assigned = _asStringList(data['assignedSections']);
    final session = SupervisorSession(
      userId: data['userId'] as String? ?? employeeId,
      employeeId: data['employeeId'] as String? ?? employeeId,
      name: data['name'] as String? ?? employeeId,
      accessToken: data['accessToken'] as String? ?? '',
      refreshToken: data['refreshToken'] as String? ?? '',
      loginTime: now,
      assignedSections: assigned.isEmpty
          ? ['SEC_KRJ_SMQ', 'GZB-ALJN']
          : assigned,
      role: data['role'] as String? ?? 'FIELD_SUPERVISOR',
      offlineEntitlementExpiresAt: now.add(const Duration(hours: 24)),
    );
    queue.setSession(session);
    return session;
  }

  /// Exchange the stored refresh token for a new access token. Returns false
  /// when there is nothing to refresh with, or the server refuses -- the
  /// caller then has a genuine sign-in problem to report.
  Future<bool> _refreshSession() async {
    final session = queue.currentSession;
    if (session == null || session.refreshToken.isEmpty) return false;
    try {
      final data = _asMap(
        await _request(
          'POST',
          '/api/v1/auth/refresh',
          body: {'refreshToken': session.refreshToken},
          headers: {'Content-Type': 'application/json'},
        ),
      );
      final access = data['accessToken'] as String? ?? '';
      if (access.isEmpty) return false;
      queue.setSession(
        session.copyWith(
          accessToken: access,
          refreshToken: data['refreshToken'] as String? ?? session.refreshToken,
        ),
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  /// A day-old access token used to leave the dashboard spinning forever: the
  /// 401 escaped every catch on the way up and the loading flag was never
  /// cleared. Refresh once, retry once, then let the error travel.
  Future<dynamic> _authedRequest(
    String method,
    String path, {
    Map<String, dynamic>? body,
  }) async {
    try {
      return await _request(method, path, body: body, headers: _headers());
    } on RailOSApiException catch (error) {
      if (error.statusCode != 401) rethrow;
      if (!await _refreshSession()) rethrow;
      return await _request(method, path, body: body, headers: _headers());
    }
  }

  Future<List<Map<String, dynamic>>> fetchMyAssignments() async {
    try {
      final data = _asMap(
        await _authedRequest('GET', '/api/v1/work/assignments/mine'),
      );
      final tasks = _asMapList(data['tasks'] ?? data['items']);
      if (tasks.isNotEmpty) queue.setCachedTasks(tasks);
      final sections = _asStringList(data['assignedSections']);
      final session = queue.currentSession;
      if (session != null && sections.isNotEmpty) {
        queue.setSession(session.copyWith(assignedSections: sections));
      }
      return tasks;
    } on RailOSNetworkException {
      if (queue.cachedTasks.isNotEmpty) return queue.cachedTasks;
    }

    // A small deterministic preview keeps the field flow inspectable when a
    // new handset has not connected yet. It is explicitly synthetic.
    return [
      {
        'taskId': 'TSK-0001',
        'title': 'Plain Track Tamping & Deep Ballast Inspection',
        'corridorId': 'GZB-ALJN',
        'department': 'ENGG',
        'status': 'STARTED',
        'synthetic': true,
        'steps': [
          {
            'stepId': 'stp-101',
            'taskId': 'TSK-0001',
            'stepIndex': 1,
            'title': 'Pre-work Site Inspection & Ballast Profile',
            'requiresPhoto': true,
            'requiresVideo': false,
            'targetLatitude': 28.6139,
            'targetLongitude': 77.2090,
            'targetRadiusMeters': 100.0,
            'status': 'READY',
          },
          {
            'stepId': 'stp-102',
            'taskId': 'TSK-0001',
            'stepIndex': 2,
            'title': 'Final Track Geometry & Clearance Video (<=90s)',
            'requiresPhoto': false,
            'requiresVideo': true,
            'targetLatitude': 28.6139,
            'targetLongitude': 77.2090,
            'targetRadiusMeters': 100.0,
            'status': 'READY',
          },
        ],
      },
    ];
  }

  Future<List<Map<String, dynamic>>> fetchMyPossessions() async {
    try {
      final data = _asMap(
        await _authedRequest('GET', '/api/v1/possessions/mine'),
      );
      final possessions = _asMapList(data['items'] ?? data['possessions']);
      if (possessions.isNotEmpty || data.containsKey('items')) {
        queue.setCachedPossessions(possessions);
      }
      return possessions;
    } on RailOSNetworkException {
      return queue.cachedPossessions;
    }
  }

  Future<Map<String, dynamic>> fetchPossession(String possessionId) async {
    try {
      final data = _asMap(
        await _request(
          'GET',
          '/api/v1/possessions/$possessionId',
          headers: _headers(),
        ),
      );
      _cachePossession(data);
      return data;
    } on RailOSNetworkException {
      return queue.cachedPossessions.firstWhere(
        (item) => item['possessionId'] == possessionId,
        orElse: () => <String, dynamic>{'possessionId': possessionId},
      );
    }
  }

  Future<Map<String, dynamic>> postPossessionAction({
    required String possessionId,
    required String action,
    String? note,
    String? formReference,
    Map<String, dynamic>? details,
    int? durationMinutes,
    int? tsrSpeedKmph,
    int? detonatorCount,
    String? deferredUntilUtc,
    String? causeCategory,
    String? clientEventAtUtc,
    String? idempotencyKey,
    bool queueWhenOffline = true,
  }) async {
    final normalizedAction = action.trim().toLowerCase();
    final eventAt =
        clientEventAtUtc ?? DateTime.now().toUtc().toIso8601String();
    final key =
        idempotencyKey ??
        'field-${possessionId}-${normalizedAction}-${DateTime.now().microsecondsSinceEpoch}';
    final body = <String, dynamic>{
      'action': normalizedAction,
      'clientEventAtUtc': eventAt,
      if (note != null && note.isNotEmpty) 'note': note,
      if (formReference != null && formReference.isNotEmpty)
        'formReference': formReference,
      if (details != null && details.isNotEmpty) 'details': details,
      if (durationMinutes != null) 'durationMinutes': durationMinutes,
      if (tsrSpeedKmph != null) 'tsrSpeedKmph': tsrSpeedKmph,
      if (detonatorCount != null) 'detonatorCount': detonatorCount,
      if (deferredUntilUtc != null) 'deferredUntilUtc': deferredUntilUtc,
      if (causeCategory != null) 'causeCategory': causeCategory,
    };

    try {
      final response = _asMap(
        await _request(
          'POST',
          '/api/v1/possessions/$possessionId/transitions/$normalizedAction',
          body: body,
          headers: _headers(idempotencyKey: key, clientEventAtUtc: eventAt),
        ),
      );
      _cachePossession(response);
      return response;
    } on RailOSNetworkException {
      if (!queueWhenOffline || isOnlineOnlyPossessionAction(normalizedAction))
        rethrow;
      if (!(queue.currentSession?.isOfflineEntitlementValid ?? false)) {
        throw const OfflineEntitlementExpiredException();
      }
      queue.enqueueTransition(
        possessionId: possessionId,
        action: normalizedAction,
        payload: body,
        idempotencyKey: key,
        clientEventAtUtc: eventAt,
      );
      return {
        'possessionId': possessionId,
        'action': normalizedAction,
        'queued': true,
        'message':
            'Saved on this device. It will replay when the connection returns.',
      };
    }
  }

  Future<void> _syncQueuedTransition(QueuedTransition transition) async {
    if (transition.action == 'work-status') {
      final assignmentId = transition.payload['assignmentId'] as String?;
      if (assignmentId == null || assignmentId.isEmpty) {
        throw const RailOSApiException(
          statusCode: 400,
          code: 'INVALID_QUEUED_WRITE',
          message: 'Queued work update has no assignment id.',
        );
      }
      await _request(
        'POST',
        '/api/v1/work/assignments/$assignmentId/updates',
        body: {
          'status': transition.payload['status'] ?? 'STARTED',
          'executionStatus': transition.payload['executionStatus'],
          'note': transition.payload['note'] ?? '',
        },
        headers: _headers(
          idempotencyKey: transition.idempotencyKey,
          clientEventAtUtc: transition.clientEventAtUtc,
          offlineReplay: transition.offlineReplay,
        ),
      );
      return;
    }

    await _request(
      'POST',
      '/api/v1/possessions/${transition.possessionId}/transitions/${transition.action}',
      body: transition.payload,
      headers: _headers(
        idempotencyKey: transition.idempotencyKey,
        clientEventAtUtc: transition.clientEventAtUtc,
        offlineReplay: transition.offlineReplay,
      ),
    );
  }

  Future<Map<String, dynamic>> updateWorkStatus({
    required String assignmentId,
    required String executionStatus,
    required String taskStatus,
    String note = '',
    String? possessionId,
  }) async {
    final eventAt = DateTime.now().toUtc().toIso8601String();
    final key =
        'work-${assignmentId}-${executionStatus}-${DateTime.now().microsecondsSinceEpoch}';
    final body = {
      'status': taskStatus,
      'executionStatus': executionStatus,
      'note': note,
    };
    try {
      return _asMap(
        await _request(
          'POST',
          '/api/v1/work/assignments/$assignmentId/updates',
          body: body,
          headers: _headers(idempotencyKey: key, clientEventAtUtc: eventAt),
        ),
      );
    } on RailOSNetworkException {
      if (possessionId == null || possessionId.isEmpty) rethrow;
      if (!(queue.currentSession?.isOfflineEntitlementValid ?? false)) {
        throw const OfflineEntitlementExpiredException();
      }
      queue.enqueueTransition(
        possessionId: possessionId,
        action: 'work-status',
        payload: {'assignmentId': assignmentId, ...body},
        idempotencyKey: key,
        clientEventAtUtc: eventAt,
      );
      return {
        'assignmentId': assignmentId,
        'executionStatus': executionStatus,
        'queued': true,
        'message': 'Work update saved on this device for replay when online.',
      };
    }
  }

  Future<void> syncEvidence(CapturedEvidence evidence) async {
    await _request(
      'POST',
      '/api/v1/evidence',
      body: {
        'evidenceId': evidence.evidenceId,
        'taskId': evidence.taskId,
        'stepId': evidence.stepId,
        'kind': evidence.kind.name.toUpperCase(),
        'captureTimeUtc': evidence.captureTimeUtc,
        'startLatitude': evidence.startLatitude,
        'startLongitude': evidence.startLongitude,
        'gpsAccuracyMeters': evidence.gpsAccuracyMeters,
        'exceptionReason': evidence.exceptionReason,
      },
      headers: _headers(),
    );
    final response = await _request(
      'POST',
      '/api/v1/evidence/${evidence.evidenceId}:finalize',
      body: {
        'locationSamples': evidence.locationSamples
            .map((s) => s.toJson())
            .toList(),
        'deviceInfo': {
          'platform': 'Android',
          'model': 'Handheld Field Terminal',
        },
      },
      headers: _headers(),
    );
    if (response is Map) {
      evidence.status = EvidenceStatus.verified;
      queue.updateStatus(evidence.evidenceId, EvidenceStatus.verified);
    }
    queue.markEvidenceSynced(evidence.evidenceId);
  }

  Future<void> submitEmergencyReport({
    required String reportId,
    required String sectionCode,
    required String kmPost,
    required double latitude,
    required double longitude,
    required String severity,
    required String hazardType,
    required String description,
  }) async {
    await _request(
      'POST',
      '/api/v1/emergency-reports',
      body: {
        'reportId': reportId,
        'sectionCode': sectionCode,
        'kmPost': kmPost,
        'latitude': latitude,
        'longitude': longitude,
        'severity': severity,
        'hazardType': hazardType,
        'description': description,
      },
      headers: _headers(),
    );
  }

  void _cachePossession(Map<String, dynamic> possession) {
    final id = possession['possessionId'];
    if (id is! String || id.isEmpty) return;
    final cached = queue.cachedPossessions
        .where((item) => item['possessionId'] != id)
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    cached.add(Map<String, dynamic>.from(possession));
    queue.setCachedPossessions(cached);
  }

  static Map<String, dynamic> _asMap(dynamic value) =>
      value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};

  static List<Map<String, dynamic>> _asMapList(dynamic value) => value is List
      ? value
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList()
      : <Map<String, dynamic>>[];

  static List<String> _asStringList(dynamic value) => value is List
      ? value.map((item) => item.toString()).toList()
      : <String>[];
}
