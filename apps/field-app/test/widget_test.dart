import 'package:flutter_test/flutter_test.dart';
import 'package:field_app/main.dart';
import 'package:field_app/models/evidence_models.dart';
import 'package:field_app/storage/offline_evidence_queue.dart';
import 'package:field_app/theme/railos_tokens.dart';

void main() {
  test('RailOSTokens enforces accessibility touch targets and media constraints', () {
    expect(RailOSTokens.minTouchTargetDp, greaterThanOrEqualTo(48.0));
    expect(RailOSTokens.maxVideoDurationSeconds, equals(90));
    expect(RailOSTokens.videoResolutionHeight, equals(720));
    expect(RailOSTokens.defaultTaskRadiusMeters, equals(100.0));
    expect(RailOSTokens.targetGpsAccuracyMeters, equals(50.0));
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

