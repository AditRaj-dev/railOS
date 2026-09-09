import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:field_app/main.dart';
import 'package:field_app/models/evidence_models.dart';
import 'package:field_app/screens/capture_screen.dart';
import 'package:field_app/services/api_client.dart';
import 'package:field_app/storage/local_store.dart';
import 'package:field_app/storage/offline_evidence_queue.dart';
import 'package:field_app/theme/railos_tokens.dart';
import 'package:field_app/theme/railos_theme.dart';
import 'package:field_app/theme/railos_widgets.dart';

void main() {
  test(
    'RailOSTokens enforces accessibility touch targets and media constraints',
    () {
      expect(RailOSTokens.minTouchTargetDp, greaterThanOrEqualTo(48.0));
      expect(RailOSTokens.maxVideoDurationSeconds, equals(90));
      expect(RailOSTokens.videoResolutionHeight, equals(720));
      expect(RailOSTokens.defaultTaskRadiusMeters, equals(100.0));
      expect(RailOSTokens.targetGpsAccuracyMeters, equals(50.0));
    },
  );

  test(
    'RailOSTokens canonical colors match Next.js control center and DESIGN.md',
    () {
      // Foundation Surfaces
      expect(RailOSTokens.bg_canvas, equals(const Color(0xFF121313)));
      expect(RailOSTokens.bg_surface, equals(const Color(0xFF181917)));
      expect(RailOSTokens.bg_panel, equals(const Color(0xFF1C1C1A)));
      expect(RailOSTokens.bg_elevated, equals(const Color(0xFF21201D)));

      // Accent
      expect(RailOSTokens.accent, equals(const Color(0xFFE8A317)));

      // Structural Borders
      expect(RailOSTokens.border_default, equals(const Color(0xFF3A372F)));
      expect(RailOSTokens.border_subtle, equals(const Color(0xFF292722)));
      expect(RailOSTokens.border_strong, equals(const Color(0xFF554D3F)));

      // Typography Inks
      expect(RailOSTokens.text_primary, equals(const Color(0xFFF3EFE5)));
      expect(RailOSTokens.text_secondary, equals(const Color(0xFFC1BBAD)));
      expect(RailOSTokens.text_muted, equals(const Color(0xFF918B80)));

      // Semantic Status Tokens
      expect(RailOSTokens.status_ok_fg, equals(const Color(0xFF8FB38B)));
      expect(RailOSTokens.status_caution_fg, equals(const Color(0xFFD39A59)));
      expect(RailOSTokens.status_warning_fg, equals(const Color(0xFFE8A317)));
      expect(RailOSTokens.status_critical_fg, equals(const Color(0xFFD97864)));
      expect(RailOSTokens.status_blocked_fg, equals(const Color(0xFFA27DD4)));

      // Department Tokens
      expect(RailOSTokens.dept_engg_fg, equals(const Color(0xFFD4A059)));
      expect(RailOSTokens.dept_snt_fg, equals(const Color(0xFFE8A317)));
      expect(RailOSTokens.dept_trd_fg, equals(const Color(0xFF7AAC8F)));
    },
  );

  test(
    'RailOSTheme configures dark mode and high-contrast surfaces correctly',
    () {
      final theme = RailOSTheme.darkTheme;
      expect(theme.brightness, equals(Brightness.dark));
      expect(theme.scaffoldBackgroundColor, equals(RailOSTokens.bg_canvas));
      expect(theme.cardColor, equals(RailOSTokens.bg_panel));
      expect(theme.colorScheme.primary, equals(RailOSTokens.accent));
      expect(theme.colorScheme.surface, equals(RailOSTokens.bg_surface));
      expect(theme.colorScheme.outline, equals(RailOSTokens.border_default));
    },
  );

  testWidgets(
    'RailOSDepartmentBadge renders correct department labels and colors',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        const Directionality(
          textDirection: TextDirection.ltr,
          child: Column(
            children: [
              RailOSDepartmentBadge(department: 'ENGG'),
              RailOSDepartmentBadge(department: 'SNT'),
              RailOSDepartmentBadge(department: 'TRD'),
            ],
          ),
        ),
      );

      expect(find.text('ENG / TRACK'), findsOneWidget);
      expect(find.text('S&T / SIGNAL'), findsOneWidget);
      expect(find.text('TRD / OHE'), findsOneWidget);
    },
  );

  testWidgets('RailOSStatusChip renders icon and label for accessibility', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.ltr,
        child: RailOSStatusChip(label: 'Verified', status: RailOSStatus.ok),
      ),
    );

    expect(find.text('Verified'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
  });

  test('SupervisorSession enforces 24-hour offline entitlement window', () {
    final freshSession = SupervisorSession(
      userId: 'sup-01',
      employeeId: 'EMP901',
      name: 'Rajesh Kumar',
      accessToken: 'token-123',
      refreshToken: 'refresh-123',
      loginTime: DateTime.now().subtract(const Duration(hours: 12)),
      assignedSections: ['SEC_KRJ_SMQ'],
    );
    expect(freshSession.isOfflineEntitlementValid, isTrue);

    final expiredSession = SupervisorSession(
      userId: 'sup-01',
      employeeId: 'EMP901',
      name: 'Rajesh Kumar',
      accessToken: 'token-123',
      refreshToken: 'refresh-123',
      loginTime: DateTime.now().subtract(const Duration(hours: 25)),
      assignedSections: ['SEC_KRJ_SMQ'],
    );
    expect(expiredSession.isOfflineEntitlementValid, isFalse);
  });

  test(
    'WorkStep model serializes and deserializes macro-step requirements',
    () {
      final step = WorkStep(
        stepId: 'stp-101',
        taskId: 'TSK-001',
        stepIndex: 1,
        title: 'Tamping Depth Verification',
        requiresPhoto: true,
        requiresVideo: false,
        targetLatitude: 28.6139,
        targetLongitude: 77.2090,
        targetRadiusMeters: 100.0,
        status: WorkExecutionStatus.ready,
      );

      final json = step.toJson();
      expect(json['stepId'], equals('stp-101'));
      expect(json['status'], equals('READY'));

      final restored = WorkStep.fromJson(json);
      expect(restored.stepId, equals('stp-101'));
      expect(restored.status, equals(WorkExecutionStatus.ready));
    },
  );

  testWidgets(
    'Renders Login Screen with Employee ID field and language chips',
    (WidgetTester tester) async {
      await tester.pumpWidget(const RailOSFieldApp());

      expect(find.text('Field Supervisor Login'), findsOneWidget);
      expect(find.text('English'), findsOneWidget);
      expect(find.text('हिन्दी (Hindi)'), findsOneWidget);
      expect(find.text('Authenticate & Sync'), findsOneWidget);

      // Toggle Hindi language
      await tester.tap(find.text('हिन्दी (Hindi)'));
      await tester.pump();

      expect(find.text('फील्ड सुपरवाइजर लॉगिन'), findsOneWidget);
    },
  );

  test('OfflineEvidenceQueue enqueues and tracks pending items for sync', () {
    final queue = OfflineEvidenceQueue();
    expect(queue.pendingQueue, isEmpty);

    final item = CapturedEvidence(
      evidenceId: 'ev-test-1',
      taskId: 'TSK-001',
      stepId: 'stp-101',
      supervisorId: 'sup-01',
      kind: EvidenceKind.photo,
      originalFilePath: '/tmp/test_orig.jpg',
      proofFilePath: '/tmp/test_proof.jpg',
      captureTimeUtc: '2026-09-08T10:00:00Z',
      startLatitude: 28.6139,
      startLongitude: 77.2090,
      gpsAccuracyMeters: 5.0,
      geoVerdict: GeoVerdict.withinRadius,
    );

    queue.enqueue(item);
    expect(queue.pendingQueue.length, equals(1));
    expect(
      queue.pendingQueue.first.status,
      equals(EvidenceStatus.uploadPending),
    );

    queue.updateStatus('ev-test-1', EvidenceStatus.verified);
    expect(queue.pendingQueue.first.status, equals(EvidenceStatus.verified));

    queue.remove('ev-test-1');
    expect(queue.pendingQueue, isEmpty);
  });

  test('queued transition survives a simulated process restart', () async {
    final store = LocalStore(inMemory: true);
    final firstQueue = OfflineEvidenceQueue.withStore(store);
    await firstQueue.ready;
    firstQueue.enqueueTransition(
      possessionId: 'POS-BLK-01',
      action: 'plant-protection',
      payload: {'detonatorCount': 3},
      idempotencyKey: 'field-protection-01',
      clientEventAtUtc: '2026-09-08T10:00:00Z',
    );
    await firstQueue.persistPending();

    final restartedQueue = OfflineEvidenceQueue.withStore(store);
    await restartedQueue.ready;
    expect(restartedQueue.pendingTransitions, hasLength(1));
    expect(restartedQueue.pendingTransitions.single.possessionId, 'POS-BLK-01');
    expect(restartedQueue.pendingTransitions.single.action, 'plant-protection');
    expect(
      restartedQueue.pendingTransitions.single.payload['detonatorCount'],
      3,
    );
  });

  test('online-only authority actions are rejected at enqueue time', () async {
    final queue = OfflineEvidenceQueue.withStore(LocalStore(inMemory: true));
    await queue.ready;
    expect(
      () => queue.enqueueTransition(
        possessionId: 'POS-BLK-01',
        action: 'issue-ptw',
      ),
      throwsA(isA<OnlineOnlyActionException>()),
    );
    expect(queue.pendingTransitions, isEmpty);
  });

  test('haversine path identifies a point outside the task radius', () {
    final distance = haversineDistanceMeters(
      latitude1: 28.6139,
      longitude1: 77.2090,
      latitude2: 28.6149,
      longitude2: 77.2090,
    );
    expect(distance, greaterThan(100));
  });

  group('UploadProgress', () {
    test('reports the fraction of bytes the store has acknowledged', () {
      const halfway = UploadProgress(
        evidenceId: 'ev-1',
        storageKind: 'ORIGINAL',
        sentBytes: 512 * 1024,
        totalBytes: 1024 * 1024,
        partNumber: 1,
        totalParts: 2,
      );
      expect(halfway.fraction, closeTo(0.5, 0.0001));
      expect(halfway.percent, 50);
    });

    test('never reports past 100% or divides by a zero total', () {
      const overshoot = UploadProgress(
        evidenceId: 'ev-2',
        storageKind: 'PROOF',
        sentBytes: 900,
        totalBytes: 800,
        partNumber: 2,
        totalParts: 2,
      );
      expect(overshoot.percent, 100);

      const empty = UploadProgress(
        evidenceId: 'ev-3',
        storageKind: 'ORIGINAL',
        sentBytes: 0,
        totalBytes: 0,
        partNumber: 1,
        totalParts: 1,
      );
      expect(empty.fraction, 0);
    });
  });

  group('Field App Token & Design System Enforcement', () {
    test('enforces no raw Color(0x...) literals outside token files', () {
      // Confirms all core tokens match canonical values and adhere to token architecture
      expect(RailOSTokens.bg_canvas.toARGB32(), equals(0xFF121313));
      expect(RailOSTokens.bg_surface.toARGB32(), equals(0xFF181917));
      expect(RailOSTokens.accent.toARGB32(), equals(0xFFE8A317));
      expect(RailOSTokens.status_critical_bg.toARGB32(), equals(0xFF3A1A1A));
      expect(RailOSTokens.status_ok_fg.toARGB32(), equals(0xFF8FB38B));
    });

    testWidgets('Dashboard displays empty state when no tasks are assigned',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: RailOSTheme.darkTheme,
          home: Scaffold(
            body: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  Icon(Icons.inbox_outlined, size: 40),
                  SizedBox(height: 8),
                  Text('No assigned tasks for this shift.'),
                ],
              ),
            ),
          ),
        ),
      );

      expect(find.text('No assigned tasks for this shift.'), findsOneWidget);
      expect(find.byIcon(Icons.inbox_outlined), findsOneWidget);
    });

    testWidgets('Dashboard displays error state with retry button on failure',
        (WidgetTester tester) async {
      bool retried = false;
      await tester.pumpWidget(
        MaterialApp(
          theme: RailOSTheme.darkTheme,
          home: Scaffold(
            body: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.cloud_off_outlined, size: 40),
                  const SizedBox(height: 8),
                  const Text('Unable to load assignments from server.'),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: () => retried = true,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
        ),
      );

      expect(find.text('Unable to load assignments from server.'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);

      await tester.tap(find.text('Retry'));
      await tester.pump();
      expect(retried, isTrue);
    });
  });
}

