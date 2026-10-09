import type { components } from './client';
import type { TerminalDocument as TerminalDocumentModel } from './types';

export type TerminalSummary = components['schemas']['TerminalSummary'];
export type TerminalDocument = TerminalDocumentModel;
export type TerminalDetail = components['schemas']['TerminalVersionDetail'];
export type ValidationIssue = components['schemas']['ValidationIssue'];

export type TerminalGraph = Omit<components['schemas']['TerminalGraph'], 'nodes' | 'elements'> & {
  nodes: TerminalDocument['nodes'];
  elements: TerminalDocument['elements'];
};

export type TerminalGraphArc = TerminalGraph['arcs'][number];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { message?: string } | null;
    throw new Error(payload?.message ?? `Request failed (${response.status})`);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function listTerminals(): Promise<TerminalSummary[]> {
  return request('/terminals');
}

export function createTerminal(name: string): Promise<TerminalSummary> {
  const document: TerminalDocument = {
    schema_version: '1.0',
    name,
    products: [],
    nodes: [],
    elements: [],
  };
  return request('/terminals', {
    method: 'POST',
    body: JSON.stringify({ name, document }),
  });
}

export function getTerminal(terminalId: string): Promise<TerminalDetail> {
  return request(`/terminals/${encodeURIComponent(terminalId)}`);
}

export function saveTerminalDocument(
  terminalId: string,
  document: TerminalDocument,
  note: string,
): Promise<{ version: number }> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/versions`, {
    method: 'POST',
    body: JSON.stringify({ document, note }),
  });
}

export function validateTerminalDocument(
  terminalId: string,
  document: TerminalDocument,
): Promise<{ issues: ValidationIssue[] }> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/validate`, {
    method: 'POST',
    body: JSON.stringify({ document }),
  });
}

export function getTerminalGraph(terminalId: string, version: number): Promise<TerminalGraph> {
  return request(
    `/terminals/${encodeURIComponent(terminalId)}/graph?version=${encodeURIComponent(version)}`,
  );
}
