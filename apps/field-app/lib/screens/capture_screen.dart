import 'dart:io';
import 'dart:math';
import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../models/evidence_models.dart';
import '../services/api_client.dart';
import '../services/evidence_processor.dart';
import '../theme/railos_tokens.dart';

double haversineDistanceMeters({
  required double latitude1,
  required double longitude1,
  required double latitude2,
  required double longitude2,
}) {
  const earthRadius = 6371000.0;
  final dLat = (latitude1 - latitude2) * (pi / 180.0);
  final dLon = (longitude1 - longitude2) * (pi / 180.0);
  final a =
      sin(dLat / 2) * sin(dLat / 2) +
      cos(latitude2 * (pi / 180.0)) *
          cos(latitude1 * (pi / 180.0)) *
          sin(dLon / 2) *
          sin(dLon / 2);
  final c = 2 * atan2(sqrt(a), sqrt(1 - a));
  return earthRadius * c;
}

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
  double _currentLat = 28.61392;
  double _currentLon = 77.20904;
  double _accuracyMeters = 8.5;
  int _fixAgeSeconds = 4;
  bool _isSimulatedFix = true;
  bool _isCaptured = false;
  bool _isProcessing = false;
  bool _isSubmitting = false;
  UploadProgress? _uploadProgress;
  String? _captureError;
  String? _exceptionReason;
  String? _capturedProofPath;
  String? _proofSha256;
  String? _evidenceId;

  @override
  void initState() {
    super.initState();
    _refreshFix();
  }

  Future<void> _refreshFix() async {
    final fix = await EvidenceProcessorService.currentFix();
    if (fix == null || !mounted) return;
    setState(() {
      _currentLat = fix.latitude;
      _currentLon = fix.longitude;
      _accuracyMeters = double.parse(fix.accuracyMeters.toStringAsFixed(1));
      _fixAgeSeconds = fix.fixAgeSeconds;
      _isSimulatedFix = false;
    });
  }

  double get _distanceToTarget {
    return haversineDistanceMeters(
      latitude1: _currentLat,
      longitude1: _currentLon,
      latitude2: widget.step.targetLatitude,
      longitude2: widget.step.targetLongitude,
    );
  }

  bool get _isWithinRadius =>
      _distanceToTarget <= widget.step.targetRadiusMeters;

  Future<void> _captureMedia() async {
    if (!_isWithinRadius &&
        (_exceptionReason == null || _exceptionReason!.isEmpty)) {
      final reason = await _promptExceptionReason();
      if (reason == null || reason.trim().isEmpty) return;
      _exceptionReason = reason;
    }

    setState(() {
      _isProcessing = true;
      _captureError = null;
    });

    final nowUtc = DateTime.now().toUtc().toIso8601String();
    final evId =
        'ev-${DateTime.now().millisecondsSinceEpoch}-${Random().nextInt(9999)}';
    _evidenceId = evId;

    final isVideo = !widget.step.requiresPhoto;
    final ext = isVideo ? 'mp4' : 'jpg';

    String? capturedPath;
    try {
      capturedPath = await EvidenceProcessorService.captureMedia(
        fileName: 'raw_$evId.$ext',
        isVideo: isVideo,
        maxSeconds: 90,
      );
    } on CapturePermissionDenied catch (e) {
      if (!mounted) return;
      setState(() {
        _isProcessing = false;
        _captureError = e.message;
      });
      return;
    }

    if (capturedPath == null) {
      if (mounted) setState(() => _isProcessing = false);
      return;
    }

    final proofPath =
        '${File(capturedPath).parent.path}${Platform.pathSeparator}proof_$evId.$ext';

    await _refreshFix();

    final session = widget.apiClient.queue.currentSession;
    final supervisorId = session?.userId ?? 'sup-01';

    final result = await EvidenceProcessorService.processPhotoProof(
      sourcePath: capturedPath,
      outputPath: proofPath,
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
      originalFilePath: capturedPath,
      proofFilePath: result.proofPath,
      originalSha256: result.originalSha256,
      proofSha256: result.proofSha256,
      captureTimeUtc: nowUtc,
      startLatitude: _currentLat,
      startLongitude: _currentLon,
      gpsAccuracyMeters: _accuracyMeters,
      distanceToTargetMeters: _distanceToTarget,
      geoVerdict: _isWithinRadius
          ? GeoVerdict.withinRadius
          : GeoVerdict.outsideRadius,
      exceptionReason: _exceptionReason,
      locationSamples: [
        GeoSample(
          timestampUtc: nowUtc,
          latitude: _currentLat,
          longitude: _currentLon,
          accuracyMeters: _accuracyMeters,
        ),
      ],
    );

    widget.apiClient.queue.enqueue(captured);

    setState(() {
      _isCaptured = true;
      _isProcessing = false;
      _capturedProofPath = result.proofPath;
      _proofSha256 = result.proofSha256;
    });
  }

  Future<void> _submitEvidence() async {
    final evidence = widget.apiClient.queue.pendingQueue.last;
    setState(() {
      _isSubmitting = true;
      _uploadProgress = null;
      _captureError = null;
    });

    String? error;
    try {
      await widget.apiClient.syncEvidence(
        evidence,
        onProgress: (progress) {
          if (mounted) setState(() => _uploadProgress = progress);
        },
      );
    } catch (e) {
      error = 'Upload failed — held in offline queue: $e';
    }

    if (!mounted) return;
    setState(() {
      _isSubmitting = false;
      _uploadProgress = null;
    });

    if (error != null) {
      setState(() => _captureError = error);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error),
          backgroundColor: RailOSTokens.status_critical_bg,
        ),
      );
    }
    if (!mounted) return;
    Navigator.pop(context, evidence);
  }

  /// Determinate bar while bytes are in flight: a field supervisor on a weak
  /// link needs to see the upload moving, not a spinner that could mean
  /// anything. Falls back to indeterminate before the first part reports.
  Widget _buildUploadProgress() {
    final progress = _uploadProgress;
    final label = progress == null
        ? 'Preparing upload…'
        : progress.totalParts > 1
        ? 'Uploading ${progress.percent}%  ·  part ${progress.partNumber} of ${progress.totalParts}'
        : 'Uploading ${progress.percent}%';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 12,
                  color: RailOSTokens.text_secondary,
                ),
              ),
              if (progress != null)
                Text(
                  '${(progress.sentBytes / 1024).round()} / ${(progress.totalBytes / 1024).round()} KB',
                  style: const TextStyle(
                    fontSize: 12,
                    color: RailOSTokens.text_muted,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
            child: LinearProgressIndicator(
              value: progress?.fraction,
              minHeight: 6,
              backgroundColor: RailOSTokens.bg_elevated,
              valueColor: const AlwaysStoppedAnimation<Color>(
                RailOSTokens.accent,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<String?> _promptExceptionReason() async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: RailOSTokens.bg_surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
          side: const BorderSide(color: RailOSTokens.border_default),
        ),
        title: const Row(
          children: [
            Icon(
              Icons.warning_amber_rounded,
              color: RailOSTokens.status_caution_fg,
              size: 20,
            ),
            SizedBox(width: 8),
            Text(
              'Out-of-Radius Capture',
              style: TextStyle(
                color: RailOSTokens.text_primary,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Current distance is ${_distanceToTarget.toStringAsFixed(1)}m (allowed radius: ${widget.step.targetRadiusMeters.toInt()}m).',
              style: const TextStyle(
                color: RailOSTokens.text_secondary,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              style: const TextStyle(
                color: RailOSTokens.text_primary,
                fontSize: 13,
              ),
              decoration: InputDecoration(
                hintText: AppStrings.get('exception_reason_prompt'),
                hintStyle: const TextStyle(
                  color: RailOSTokens.text_muted,
                  fontSize: 12,
                ),
                filled: true,
                fillColor: RailOSTokens.bg_panel,
              ),
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, null),
            child: const Text(
              'Cancel',
              style: TextStyle(color: RailOSTokens.text_muted),
            ),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: RailOSTokens.accent,
              foregroundColor: RailOSTokens.bg_canvas,
            ),
            onPressed: () => Navigator.pop(ctx, controller.text),
            child: const Text('Confirm Exception'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isFreshGps = _fixAgeSeconds <= 30;

    return Scaffold(
      backgroundColor: RailOSTokens.bg_canvas,
      appBar: AppBar(
        backgroundColor: RailOSTokens.bg_surface,
        title: Text(
          widget.step.requiresPhoto
              ? 'Live Step Photo'
              : 'Completion Video (<=90s)',
          style: const TextStyle(
            color: RailOSTokens.text_primary,
            fontSize: 14,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.2,
          ),
        ),
        iconTheme: const IconThemeData(color: RailOSTokens.text_secondary),
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Viewfinder Container
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  // Viewfinder area or captured proof preview
                  Container(
                    color: RailOSTokens.bg_canvas,
                    child:
                        _isCaptured &&
                            _capturedProofPath != null &&
                            File(_capturedProofPath!).existsSync()
                        ? Image.file(
                            File(_capturedProofPath!),
                            fit: BoxFit.contain,
                          )
                        : Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  widget.step.requiresPhoto
                                      ? Icons.camera_alt_outlined
                                      : Icons.videocam_outlined,
                                  size: 56,
                                  color: RailOSTokens.text_muted.withValues(
                                    alpha: 0.4,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  widget.step.requiresPhoto
                                      ? 'Live Camera Sensor'
                                      : 'Live Video Stream (720p)',
                                  style: const TextStyle(
                                    color: RailOSTokens.text_muted,
                                    fontSize: 13,
                                  ),
                                ),
                              ],
                            ),
                          ),
                  ),

                  // Top Status Pills: GPS Freshness & Distance Match
                  Positioned(
                    top: 14,
                    left: 14,
                    right: 14,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // Freshness pill
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: isFreshGps
                                ? RailOSTokens.status_ok_bg
                                : RailOSTokens.status_caution_bg,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: isFreshGps
                                  ? RailOSTokens.status_ok_border
                                  : RailOSTokens.status_caution_border,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                Icons.gps_fixed,
                                size: 13,
                                color: isFreshGps
                                    ? RailOSTokens.status_ok_fg
                                    : RailOSTokens.status_caution_fg,
                              ),
                              const SizedBox(width: 5),
                              Text(
                                '${_fixAgeSeconds}s ago (±${_accuracyMeters}m)',
                                style: TextStyle(
                                  color: isFreshGps
                                      ? RailOSTokens.status_ok_text
                                      : RailOSTokens.status_caution_text,
                                  fontSize: 11,
                                  fontFamily: 'monospace',
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),

                        // Radius match pill
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: _isWithinRadius
                                ? RailOSTokens.status_ok_bg
                                : RailOSTokens.status_warning_bg,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: _isWithinRadius
                                  ? RailOSTokens.status_ok_border
                                  : RailOSTokens.status_warning_border,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                _isWithinRadius
                                    ? Icons.check
                                    : Icons.warning_amber_rounded,
                                size: 13,
                                color: _isWithinRadius
                                    ? RailOSTokens.status_ok_fg
                                    : RailOSTokens.status_warning_fg,
                              ),
                              const SizedBox(width: 5),
                              Text(
                                _isWithinRadius
                                    ? '${_distanceToTarget.toStringAsFixed(1)}m Match'
                                    : '${_distanceToTarget.toStringAsFixed(1)}m Outside',
                                style: TextStyle(
                                  color: _isWithinRadius
                                      ? RailOSTokens.status_ok_text
                                      : RailOSTokens.status_warning_text,
                                  fontSize: 11,
                                  fontFamily: 'monospace',
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
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
                      decoration: const BoxDecoration(
                        color: RailOSTokens.evidenceStrip_overlayBg,
                        border: Border(
                          top: BorderSide(
                            color: RailOSTokens.border_default,
                            width: 1,
                          ),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(
                                Icons.verified_user_outlined,
                                color: RailOSTokens.accent,
                                size: 14,
                              ),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  'RAILOS PROOF // TASK: ${widget.step.taskId} | STEP: ${widget.step.stepId}',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: RailOSTokens.accent,
                                    fontFamily: 'monospace',
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'GPS: ${_currentLat.toStringAsFixed(5)}, ${_currentLon.toStringAsFixed(5)} (±${_accuracyMeters}m) | DIST: ${_distanceToTarget.toStringAsFixed(1)}m',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: RailOSTokens.text_secondary,
                              fontFamily: 'monospace',
                              fontSize: 10,
                            ),
                          ),
                          if (_isCaptured && _proofSha256 != null) ...[
                            const SizedBox(height: 3),
                            Text(
                              'PROOF SHA: ${_proofSha256!.substring(0, min(16, _proofSha256!.length))}... // ID: ${_evidenceId ?? 'PENDING'}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: RailOSTokens.text_muted,
                                fontFamily: 'monospace',
                                fontSize: 9,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Controls Bar
            Container(
              padding: const EdgeInsets.all(RailOSTokens.spacingMd),
              decoration: const BoxDecoration(
                color: RailOSTokens.bg_surface,
                border: Border(
                  top: BorderSide(color: RailOSTokens.border_default, width: 1),
                ),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (_captureError != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Text(
                        _captureError!,
                        style: const TextStyle(
                          color: RailOSTokens.status_critical_fg,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  if (_isSimulatedFix)
                    const Padding(
                      padding: EdgeInsets.only(bottom: 10),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.info_outline,
                            size: 13,
                            color: RailOSTokens.status_caution_fg,
                          ),
                          SizedBox(width: 5),
                          Text(
                            'Simulated GPS fix — grant location for a device fix',
                            style: TextStyle(
                              color: RailOSTokens.status_caution_fg,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                  if (_isSubmitting) _buildUploadProgress(),
                  _isCaptured
                      ? Row(
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
                                    foregroundColor: RailOSTokens.text_primary,
                                    side: const BorderSide(
                                      color: RailOSTokens.border_default,
                                    ),
                                  ),
                                  child: FittedBox(
                                    fit: BoxFit.scaleDown,
                                    child: Text(
                                      AppStrings.get('retake_btn'),
                                      maxLines: 1,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: SizedBox(
                                height: RailOSTokens.minTouchTargetDp,
                                child: ElevatedButton(
                                  onPressed: _isSubmitting
                                      ? null
                                      : _submitEvidence,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: RailOSTokens.accent,
                                    foregroundColor: RailOSTokens.bg_canvas,
                                    disabledBackgroundColor:
                                        RailOSTokens.bg_elevated,
                                  ),
                                  child: _isSubmitting
                                      ? const SizedBox(
                                          width: 18,
                                          height: 18,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            color: RailOSTokens.bg_canvas,
                                          ),
                                        )
                                      : FittedBox(
                                          fit: BoxFit.scaleDown,
                                          child: Text(
                                            AppStrings.get('submit_evidence'),
                                            maxLines: 1,
                                            style: const TextStyle(
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                ),
                              ),
                            ),
                          ],
                        )
                      : Center(
                          child: SizedBox(
                            width: 68,
                            height: 68,
                            child: FloatingActionButton(
                              elevation: 0,
                              backgroundColor: _isWithinRadius
                                  ? RailOSTokens.accent
                                  : RailOSTokens.status_caution_fg,
                              foregroundColor: RailOSTokens.bg_canvas,
                              onPressed: _isProcessing ? null : _captureMedia,
                              child: _isProcessing
                                  ? const SizedBox(
                                      width: 24,
                                      height: 24,
                                      child: CircularProgressIndicator(
                                        color: RailOSTokens.bg_canvas,
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : Icon(
                                      widget.step.requiresPhoto
                                          ? Icons.camera_alt_outlined
                                          : Icons.videocam_outlined,
                                      size: 30,
                                    ),
                            ),
                          ),
                        ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
