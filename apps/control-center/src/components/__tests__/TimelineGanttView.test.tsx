import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockPlans, useBlockRequests, useNetworkCatalog, useTrains } from '@/lib/queries';
import { TimelineGanttView } from '../TimelineGanttView';

const push = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

vi.mock('@/lib/queries', () => ({
  useBlockPlans: vi.fn(),
  useBlockRequests: vi.fn(),
  useNetworkCatalog: vi.fn(),
  useTrains: vi.fn(),
}));

vi.mock('../../store/railosStore', () => ({
  useRailOSStore: () => ({ setSelectedBlockId: vi.fn() }),
}));

const plan = {
  planId: 'PLAN-1',
  planVersion: 1,
  status: 'GENERATED',
  objectiveProfile: 'BALANCED',
  blocks: [
    {
      blockId: 'BLK-1',
      sectionId: 'SEC_KRJ_SMQ',
      track: 'DOWN',
      blockType: 'TRAFFIC',
      start: 780,
      end: 900,
      taskIds: ['TKT-REQ-1'],
      departments: ['TRD'],
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useNetworkCatalog).mockReturnValue({
    data: { sections: [{ sectionId: 'SEC_KRJ_SMQ', name: 'Khurja–Somna' }] },
  } as never);
  vi.mocked(useBlockPlans).mockReturnValue({ data: { plans: [plan] } } as never);
  vi.mocked(useTrains).mockReturnValue({ data: [] } as never);
  vi.mocked(useBlockRequests).mockReturnValue({
    data: {
      items: [{
        requestId: 'REQ-1',
        department: 'TRD',
        status: 'REQUESTED',
        taskType: 'OHE_INSPECTION',
        linkedTaskId: 'TKT-REQ-1',
        requestedStart: '780',
        requestedEnd: '900',
      }],
      count: 1,
    },
  } as never);
});

describe('TimelineGanttView', () => {
  it('draws possession bars as buttons that name the whole window (DP-002)', () => {
    render(<TimelineGanttView />);
    // The visible label is clipped to the bar's width, so the accessible name
    // has to carry the section and the times.
    const bar = screen.getByRole('button', { name: /possession blk-1, khurja–somna, 13:00 to 15:00, 120 minutes/i });
    fireEvent.click(bar);
    expect(push).toHaveBeenCalledWith('/planner');
  });

  it('states REQUESTED in words on the demand lane, not by pattern alone', () => {
    render(<TimelineGanttView />);
    expect(screen.getAllByText(/REQUESTED/).length).toBeGreaterThan(0);
    expect(screen.getByRole('link', { name: 'REQ-1' })).toBeInTheDocument();
  });
});
