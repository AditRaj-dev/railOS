import 'dart:io';
import 'package:flutter/services.dart';

class EvidenceProcessorResult {
  final String originalSha256;
  final String proofSha256;
  final String proofPath;
  final int originalSizeBytes;
  final int proofSizeBytes;

  const EvidenceProcessorResult({
    required this.originalSha256,
    required this.proofSha256,
    required this.proofPath,
    required this.originalSizeBytes,
    required this.proofSizeBytes,
  });
}

/// A single GPS fix from the device.
class DeviceFix {
  final double latitude;
  final double longitude;
  final double altitude;
  final double accuracyMeters;
  final int fixAgeSeconds;

  const DeviceFix({
    required this.latitude,
    required this.longitude,
    required this.altitude,
    required this.accuracyMeters,
    required this.fixAgeSeconds,
  });
}

/// Raised when the operator declines the camera permission.
class CapturePermissionDenied implements Exception {
  final String message;
  const CapturePermissionDenied(this.message);
  @override
  String toString() => message;
}

class EvidenceProcessorService {
  static const MethodChannel _channel = MethodChannel(
    'in.gov.railos.field_app/evidence_processor',
  );

  /// Opens the system camera and writes [fileName] into the app's capture
  /// directory (chosen natively, since FileProvider can only share declared roots).
  /// Returns the written path, null when the operator cancels; throws
  /// [CapturePermissionDenied] when the camera permission is refused.
  static Future<String?> captureMedia({
    required String fileName,
    required bool isVideo,
    int maxSeconds = 90,
  }) async {
    try {
      final res = await _channel.invokeMethod<Map>(
        isVideo ? 'captureVideo' : 'capturePhoto',
        {'fileName': fileName, 'maxSeconds': maxSeconds},
      );
      return res?['path'] as String?;
    } on PlatformException catch (e) {
      if (e.code == 'PERMISSION_DENIED') {
        throw CapturePermissionDenied(e.message ?? 'Camera permission denied');
      }
      rethrow;
    } on MissingPluginException {
      return null; // desktop/unit-test runs have no native engine
    }
  }

  /// SHA-256 of a file on the handset, computed natively so a large video is
  /// never held in Dart memory. Null when the native engine is unavailable.
  static Future<String?> computeSha256(String filePath) async {
    try {
      final res = await _channel.invokeMethod<Map>('computeSha256', {
        'filePath': filePath,
      });
      return res?['sha256'] as String?;
    } on PlatformException {
      return null;
    } on MissingPluginException {
      return null;
    }
  }

  /// Returns the device's current fix, or null when location is denied/unavailable.
  static Future<DeviceFix?> currentFix({int timeoutMs = 8000}) async {
    try {
      final res = await _channel.invokeMethod<Map>('currentLocation', {
        'timeoutMs': timeoutMs,
      });
      if (res == null) return null;
      return DeviceFix(
        latitude: (res['latitude'] as num).toDouble(),
        longitude: (res['longitude'] as num).toDouble(),
        altitude: (res['altitude'] as num?)?.toDouble() ?? 0.0,
        accuracyMeters: (res['accuracyMeters'] as num).toDouble(),
        fixAgeSeconds: (res['fixAgeSeconds'] as num).toInt(),
      );
    } catch (_) {
      return null;
    }
  }

  /// Processes raw photo capture into an annotated proof copy with RailOS evidence strip
  /// and writes EXIF GPS metadata.
  static Future<EvidenceProcessorResult> processPhotoProof({
    required String sourcePath,
    required String outputPath,
    required String evidenceId,
    required String taskId,
    required String stepId,
    required String supervisorId,
    required String timestampUtc,
    required double latitude,
    required double longitude,
    double altitude = 0.0,
    required double accuracyMeters,
    required String geoVerdict,
    required double distanceMeters,
  }) async {
    try {
      final res = await _channel.invokeMethod<Map>('burnPhotoOverlay', {
        'sourcePath': sourcePath,
        'outputPath': outputPath,
        'evidenceId': evidenceId,
        'taskId': taskId,
        'stepId': stepId,
        'supervisorId': supervisorId,
        'timestampUtc': timestampUtc,
        'latitude': latitude,
        'longitude': longitude,
        'altitude': altitude,
        'accuracyMeters': accuracyMeters,
        'geoVerdict': geoVerdict,
        'distanceMeters': distanceMeters,
      });

      if (res != null) {
        return EvidenceProcessorResult(
          originalSha256: res['originalSha256'] as String,
          proofSha256: res['proofSha256'] as String,
          proofPath: res['proofPath'] as String,
          originalSizeBytes: (res['originalSizeBytes'] as num).toInt(),
          proofSizeBytes: (res['proofSizeBytes'] as num).toInt(),
        );
      }
    } catch (_) {
      // Fallback for mock/test runs without native Android engine
    }

    // Fallback for unit tests, desktop preview, and a native overlay pass
    // that failed. It used to hand back outputPath -- a watermarked file that
    // was never written -- plus placeholder digests, so the upload then died
    // on a file that did not exist and would have attested a false hash.
    // Point the proof at the original instead: no phantom file, and the
    // caller can see the two paths are the same and skip the second upload.
    final srcFile = File(sourcePath);
    final size = await srcFile.exists() ? await srcFile.length() : 0;
    return EvidenceProcessorResult(
      originalSha256: '',
      proofSha256: '',
      proofPath: sourcePath,
      originalSizeBytes: size,
      proofSizeBytes: size,
    );
  }
}
