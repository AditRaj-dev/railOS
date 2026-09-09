import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { BlockRequest } from '@/lib/api';
import { useBlockRequests, useUpdateBlockRequestStatus } from '@/lib/queries';
import { useRailOSStore } from '@/store/railosStore';
import { TicketDashboardView } from '../TicketDashboardView';

vi.mock('@/lib/queries', () => ({
  useBlockRequests: vi.fn(),
  useUpdateBlockRequestStatus: vi.fn(),
}));

vi.mock('@/store/railosStore', () => ({
  useRailOSStore: vi.fn(),
}));

vi.mock('../TicketComposer', () => ({
  TicketComposer: () => <div>ticket composer</div>,
}));

const ticket: BlockRequest = {
  requestId: 'REQ-001',
  department: 'ENGG',
  status: 'REQUESTED',
  corridorId: 'GZB-ALJN',
  sectionId: 'SEC-1',
  track: 'DOWN',
  kmStart: 10,
  kmEnd: 12,
  taskType: 'TAMPING',
  severity: 6,
  estimatedDuration: 90,
  blockType: 'TRAFFIC',
  requestedStart: '120',
  requestedEnd: '240',
  linkedTaskId: 'TSK-0001',
  createdAt: '2026-09-09T01:00:00Z',
  synthetic: true,
};

function mockRole(role: string) {
  vi.mocked(useRailOSStore).mockImplementation(((selector: (state: { userRole: string }) => unknown) =>
    selector({ userRole: role })) as never);
}

function mockTickets(items: BlockRequest[], overrides: Partial<ReturnType<typeof useBlockRequests>> = {}) {
  vi.mocked(useBlockRequests).mockReturnValue({
    data: { items, count: items.length },
    isLoading: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  } as never);
}

describe('TicketDashboardView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useUpdateBlockRequestStatus).mockReturnValue({ isPending: false, isError: false, error: null, mutate: vi.fn() } as never);
  });

  it('renders all three department tabs plus All for a broad role', () => {
    mockRole('CONTROL_OFFICER');
    mockTickets([ticket]);
    render(<TicketDashboardView />);

    expect(screen.getByRole('tab', { name: /^All/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /^ENGG/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /^SNT/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /^TRD/ })).toBeInTheDocument();
  });

  it('locks a department role to its own tab and hides the others', () => {
    mockRole('ENGINEERING');
    mockTickets([ticket]);
    render(<TicketDashboardView />);

    expect(screen.getByRole('tab', { name: /^ENGG/ })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /^SNT/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /^TRD/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /^All/ })).not.toBeInTheDocument();
  });

  it('renders queue rows from the block request query', () => {
    mockRole('CONTROL_OFFICER');
    mockTickets([ticket]);
    render(<TicketDashboardView />);

    expect(screen.getByText('REQ-001')).toBeInTheDocument();
    expect(screen.getByText('TSK-0001')).toBeInTheDocument();
    expect(screen.getByText('TAMPING')).toBeInTheDocument();
  });

  it('shows an empty state when the queue has no tickets', () => {
    mockRole('CONTROL_OFFICER');
    mockTickets([]);
    render(<TicketDashboardView />);

    expect(screen.getByText('No tickets in this queue')).toBeInTheDocument();
  });

  it('shows an error state with a retry action', () => {
    mockRole('CONTROL_OFFICER');
    mockTickets([], {
      isError: true,
      error: { message: 'Network unreachable' } as never,
    });
    render(<TicketDashboardView />);

    expect(screen.getByRole('alert')).toHaveTextContent('Network unreachable');
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });
});
