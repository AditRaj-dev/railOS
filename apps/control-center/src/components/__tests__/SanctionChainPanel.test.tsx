import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRailOSStore } from '@/store/railosStore';
import type { SanctionChain } from '@/lib/api';
import { usePlanSanctions, useSignPlanSanction } from '@/lib/queries';
import { SanctionChainPanel } from '../SanctionChainPanel';

vi.mock('@/lib/queries', () => ({
  usePlanSanctions: vi.fn(),
  useSignPlanSanction: vi.fn(),
}));

const chain: SanctionChain = {
  planId: 'PLAN-2026-01',
  planVersion: 3,
  requiredAuthorities: ['SECTION_CONTROL', 'TRACTION_POWER'],
  signatures: [],
  complete: false,
  refused: false,
  derivedFrom: ['HC-001'],
  backfilled: false,
};

describe('SanctionChainPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useRailOSStore.setState({ userRole: 'CONTROL_OFFICER' });
    vi.mocked(usePlanSanctions).mockReturnValue({
      data: chain,
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useSignPlanSanction).mockReturnValue({
      data: { ...chain },
      isPending: false,
      isError: false,
      mutate: vi.fn(),
    } as never);
  });

  it('shows an accepted 202 response while the chain remains open', () => {
    render(<SanctionChainPanel planId={chain.planId} />);

    expect(screen.getByRole('heading', { name: 'Sanction chain' })).toBeInTheDocument();
    expect(screen.getByText(/Authority response accepted \(HTTP 202\)/)).toBeInTheDocument();
    expect(screen.getByText('Section Controller')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign authority chain' })).toBeEnabled();
  });

  it('posts the current authority with the plan version', () => {
    const mutate = vi.fn();
    vi.mocked(useSignPlanSanction).mockReturnValue({
      data: undefined,
      isPending: false,
      isError: false,
      mutate,
    } as never);
    render(<SanctionChainPanel planId={chain.planId} />);

    fireEvent.click(screen.getByRole('button', { name: 'Sign authority chain' }));

    expect(mutate).toHaveBeenCalledWith(expect.objectContaining({
      planId: chain.planId,
      authority: 'SECTION_CONTROL',
      decision: 'GRANTED',
      expectedVersion: 3,
    }));
  });
});
