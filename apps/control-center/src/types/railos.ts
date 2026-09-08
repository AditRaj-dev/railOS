export type Department = 'CIVIL' | 'S_AND_T' | 'TRD' | 'OPERATING';

export type DefectSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type PriorityBand = 'P0_EMERGENCY' | 'P1_SAFETY_CRITICAL' | 'P2_DEFERRED_RISK' | 'P3_ROUTINE';

export type BlockStatus = 'PLANNED' | 'REQUESTED' | 'APPROVED' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED' | 'REJECTED';

export type ObjectiveMode = 'SAFETY_FIRST' | 'BALANCED' | 'OPERATIONS_FIRST';

export interface Defect {
  id: string;
  code: string;
  department: Department;
  title: string;
  description: string;
  assetId: string;
  assetType: string;
  sectionId: string;
  locationKm: string;
  severity: DefectSeverity;
  riskScore: number;
  speedRestrictionKmph?: number;
  detectedAt: string;
  deadlineHours: number;
  isOverdue: boolean;
  blockRequired: boolean;
  requiredDurationMins: number;
}

export interface MaintenanceTask {
  id: string;
  taskCode: string;
  department: Department;
  title: string;
  assetId: string;
  assetName: string;
  sectionId: string;
  sectionName: string;
  trackId: 'UP' | 'DOWN' | 'BOTH';
  severity: DefectSeverity;
  riskScore: number;
  priorityBand: PriorityBand;
  priorityScore: number;
  dueDate: string;
  estimatedMinutes: number;
  blockRequirement: 'TRAFFIC' | 'POWER' | 'INTEGRATED' | 'NONE';
  status: 'PENDING' | 'BUNDLED' | 'IN_PROGRESS' | 'COMPLETED';
  crewRequired: number;
  specialMachine?: 'BCM' | 'CSM' | 'TOWER_WAGON' | 'UTV';
  isolationRequired: boolean;
  reasons: string[];
}

export interface CorridorSection {
  id: string;
  code: string;
  name: string;
  fromStation: string;
  toStation: string;
  distanceKm: number;
  tracks: number;
  electrified: boolean;
  capacityUtilizationPct: number;
  speedMaxKmph: number;
  healthScore: number;
  status: 'NORMAL' | 'CAUTION' | 'RESTRICTED' | 'BLOCK_ACTIVE';
  activeBlocksCount: number;
  criticalDefectsCount: number;
  pendingTasksCount: number;
  civilDefects: number;
  sandTDefects: number;
  trdDefects: number;
  description?: string;
}

export interface TrainMovement {
  id: string;
  trainNumber: string;
  trainName: string;
  type: 'PASSENGER_PREMIUM' | 'PASSENGER_EXPRESS' | 'SUBURBAN' | 'FREIGHT';
  sectionId: string;
  track: 'UP' | 'DOWN';
  scheduledEntry: string;
  scheduledExit: string;
  delayMinutes: number;
  priorityWeight: number;
  status: 'RUNNING' | 'REGULATED' | 'DIVERTED' | 'RESCHEDULED';
}

export interface BlockOpportunityWindow {
  id: string;
  sectionId: string;
  track: 'UP' | 'DOWN' | 'BOTH';
  startTime: string;
  endTime: string;
  durationMinutes: number;
  naturalGap: boolean;
  passengerTrainsImpacted: number;
  freightTrainsRegulated: number;
  confidenceScore: number;
}

export interface CandidateBlock {
  id: string;
  blockCode: string;
  sectionId: string;
  sectionName: string;
  track: 'UP' | 'DOWN' | 'BOTH';
  startTime: string;
  endTime: string;
  durationMinutes: number;
  type: 'TRAFFIC' | 'POWER' | 'INTEGRATED_SHADOW';
  departments: Department[];
  bundledTaskIds: string[];
  tasks: MaintenanceTask[];
  status: BlockStatus;
  utilizationRatePct: number;
  riskReductionScore: number;
  passengerDisruptionMins: number;
  freightDelaysMins: number;
  isolationProtocol: string;
  whyThisBlock: {
    bundlingEfficiency: string;
    gapExploitation: string;
    criticalRiskNeutralized: string;
    trainImpactMitigation: string;
    shadowPossessionBenefit: string;
  };
}

export interface PlanCandidate {
  id?: string;
  mode: ObjectiveMode;
  name: string;
  version: string;
  criticalTasksCompleted: number;
  totalTasksScheduled: number;
  unassignedTasksCount: number;
  trainDisruptionMinutes: number;
  maintenanceDebtReductionPct: number;
  averageBlockUtilizationPct: number;
  blocks: CandidateBlock[];
  recommendationNote: string;
}

export interface EmergencyScenario {
  id: string;
  defect: Defect;
  detectedAt: string;
  immediateAction: string;
  affectedBlockIds: string[];
  shiftedTaskIds: string[];
}
