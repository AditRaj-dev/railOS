import { describe, expect, it } from 'vitest';
import { createPayload } from '../TicketComposer';

/**
 * The API's BlockRequestCreate is extra="forbid" and populate_by_name=False:
 * an undeclared key is a hard 422, and so is a missing required one. This pins
 * the composer's half of that contract; tests/test_ticket_payload_contract.py
 * pins the schema's half against the same list.
 */
const CONTRACT_KEYS = [
  'department', 'corridorId', 'sectionId', 'assetId', 'track',
  'kmStart', 'kmEnd', 'taskType', 'severity', 'estimatedDuration',
  'blockType', 'requestedStart', 'requestedEnd',
].sort();

const draft = {
  department: 'ENGG',
  sectionId: 'SEC_GZB_DER',
  track: 'UP',
  kmStart: '1.0',
  kmEnd: '2.0',
  taskType: 'TAMPING',
  assetId: 'TRACK_SEC_GZB_DER_UP',
  severity: '5',
  estimatedDuration: '150',
  blockType: 'TRAFFIC',
  requestedStart: '2026-09-09T01:00',
  requestedEnd: '2026-09-09T05:00',
};

describe('createPayload wire contract', () => {
  it('emits only keys BlockRequestCreate declares', () => {
    const payload = createPayload(draft as never, 'GZB-ALJN');
    expect(Object.keys(payload).sort()).toEqual(CONTRACT_KEYS);
  });

  it('omits assetId entirely rather than sending an empty string', () => {
    // An empty assetId is not "no asset" to the server — it is an unknown one.
    const payload = createPayload({ ...draft, assetId: '' } as never, 'GZB-ALJN');
    expect('assetId' in payload).toBe(false);
  });

  it('converts the window to horizon-relative minutes, not ISO strings', () => {
    const payload = createPayload(draft as never, 'GZB-ALJN');
    expect(typeof payload.requestedStart).toBe('number');
    expect(typeof payload.requestedEnd).toBe('number');
    expect(payload.requestedEnd).toBeGreaterThan(payload.requestedStart);
  });

  it('sends numbers, not the form\'s strings, for numeric fields', () => {
    const payload = createPayload(draft as never, 'GZB-ALJN');
    for (const key of ['kmStart', 'kmEnd', 'severity', 'estimatedDuration'] as const) {
      expect(typeof payload[key]).toBe('number');
    }
  });

  it('never sends server-derived optimizer flags', () => {
    const payload = createPayload(draft as never, 'GZB-ALJN') as unknown as Record<string, unknown>;
    for (const key of ['requiresPTW', 'requiresT351', 'requiresCorrespondenceTest', 'machineType']) {
      expect(key in payload).toBe(false);
    }
  });
});
