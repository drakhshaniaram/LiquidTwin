import type { components } from './client';
import type { TerminalDocument as TerminalDocumentModel } from './types';

export type TerminalSummary = components['schemas']['TerminalSummary'];
export type TerminalImportResult = components['schemas']['ImportResponse'];
export type TerminalDocument = TerminalDocumentModel;
export type TerminalDetail = components['schemas']['TerminalVersionDetail'];
export type TerminalVersionInfo = components['schemas']['VersionInfo'];
export type ValidationIssue = components['schemas']['ValidationIssue'];

export type TerminalGraph = Omit<components['schemas']['TerminalGraph'], 'nodes' | 'elements'> & {
  nodes: TerminalDocument['nodes'];
  elements: TerminalDocument['elements'];
};

export type TerminalGraphArc = TerminalGraph['arcs'][number];
export type RouteRequest = components['schemas']['RouteRequest'];
export type RouteResponse = components['schemas']['RouteResponse'];
export type OptimizationScenario = components['schemas']['OptimizationScenario'];
export type OptimizationPreparation = components['schemas']['OptimizationPreparation'];
export type OptimizationResult = components['schemas']['OptimizationResult'];
export type TerminalRoute = components['schemas']['Route'];
export type ConfirmedRoute = components['schemas']['ConfirmedRoute'];
export type AvailabilityWindow = components['schemas']['AvailabilityWindow'];
export type AvailabilityWindowInput = components['schemas']['AvailabilityWindowInput'];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
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

export function importTerminalJson(
  name: string,
  document: TerminalDocument,
): Promise<TerminalImportResult> {
  return request('/terminals/import', {
    method: 'POST',
    body: JSON.stringify({ name, document }),
  });
}

export function importTerminalCsvBundle(
  name: string,
  files: readonly File[],
): Promise<TerminalImportResult> {
  const body = new FormData();
  body.append('name', name);
  for (const file of files) body.append('files', file, file.name);
  return request('/terminals/import', { method: 'POST', body });
}

export async function exportTerminal(terminalId: string, format: 'json' | 'csv'): Promise<Blob> {
  const response = await fetch(
    `/api/v1/terminals/${encodeURIComponent(terminalId)}/export?format=${format}`,
  );
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { message?: string } | null;
    throw new Error(payload?.message ?? `Request failed (${response.status})`);
  }
  return response.blob();
}

export function deleteTerminal(terminalId: string): Promise<void> {
  return request(`/terminals/${encodeURIComponent(terminalId)}`, { method: 'DELETE' });
}

export function requestRoutes(
  terminalId: string,
  routeRequest: RouteRequest,
): Promise<RouteResponse> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/routes`, {
    method: 'POST',
    body: JSON.stringify(routeRequest),
  });
}

export function prepareOptimization(
  terminalId: string,
  scenario: OptimizationScenario,
): Promise<OptimizationPreparation> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/optimization/prepare`, {
    method: 'POST',
    body: JSON.stringify(scenario),
  });
}

export function optimizeTerminal(
  terminalId: string,
  scenario: OptimizationScenario,
): Promise<OptimizationResult> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/optimize`, {
    method: 'POST',
    body: JSON.stringify(scenario),
  });
}

export function confirmTerminalRoute(
  terminalId: string,
  routeRequest: RouteRequest,
  route: TerminalRoute,
): Promise<ConfirmedRoute> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/routes/confirm`, {
    method: 'POST',
    body: JSON.stringify({ request: routeRequest, route }),
  });
}

export function listConfirmedRoutes(terminalId: string): Promise<ConfirmedRoute[]> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/routes/confirmed`);
}

export function listAvailabilityWindows(terminalId: string): Promise<AvailabilityWindow[]> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/availability`);
}

export function upsertAvailabilityWindows(
  terminalId: string,
  windows: AvailabilityWindowInput[],
): Promise<{ applied: number; rejected: { index: number; reason: string }[] }> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/availability`, {
    method: 'POST',
    body: JSON.stringify({ windows }),
  });
}

export function deleteAvailabilityWindow(terminalId: string, windowId: string): Promise<void> {
  return request(
    `/terminals/${encodeURIComponent(terminalId)}/availability/${encodeURIComponent(windowId)}`,
    {
      method: 'DELETE',
    },
  );
}

export function getTerminal(terminalId: string): Promise<TerminalDetail> {
  return request(`/terminals/${encodeURIComponent(terminalId)}`);
}

export function listTerminalVersions(terminalId: string): Promise<TerminalVersionInfo[]> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/versions`);
}

export function restoreTerminalVersion(
  terminalId: string,
  version: number,
): Promise<TerminalVersionInfo> {
  return request(`/terminals/${encodeURIComponent(terminalId)}/versions`, {
    method: 'POST',
    body: JSON.stringify({ restore_from: version }),
  });
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
