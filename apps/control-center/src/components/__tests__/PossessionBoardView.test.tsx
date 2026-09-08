import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PossessionView } from '@/lib/api';
import { usePossessionAction, usePossessions } from '@/lib/queries';
import { PossessionBoardView } from '../PossessionBoardView';

vi.mock('@/lib/queries', () => ({
  usePossessions: vi.fn(),
  usePossessionAction: vi.fn(),
}));

vi.mock('@/lib/useRailOSEventStream', () => ({
  useRailOSEventStream: vi.fn(),
}));

const possession: PossessionView = {
  possessionId: 'POS-001',
  planId: 'PLAN-001',
  planVersion: 1,
  blockId: 'BLK-001',
  sectionId: 'GZB-ALJN',
  track: 'DOWN',
  state: 'CLEARANCE_REQUESTED',
  plannedStartUtc: '2026-09-08T08:00:00Z',
  plannedEndUtc: '2026-09-08T10:00:00Z',
  deferralCount: 0,
  requiresPTW: false,
  requiresT351: true,
  requiresCorrespondenceTest: false,
  stationClosed: false,
  formT351: null,
  permitToWork: null,
  protectionRecord: null,
  correspondenceTest: null,
  fitnessCertificate: null,
  transitions: [],
  assignedTaskIds: [],
  department: 'ENGG',
  leadInMinutes: 15,
  overrunMinutesLive: 0,
  handbackChecklist: [],
  allowedActions: ['grant-clearance'],
};

function mockQueries(data: PossessionView) {
  vi.mocked(usePossessions).mockReturnValue({
    data: { items: [data], count: 1 },
    isLoading: false,
    isError: false,
    isFetching: false,
    refetch: vi.fn(),
  } as never);
  vi.mocked(usePossessionAction).mockReturnValue({
    isPending: false,
    isError: false,
    mutate: vi.fn(),
  } as never);
}

describe('PossessionBoardView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockQueries(possession);
  });

  it('renders only the actions authorized by the server', () => {
    render(<PossessionBoardView />);

    expect(screen.getByRole('button', { name: 'Grant clearance' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: 'Defer' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument();
  });

  it('does not invent a grant action when the server only allows cancellation', () => {
    mockQueries({ ...possession, allowedActions: ['cancel'] });
    render(<PossessionBoardView />);

    expect(screen.getByRole('button', { name: 'Cancel' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: 'Grant clearance' })).not.toBeInTheDocument();
  });
});
