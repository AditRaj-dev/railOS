import 'dart:math';
import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../models/evidence_models.dart';
import '../services/api_client.dart';
import '../services/evidence_processor.dart';
import '../theme/railos_tokens.dart';

class CaptureScreen extends StatefulWidget {
  final Map<String, dynamic> task;
  final WorkStep step;
  final RailOSApiClient apiClient;

  const CaptureScreen({
    super.key,
    required this.task,
    required this.step,
    required this.apiClient,
  });

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  // GPS State (simulated fresh fix)
  double _currentLat = 28.61392;
  double _currentLon = 77.20904;
  double _accuracyMeters = 8.5;
  int _fixAgeSeconds = 4;
  bool _isCaptured = false;
  bool _isProcessing = false;
  String? _exceptionReason;
  String? _capturedProofPath;
  String? _originalSha256;
  String? _proofSha256;
  String? _evidenceId;

  double get _distanceToTarget {
    // Haversine
    const earthRadius = 6371000.0;
    final dLat = (_currentLat - widget.step.targetLatitude) * (pi / 180.0);
    final dLon = (_currentLon - widget.step.targetLongitude) * (pi / 180.0);
    final a = sin(dLat / 2) * sin(dLat / 2) +
        cos(widget.step.targetLatitude * (pi / 180.0)) *
            cos(_currentLat * (pi / 180.0)) *
            sin(dLon / 2) *
            sin(dLon / 2);
    final c = 2 * atan2(sqrt(a), sqrt(1 - a));
    return earthRadius * c;
  }

  bool get _isWithinRadius => _distanceToTarget <= widget.step.targetRadiusMeters;

  Future<void> _captureMedia() async {
    if (!_isWithinRadius && (_exceptionReason == null || _exceptionReason!.isEmpty)) {
      final reason = await _promptExceptionReason();
      if (reason == null || reason.trim().isEmpty) return;
      _exceptionReason = reason;
    }

    setState(() => _isProcessing = true);

    final nowUtc = DateTime.now().toUtc().toIso8601String();
    final evId = 'ev-${DateTime.now().millisecondsSinceEpoch}-${Random().nextInt(9999)}';
    _evidenceId = evId;

    final session = widget.apiClient.queue.currentSession;
    final supervisorId = session?.userId ?? 'sup-01';

    // Process via EvidenceProcessorService
    final result = await EvidenceProcessorService.processPhotoProof(
      sourcePath: '/tmp/cam_raw_$evId.jpg',
      outputPath: '/tmp/cam_proof_$evId.jpg',
      evidenceId: evId,
      taskId: widget.step.taskId,
      stepId: widget.step.stepId,
      supervisorId: supervisorId,
      timestampUtc: nowUtc,
      latitude: _currentLat,
      longitude: _currentLon,
      accuracyMeters: _accuracyMeters,
      geoVerdict: _isWithinRadius ? 'WITHIN_RADIUS' : 'OUTSIDE_RADIUS',
      distanceMeters: _distanceToTarget,
    );

    final captured = CapturedEvidence(
      evidenceId: evId,
      taskId: widget.step.taskId,
      stepId: widget.step.stepId,
      supervisorId: supervisorId,
      kind: widget.step.requiresPhoto ? EvidenceKind.photo : EvidenceKind.video,
      originalFilePath: '/tmp/cam_raw_$evId.jpg',
      proofFilePath: result.proofPath,
      originalSha256: result.originalSha256,
      proofSha256: result.proofSha256,
      captureTimeUtc: nowUtc,
      startLatitude: _currentLat,
      startLongitude: _currentLon,
      gpsAccuracyMeters: _accuracyMeters,
      distanceToTargetMeters: _distanceToTarget,
      geoVerdict: _isWithinRadius ? GeoVerdict.withinRadius : GeoVerdict.outsideRadius,
      exceptionReason: _exceptionReason,
      locationSamples: [
        GeoSample(
          timestampUtc: nowUtc,
          latitude: _currentLat,
          longitude: _currentLon,
          accuracyMeters: _accuracyMeters,
        )
      ],
    );

    widget.apiClient.queue.enqueue(captured);

    setState(() {
      _isCaptured = true;
      _isProcessing = false;
      _capturedProofPath = result.proofPath;
      _originalSha256 = result.originalSha256;
      _proofSha256 = result.proofSha256;
    });
  }

  Future<String?> _promptExceptionReason() async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: RailOSTokens.bg_darkSurface,
        title: const Row(
          children: [
            Icon(Icons.warning, color: Colors.amberAccent),
            SizedBox(width: 8),
            Text('Out-of-Radius Capture', style: TextStyle(color: Colors.white, fontSize: 16)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Current distance is ${_distanceToTarget.toStringAsFixed(1)}m (allowed radius: ${widget.step.targetRadiusMeters.toInt()}m).',
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: AppStrings.get('exception_reason_prompt'),
                hintStyle: const TextStyle(color: Colors.white38),
                filled: true,
                fillColor: RailOSTokens.bg_darkRoot,
                border: const OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, null),
            child: const Text('Cancel', style: TextStyle(color: Colors.white54)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.amber.shade700),
            onPressed: () => Navigator.pop(ctx, controller.text),
            child: const Text('Confirm Exception', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: Text(
          widget.step.requiresPhoto ? 'Live Step Photo' : 'Completion Video (<=90s)',
          style: const TextStyle(color: Colors.white, fontSize: 15),
        ),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Viewfinder Container
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  // Viewfinder Mock (disabled gallery imports, live feed only)
                  Container(
                    color: RailOSTokens.bg_darkSurface,
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            widget.step.requiresPhoto ? Icons.camera : Icons.videocam,
                            size: 64,
                            color: Colors.white24,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            widget.step.requiresPhoto ? 'Live Camera Sensor' : 'Live Video Stream (720p)',
                            style: const TextStyle(color: Colors.white38, fontSize: 13),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Top Pill: GPS Freshness & Distance Match
                  Positioned(
                    top: 16,
                    left: 16,
                    right: 16,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // Freshness pill
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: _fixAgeSeconds <= 30
                                ? RailOSTokens.status_verified_bg
                                : RailOSTokens.status_caution_bg,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: _fixAgeSeconds <= 30
                                  ? RailOSTokens.status_verified_border
                                  : RailOSTokens.status_caution_border,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                Icons.gps_fixed,
                                size: 14,
                                color: _fixAgeSeconds <= 30 ? Colors.greenAccent : Colors.amberAccent,
                              ),
                              const SizedBox(width: 6),
                              Text(
                                '${_fixAgeSeconds}s ago (±${_accuracyMeters}m)',
                                style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ],
                          ),
                        ),

                        // Radius pill
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: _isWithinRadius
                                ? RailOSTokens.status_verified_bg
                                : RailOSTokens.status_flagged_bg,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: _isWithinRadius
                                  ? RailOSTokens.status_verified_border
                                  : RailOSTokens.status_flagged_border,
                            ),
                          ),
                          child: Text(
                            _isWithinRadius
                                ? '${_distanceToTarget.toStringAsFixed(1)}m Match'
                                : '${_distanceToTarget.toStringAsFixed(1)}m Outside',
                            style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Bottom Viewfinder Overlay Strip (Live Watermark Preview)
                  Positioned(
                    bottom: 0,
                    left: 0,
                    right: 0,
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      color: Colors.black.withOpacity(0.85),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.verified_user, color: Colors.cyanAccent, size: 14),
                              const SizedBox(width: 6),
                              Text(
                                'RAILOS PROOF // TASK: ${widget.step.taskId} | STEP: ${widget.step.stepId}',
                                style: const TextStyle(
                                  color: Colors.cyanAccent,
                                  fontFamily: 'monospace',
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'GPS: ${_currentLat.toStringAsFixed(5)}, ${_currentLon.toStringAsFixed(5)} (±${_accuracyMeters}m) | DIST: ${_distanceToTarget.toStringAsFixed(1)}m',
                            style: const TextStyle(
                              color: Colors.white,
                              fontFamily: 'monospace',
                              fontSize: 10,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Controls Bar
            Container(
              padding: const EdgeInsets.all(RailOSTokens.spacingLg),
              color: RailOSTokens.bg_darkSurface,
              child: _isCaptured
                  ? Column(
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: SizedBox(
                                height: RailOSTokens.minTouchTargetDp,
                                child: OutlinedButton(
                                  onPressed: () {
                                    setState(() {
                                      _isCaptured = false;
                                      _exceptionReason = null;
                                    });
                                  },
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: Colors.white,
                                    side: const BorderSide(color: Colors.white38),
                                  ),
                                  child: Text(AppStrings.get('retake_btn')),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: SizedBox(
                                height: RailOSTokens.minTouchTargetDp,
                                child: ElevatedButton(
                                  onPressed: () {
                                    Navigator.pop(
                                      context,
                                      widget.apiClient.queue.pendingQueue.last,
                                    );
                                  },
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: RailOSTokens.primary_railBlue,
                                  ),
                                  child: Text(AppStrings.get('submit_evidence')),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    )
                  : Center(
                      child: SizedBox(
                        width: 72,
                        height: 72,
                        child: FloatingActionButton(
                          backgroundColor: _isWithinRadius
                              ? RailOSTokens.primary_railBlue
                              : Colors.amber.shade700,
                          onPressed: _isProcessing ? null : _captureMedia,
                          child: _isProcessing
                              ? const CircularProgressIndicator(color: Colors.white)
                              : Icon(
                                  widget.step.requiresPhoto ? Icons.camera : Icons.videocam,
                                  size: 32,
                                  color: Colors.white,
                                ),
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
