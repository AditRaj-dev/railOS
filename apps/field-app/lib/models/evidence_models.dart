// Shared domain models matching the canonical RailOS evidence specification.

enum EvidenceKind { photo, video }

enum EvidenceStatus {
  draft,
  uploadPending,
  uploading,
  verifying,
  verified,
  flaggedReview,
  acceptedException,
  rejected,
}

enum GeoVerdict {
  withinRadius,
  outsideRadius,
  lowAccuracy,
  noFix,
  mockedLocation,
  clockDrift,
}

enum WorkExecutionStatus {
  ready,
  started,
  inProgress,
  paused,
  delayed,
  cannotComplete,
  completedPendingEvidence,
  completed,
}

class GeoSample {
  final String timestampUtc;
  final double latitude;
  final double longitude;
  final double? altitudeMeters;
  final double accuracyMeters;
  final double? speedMps;
  final bool isMocked;

  const GeoSample({
    required this.timestampUtc,
    required this.latitude,
    required this.longitude,
    this.altitudeMeters,
    required this.accuracyMeters,
    this.speedMps,
    this.isMocked = false,
  });

  Map<String, dynamic> toJson() => {
    'timestampUtc': timestampUtc,
    'latitude': latitude,
    'longitude': longitude,
    'altitudeMeters': altitudeMeters,
    'accuracyMeters': accuracyMeters,
    'speedMps': speedMps,
    'isMocked': isMocked,
  };

  factory GeoSample.fromJson(Map<String, dynamic> json) => GeoSample(
    timestampUtc: json['timestampUtc'] as String,
    latitude: (json['latitude'] as num).toDouble(),
    longitude: (json['longitude'] as num).toDouble(),
    altitudeMeters: (json['altitudeMeters'] as num?)?.toDouble(),
    accuracyMeters: (json['accuracyMeters'] as num).toDouble(),
    speedMps: (json['speedMps'] as num?)?.toDouble(),
    isMocked: json['isMocked'] as bool? ?? false,
  );
}

class WorkStep {
  final String stepId;
  final String taskId;
  final int stepIndex;
  final String title;
  final String description;
  final bool requiresPhoto;
  final bool requiresVideo;
  final double targetLatitude;
  final double targetLongitude;
  final double targetRadiusMeters;
  WorkExecutionStatus status;
  String? evidenceId;

  WorkStep({
    required this.stepId,
    required this.taskId,
    required this.stepIndex,
    required this.title,
    this.description = '',
    this.requiresPhoto = true,
    this.requiresVideo = false,
    required this.targetLatitude,
    required this.targetLongitude,
    this.targetRadiusMeters = 100.0,
    this.status = WorkExecutionStatus.ready,
    this.evidenceId,
  });

  Map<String, dynamic> toJson() => {
    'stepId': stepId,
    'taskId': taskId,
    'stepIndex': stepIndex,
    'title': title,
    'description': description,
    'requiresPhoto': requiresPhoto,
    'requiresVideo': requiresVideo,
    'targetLatitude': targetLatitude,
    'targetLongitude': targetLongitude,
    'targetRadiusMeters': targetRadiusMeters,
    'status': status.name.toUpperCase(),
    'evidenceId': evidenceId,
  };

  factory WorkStep.fromJson(Map<String, dynamic> json) => WorkStep(
    stepId: json['stepId'] as String,
    taskId: json['taskId'] as String,
    stepIndex: json['stepIndex'] as int,
    title: json['title'] as String,
    description: json['description'] as String? ?? '',
    requiresPhoto: json['requiresPhoto'] as bool? ?? true,
    requiresVideo: json['requiresVideo'] as bool? ?? false,
    targetLatitude: (json['targetLatitude'] as num).toDouble(),
    targetLongitude: (json['targetLongitude'] as num).toDouble(),
    targetRadiusMeters:
        (json['targetRadiusMeters'] as num?)?.toDouble() ?? 100.0,
    status: WorkExecutionStatus.values.firstWhere(
      (e) => e.name.toUpperCase() == (json['status'] as String? ?? 'READY'),
      orElse: () => WorkExecutionStatus.ready,
    ),
    evidenceId: json['evidenceId'] as String?,
  );
}

class CapturedEvidence {
  final String evidenceId;
  final String taskId;
  final String stepId;
  final String supervisorId;
  final EvidenceKind kind;
  EvidenceStatus status;
  final String originalFilePath;
  final String proofFilePath;
  String? originalSha256;
  String? proofSha256;
  final String captureTimeUtc;
  final double startLatitude;
  final double startLongitude;
  final double gpsAccuracyMeters;
  final double? distanceToTargetMeters;
  final GeoVerdict geoVerdict;
  final String? exceptionReason;
  final List<GeoSample> locationSamples;

  CapturedEvidence({
    required this.evidenceId,
    required this.taskId,
    required this.stepId,
    required this.supervisorId,
    required this.kind,
    this.status = EvidenceStatus.uploadPending,
    required this.originalFilePath,
    required this.proofFilePath,
    this.originalSha256,
    this.proofSha256,
    required this.captureTimeUtc,
    required this.startLatitude,
    required this.startLongitude,
    required this.gpsAccuracyMeters,
    this.distanceToTargetMeters,
    required this.geoVerdict,
    this.exceptionReason,
    this.locationSamples = const [],
  });

  factory CapturedEvidence.fromJson(Map<String, dynamic> json) =>
      CapturedEvidence(
        evidenceId: json['evidenceId'] as String,
        taskId: json['taskId'] as String,
        stepId: json['stepId'] as String,
        supervisorId: json['supervisorId'] as String? ?? '',
        kind: EvidenceKind.values.firstWhere(
          (value) =>
              value.name.toUpperCase() == (json['kind'] as String? ?? 'PHOTO'),
          orElse: () => EvidenceKind.photo,
        ),
        status: EvidenceStatus.values.firstWhere(
          (value) =>
              value.name.toUpperCase() ==
              (json['status'] as String? ?? 'UPLOAD_PENDING'),
          orElse: () => EvidenceStatus.uploadPending,
        ),
        originalFilePath: json['originalFilePath'] as String? ?? '',
        proofFilePath: json['proofFilePath'] as String? ?? '',
        originalSha256: json['originalSha256'] as String?,
        proofSha256: json['proofSha256'] as String?,
        captureTimeUtc: json['captureTimeUtc'] as String,
        startLatitude: (json['startLatitude'] as num).toDouble(),
        startLongitude: (json['startLongitude'] as num).toDouble(),
        gpsAccuracyMeters: (json['gpsAccuracyMeters'] as num).toDouble(),
        distanceToTargetMeters: (json['distanceToTargetMeters'] as num?)
            ?.toDouble(),
        geoVerdict: GeoVerdict.values.firstWhere(
          (value) =>
              value.name.toUpperCase() ==
              (json['geoVerdict'] as String? ?? 'NO_FIX'),
          orElse: () => GeoVerdict.noFix,
        ),
        exceptionReason: json['exceptionReason'] as String?,
        locationSamples: (json['locationSamples'] as List? ?? const [])
            .whereType<Map>()
            .map(
              (sample) => GeoSample.fromJson(Map<String, dynamic>.from(sample)),
            )
            .toList(),
      );

  Map<String, dynamic> toJson() => {
    'evidenceId': evidenceId,
    'taskId': taskId,
    'stepId': stepId,
    'supervisorId': supervisorId,
    'kind': kind.name.toUpperCase(),
    'status': status.name.toUpperCase(),
    'originalFilePath': originalFilePath,
    'proofFilePath': proofFilePath,
    'originalSha256': originalSha256,
    'proofSha256': proofSha256,
    'captureTimeUtc': captureTimeUtc,
    'startLatitude': startLatitude,
    'startLongitude': startLongitude,
    'gpsAccuracyMeters': gpsAccuracyMeters,
    'distanceToTargetMeters': distanceToTargetMeters,
    'geoVerdict': geoVerdict.name.toUpperCase(),
    'exceptionReason': exceptionReason,
    'locationSamples': locationSamples.map((s) => s.toJson()).toList(),
  };
}
