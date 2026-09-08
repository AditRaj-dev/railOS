import { create } from 'zustand';
import {
  CorridorSection,
  MaintenanceTask,
  TrainMovement,
  PlanCandidate,
  ObjectiveMode,
  CandidateBlock,
  EmergencyScenario
} from '../types/railos';
import {
  mockCorridorSections,
  mockMaintenanceTasks,
  mockTrainMovements,
  mockPlanCandidates
} from '../data/mockData';

export type UserRole =
  | 'ADMIN'
  | 'CONTROL_OFFICER'
  | 'PLANNER'
  | 'ENGINEERING'
  | 'SIGNAL_TELECOM'
  | 'TRACTION'
  | 'FIELD_SUPERVISOR'
  | 'MANAGEMENT'
  | 'STATION_MASTER'
  | 'TPC';
type DrawerType = 'block' | 'task' | 'section' | 'plan' | 'alerts' | null;

interface RailOSStore {
  // ===== UI STATE ONLY =====

  // Territory Selection (for URL params & filtering)
  selectedZone: string;
  selectedDivision: string;
  selectedSection: string;
  setSelectedZone: (zone: string) => void;
  setSelectedDivision: (division: string) => void;
  setSelectedSection: (section: string) => void;

  // Selected Objects for Inspector / Drawer
  selectedSectionId: string | null;
  selectedTaskId: string | null;
  selectedBlockId: string | null;
  setSelectedSectionId: (id: string | null) => void;
  setSelectedTaskId: (id: string | null) => void;
  setSelectedBlockId: (id: string | null) => void;

  // Context Rail / Drawer State
  activeDrawer: DrawerType;
  setActiveDrawer: (drawer: DrawerType) => void;

  // Map & Viewport State
  mapMode: 'GEOGRAPHIC' | 'SCHEMATIC';
  setMapMode: (mode: 'GEOGRAPHIC' | 'SCHEMATIC') => void;
  visibleLayers: Record<string, boolean>;
  toggleLayer: (layerId: string) => void;

  // User & Role Management
  userRole: UserRole;
  setUserRole: (role: UserRole) => void;

  // SHIM: setActiveScreen (synthetic mode; routes now handle navigation)
  // Kept for backward compatibility with view components that may call it.
  activeScreen?: 'COMMAND_CENTER' | 'NETWORK' | 'MAINTENANCE' | 'BLOCK_PLANNER' | 'TIMELINE' | 'PLAN_COMPARISON' | 'ANALYTICS' | 'FIELD_PWA';
  setActiveScreen: (screen: string) => void;

  // Transient Workflow State (for synthetic mode)
  isGeneratingPlan: boolean;
  plannerStage: string;
  setIsGeneratingPlan: (generating: boolean) => void;
  setPlannerStage: (stage: string) => void;

  // Emergency State (transient workflow)
  emergencyState: EmergencyScenario | null;
  isEmergencyActive: boolean;
  setEmergencyState: (state: EmergencyScenario | null) => void;
  setIsEmergencyActive: (active: boolean) => void;

  // Field PWA State (UI state)
  fieldTaskStatus: Record<string, 'READY' | 'START' | 'DELAY' | 'COMPLETED'>;
  updateFieldTaskStatus: (taskId: string, status: 'READY' | 'START' | 'DELAY' | 'COMPLETED') => void;

  // ===== SYNTHETIC DATA MODE (fixtures-only) =====
  // These keep existing view components working in synthetic mode only.
  // Server data (from React Query) should come from @/lib/queries.

  // SHIM: sections (synthetic mode only; real data from queries)
  sections: CorridorSection[];

  // SHIM: tasks (synthetic mode only; real data from queries)
  tasks: MaintenanceTask[];

  // SHIM: trains (synthetic mode only; real data from queries)
  trains: TrainMovement[];

  // SHIM: candidates (synthetic mode only; real data from queries)
  candidates: PlanCandidate[];
  selectedMode: ObjectiveMode;
  activePlan: PlanCandidate;

  // SHIM: approvedCandidate (synthetic mode; real mutations from queries)
  approvedCandidate: PlanCandidate | null;

  // ===== SYNTHETIC MODE ACTIONS (to be replaced by React Query) =====
  generatePlan: (mode: ObjectiveMode) => void;
  setSelectedMode: (mode: ObjectiveMode) => void;
  approvePlan: (candidate: PlanCandidate) => void;
  triggerEmergencyFlaw: () => void;
  replanEmergency: () => void;
  dismissEmergency: () => void;
  resetToDefault: () => void;
}

export const useRailOSStore = create<RailOSStore>((set, get) => ({
  // Territory Selection
  selectedZone: 'NCR',
  selectedDivision: 'Delhi',
  selectedSection: 'GZB-ALJN',
  setSelectedZone: (zone) => set({ selectedZone: zone }),
  setSelectedDivision: (division) => set({ selectedDivision: division }),
  setSelectedSection: (section) => set({ selectedSection: section }),

  // Selected Objects
  selectedSectionId: 'sec-krj-aljn',
  selectedTaskId: 'tsk-01',
  selectedBlockId: 'blk-rec-01',
  setSelectedSectionId: (id) => set({ selectedSectionId: id }),
  setSelectedTaskId: (id) => set({ selectedTaskId: id }),
  setSelectedBlockId: (id) => set({ selectedBlockId: id }),

  // Context Rail / Drawer
  activeDrawer: null,
  setActiveDrawer: (drawer) => set({ activeDrawer: drawer }),

  // Map & Viewport
  mapMode: 'GEOGRAPHIC',
  setMapMode: (mode) => set({ mapMode: mode }),
  visibleLayers: {
    tracks: true,
    blocks: true,
    defects: true,
    trains: true,
    maintenance: true,
    restrictions: true,
  },
  toggleLayer: (layerId) => {
    set(state => ({
      visibleLayers: {
        ...state.visibleLayers,
        [layerId]: !state.visibleLayers[layerId]
      }
    }));
  },

  // User & Role
  // Synthetic mode starts as the Section Controller so server queries always
  // have an explicit authority context. Production auth can replace this.
  userRole: 'CONTROL_OFFICER',
  setUserRole: (role) => set({ userRole: role }),

  // SHIM: setActiveScreen (backward compatibility; routes now handle navigation)
  activeScreen: 'COMMAND_CENTER',
  setActiveScreen: () => {
    // No-op; navigation is now route-based. Kept for backward compatibility.
  },

  // Transient Workflow
  isGeneratingPlan: false,
  plannerStage: '',
  setIsGeneratingPlan: (generating) => set({ isGeneratingPlan: generating }),
  setPlannerStage: (stage) => set({ plannerStage: stage }),

  // Emergency State
  emergencyState: null,
  isEmergencyActive: false,
  setEmergencyState: (state) => set({ emergencyState: state }),
  setIsEmergencyActive: (active) => set({ isEmergencyActive: active }),

  // Field PWA
  fieldTaskStatus: {
    'tsk-01': 'READY',
    'tsk-02': 'READY',
    'tsk-03': 'READY'
  },
  updateFieldTaskStatus: (taskId, status) => {
    set(state => ({
      fieldTaskStatus: {
        ...state.fieldTaskStatus,
        [taskId]: status
      }
    }));
  },

  // ===== SYNTHETIC DATA SHIMS (fixtures for backward compatibility) =====
  sections: mockCorridorSections,
  tasks: mockMaintenanceTasks,
  trains: mockTrainMovements,
  candidates: mockPlanCandidates,
  selectedMode: 'BALANCED',
  approvedCandidate: null,
  activePlan: mockPlanCandidates[0],

  // ===== SYNTHETIC MODE ACTIONS (to be replaced by React Query) =====
  setSelectedMode: (mode) => {
    const candidate = get().candidates.find(c => c.mode === mode) || get().candidates[0];
    set({ selectedMode: mode, activePlan: candidate });
  },

  generatePlan: (mode) => {
    set({ isGeneratingPlan: true, plannerStage: 'Ingesting Corridor Headway & Timetable...' });

    setTimeout(() => {
      set({ plannerStage: 'Evaluating Cross-Departmental Compatibility (Track + S&T + TRD)...' });
    }, 400);

    setTimeout(() => {
      set({ plannerStage: 'Solving Multi-Possession Schedule under Headway Constraints...' });
    }, 900);

    setTimeout(() => {
      set({ plannerStage: 'Synthesizing Coordinated Candidate Schedules...' });
    }, 1400);

    setTimeout(() => {
      const candidate = get().candidates.find(c => c.mode === mode) || get().candidates[0];
      set({
        isGeneratingPlan: false,
        plannerStage: 'Plan Optimization Complete',
        selectedMode: mode,
        activePlan: candidate
      });
    }, 1800);
  },

  approvePlan: (candidate) => {
    set({ approvedCandidate: candidate });
  },

  triggerEmergencyFlaw: () => {
    const emergency: EmergencyScenario = {
      id: 'emg-weld-burst-99',
      defect: {
        id: 'def-emg-01',
        code: 'DEF-FLAW-ALJN-99',
        department: 'CIVIL',
        title: 'EMERGENCY: Immediate Rail Fracture Detected (Km 1332/08 Down Line)',
        description: 'Transverse complete rail fissure observed under acoustic vibration sensor. Complete track stoppage required immediately.',
        assetId: 'ast-rail-aljn-01',
        assetType: '60kg CWR Rail Section',
        sectionId: 'sec-krj-aljn',
        locationKm: '1332/08',
        severity: 'CRITICAL',
        riskScore: 100,
        speedRestrictionKmph: 0,
        detectedAt: 'Just Now (14:02:18)',
        deadlineHours: 0.5,
        isOverdue: true,
        blockRequired: true,
        requiredDurationMins: 55
      },
      detectedAt: '14:02',
      immediateAction: 'Caution Order 0 km/h (Stop Dead). Immediate possession window required.',
      affectedBlockIds: ['blk-rec-02'],
      shiftedTaskIds: ['tsk-04']
    };

    const updatedSections = get().sections.map(sec =>
      sec.id === 'sec-krj-aljn'
        ? { ...sec, status: 'RESTRICTED' as const, criticalDefectsCount: sec.criticalDefectsCount + 1 }
        : sec
    );

    set({
      emergencyState: emergency,
      isEmergencyActive: true,
      sections: updatedSections
    });
  },

  replanEmergency: () => {
    const emergencyTask: MaintenanceTask = {
      id: 'tsk-emg-burst',
      taskCode: 'ENG-EMG-CLAMP',
      department: 'CIVIL',
      title: 'EMERGENCY: Clamp & Replace Fractured Rail Piece',
      assetId: 'ast-rail-aljn-01',
      assetName: '60kg Track Section Km 1332/08',
      sectionId: 'sec-krj-aljn',
      sectionName: 'Khurja – Aligarh (Down Line)',
      trackId: 'DOWN',
      severity: 'CRITICAL',
      riskScore: 100,
      priorityBand: 'P0_EMERGENCY',
      priorityScore: 100,
      dueDate: 'Immediate',
      estimatedMinutes: 50,
      blockRequirement: 'TRAFFIC',
      status: 'IN_PROGRESS',
      crewRequired: 16,
      specialMachine: 'UTV',
      isolationRequired: false,
      reasons: ['Critical Fracture Risk', 'Restores line at 20 km/h after fish-plating']
    };

    const emergencyBlock: CandidateBlock = {
      id: 'blk-emergency-immediate',
      blockCode: 'BLK-EMG-POSSESSION-1410',
      sectionId: 'sec-krj-aljn',
      sectionName: 'Khurja – Aligarh (Down Line)',
      track: 'DOWN',
      startTime: '14:10',
      endTime: '15:05',
      durationMinutes: 55,
      type: 'TRAFFIC',
      departments: ['CIVIL'],
      bundledTaskIds: ['tsk-emg-burst'],
      tasks: [emergencyTask],
      status: 'ACTIVE',
      utilizationRatePct: 98,
      riskReductionScore: 99,
      passengerDisruptionMins: 28,
      freightDelaysMins: 45,
      isolationProtocol: 'Emergency Stop-Flag Protection under Red Signal hold. Trains regulated at Somna & Danwar loops.',
      whyThisBlock: {
        bundlingEfficiency: 'Emergency corridor seizure; shifted routine CSM tamping (Task ENG-CSM-88) to tomorrow morning 03:30 night window.',
        gapExploitation: 'Forced window: holds freight rake BOXN-99 and reschedules local shuttle.',
        criticalRiskNeutralized: 'Direct derailment risk averted on 130 km/h trunk corridor.',
        trainImpactMitigation: 'Howrah Rajdhani held at Khurja for 14 minutes; priority restored upon line clearance.',
        shadowPossessionBenefit: 'Prevented complete multi-hour corridor shutdown.'
      }
    };

    const currentPlan = get().activePlan;
    const replannedCandidate: PlanCandidate = {
      ...currentPlan,
      version: 'v2.5-EMERGENCY-REPLAN',
      trainDisruptionMinutes: currentPlan.trainDisruptionMinutes + 28,
      blocks: [emergencyBlock, ...currentPlan.blocks.filter(b => b.id !== 'blk-rec-02')]
    };

    set({
      activePlan: replannedCandidate,
      tasks: [emergencyTask, ...get().tasks],
      selectedBlockId: 'blk-emergency-immediate'
    });
  },

  dismissEmergency: () => {
    set({ isEmergencyActive: false, emergencyState: null });
  },

  resetToDefault: () => {
    set({
      selectedZone: 'NCR',
      selectedDivision: 'Delhi',
      selectedSection: 'GZB-ALJN',
      sections: mockCorridorSections,
      tasks: mockMaintenanceTasks,
      trains: mockTrainMovements,
      candidates: mockPlanCandidates,
      selectedMode: 'BALANCED',
      approvedCandidate: null,
      activePlan: mockPlanCandidates[0],
      selectedSectionId: 'sec-krj-aljn',
      selectedTaskId: 'tsk-01',
      selectedBlockId: 'blk-rec-01',
      emergencyState: null,
      isEmergencyActive: false,
      activeDrawer: null,
      fieldTaskStatus: {
        'tsk-01': 'READY',
        'tsk-02': 'READY',
        'tsk-03': 'READY'
      }
    });
  }
}));
