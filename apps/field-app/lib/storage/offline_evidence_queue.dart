import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

import '../models/evidence_models.dart';
import 'local_store.dart';

class SupervisorSession {
  final String userId;
  final String employeeId;
  final String name;
  final String accessToken;
  final String refreshToken;
  final DateTime loginTime;
  final List<String> assignedSections;
  final String role;
  final DateTime? offlineEntitlementExpiresAt;

  SupervisorSession({
    required this.userId,
    required this.employeeId,
    required this.name,
    required this.accessToken,
    required this.refreshToken,
    required this.loginTime,
    required this.assignedSections,
    this.role = 'FIELD_SUPERVISOR',
    this.offlineEntitlementExpiresAt,
  });

  /// The backend accepts the canonical role vocabulary at the authorization
  /// boundary. Older accounts still return SUPERVISOR, so normalize it here.
  String get normalizedRole {
    switch (role.trim().toUpperCase()) {
      case 'SUPERVISOR':
        return 'FIELD_SUPERVISOR';
      case 'DISPATCHER':
        return 'CONTROL_OFFICER';
      case 'INSPECTOR':
        return 'MANAGEMENT';
      default:
        return role.trim().toUpperCase();
    }
  }

  DateTime get entitlementExpiry =>
      (offlineEntitlementExpiresAt ?? loginTime.add(const Duration(hours: 24)))
          .toUtc();

  bool get isOfflineEntitlementValid =>
      DateTime.now().toUtc().isBefore(entitlementExpiry);

  SupervisorSession copyWith({
    String? userId,
    String? employeeId,
    String? name,
    String? accessToken,
    String? refreshToken,
    DateTime? loginTime,
    List<String>? assignedSections,
    String? role,
    DateTime? offlineEntitlementExpiresAt,
  }) => SupervisorSession(
    userId: userId ?? this.userId,
    employeeId: employeeId ?? this.employeeId,
    name: name ?? this.name,
    accessToken: accessToken ?? this.accessToken,
    refreshToken: refreshToken ?? this.refreshToken,
    loginTime: loginTime ?? this.loginTime,
    assignedSections: assignedSections ?? this.assignedSections,
    role: role ?? this.role,
    offlineEntitlementExpiresAt:
        offlineEntitlementExpiresAt ?? this.offlineEntitlementExpiresAt,
  );

  Map<String, dynamic> toJson() => {
    'userId': userId,
    'employeeId': employeeId,
    'name': name,
    'accessToken': accessToken,
    'refreshToken': refreshToken,
    'loginTime': loginTime.toUtc().toIso8601String(),
    'assignedSections': assignedSections,
    'role': normalizedRole,
    'offlineEntitlementExpiresAt': entitlementExpiry.toIso8601String(),
  };

  factory SupervisorSession.fromJson(Map<String, dynamic> json) =>
      SupervisorSession(
        userId: json['userId'] as String? ?? '',
        employeeId: json['employeeId'] as String? ?? '',
        name: json['name'] as String? ?? '',
        accessToken: json['accessToken'] as String? ?? '',
        refreshToken: json['refreshToken'] as String? ?? '',
        loginTime:
            DateTime.tryParse(json['loginTime'] as String? ?? '')?.toUtc() ??
            DateTime.now().toUtc(),
        assignedSections: (json['assignedSections'] as List? ?? const [])
            .map((value) => value.toString())
            .toList(),
        role: json['role'] as String? ?? 'FIELD_SUPERVISOR',
        offlineEntitlementExpiresAt: DateTime.tryParse(
          json['offlineEntitlementExpiresAt'] as String? ?? '',
        )?.toUtc(),
      );
}

class OnlineOnlyActionException implements Exception {
  final String action;
  final String message;

  const OnlineOnlyActionException(this.action, this.message);

  @override
  String toString() => message;
}

/// The actions that must never be delayed by an offline queue. These are live
/// authority assertions about the railway state and require an online server.
const Set<String> onlineOnlyPossessionActions = {
  'issue-ptw',
  'cancel-ptw',
  're-energise',
  'grant-clearance',
  'endorse-t351',
  'issue-t351',
  'certify-fitness',
  'station-close',
  'close',
  'cancel',
  'abandon',
};

bool isOnlineOnlyPossessionAction(String action) =>
    onlineOnlyPossessionActions.contains(action.trim().toLowerCase());

class OfflineEvidenceQueue extends ChangeNotifier {
  static final OfflineEvidenceQueue _instance = OfflineEvidenceQueue._internal(
    LocalStore(),
  );

  factory OfflineEvidenceQueue() => _instance;

  /// Creates an isolated queue, useful for a restart simulation or a test.
  /// Reusing the same [LocalStore] gives two queue instances the same durable
  /// backing store without changing the singleton used by the app.
  OfflineEvidenceQueue.withStore(LocalStore store) : _store = store {
    _restoreFuture = _restore();
  }

  OfflineEvidenceQueue._internal(this._store) {
    _restoreFuture = _restore();
  }

  final LocalStore _store;
  late final Future<void> _restoreFuture;
  StreamSubscription<ConnectivityResult>? _connectivitySubscription;
  Future<void> Function(CapturedEvidence evidence)? _syncEvidence;
  Future<void> Function(QueuedTransition transition)? _syncTransition;

  SupervisorSession? _currentSession;
  final List<CapturedEvidence> _queue = [];
  final List<QueuedTransition> _transitions = [];
  final List<Map<String, dynamic>> _cachedTasks = [];
  final List<Map<String, dynamic>> _cachedPossessions = [];
  bool _isFlushing = false;
  bool _restored = false;
  String? _lastSyncError;

  SupervisorSession? get currentSession => _currentSession;
  List<CapturedEvidence> get pendingQueue => List.unmodifiable(_queue);
  List<QueuedTransition> get pendingTransitions =>
      List.unmodifiable(_transitions);
  List<Map<String, dynamic>> get cachedTasks => List.unmodifiable(_cachedTasks);
  List<Map<String, dynamic>> get cachedPossessions =>
      List.unmodifiable(_cachedPossessions);
  String? get lastSyncError => _lastSyncError;
  Future<void> get ready => _restoreFuture;

  Future<void> initialize() async {
    await _restoreFuture;
    if (_connectivitySubscription != null) return;

    try {
      _connectivitySubscription = Connectivity().onConnectivityChanged.listen((
        result,
      ) {
        if (result != ConnectivityResult.none) unawaited(flush());
      });
      final result = await Connectivity().checkConnectivity();
      if (result != ConnectivityResult.none) unawaited(flush());
    } catch (_) {
      // Native connectivity is unavailable in widget tests and desktop
      // previews. Manual sync still works through the registered callbacks.
    }
  }

  Future<void> _restore() async {
    await _store.initialize();
    try {
      final session = await _store.loadSession();
      if (session != null)
        _currentSession = SupervisorSession.fromJson(session);

      final evidence = await _store.loadEvidence();
      for (final payload in evidence) {
        try {
          final item = CapturedEvidence.fromJson(payload);
          if (_queue.every(
            (existing) => existing.evidenceId != item.evidenceId,
          )) {
            _queue.add(item);
          }
        } catch (_) {
          // A malformed row must not prevent the rest of the field cache from
          // being restored. The server remains the source of truth.
        }
      }

      _transitions.addAll(await _store.loadTransitions());
      _cachedTasks.addAll(await _store.loadTasks());
      _cachedPossessions.addAll(await _store.loadPossessions());
    } catch (_) {
      // A cache read is best effort. The next online fetch will repopulate it.
    }
    _restored = true;
  }

  void attachSyncHandlers({
    required Future<void> Function(CapturedEvidence evidence) evidenceSync,
    required Future<void> Function(QueuedTransition transition) transitionSync,
  }) {
    _syncEvidence = evidenceSync;
    _syncTransition = transitionSync;
    unawaited(flush());
  }

  void setSession(SupervisorSession session) {
    _currentSession = session;
    unawaited(_store.saveSession(session.toJson()));
    notifyListeners();
  }

  void clearSession() {
    _currentSession = null;
    unawaited(_store.clearSession());
    notifyListeners();
  }

  void setCachedTasks(List<Map<String, dynamic>> tasks) {
    _cachedTasks
      ..clear()
      ..addAll(tasks.map((task) => Map<String, dynamic>.from(task)));
    unawaited(_store.saveTasks(_cachedTasks));
    notifyListeners();
  }

  void setCachedPossessions(List<Map<String, dynamic>> possessions) {
    _cachedPossessions
      ..clear()
      ..addAll(
        possessions.map((possession) => Map<String, dynamic>.from(possession)),
      );
    unawaited(_store.savePossessions(_cachedPossessions));
    notifyListeners();
  }

  void enqueue(CapturedEvidence evidence) {
    _queue.removeWhere((item) => item.evidenceId == evidence.evidenceId);
    _queue.add(evidence);
    unawaited(_store.saveEvidence(evidence.toJson()));
    notifyListeners();
  }

  /// Queue a field observation or physical act for replay. Authority actions
  /// are rejected before any row is written, with recovery guidance for the
  /// operator instead of a delayed server failure.
  void enqueueTransition({
    required String possessionId,
    required String action,
    Map<String, dynamic> payload = const <String, dynamic>{},
    String? idempotencyKey,
    String? clientEventAtUtc,
    bool offlineReplay = true,
  }) {
    final normalizedAction = action.trim().toLowerCase();
    if (isOnlineOnlyPossessionAction(normalizedAction)) {
      throw OnlineOnlyActionException(
        normalizedAction,
        '“$normalizedAction” needs live online authority. Reconnect before trying again; it was not queued.',
      );
    }

    final now = DateTime.now().toUtc();
    final transition = QueuedTransition(
      id: 'QTR-${now.microsecondsSinceEpoch}',
      possessionId: possessionId,
      action: normalizedAction,
      payload: Map<String, dynamic>.from(payload),
      idempotencyKey: idempotencyKey ?? 'field-${now.microsecondsSinceEpoch}',
      clientEventAtUtc: clientEventAtUtc ?? now.toIso8601String(),
      offlineReplay: offlineReplay,
    );
    _transitions.removeWhere(
      (item) => item.idempotencyKey == transition.idempotencyKey,
    );
    _transitions.add(transition);
    unawaited(_store.saveTransition(transition));
    notifyListeners();
  }

  void updateStatus(String evidenceId, EvidenceStatus newStatus) {
    final idx = _queue.indexWhere((e) => e.evidenceId == evidenceId);
    if (idx != -1) {
      _queue[idx].status = newStatus;
      unawaited(_store.saveEvidence(_queue[idx].toJson()));
      notifyListeners();
    }
  }

  /// Remove a row once the server accepted it. Synced rows must not grow
  /// without bound on a long-lived field handset.
  void markEvidenceSynced(String evidenceId) {
    _queue.removeWhere((item) => item.evidenceId == evidenceId);
    unawaited(_store.deleteEvidence(evidenceId));
    notifyListeners();
  }

  void remove(String evidenceId) => markEvidenceSynced(evidenceId);

  void removeTransition(String transitionId) {
    _transitions.removeWhere((item) => item.id == transitionId);
    unawaited(_store.deleteTransition(transitionId));
    notifyListeners();
  }

  /// Wait until the current in-memory snapshot has been written. Production
  /// callers normally do not need this; it is useful before a controlled
  /// process handoff and makes restart tests deterministic.
  Future<void> persistPending() async {
    await _restoreFuture;
    await Future.wait([
      ..._queue.map((item) => _store.saveEvidence(item.toJson())),
      ..._transitions.map(_store.saveTransition),
      if (_currentSession != null)
        _store.saveSession(_currentSession!.toJson()),
    ]);
  }

  Future<bool> _hasConnectivity() async {
    try {
      return await Connectivity().checkConnectivity() !=
          ConnectivityResult.none;
    } catch (_) {
      // If the platform cannot report connectivity, let the HTTP request make
      // the final determination. This is also what makes local tests useful.
      return true;
    }
  }

  Future<void> flush() async {
    await _restoreFuture;
    if (_isFlushing || !_restored || !_hasWork || !_hasHandlers) return;
    if (!await _hasConnectivity()) return;

    _isFlushing = true;
    try {
      _lastSyncError = null;
      for (final evidence in List<CapturedEvidence>.from(_queue)) {
        if (evidence.status != EvidenceStatus.uploadPending ||
            _syncEvidence == null)
          continue;
        try {
          await _syncEvidence!(evidence);
          // The callback may have marked it already; this is idempotent.
          if (_queue.any((item) => item.evidenceId == evidence.evidenceId)) {
            markEvidenceSynced(evidence.evidenceId);
          }
        } catch (error) {
          _lastSyncError = error.toString();
          break;
        }
      }

      for (final transition in List<QueuedTransition>.from(_transitions)) {
        if (_syncTransition == null) break;
        if (transition.nextAttemptAt != null &&
            transition.nextAttemptAt!.isAfter(DateTime.now().toUtc())) {
          continue;
        }
        try {
          await _syncTransition!(transition);
          removeTransition(transition.id);
        } catch (error) {
          transition.attempts += 1;
          transition.lastError = error.toString();
          final seconds = (1 << transition.attempts.clamp(0, 8).toInt()).clamp(
            2,
            300,
          );
          transition.nextAttemptAt = DateTime.now().toUtc().add(
            Duration(seconds: seconds),
          );
          unawaited(_store.saveTransition(transition));
          _lastSyncError = error.toString();
        }
      }
      notifyListeners();
    } finally {
      _isFlushing = false;
    }
  }

  bool get _hasWork =>
      _queue.any((item) => item.status == EvidenceStatus.uploadPending) ||
      _transitions.isNotEmpty;
  bool get _hasHandlers => _syncEvidence != null || _syncTransition != null;

  @override
  void dispose() {
    final subscription = _connectivitySubscription;
    if (subscription != null) unawaited(subscription.cancel());
    super.dispose();
  }
}
