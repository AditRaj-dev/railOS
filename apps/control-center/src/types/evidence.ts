/**
 * TypeScript types for RailOS Geotagged Field-Evidence system.
 */

export type EvidenceKind = 'PHOTO' | 'VIDEO';

export type EvidenceStatus =
  | 'DRAFT'
  | 'UPLOAD_PENDING'
  | 'UPLOADING'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'FLAGGED_REVIEW'
  | 'ACCEPTED_EXCEPTION'
  | 'REJECTED';

export type GeoVerdict =
  | 'WITHIN_RADIUS'
  | 'OUTSIDE_RADIUS'
  | 'LOW_ACCURACY'
  | 'NO_FIX'
  | 'MOCKED_LOCATION'
  | 'CLOCK_DRIFT';

export type WorkExecutionStatus =
  | 'READY'
  | 'STARTED'
  | 'IN_PROGRESS'
  | 'PAUSED'
  | 'DELAYED'
  | 'CANNOT_COMPLETE'
  | 'COMPLETED_PENDING_EVIDENCE'
  | 'COMPLETED';

export interface GeoSample {
  timestampUtc: string;
  latitude: number;
  longitude: number;
  altitudeMeters?: number;
  accuracyMeters: number;
  speedMps?: number;
  isMocked?: boolean;
}

export interface EvidenceTargetSnapshot {
  latitude: number;
  longitude: number;
  radiusMeters: number;
  sectionCode: string;
  kmPost: string;
}

export interface EvidenceManifestV1 {
  manifestVersion: string;
  evidenceId: string;
  taskId: string;
  stepId: string;
  supervisorId: string;
  kind: EvidenceKind;
  captureStartTimeUtc: string;
  captureEndTimeUtc?: string;
  originalSha256: string;
  proofSha256: string;
  originalSizeBytes: number;
  proofSizeBytes: number;
  mediaProperties: Record<string, unknown>;
  targetLocation: EvidenceTargetSnapshot;
  locationSamples: GeoSample[];
  geoVerdict: GeoVerdict;
  distanceToTargetMeters?: number;
  exceptionReason?: string;
  deviceInfo: Record<string, unknown>;
  clientCreatedTimeUtc: string;
  signedAtUtc?: string;
  serverSignature?: string;
}

export interface EvidenceItem {
  evidenceId: string;
  taskId: string;
  stepId: string;
  supervisorId: string;
  kind: EvidenceKind;
  status: EvidenceStatus;
  originalStorageKey?: string;
  proofStorageKey?: string;
  originalSha256?: string;
  proofSha256?: string;
  originalSizeBytes?: number;
  proofSizeBytes?: number;
  captureTimeUtc: string;
  startLatitude: number;
  startLongitude: number;
  gpsAccuracyMeters: number;
  distanceToTargetMeters?: number;
  geoVerdict: GeoVerdict;
  exceptionReason?: string;
  reviewerId?: string;
  reviewNotes?: string;
  reviewedAt?: string;
  canonicalManifest?: EvidenceManifestV1;
  ed25519Signature?: string;
  originalDownloadUrl?: string;
  proofDownloadUrl?: string;
  createdTimeUtc?: string;
  updatedTimeUtc?: string;
}

export interface SupervisorRecord {
  userId: string;
  employeeId: string;
  name: string;
  email?: string;
  active: boolean;
  assignedSections: string[];
  createdAt?: string;
}
