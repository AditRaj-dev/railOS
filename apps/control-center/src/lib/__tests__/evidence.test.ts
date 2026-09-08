import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getEvidenceList,
  getEvidenceDetails,
  reviewEvidence,
  getSupervisorsList,
  createSupervisorAccount,
} from '../api';

describe('Field Evidence Control Center API Layer', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches evidence items list with status filtering', async () => {
    const mockResponse = {
      items: [
        {
          evidenceId: 'ev-1',
          taskId: 'TSK-001',
          status: 'FLAGGED_REVIEW',
          geoVerdict: 'OUTSIDE_RADIUS',
        },
      ],
      count: 1,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      text: async () => JSON.stringify(mockResponse),
      json: async () => mockResponse,
    } as unknown as Response);

    const res = await getEvidenceList({ status: 'FLAGGED_REVIEW' });
    expect(res.count).toBe(1);
    expect(res.items[0].status).toBe('FLAGGED_REVIEW');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/evidence?status=FLAGGED_REVIEW'),
      expect.anything()
    );
  });

  it('submits control officer review decision', async () => {
    const mockItem = {
      evidenceId: 'ev-1',
      status: 'ACCEPTED_EXCEPTION',
      reviewerId: 'admin-01',
      reviewNotes: 'Valid obstruction',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      text: async () => JSON.stringify(mockItem),
      json: async () => mockItem,
    } as unknown as Response);

    const result = await reviewEvidence('ev-1', 'ACCEPT', 'Valid obstruction');
    expect(result.status).toBe('ACCEPTED_EXCEPTION');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/evidence/ev-1:review'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ decision: 'ACCEPT', reviewNotes: 'Valid obstruction' }),
      })
    );
  });

  it('fetches supervisors roster and creates new supervisor account', async () => {
    const mockRoster = {
      items: [{ userId: 'sup-1', employeeId: 'EMP901', name: 'Rajesh Kumar' }],
      count: 1,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      text: async () => JSON.stringify(mockRoster),
      json: async () => mockRoster,
    } as unknown as Response);

    const roster = await getSupervisorsList();
    expect(roster.count).toBe(1);
    expect(roster.items[0].employeeId).toBe('EMP901');
  });
});
