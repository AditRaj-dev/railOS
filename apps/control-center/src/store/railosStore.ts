import { create } from 'zustand';

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
  // Server data lives in TanStack Query (see src/lib/queries.ts) — never here.

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

  // SHIM: setActiveScreen (routes now handle navigation)
  // Kept for backward compatibility with view components that may call it.
  activeScreen?: 'COMMAND_CENTER' | 'NETWORK' | 'MAINTENANCE' | 'BLOCK_PLANNER' | 'TIMELINE' | 'PLAN_COMPARISON' | 'ANALYTICS' | 'FIELD_PWA';
  setActiveScreen: (screen: string) => void;

  // Field PWA State (UI state)
  fieldTaskStatus: Record<string, 'READY' | 'START' | 'DELAY' | 'COMPLETED'>;
  updateFieldTaskStatus: (taskId: string, status: 'READY' | 'START' | 'DELAY' | 'COMPLETED') => void;
}

export const useRailOSStore = create<RailOSStore>((set) => ({
  // Territory Selection
  selectedZone: 'NCR',
  selectedDivision: 'Delhi',
  selectedSection: '',
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
  // Starts as the Section Controller so server queries always have an explicit
  // authority context. The shell's role selector drives this from here on.
  userRole: 'CONTROL_OFFICER',
  setUserRole: (role) => set({ userRole: role }),

  // SHIM: setActiveScreen (backward compatibility; routes now handle navigation)
  activeScreen: 'COMMAND_CENTER',
  setActiveScreen: () => {
    // No-op; navigation is now route-based. Kept for backward compatibility.
  },

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
}));
