import 'dart:convert';
import 'dart:io';
import '../models/evidence_models.dart';
import '../storage/offline_evidence_queue.dart';

class RailOSApiClient {
  final String baseUrl;
  final OfflineEvidenceQueue queue = OfflineEvidenceQueue();

  // ponytail: 10.0.2.2 = emulator host loopback; physical device uses `adb reverse tcp:8000 tcp:8000`
  // plus --dart-define=RAILOS_API_BASE=http://127.0.0.1:8000
  static const _defaultBase = String.fromEnvironment('RAILOS_API_BASE', defaultValue: 'http://10.0.2.2:8000');

  RailOSApiClient({String? baseUrl}) : baseUrl = baseUrl ?? _defaultBase;

  String? get _token => queue.currentSession?.accessToken;

  Map<String, String> _headers() => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
        'X-RailOS-Role': 'FIELD_SUPERVISOR',
      };

  Future<SupervisorSession> login(String employeeId, String password) async {
    final client = HttpClient();
    try {
      final req = await client.postUrl(Uri.parse('$baseUrl/api/v1/auth/login'));
      req.headers.contentType = ContentType.json;
      req.write(jsonEncode({'employeeId': employeeId, 'password': password}));
      final resp = await req.close();
      final body = await resp.transform(utf8.decoder).join();

      if (resp.statusCode == 200) {
        final data = jsonDecode(body) as Map<String, dynamic>;
        final session = SupervisorSession(
          userId: data['userId'] as String,
          employeeId: data['employeeId'] as String,
          name: data['name'] as String,
          accessToken: data['accessToken'] as String,
          refreshToken: data['refreshToken'] as String,
          loginTime: DateTime.now(),
          assignedSections: ['SEC_KRJ_SMQ', 'GZB-ALJN'],
        );
        queue.setSession(session);
        return session;
      } else {
        throw Exception('Login failed (${resp.statusCode}): $body');
      }
    } finally {
      client.close();
    }
  }

  Future<List<Map<String, dynamic>>> fetchMyAssignments() async {
    final client = HttpClient();
    try {
      final req = await client.getUrl(Uri.parse('$baseUrl/api/v1/work/assignments/mine'));
      _headers().forEach((k, v) => req.headers.set(k, v));
      final resp = await req.close();
      final body = await resp.transform(utf8.decoder).join();

      if (resp.statusCode == 200) {
        final data = jsonDecode(body) as Map<String, dynamic>;
        final tasks = (data['tasks'] as List).cast<Map<String, dynamic>>();
        queue.setCachedTasks(tasks);
        return tasks;
      }
    } catch (_) {
      // Return cached tasks if offline
      if (queue.cachedTasks.isNotEmpty) {
        return queue.cachedTasks;
      }
    } finally {
      client.close();
    }

    // Default demo task if no network and no cache
    return [
      {
        'taskId': 'TSK-0001',
        'title': 'Plain Track Tamping & Deep Ballast Inspection',
        'corridorId': 'GZB-ALJN',
        'department': 'ENGG',
        'status': 'STARTED',
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
          }
        ]
      }
    ];
  }

  Future<void> syncEvidence(CapturedEvidence evidence) async {
    final client = HttpClient();
    try {
      // 1. Post evidence record
      final createReq = await client.postUrl(Uri.parse('$baseUrl/api/v1/evidence'));
      _headers().forEach((k, v) => createReq.headers.set(k, v));
      createReq.write(jsonEncode({
        'evidenceId': evidence.evidenceId,
        'taskId': evidence.taskId,
        'stepId': evidence.stepId,
        'kind': evidence.kind.name.toUpperCase(),
        'captureTimeUtc': evidence.captureTimeUtc,
        'startLatitude': evidence.startLatitude,
        'startLongitude': evidence.startLongitude,
        'gpsAccuracyMeters': evidence.gpsAccuracyMeters,
        'exceptionReason': evidence.exceptionReason,
      }));
      await createReq.close();

      // 2. Finalize verification
      final finReq = await client.postUrl(Uri.parse('$baseUrl/api/v1/evidence/${evidence.evidenceId}:finalize'));
      _headers().forEach((k, v) => finReq.headers.set(k, v));
      finReq.write(jsonEncode({
        'locationSamples': evidence.locationSamples.map((s) => s.toJson()).toList(),
        'deviceInfo': {'platform': 'Android', 'model': 'Handheld Field Terminal'},
      }));
      final finResp = await finReq.close();

      if (finResp.statusCode == 202) {
        evidence.status = EvidenceStatus.verified;
        queue.updateStatus(evidence.evidenceId, EvidenceStatus.verified);
      }
    } finally {
      client.close();
    }
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
    final client = HttpClient();
    try {
      final req = await client.postUrl(Uri.parse('$baseUrl/api/v1/emergency-reports'));
      _headers().forEach((k, v) => req.headers.set(k, v));
      req.write(jsonEncode({
        'reportId': reportId,
        'sectionCode': sectionCode,
        'kmPost': kmPost,
        'latitude': latitude,
        'longitude': longitude,
        'severity': severity,
        'hazardType': hazardType,
        'description': description,
      }));
      final resp = await req.close();
      if (resp.statusCode != 200) {
        throw Exception('Failed to submit emergency report: ${resp.statusCode}');
      }
    } finally {
      client.close();
    }
  }
}
