import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:field_app/main.dart';
import 'package:field_app/models/evidence_models.dart';
import 'package:field_app/storage/offline_evidence_queue.dart';
import 'package:field_app/theme/railos_tokens.dart';
import 'package:field_app/theme/railos_theme.dart';
import 'package:field_app/theme/railos_widgets.dart';

void main() {
  test('RailOSTokens enforces accessibility touch targets and media constraints', () {
    expect(RailOSTokens.minTouchTargetDp, greaterThanOrEqualTo(48.0));
    expect(RailOSTokens.maxVideoDurationSeconds, equals(90));
    expect(RailOSTokens.videoResolutionHeight, equals(720));
    expect(RailOSTokens.defaultTaskRadiusMeters, equals(100.0));
    expect(RailOSTokens.targetGpsAccuracyMeters, equals(50.0));
  });

  test('RailOSTokens canonical colors match Next.js control center and DESIGN.md', () {
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
  });

  test('RailOSTheme configures dark mode and high-contrast surfaces correctly', () {
    final theme = RailOSTheme.darkTheme;
    expect(theme.brightness, equals(Brightness.dark));
    expect(theme.scaffoldBackgroundColor, equals(RailOSTokens.bg_canvas));
    expect(theme.cardColor, equals(RailOSTokens.bg_panel));
    expect(theme.colorScheme.primary, equals(RailOSTokens.accent));
    expect(theme.colorScheme.surface, equals(RailOSTokens.bg_surface));
    expect(theme.colorScheme.outline, equals(RailOSTokens.border_default));
  });

  testWidgets('RailOSDepartmentBadge renders correct department labels and colors',
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
  });

  testWidgets('RailOSStatusChip renders icon and label for accessibility',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.ltr,
        child: RailOSStatusChip(
          label: 'Verified',
          status: RailOSStatus.ok,
        ),
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

  test('WorkStep model serializes and deserializes macro-step requirements', () {
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
  });

  testWidgets('Renders Login Screen with Employee ID field and language chips',
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
  });

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
    expect(queue.pendingQueue.first.status, equals(EvidenceStatus.uploadPending));

    queue.updateStatus('ev-test-1', EvidenceStatus.verified);
    expect(queue.pendingQueue.first.status, equals(EvidenceStatus.verified));

    queue.remove('ev-test-1');
    expect(queue.pendingQueue, isEmpty);
  });
}
