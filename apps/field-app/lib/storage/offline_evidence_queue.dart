import 'package:flutter/foundation.dart';
import '../models/evidence_models.dart';

class SupervisorSession {
  final String userId;
  final String employeeId;
  final String name;
  final String accessToken;
  final String refreshToken;
  final DateTime loginTime;
  final List<String> assignedSections;

  SupervisorSession({
    required this.userId,
    required this.employeeId,
    required this.name,
    required this.accessToken,
    required this.refreshToken,
    required this.loginTime,
    required this.assignedSections,
  });

  bool get isOfflineEntitlementValid {
    // 24-hour offline grace period allowed after login per spec
    final difference = DateTime.now().difference(loginTime);
    return difference.inHours < 24;
  }
}

class OfflineEvidenceQueue extends ChangeNotifier {
  static final OfflineEvidenceQueue _instance = OfflineEvidenceQueue._internal();
  factory OfflineEvidenceQueue() => _instance;
  OfflineEvidenceQueue._internal();

  SupervisorSession? _currentSession;
  final List<CapturedEvidence> _queue = [];
  final List<Map<String, dynamic>> _cachedTasks = [];

  SupervisorSession? get currentSession => _currentSession;
  List<CapturedEvidence> get pendingQueue => List.unmodifiable(_queue);
  List<Map<String, dynamic>> get cachedTasks => List.unmodifiable(_cachedTasks);

  void setSession(SupervisorSession session) {
    _currentSession = session;
    notifyListeners();
  }

  void clearSession() {
    _currentSession = null;
    notifyListeners();
  }

  void setCachedTasks(List<Map<String, dynamic>> tasks) {
    _cachedTasks.clear();
    _cachedTasks.addAll(tasks);
    notifyListeners();
  }

  void enqueue(CapturedEvidence evidence) {
    _queue.add(evidence);
    notifyListeners();
  }

  void updateStatus(String evidenceId, EvidenceStatus newStatus) {
    final idx = _queue.indexWhere((e) => e.evidenceId == evidenceId);
    if (idx != -1) {
      _queue[idx].status = newStatus;
      notifyListeners();
    }
  }

  void remove(String evidenceId) {
    _queue.removeWhere((e) => e.evidenceId == evidenceId);
    notifyListeners();
  }
}
