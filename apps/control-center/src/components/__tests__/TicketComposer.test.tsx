import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssets, useCreateBlockRequest, useNetworkCatalog, useTicketTaskTypes } from '@/lib/queries';
import { TicketComposer } from '../TicketComposer';

vi.mock('@/lib/queries', () => ({
  useAssets: vi.fn(),
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
    data: [
      { taskType: 'TAMPING', department: 'ENGG', minDurationMinutes: 150, assetType: 'TRACK_SECTION', requiresPTW: false, requiresT351: false, requiresCorrespondenceTest: false },
      { taskType: 'TURNOUT_RENEWAL', department: 'ENGG', minDurationMinutes: 0, assetType: 'POINT', requiresPTW: true, requiresT351: true, requiresCorrespondenceTest: false },
    ],
  } as never);
  vi.mocked(useAssets).mockReturnValue({
    data: [
      { assetId: 'TRACK_SEC_KRJ_SMQ_DOWN', assetType: 'TRACK_SECTION', sectionId: 'SEC_KRJ_SMQ', track: 'DOWN' },
      { assetId: 'PT_KRJ_SMQ_101', assetType: 'POINT', sectionId: 'SEC_KRJ_SMQ', track: 'DOWN', name: 'Point 101' },
      { assetId: 'PT_KRJ_SMQ_102', assetType: 'POINT', sectionId: 'SEC_KRJ_SMQ', track: 'DOWN', name: 'Point 102' },
    ],
    isLoading: false,
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

describe('TicketComposer asset picker', () => {
  /** Stop on the work step, where the asset choice lives. */
  function gotoWorkStep() {
    render(<TicketComposer initialDepartment="ENGG" />);
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    fireEvent.change(screen.getByLabelText(/affected section/i), { target: { value: 'SEC_KRJ_SMQ' } });
    fireEvent.change(screen.getByLabelText(/start kilometre/i), { target: { value: '60' } });
    fireEvent.change(screen.getByLabelText(/end kilometre/i), { target: { value: '62' } });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
  }

  it('demands a choice when the section holds several candidate assets', () => {
    gotoWorkStep();
    fireEvent.change(screen.getByLabelText(/work type/i), { target: { value: 'TURNOUT_RENEWAL' } });
    expect(screen.getByLabelText(/asset \(point\)/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/choose which point/i);
    fireEvent.change(screen.getByLabelText(/asset \(point\)/i), { target: { value: 'PT_KRJ_SMQ_102' } });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    // Moved on to the block-need step, so the asset satisfied the gate.
    expect(screen.getByLabelText(/estimated duration/i)).toBeInTheDocument();
  });

  it('leaves a lone candidate to the server instead of demanding a choice', () => {
    gotoWorkStep();
    fireEvent.change(screen.getByLabelText(/work type/i), { target: { value: 'TAMPING' } });
    expect(screen.getByText(/one candidate on this section and track/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(screen.getByLabelText(/estimated duration/i)).toBeInTheDocument();
  });
});
