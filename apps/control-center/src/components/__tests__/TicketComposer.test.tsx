import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCreateBlockRequest, useNetworkCatalog, useTicketTaskTypes } from '@/lib/queries';
import { TicketComposer } from '../TicketComposer';

vi.mock('@/lib/queries', () => ({
  useCreateBlockRequest: vi.fn(),
  useNetworkCatalog: vi.fn(),
  useTicketTaskTypes: vi.fn(),
}));

const mutate = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useNetworkCatalog).mockReturnValue({
    data: { sections: [{ sectionId: 'SEC_KRJ_SMQ', name: 'Khurja–Somna' }] },
    isLoading: false,
  } as never);
  vi.mocked(useTicketTaskTypes).mockReturnValue({
    data: [{ taskType: 'TAMPING', department: 'ENGG', minDurationMinutes: 150, requiresPTW: false, requiresT351: false, requiresCorrespondenceTest: false }],
  } as never);
  vi.mocked(useCreateBlockRequest).mockReturnValue({ mutate, isPending: false } as never);
});

/** Walk the composer from the department step to the block-need step. */
function gotoBlockStep() {
  render(<TicketComposer initialDepartment="ENGG" />);
  fireEvent.click(screen.getByRole('button', { name: /continue/i }));
  fireEvent.change(screen.getByLabelText(/affected section/i), { target: { value: 'SEC_KRJ_SMQ' } });
  fireEvent.change(screen.getByLabelText(/start kilometre/i), { target: { value: '60' } });
  fireEvent.change(screen.getByLabelText(/end kilometre/i), { target: { value: '62' } });
  fireEvent.click(screen.getByRole('button', { name: /continue/i }));
  fireEvent.change(screen.getByLabelText(/work type/i), { target: { value: 'TAMPING' } });
  fireEvent.click(screen.getByRole('button', { name: /continue/i }));
}

describe('TicketComposer duration floor', () => {
  it('states the statutory minimum for the chosen work type', () => {
    gotoBlockStep();
    expect(screen.getByText(/minimum block of 150 minutes/i)).toBeInTheDocument();
  });

  it('refuses a duration under the floor instead of letting the API 422 it', () => {
    gotoBlockStep();
    fireEvent.change(screen.getByLabelText(/estimated duration/i), { target: { value: '90' } });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/at least 150 minutes/i);
    // Still on the block step: the bad value was never carried forward.
    expect(screen.getByLabelText(/estimated duration/i)).toBeInTheDocument();
  });

  it('clears the error banner once the value is corrected', () => {
    gotoBlockStep();
    fireEvent.change(screen.getByLabelText(/estimated duration/i), { target: { value: '90' } });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(screen.getByRole('alert')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/estimated duration/i), { target: { value: '150' } });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
