import {
  Activity,
  ArrowUpRight,
  Boxes,
  CalendarDays,
  CircleAlert,
  Copy,
  Download,
  GitBranch,
  History,
  LoaderCircle,
  Maximize,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Redo2,
  Route as RouteIcon,
  Save,
  Trash2,
  Undo2,
  Upload,
  Wrench,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  Link,
  NavLink,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router-dom';

import {
  confirmTerminalRoute,
  createTerminal,
  deleteAvailabilityWindow,
  deleteTerminal,
  exportTerminal,
  getTerminalGraph,
  getTerminal,
  importTerminalCsvBundle,
  importTerminalJson,
  listAvailabilityWindows,
  listConfirmedRoutes,
  listTerminals,
  listTerminalVersions,
  optimizeTerminal,
  prepareOptimization,
  requestRoutes,
  restoreTerminalVersion,
  saveTerminalDocument,
  upsertAvailabilityWindows,
  validateTerminalDocument,
  type AvailabilityWindow,
  type OptimizationPreparation,
  type OptimizationResult,
  type OptimizationScenario,
  type TerminalGraph,
  type RouteRequest,
  type RouteResponse,
  type TerminalSummary,
  type ValidationIssue,
} from './api/terminals';
import type {
  Element as TerminalElement,
  Node as TerminalNode,
  PerformanceCurve,
  PumpTrain,
  TerminalDocument,
} from './api/types';
import { commitHistory, createHistory, redoHistory, undoHistory } from './editor/history';
import { useWorkspaceStore } from './store/workspace';

const navigation = [
  { to: '/terminals', label: 'Terminals', Icon: Boxes },
  { to: '/designer', label: 'Designer', Icon: GitBranch },
  { to: '/planner', label: 'Route planner', Icon: RouteIcon },
  { to: '/optimization', label: 'Optimization', Icon: CalendarDays },
  { to: '/availability', label: 'Availability', Icon: Activity },
  { to: '/versions', label: 'Versions', Icon: History },
];

function AppFrame() {
  const activeTerminalId = useWorkspaceStore((state) => state.activeTerminalId);
  const location = useLocation();
  const isDesigner = location.pathname.startsWith('/designer/');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className={`app-shell${isDesigner ? ' designer-app' : ''}`}>
      <header className="topbar">
        <button
          aria-label={sidebarCollapsed ? 'Expand navigation' : 'Collapse navigation'}
          className="sidebar-toggle"
          title={sidebarCollapsed ? 'Expand navigation' : 'Collapse navigation'}
          type="button"
          onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
        >
          {sidebarCollapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
        </button>
        <Link className="brand" to="/terminals" aria-label="LiquidTwin terminal register">
          <img src="/flow-mark.svg" alt="" width="38" height="38" />
          <span className="brand-copy">
            <strong>LiquidTwin</strong>
            <small>TERMINAL WORKSPACE</small>
          </span>
        </Link>
        <div className="topbar-state">
          {!isDesigner && (
            <span className="local-state">
              <span aria-hidden="true" />
              LOCAL WORKSPACE
            </span>
          )}
          <span className="active-terminal">
            {activeTerminalId ? `TERMINAL ${activeTerminalId.slice(0, 8)}` : 'NO ACTIVE TERMINAL'}
          </span>
        </div>
      </header>

      <div className={`workspace-layout${sidebarCollapsed ? ' is-sidebar-collapsed' : ''}`}>
        <aside className="sidebar" aria-label="Workspace navigation">
          <nav className="primary-nav">
            {navigation.map(({ to, label, Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/terminals'}
                className={({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`}
              >
                <Icon aria-hidden="true" size={18} strokeWidth={1.8} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-footer">
            <span className="footer-mark" aria-hidden="true" />
            <span className="sidebar-footer-label">DEVELOPMENT</span>
            <span className="build-number">0.1.0</span>
          </div>
        </aside>

        <main className={`main-content${isDesigner ? ' designer-main' : ''}`} id="main-content">
          {!isDesigner && (
            <div className="content-ruler">
              <span>LIQUID BULK / OPERATIONS</span>
              <span>WORKSPACE 01</span>
            </div>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function PageHeading({
  eyebrow,
  title,
  summary,
  action,
  compact = false,
}: {
  eyebrow: string;
  title: string;
  summary: string;
  action?: React.ReactNode;
  compact?: boolean;
}) {
  return (
    <div className={`page-heading${compact ? ' compact-heading' : ''}`}>
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-summary">{summary}</p>
      </div>
      {action}
    </div>
  );
}

function TerminalRegister() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const setActiveTerminal = useWorkspaceStore((state) => state.setActiveTerminal);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [terminalName, setTerminalName] = useState('');
  const [showImportForm, setShowImportForm] = useState(false);
  const [importName, setImportName] = useState('');
  const [importFiles, setImportFiles] = useState<File[]>([]);
  const [registerError, setRegisterError] = useState('');
  const terminals = useQuery({ queryKey: ['terminals'], queryFn: listTerminals });
  const create = useMutation({
    mutationFn: createTerminal,
    onSuccess: async (terminal) => {
      setActiveTerminal(terminal.id);
      await queryClient.invalidateQueries({ queryKey: ['terminals'] });
      navigate(`/designer/${terminal.id}`);
    },
  });
  const importTerminal = useMutation({
    mutationFn: async ({ name, files }: { name: string; files: File[] }) => {
      if (files.length === 0) throw new Error('Choose a JSON file or CSV bundle.');
      const trimmedName = name.trim();
      if (files.length === 1 && files[0].name.toLowerCase().endsWith('.json')) {
        const parsed: unknown = JSON.parse(await files[0].text());
        if (!parsed || typeof parsed !== 'object')
          throw new Error('The JSON file must contain a terminal document.');
        const envelope = parsed as { name?: unknown; document?: unknown };
        const document = (envelope.document ?? parsed) as TerminalDocument;
        const resolvedName =
          trimmedName || (typeof envelope.name === 'string' ? envelope.name : '') || document.name;
        if (!resolvedName) throw new Error('Provide a terminal name for this JSON document.');
        return importTerminalJson(resolvedName, document);
      }
      if (!trimmedName) throw new Error('Enter a terminal name for the CSV bundle.');
      if (files.some((file) => !file.name.toLowerCase().endsWith('.csv'))) {
        throw new Error('Choose one JSON file or CSV files only.');
      }
      return importTerminalCsvBundle(trimmedName, files);
    },
    onSuccess: async (terminal) => {
      setActiveTerminal(terminal.id);
      setShowImportForm(false);
      setImportFiles([]);
      setRegisterError('');
      await queryClient.invalidateQueries({ queryKey: ['terminals'] });
      navigate(`/designer/${terminal.id}`);
    },
    onError: (error: Error) => setRegisterError(error.message),
  });
  const removeTerminal = useMutation({
    mutationFn: deleteTerminal,
    onSuccess: async (_result, terminalId) => {
      if (useWorkspaceStore.getState().activeTerminalId === terminalId) setActiveTerminal(null);
      await queryClient.invalidateQueries({ queryKey: ['terminals'] });
    },
    onError: (error: Error) => setRegisterError(error.message),
  });
  const exportSavedTerminal = useMutation({
    mutationFn: ({
      terminalId,
      format,
    }: {
      terminalId: string;
      format: 'json' | 'csv';
      terminal: TerminalSummary;
    }) => exportTerminal(terminalId, format),
    onSuccess: (blob, { terminal, format }) => {
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement('a');
      const baseName = terminal.name
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-');
      const extension = format === 'csv' ? 'zip' : 'json';
      anchor.href = url;
      anchor.download = `${baseName || 'terminal'}.${extension}`;
      anchor.click();
      URL.revokeObjectURL(url);
    },
    onError: (error: Error) => setRegisterError(error.message),
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = terminalName.trim();
    if (name) create.mutate(name);
  }

  function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    importTerminal.mutate({ name: importName, files: importFiles });
  }

  function confirmDelete(terminal: TerminalSummary) {
    if (window.confirm(`Delete ${terminal.name} and its version history?`)) {
      removeTerminal.mutate(terminal.id);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="ASSET REGISTER"
        title="Terminals"
        summary="Terminal inventory"
        action={
          <div className="register-actions">
            <button
              className="primary-action"
              type="button"
              onClick={() => {
                setShowCreateForm((visible) => !visible);
                setShowImportForm(false);
                setRegisterError('');
              }}
            >
              <Plus size={16} aria-hidden="true" /> New terminal
            </button>
            <button
              aria-label="Import terminal"
              className="secondary-action"
              title="Import JSON or CSV"
              type="button"
              onClick={() => {
                setShowImportForm((visible) => !visible);
                setShowCreateForm(false);
                setRegisterError('');
              }}
            >
              <Upload size={16} aria-hidden="true" /> <span>Import</span>
            </button>
          </div>
        }
      />
      {showCreateForm && (
        <form className="create-terminal" onSubmit={handleCreate}>
          <label htmlFor="terminal-name">Terminal name</label>
          <input
            autoFocus
            id="terminal-name"
            maxLength={120}
            onChange={(event) => setTerminalName(event.target.value)}
            placeholder="e.g. North Jetty Terminal"
            required
            value={terminalName}
          />
          <button className="primary-action" disabled={create.isPending} type="submit">
            {create.isPending ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />}
            Create and design
          </button>
          {create.isError && (
            <p className="form-error" role="alert">
              {create.error.message}
            </p>
          )}
        </form>
      )}
      {showImportForm && (
        <form className="create-terminal import-terminal" onSubmit={handleImport}>
          <label htmlFor="import-terminal-name">Terminal name</label>
          <input
            id="import-terminal-name"
            maxLength={120}
            onChange={(event) => setImportName(event.target.value)}
            placeholder="Required for CSV; JSON name is used by default"
            value={importName}
          />
          <label htmlFor="terminal-import-files">JSON file or CSV bundle</label>
          <input
            accept=".json,.csv"
            id="terminal-import-files"
            multiple
            onChange={(event) => setImportFiles(Array.from(event.target.files ?? []))}
            required
            type="file"
          />
          <button className="primary-action" disabled={importTerminal.isPending} type="submit">
            {importTerminal.isPending ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Upload size={16} />
            )}
            Import and design
          </button>
        </form>
      )}
      {registerError && (
        <p className="form-error register-error" role="alert">
          {registerError}
        </p>
      )}
      <section className="register" aria-label="Terminal inventory">
        <div className="register-head">
          <span>TERMINAL</span>
          <span>VERSION</span>
          <span>UPDATED</span>
          <span>OPEN</span>
          <span>ACTIONS</span>
        </div>
        {terminals.isLoading && (
          <div className="register-message">
            <LoaderCircle className="spin" size={18} /> Loading terminals
          </div>
        )}
        {terminals.isError && (
          <div className="register-message error-message" role="alert">
            <CircleAlert size={18} /> {terminals.error.message}. Check that the API and database are
            running.
          </div>
        )}
        {terminals.isSuccess && terminals.data.length === 0 && (
          <div className="register-empty">
            <div className="empty-symbol" aria-hidden="true">
              <Boxes size={25} strokeWidth={1.6} />
            </div>
            <div className="empty-copy">
              <strong>No terminals yet</strong>
              <p>Create a terminal to start laying out equipment and pipework.</p>
            </div>
            <button className="text-action" type="button" onClick={() => setShowCreateForm(true)}>
              Register terminal <ArrowUpRight size={16} aria-hidden="true" />
            </button>
          </div>
        )}
        {terminals.data && terminals.data.length > 0 && (
          <div className="terminal-rows">
            {terminals.data.map((terminal) => (
              <div className="terminal-row" key={terminal.id}>
                <Link
                  className="terminal-row-name"
                  onClick={() => setActiveTerminal(terminal.id)}
                  to={`/designer/${terminal.id}`}
                >
                  <strong>{terminal.name}</strong>
                </Link>
                <span className="table-number">V{terminal.current_version}</span>
                <time dateTime={terminal.updated_at}>
                  {new Date(terminal.updated_at).toLocaleString()}
                </time>
                <Link
                  className="row-open"
                  onClick={() => setActiveTerminal(terminal.id)}
                  to={`/designer/${terminal.id}`}
                >
                  Design <ArrowUpRight size={15} />
                </Link>
                <div className="terminal-row-actions">
                  <button
                    aria-label={`Export ${terminal.name} as JSON`}
                    disabled={exportSavedTerminal.isPending}
                    title="Export JSON"
                    type="button"
                    onClick={() =>
                      exportSavedTerminal.mutate({
                        terminalId: terminal.id,
                        format: 'json',
                        terminal,
                      })
                    }
                  >
                    <Download size={14} />
                  </button>
                  <button
                    aria-label={`Export ${terminal.name} as CSV bundle`}
                    disabled={exportSavedTerminal.isPending}
                    title="Export CSV bundle"
                    type="button"
                    onClick={() =>
                      exportSavedTerminal.mutate({
                        terminalId: terminal.id,
                        format: 'csv',
                        terminal,
                      })
                    }
                  >
                    <Boxes size={14} />
                  </button>
                  <button
                    aria-label={`Delete ${terminal.name}`}
                    disabled={removeTerminal.isPending}
                    title="Delete terminal"
                    type="button"
                    onClick={() => confirmDelete(terminal)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="register-foot">
          <span>{terminals.data?.length ?? 0} TERMINALS</span>
          <span>VERSIONED TERMINAL DOCUMENTS</span>
        </div>
      </section>
    </>
  );
}

function ModulePage({
  eyebrow,
  title,
  summary,
  Icon,
}: {
  eyebrow: string;
  title: string;
  summary: string;
  Icon: typeof Wrench;
}) {
  const activeTerminalId = useWorkspaceStore((state) => state.activeTerminalId);

  return (
    <>
      <PageHeading eyebrow={eyebrow} title={title} summary={summary} />
      <section className="module-state">
        <div className="module-index">
          <Icon size={23} strokeWidth={1.6} aria-hidden="true" />
          <span>{activeTerminalId ? 'READY' : 'IDLE'}</span>
        </div>
        <div className="module-message">
          <p className="eyebrow">{activeTerminalId ? 'ACTIVE TERMINAL' : 'NO ACTIVE TERMINAL'}</p>
          <h2>{activeTerminalId ? 'Workspace selected' : 'Select a terminal to continue'}</h2>
          <p>
            {activeTerminalId
              ? `Terminal ${activeTerminalId} is selected.`
              : 'Choose a terminal from the register to open this workspace.'}
          </p>
        </div>
        {!activeTerminalId && (
          <Link className="text-action" to="/terminals">
            Terminal register <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        )}
      </section>
    </>
  );
}

function VersionsPage() {
  const terminalId = useWorkspaceStore((state) => state.activeTerminalId);
  const queryClient = useQueryClient();
  const [message, setMessage] = useState('');
  const terminal = useQuery({
    queryKey: ['terminal', terminalId],
    queryFn: () => getTerminal(terminalId!),
    enabled: terminalId !== null,
  });
  const versions = useQuery({
    queryKey: ['terminal-versions', terminalId],
    queryFn: () => listTerminalVersions(terminalId!),
    enabled: terminalId !== null,
  });
  const restore = useMutation({
    mutationFn: (version: number) => restoreTerminalVersion(terminalId!, version),
    onSuccess: async (result) => {
      setMessage(`Version ${result.version} restored as the current version.`);
      await queryClient.invalidateQueries({ queryKey: ['terminal', terminalId] });
      await queryClient.invalidateQueries({ queryKey: ['terminal-versions', terminalId] });
      await queryClient.invalidateQueries({ queryKey: ['terminals'] });
    },
  });

  return (
    <>
      <PageHeading
        eyebrow="CHANGE HISTORY"
        title="Versions"
        summary={
          terminalId
            ? `Saved versions · ${terminal.data?.name ?? 'Loading terminal'}`
            : 'Terminal document history'
        }
        action={
          terminalId ? (
            <Link className="text-action" to={`/designer/${terminalId}`}>
              Open designer <ArrowUpRight size={16} />
            </Link>
          ) : undefined
        }
      />
      {!terminalId ? (
        <div className="register-message">
          Select a terminal from the register to view its version history.
        </div>
      ) : versions.isLoading ? (
        <div className="register-message">
          <LoaderCircle className="spin" size={18} /> Loading versions
        </div>
      ) : versions.isError ? (
        <div className="register-message error-message" role="alert">
          {versions.error.message}
        </div>
      ) : (
        <section className="version-history" aria-label="Terminal version history">
          {message && (
            <p className="version-status" role="status">
              {message}
            </p>
          )}
          {versions.data?.map((item) => (
            <div className="version-row" key={item.version}>
              <strong>V{item.version}</strong>
              <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time>
              <span>
                {item.version === terminal.data?.version ? 'Current' : item.note || 'Saved version'}
              </span>
              {item.version === terminal.data?.version ? (
                <span className="version-current">CURRENT</span>
              ) : (
                <button
                  className="secondary-action"
                  disabled={restore.isPending}
                  type="button"
                  onClick={() => {
                    setMessage('');
                    restore.mutate(item.version);
                  }}
                >
                  {restore.isPending ? (
                    <LoaderCircle className="spin" size={14} />
                  ) : (
                    <History size={14} />
                  )}
                  Restore
                </button>
              )}
            </div>
          ))}
        </section>
      )}
    </>
  );
}

type PlannerFormState = {
  direction: 'IN' | 'OUT' | 'TRANSFER';
  productId: string;
  sourceId: string;
  destinationId: string;
  volume: string;
  rate: string;
  windowFrom: string;
  windowTo: string;
};

type AvailabilityStatus = 'AVAILABLE' | 'MAINTENANCE' | 'FLUSHING' | 'CLEANING' | 'OUT_OF_SERVICE';

function AvailabilityPage() {
  const terminalId = useWorkspaceStore((state) => state.activeTerminalId);
  const queryClient = useQueryClient();
  const [elementId, setElementId] = useState('');
  const [status, setStatus] = useState<AvailabilityStatus>('MAINTENANCE');
  const [startsAt, setStartsAt] = useState(localDateTimeInputValue());
  const [endsAt, setEndsAt] = useState('');
  const [reason, setReason] = useState('');
  const [source, setSource] = useState('manual');
  const [externalRef, setExternalRef] = useState('');
  const [message, setMessage] = useState('');
  const terminal = useQuery({
    queryKey: ['terminal', terminalId],
    queryFn: () => getTerminal(terminalId!),
    enabled: terminalId !== null,
  });
  const windows = useQuery({
    queryKey: ['availability', terminalId],
    queryFn: () => listAvailabilityWindows(terminalId!),
    enabled: terminalId !== null,
  });
  const save = useMutation({
    mutationFn: () => {
      if (!terminalId) throw new Error('Select a terminal first.');
      return upsertAvailabilityWindows(terminalId, [
        {
          element_id: elementId,
          status,
          from: new Date(startsAt).toISOString(),
          ...(endsAt ? { to: new Date(endsAt).toISOString() } : {}),
          reason,
          source,
          ...(externalRef ? { external_ref: externalRef } : {}),
        },
      ]);
    },
    onSuccess: async (result) => {
      setMessage(
        result.rejected.length
          ? result.rejected.map((item) => item.reason).join('; ')
          : `${result.applied} availability window saved.`,
      );
      await queryClient.invalidateQueries({ queryKey: ['availability', terminalId] });
      await queryClient.invalidateQueries({ queryKey: ['confirmed-routes', terminalId] });
    },
  });
  const remove = useMutation({
    mutationFn: (windowId: string) => deleteAvailabilityWindow(terminalId!, windowId),
    onSuccess: async () => {
      setMessage('Availability window deleted. Affected confirmed routes may be outdated.');
      await queryClient.invalidateQueries({ queryKey: ['availability', terminalId] });
      await queryClient.invalidateQueries({ queryKey: ['confirmed-routes', terminalId] });
    },
  });

  if (!terminalId) {
    return (
      <ModulePage
        eyebrow="EQUIPMENT STATUS"
        title="Availability"
        summary="Maintenance and equipment windows"
        Icon={Activity}
      />
    );
  }

  const elements = terminal.data?.document.elements ?? [];
  return (
    <>
      <PageHeading
        eyebrow="EQUIPMENT STATUS"
        title="Availability"
        summary={
          terminal.data
            ? `${terminal.data.name} · V${terminal.data.version}`
            : 'Maintenance and equipment windows'
        }
        action={
          <Link className="text-action" to={`/designer/${terminalId}`}>
            Terminal graph <ArrowUpRight size={16} />
          </Link>
        }
      />
      {terminal.isLoading ? (
        <div className="register-message">
          <LoaderCircle className="spin" size={18} /> Loading terminal
        </div>
      ) : terminal.isError ? (
        <div className="register-message error-message" role="alert">
          {terminal.error.message}
        </div>
      ) : (
        <>
          <form
            className="availability-form"
            onSubmit={(event) => {
              event.preventDefault();
              save.mutate();
            }}
          >
            <label>
              Equipment
              <select
                required
                value={elementId}
                onChange={(event) => setElementId(event.target.value)}
              >
                <option value="">Select pipeline or component</option>
                {elements.map((element) => (
                  <option key={element.id} value={element.id}>
                    {element.id} · {element.type.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Status
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value as AvailabilityStatus)}
              >
                <option value="AVAILABLE">Available</option>
                <option value="MAINTENANCE">Maintenance</option>
                <option value="FLUSHING">Flushing</option>
                <option value="CLEANING">Cleaning</option>
                <option value="OUT_OF_SERVICE">Out of service</option>
              </select>
            </label>
            <label>
              From
              <input
                required
                type="datetime-local"
                value={startsAt}
                onChange={(event) => setStartsAt(event.target.value)}
              />
            </label>
            <label>
              To
              <input
                type="datetime-local"
                value={endsAt}
                onChange={(event) => setEndsAt(event.target.value)}
              />
            </label>
            <label>
              Reason
              <input
                maxLength={500}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            <label>
              Source
              <input
                maxLength={120}
                required
                value={source}
                onChange={(event) => setSource(event.target.value)}
              />
            </label>
            <label>
              External reference
              <input
                maxLength={255}
                value={externalRef}
                onChange={(event) => setExternalRef(event.target.value)}
              />
            </label>
            <button
              className="primary-action"
              disabled={save.isPending || elements.length === 0}
              type="submit"
            >
              {save.isPending ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />}
              Save window
            </button>
            {(save.isError || remove.isError) && (
              <p className="form-error" role="alert">
                {save.error?.message ?? remove.error?.message}
              </p>
            )}
            {message && (
              <p className="availability-message" role="status">
                {message}
              </p>
            )}
          </form>
          <section className="availability-list" aria-label="Availability windows">
            <div className="availability-list-heading">
              <strong>Scheduled windows</strong>
              <span>{windows.data?.length ?? 0}</span>
            </div>
            {windows.isLoading ? (
              <div className="register-message">
                <LoaderCircle className="spin" size={18} /> Loading windows
              </div>
            ) : windows.isError ? (
              <div className="register-message error-message" role="alert">
                {windows.error.message}
              </div>
            ) : windows.data?.length ? (
              windows.data.map((window) => (
                <div className="availability-row" key={window.id}>
                  <strong>{window.element_id}</strong>
                  <span
                    className={`availability-state is-${window.status.toLowerCase().replaceAll('_', '-')}`}
                  >
                    {window.status.replaceAll('_', ' ')}
                  </span>
                  <time dateTime={window.from}>{new Date(window.from).toLocaleString()}</time>
                  <span>{window.to ? new Date(window.to).toLocaleString() : 'Open ended'}</span>
                  <span>{window.reason || window.source}</span>
                  <button
                    aria-label={`Delete availability window for ${window.element_id}`}
                    disabled={remove.isPending}
                    title="Delete window"
                    type="button"
                    onClick={() => remove.mutate(window.id)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            ) : (
              <p className="planner-empty">No availability windows recorded for this terminal.</p>
            )}
          </section>
        </>
      )}
    </>
  );
}

function localDateTimeInputValue(date = new Date()): string {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

type RouteExclusion = RouteResponse['exclusions'][number];

const ROUTE_CRITERIA: Record<
  RouteExclusion['reason'],
  { id: string; title: string; rule: string }
> = {
  NOT_CERTIFIED: {
    id: 'C-01',
    title: 'Product certification',
    rule: 'Every route element must be certified for the selected product.',
  },
  VELOCITY: {
    id: 'C-02',
    title: 'Velocity limit',
    rule: 'Flow velocity must not exceed the product limit in any pipe.',
  },
  RESIDUE: {
    id: 'C-03',
    title: 'Residue and cleaning',
    rule: 'A route is rejected when the previous product requires manual cleaning.',
  },
  ONE_WAY_PUMP: {
    id: 'C-04',
    title: 'Pump direction',
    rule: 'A one-way pump cannot be traversed in reverse.',
  },
  UNAVAILABLE: {
    id: 'C-05',
    title: 'Equipment availability',
    rule: 'Unavailable equipment cannot be used during the requested job window.',
  },
  DEDICATED_OTHER_GROUP: {
    id: 'C-06',
    title: 'Equipment dedication',
    rule: 'Dedicated equipment must match the endpoint tank group or product.',
  },
  PUMP_HEAD: {
    id: 'C-07',
    title: 'Pump head',
    rule: 'Available pump head must cover route friction and elevation lift.',
  },
  ENDPOINT_STOCK: {
    id: 'C-08',
    title: 'Source stock',
    rule: 'The source tank must contain the requested transfer volume.',
  },
  ENDPOINT_SPACE: {
    id: 'C-09',
    title: 'Destination ullage',
    rule: 'The destination tank must have capacity for the requested volume.',
  },
  ENDPOINT_PRODUCT: {
    id: 'C-10',
    title: 'Endpoint product',
    rule: 'Tank contents and endpoint compatibility must match the selected product.',
  },
  ENDPOINT_DIRECTION: {
    id: 'C-11',
    title: 'Endpoint direction',
    rule: 'Source and destination must permit the requested operation direction.',
  },
  INVALID_PUMP_CURVE: {
    id: 'C-12',
    title: 'Pump curve validity',
    rule: 'A curve must be valid and configured on a pump element.',
  },
  PUMP_FLOW_OUT_OF_RANGE: {
    id: 'C-13',
    title: 'Pump flow range',
    rule: 'The requested minimum flow must fit within every pump and pipe limit.',
  },
  NO_PUMP_SYSTEM_INTERSECTION: {
    id: 'C-14',
    title: 'Operating point',
    rule: 'The pump curve must intersect the route system-head curve in range.',
  },
  PUMP_SPEED_OUT_OF_RANGE: {
    id: 'C-15',
    title: 'Pump speed range',
    rule: 'The operating point must fit the common permitted speed range.',
  },
  PUMP_SUCTION_MARGIN: {
    id: 'C-16',
    title: 'Suction margin',
    rule: 'Available NPSH must meet required NPSH plus the configured margin.',
  },
};

function RouteExclusionDetail({
  exclusion,
  onFocus,
}: {
  exclusion: RouteExclusion;
  onFocus?: (elementId: string) => void;
}) {
  const criterion = ROUTE_CRITERIA[exclusion.reason];
  return (
    <details className="route-exclusion-detail">
      <summary>
        <span>{criterion.id}</span> {criterion.title} · {exclusion.reason.replaceAll('_', ' ')}
      </summary>
      <p>{criterion.rule}</p>
      <p>{exclusion.detail}</p>
      {exclusion.element_id && onFocus && (
        <button
          className="route-exclusion-focus"
          type="button"
          onClick={() => onFocus(exclusion.element_id!)}
        >
          Focus {exclusion.element_id} in terminal
        </button>
      )}
    </details>
  );
}

type OptimizationJobDraft = {
  id: string;
  direction: PlannerFormState['direction'];
  productId: string;
  sourceId: string;
  destinationId: string;
  volume: string;
  rate: string;
  earliestStart: string;
  due: string;
  pumpSuctionInputs: Record<string, string>;
};

function createOptimizationJob(id: string): OptimizationJobDraft {
  return {
    id,
    direction: 'IN',
    productId: '',
    sourceId: '',
    destinationId: '',
    volume: '1000',
    rate: '500',
    earliestStart: '0',
    due: '400',
    pumpSuctionInputs: {},
  };
}

function OptimizationPage() {
  const terminalId = useWorkspaceStore((state) => state.activeTerminalId);
  const setActiveTerminal = useWorkspaceStore((state) => state.setActiveTerminal);
  const setFocusedRoute = useWorkspaceStore((state) => state.setFocusedRoute);
  const terminals = useQuery({ queryKey: ['terminals'], queryFn: listTerminals });
  const terminal = useQuery({
    queryKey: ['terminal', terminalId],
    queryFn: () => getTerminal(terminalId!),
    enabled: terminalId !== null,
  });
  const [horizonStart, setHorizonStart] = useState(localDateTimeInputValue());
  const [horizonMinutes, setHorizonMinutes] = useState('1000');
  const [jobs, setJobs] = useState<OptimizationJobDraft[]>([createOptimizationJob('job-1')]);
  const [preparation, setPreparation] = useState<OptimizationPreparation | null>(null);
  const [preparedScenario, setPreparedScenario] = useState<OptimizationScenario | null>(null);
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null);
  const [objectiveWeights, setObjectiveWeights] = useState({
    waiting: '1',
    lateness: '20',
    flush_volume: '1',
    valves: '2',
    shared_headers: '3',
  });
  const nodes = terminal.data?.document.nodes ?? [];
  const products = terminal.data?.document.products ?? [];
  const curvePumps = (terminal.data?.document.elements ?? []).filter(
    (element) => element.type === 'PUMP' && element.performance_curve,
  );
  const prepare = useMutation({
    mutationFn: (scenario: OptimizationScenario) => {
      if (!terminalId) throw new Error('Select a terminal first.');
      return prepareOptimization(terminalId, scenario);
    },
    onSuccess: (result, scenario) => {
      setPreparation(result);
      setPreparedScenario(scenario);
      setOptimizationResult(null);
    },
  });
  const optimize = useMutation({
    mutationFn: (scenario: OptimizationScenario) => {
      if (!terminalId) throw new Error('Select a terminal first.');
      return optimizeTerminal(terminalId, scenario);
    },
    onSuccess: setOptimizationResult,
  });

  useEffect(() => {
    setPreparation(null);
    setPreparedScenario(null);
    setOptimizationResult(null);
    setFocusedRoute(null);
  }, [terminalId, setFocusedRoute]);

  function updateJob(jobId: string, patch: Partial<OptimizationJobDraft>) {
    setPreparation(null);
    setPreparedScenario(null);
    setOptimizationResult(null);
    setJobs((current) => current.map((job) => (job.id === jobId ? { ...job, ...patch } : job)));
  }

  function submitPreparation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!terminalId || !terminal.data) return;
    const scenario: OptimizationScenario = {
      terminal_version: terminal.data.version,
      horizon_start: new Date(horizonStart).toISOString(),
      horizon_minutes: Number(horizonMinutes),
      objective_weights: {
        waiting: Number(objectiveWeights.waiting),
        lateness: Number(objectiveWeights.lateness),
        flush_volume: Number(objectiveWeights.flush_volume),
        valves: Number(objectiveWeights.valves),
        shared_headers: Number(objectiveWeights.shared_headers),
      },
      time_limit_seconds: 30,
      random_seed: 1,
      jobs: jobs.map((job) => ({
        id: job.id,
        direction: job.direction,
        product_id: job.productId,
        source_ids: [job.sourceId],
        destination_ids: [job.destinationId],
        volume_m3: Number(job.volume),
        rate_m3h: Number(job.rate),
        earliest_start_min: Number(job.earliestStart),
        due_min: Number(job.due),
        pump_suction_inputs: curvePumps
          .filter((pump) => job.pumpSuctionInputs[pump.id]?.trim())
          .map((pump) => ({
            pump_id: pump.id,
            npsh_available_m: Number(job.pumpSuctionInputs[pump.id]),
          })),
      })),
    };
    prepare.mutate(scenario);
  }

  function updateObjectiveWeight(key: keyof typeof objectiveWeights, value: string) {
    setObjectiveWeights((current) => ({ ...current, [key]: value }));
    setPreparation(null);
    setPreparedScenario(null);
    setOptimizationResult(null);
  }

  return (
    <>
      <PageHeading
        eyebrow="OPERATIONS PLANNING"
        title="Optimization"
        summary={
          terminal.data
            ? `${terminal.data.name} · V${terminal.data.version}`
            : 'Multi-job line-up workspace'
        }
        action={
          terminalId ? (
            <Link className="text-action" to={`/designer/${terminalId}`}>
              Terminal graph <ArrowUpRight size={16} />
            </Link>
          ) : null
        }
      />
      <div className="planner-terminal-picker">
        <label>
          Terminal
          <select
            value={terminalId ?? ''}
            onChange={(event) => setActiveTerminal(event.target.value || null)}
          >
            <option value="">Select terminal</option>
            {(terminals.data ?? []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
        {terminals.isError && <span role="alert">{terminals.error.message}</span>}
      </div>
      {!terminalId ? (
        <div className="register-message">
          Select a terminal to prepare an optimization scenario.
        </div>
      ) : terminal.isLoading ? (
        <div className="register-message">
          <LoaderCircle className="spin" size={18} /> Loading terminal
        </div>
      ) : terminal.isError ? (
        <div className="register-message error-message" role="alert">
          {terminal.error.message}
        </div>
      ) : terminal.data ? (
        <div className="optimization-workspace">
          <form className="optimization-scenario" onSubmit={submitPreparation}>
            <div className="planner-form-heading">
              <span className="eyebrow">STAGE 2 · SCENARIO</span>
              <strong>Jobs to schedule</strong>
            </div>
            <div className="optimization-horizon">
              <label>
                Horizon starts
                <input
                  required
                  type="datetime-local"
                  value={horizonStart}
                  onChange={(event) => {
                    setHorizonStart(event.target.value);
                    setPreparation(null);
                    setPreparedScenario(null);
                    setOptimizationResult(null);
                  }}
                />
              </label>
              <label>
                Horizon (min)
                <input
                  min="1"
                  max="10080"
                  required
                  step="1"
                  type="number"
                  value={horizonMinutes}
                  onChange={(event) => {
                    setHorizonMinutes(event.target.value);
                    setPreparation(null);
                    setPreparedScenario(null);
                    setOptimizationResult(null);
                  }}
                />
              </label>
            </div>
            <details className="optimization-weights">
              <summary>Objective weights</summary>
              <div className="optimization-weight-grid">
                <label>
                  Waiting
                  <input
                    min="0"
                    max="1000"
                    step="1"
                    type="number"
                    value={objectiveWeights.waiting}
                    onChange={(event) => updateObjectiveWeight('waiting', event.target.value)}
                  />
                </label>
                <label>
                  Lateness
                  <input
                    min="0"
                    max="1000"
                    step="1"
                    type="number"
                    value={objectiveWeights.lateness}
                    onChange={(event) => updateObjectiveWeight('lateness', event.target.value)}
                  />
                </label>
                <label>
                  Flush volume
                  <input
                    min="0"
                    max="1000"
                    step="1"
                    type="number"
                    value={objectiveWeights.flush_volume}
                    onChange={(event) => updateObjectiveWeight('flush_volume', event.target.value)}
                  />
                </label>
                <label>
                  Valves
                  <input
                    min="0"
                    max="1000"
                    step="1"
                    type="number"
                    value={objectiveWeights.valves}
                    onChange={(event) => updateObjectiveWeight('valves', event.target.value)}
                  />
                </label>
                <label>
                  Shared headers
                  <input
                    min="0"
                    max="1000"
                    step="1"
                    type="number"
                    value={objectiveWeights.shared_headers}
                    onChange={(event) =>
                      updateObjectiveWeight('shared_headers', event.target.value)
                    }
                  />
                </label>
              </div>
            </details>
            <div className="optimization-job-list">
              {jobs.map((job, index) => (
                <section className="optimization-job" key={job.id} aria-label={`Job ${index + 1}`}>
                  <div className="optimization-job-heading">
                    <strong>Job {String(index + 1).padStart(2, '0')}</strong>
                    <button
                      aria-label={`Remove job ${job.id}`}
                      disabled={jobs.length <= 1}
                      title="Remove job"
                      type="button"
                      onClick={() => {
                        setJobs((current) => current.filter((item) => item.id !== job.id));
                        setPreparation(null);
                        setPreparedScenario(null);
                        setOptimizationResult(null);
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="optimization-job-grid">
                    <label>
                      Job ID
                      <input
                        required
                        value={job.id}
                        onChange={(event) => updateJob(job.id, { id: event.target.value })}
                      />
                    </label>
                    <label>
                      Direction
                      <select
                        value={job.direction}
                        onChange={(event) =>
                          updateJob(job.id, {
                            direction: event.target.value as PlannerFormState['direction'],
                          })
                        }
                      >
                        <option value="IN">Inbound</option>
                        <option value="OUT">Outbound</option>
                        <option value="TRANSFER">Transfer</option>
                      </select>
                    </label>
                    <label>
                      Product
                      <select
                        required
                        value={job.productId}
                        onChange={(event) => updateJob(job.id, { productId: event.target.value })}
                      >
                        <option value="">Select product</option>
                        {products.map((product) => (
                          <option key={product.id} value={product.id}>
                            {product.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Source
                      <select
                        required
                        value={job.sourceId}
                        onChange={(event) => updateJob(job.id, { sourceId: event.target.value })}
                      >
                        <option value="">Select source</option>
                        {nodes.map((node) => (
                          <option key={node.id} value={node.id}>
                            {node.name ?? node.id}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Destination
                      <select
                        required
                        value={job.destinationId}
                        onChange={(event) =>
                          updateJob(job.id, { destinationId: event.target.value })
                        }
                      >
                        <option value="">Select destination</option>
                        {nodes.map((node) => (
                          <option key={node.id} value={node.id}>
                            {node.name ?? node.id}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Volume (m³)
                      <input
                        min="0.1"
                        required
                        step="any"
                        type="number"
                        value={job.volume}
                        onChange={(event) => updateJob(job.id, { volume: event.target.value })}
                      />
                    </label>
                    <label>
                      Minimum rate (m³/h)
                      <input
                        min="0.1"
                        required
                        step="any"
                        type="number"
                        value={job.rate}
                        onChange={(event) => updateJob(job.id, { rate: event.target.value })}
                      />
                    </label>
                    <label>
                      Earliest start (min)
                      <input
                        min="0"
                        required
                        step="1"
                        type="number"
                        value={job.earliestStart}
                        onChange={(event) =>
                          updateJob(job.id, { earliestStart: event.target.value })
                        }
                      />
                    </label>
                    <label>
                      Due (min)
                      <input
                        min="0"
                        required
                        step="1"
                        type="number"
                        value={job.due}
                        onChange={(event) => updateJob(job.id, { due: event.target.value })}
                      />
                    </label>
                  </div>
                  {curvePumps.length > 0 && (
                    <details className="optimization-suction">
                      <summary>Pump suction inputs</summary>
                      {curvePumps.map((pump) => (
                        <label key={pump.id}>
                          {pump.id} · available NPSH (m)
                          <input
                            min="0"
                            step="any"
                            type="number"
                            value={job.pumpSuctionInputs[pump.id] ?? ''}
                            onChange={(event) =>
                              updateJob(job.id, {
                                pumpSuctionInputs: {
                                  ...job.pumpSuctionInputs,
                                  [pump.id]: event.target.value,
                                },
                              })
                            }
                          />
                        </label>
                      ))}
                    </details>
                  )}
                </section>
              ))}
            </div>
            <div className="optimization-form-actions">
              <button
                className="secondary-action"
                type="button"
                onClick={() => {
                  setJobs((current) => [
                    ...current,
                    createOptimizationJob(`job-${crypto.randomUUID().slice(0, 8)}`),
                  ]);
                  setPreparation(null);
                  setPreparedScenario(null);
                  setOptimizationResult(null);
                }}
              >
                <Plus size={14} /> Add job
              </button>
              <button className="primary-action" disabled={prepare.isPending} type="submit">
                {prepare.isPending ? (
                  <LoaderCircle className="spin" size={16} />
                ) : (
                  <RouteIcon size={16} />
                )}
                Prepare candidates
              </button>
            </div>
            {prepare.isError && (
              <p className="form-error" role="alert">
                {prepare.error.message}
              </p>
            )}
          </form>
          <section className="optimization-review" aria-label="Candidate review" aria-live="polite">
            <div className="planner-results-heading">
              <div>
                <span className="eyebrow">STAGE 1 · CANDIDATE REVIEW</span>
                <strong>
                  {preparation
                    ? `${preparation.jobs.filter((job) => job.routes.length > 0).length}/${preparation.jobs.length} jobs routable`
                    : 'No scenario prepared'}
                </strong>
              </div>
              {preparation && <span>Terminal V{preparation.terminal_version}</span>}
            </div>
            {!preparation ? (
              <p className="planner-empty">
                Prepare the job set to inspect route candidates and blockers.
              </p>
            ) : (
              <div className="optimization-review-list">
                {preparedScenario && (
                  <button
                    className="primary-action optimization-run"
                    disabled={
                      optimize.isPending || preparation.jobs.some((job) => job.routes.length === 0)
                    }
                    type="button"
                    onClick={() => optimize.mutate(preparedScenario)}
                  >
                    {optimize.isPending ? (
                      <LoaderCircle className="spin" size={15} />
                    ) : (
                      <CalendarDays size={15} />
                    )}
                    Optimize lineup
                  </button>
                )}
                {preparation.jobs.map((job) => (
                  <section className="optimization-review-job" key={job.job_id}>
                    <div className="optimization-job-heading">
                      <strong>{job.job_id}</strong>
                      <span>{job.routes.length} candidate routes</span>
                    </div>
                    {job.routes.map((route) => (
                      <button
                        className="optimization-candidate"
                        key={`${job.job_id}-${route.rank}-${route.source_id}-${route.destination_id}`}
                        type="button"
                        onClick={() =>
                          setFocusedRoute({
                            terminalId,
                            elementIds: route.steps.map((step) => step.element_id),
                          })
                        }
                      >
                        <strong>
                          Route {route.rank} · {route.source_id} → {route.destination_id}
                        </strong>
                        <span>
                          {route.metrics.total_min} min ·{' '}
                          {route.steps.map((step) => step.element_id).join(' → ')}
                        </span>
                      </button>
                    ))}
                    {job.blockers.length > 0 && (
                      <details className="route-exclusions" open={job.routes.length === 0}>
                        <summary>{job.blockers.length} route blockers · criteria</summary>
                        {job.blockers.map((blocker, index) => (
                          <RouteExclusionDetail
                            exclusion={blocker}
                            key={`${job.job_id}-${blocker.element_id ?? blocker.node_id ?? 'blocker'}-${index}`}
                            onFocus={(elementId) =>
                              setFocusedRoute({ terminalId, elementIds: [elementId] })
                            }
                          />
                        ))}
                      </details>
                    )}
                  </section>
                ))}
              </div>
            )}
            {optimize.isError && (
              <p className="form-error" role="alert">
                {optimize.error.message}
              </p>
            )}
            {optimizationResult && (
              <section className="optimization-solve-result" aria-label="Optimization result">
                <div className="optimization-solve-heading">
                  <strong>{optimizationResult.status}</strong>
                  <span>
                    {optimizationResult.objective == null
                      ? 'No objective'
                      : `Objective ${optimizationResult.objective}`}
                    {optimizationResult.best_bound != null &&
                      ` · bound ${optimizationResult.best_bound}`}
                  </span>
                </div>
                <p className="optimization-result-detail">{optimizationResult.detail}</p>
                <dl className="optimization-kpis">
                  <div>
                    <dt>On time</dt>
                    <dd>{optimizationResult.kpis.on_time_jobs}</dd>
                  </div>
                  <div>
                    <dt>Lateness</dt>
                    <dd>{optimizationResult.kpis.total_lateness_min} min</dd>
                  </div>
                  <div>
                    <dt>Waiting</dt>
                    <dd>{optimizationResult.kpis.waiting_min} min</dd>
                  </div>
                  <div>
                    <dt>Makespan</dt>
                    <dd>{optimizationResult.kpis.makespan_min} min</dd>
                  </div>
                </dl>
                {optimizationResult.scheduled_jobs.map((scheduled) => (
                  <button
                    className="optimization-scheduled-job"
                    key={scheduled.job_id}
                    type="button"
                    onClick={() =>
                      setFocusedRoute({
                        terminalId,
                        elementIds: scheduled.route.steps.map((step) => step.element_id),
                      })
                    }
                  >
                    <strong>
                      {scheduled.job_id} · {scheduled.start_min}–{scheduled.end_min} min
                    </strong>
                    <span>
                      Route {scheduled.route.rank} ·{' '}
                      {scheduled.route.steps.map((step) => step.element_id).join(' → ')}
                      {scheduled.late_min > 0 && ` · ${scheduled.late_min} min late`}
                    </span>
                  </button>
                ))}
                {optimizationResult.unscheduled_jobs.map((unscheduled) => (
                  <details className="optimization-unscheduled" key={unscheduled.job_id} open>
                    <summary>
                      {unscheduled.job_id} · {unscheduled.detail}
                    </summary>
                    {unscheduled.conflict_elements.length > 0 && (
                      <p>Conflicting resources: {unscheduled.conflict_elements.join(', ')}</p>
                    )}
                    {unscheduled.blockers.map((blocker, index) => (
                      <RouteExclusionDetail
                        exclusion={blocker}
                        key={`${unscheduled.job_id}-${index}`}
                        onFocus={(elementId) =>
                          setFocusedRoute({ terminalId, elementIds: [elementId] })
                        }
                      />
                    ))}
                  </details>
                ))}
                {optimizationResult.element_timeline.length > 0 && (
                  <details className="optimization-timeline">
                    <summary>
                      {optimizationResult.element_timeline.length} element uses · timeline
                    </summary>
                    {optimizationResult.element_timeline.map((use, index) => (
                      <div key={`${use.element_id}-${use.job_id}-${index}`}>
                        <strong>{use.element_id}</strong>
                        <span>
                          {use.start_min}–{use.end_min} min · {use.job_id} · {use.product_id}
                        </span>
                      </div>
                    ))}
                  </details>
                )}
              </section>
            )}
          </section>
        </div>
      ) : null}
    </>
  );
}

function RoutePlannerPage() {
  const terminalId = useWorkspaceStore((state) => state.activeTerminalId);
  const setActiveTerminal = useWorkspaceStore((state) => state.setActiveTerminal);
  const setFocusedRoute = useWorkspaceStore((state) => state.setFocusedRoute);
  const queryClient = useQueryClient();
  const terminals = useQuery({ queryKey: ['terminals'], queryFn: listTerminals });
  const [form, setForm] = useState<PlannerFormState>({
    direction: 'IN',
    productId: '',
    sourceId: '',
    destinationId: '',
    volume: '4000',
    rate: '1000',
    windowFrom: localDateTimeInputValue(),
    windowTo: '',
  });
  const [result, setResult] = useState<RouteResponse | null>(null);
  const [routeRequest, setRouteRequest] = useState<RouteRequest | null>(null);
  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [confirmationMessage, setConfirmationMessage] = useState('');
  const terminal = useQuery({
    queryKey: ['terminal', terminalId],
    queryFn: () => getTerminal(terminalId!),
    enabled: terminalId !== null,
  });
  const confirmedRoutes = useQuery({
    queryKey: ['confirmed-routes', terminalId],
    queryFn: () => listConfirmedRoutes(terminalId!),
    enabled: terminalId !== null,
  });
  useEffect(() => {
    setResult(null);
    setRouteRequest(null);
    setSelectedRank(null);
    setConfirmationMessage('');
    setPumpSuctionInputs({});
    setFocusedRoute(null);
  }, [terminalId, setFocusedRoute]);
  const nodeChoices = terminal.data?.document.nodes ?? [];
  const productChoices = terminal.data?.document.products ?? [];
  const selectedSource = nodeChoices.find((node) => node.id === form.sourceId);
  const selectedDestination = nodeChoices.find((node) => node.id === form.destinationId);
  const selectedProduct = productChoices.find((product) => product.id === form.productId);
  const endpointRateLimits = [
    selectedSource?.max_rate_m3h,
    selectedDestination?.max_rate_m3h,
  ].filter((rate): rate is number => rate != null);
  const endpointRateLimit = endpointRateLimits.length > 0 ? Math.min(...endpointRateLimits) : null;
  const curvePumps = (terminal.data?.document.elements ?? []).filter(
    (element) => element.type === 'PUMP' && element.performance_curve,
  );
  const [pumpSuctionInputs, setPumpSuctionInputs] = useState<Record<string, string>>({});
  const updateField = <K extends keyof PlannerFormState>(key: K, value: PlannerFormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };
  const search = useMutation({
    mutationFn: ({ request }: { request: RouteRequest }) => requestRoutes(terminalId!, request),
    onSuccess: (response, variables) => {
      setResult(response);
      setRouteRequest(variables.request);
      setConfirmationMessage('');
      const first = response.routes[0];
      setSelectedRank(first?.rank ?? null);
      setFocusedRoute(
        first
          ? { terminalId: terminalId!, elementIds: first.steps.map((step) => step.element_id) }
          : null,
      );
    },
  });
  const confirm = useMutation({
    mutationFn: () => {
      const selected = result?.routes.find((route) => route.rank === selectedRank);
      if (!terminalId || !routeRequest || !selected)
        throw new Error('Select a feasible route first.');
      return confirmTerminalRoute(terminalId, routeRequest, selected);
    },
    onSuccess: async (confirmed) => {
      setConfirmationMessage(
        `Route ${confirmed.route.rank} confirmed against version ${confirmed.terminal_version}.`,
      );
      await queryClient.invalidateQueries({ queryKey: ['confirmed-routes', terminalId] });
    },
  });

  function submitRoute(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!terminalId || !form.sourceId || !form.destinationId || !form.productId) return;
    const request: RouteRequest = {
      direction: form.direction,
      product_id: form.productId,
      volume_m3: Number(form.volume),
      rate_m3h: Number(form.rate),
      window_from: new Date(form.windowFrom).toISOString(),
      ...(form.windowTo ? { window_to: new Date(form.windowTo).toISOString() } : {}),
      source_ids: [form.sourceId],
      destination_ids: [form.destinationId],
      max_routes: 5,
      ...(curvePumps.some((pump) => pumpSuctionInputs[pump.id]?.trim())
        ? {
            pump_suction_inputs: curvePumps
              .filter((pump) => pumpSuctionInputs[pump.id]?.trim())
              .map((pump) => ({
                pump_id: pump.id,
                npsh_available_m: Number(pumpSuctionInputs[pump.id]),
              })),
          }
        : {}),
    };
    search.mutate({ request });
  }

  const selectedRoute = result?.routes.find((route) => route.rank === selectedRank);
  return (
    <>
      <PageHeading
        eyebrow="OPERATIONS PLANNING"
        title="Route planner"
        summary={
          terminal.data
            ? `${terminal.data.name} · V${terminal.data.version}`
            : 'Transfer route workspace'
        }
        action={
          terminalId ? (
            <Link className="text-action" to={`/designer/${terminalId}`}>
              Terminal graph <ArrowUpRight size={16} />
            </Link>
          ) : null
        }
      />
      <div className="planner-terminal-picker">
        <label>
          Terminal
          <select
            value={terminalId ?? ''}
            onChange={(event) => setActiveTerminal(event.target.value || null)}
          >
            <option value="">Select terminal</option>
            {(terminals.data ?? []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
        {terminals.isError && <span role="alert">{terminals.error.message}</span>}
      </div>
      {!terminalId ? (
        <div className="register-message">Select a terminal to prepare a route request.</div>
      ) : terminal.isLoading ? (
        <div className="register-message">
          <LoaderCircle className="spin" size={18} /> Loading terminal
        </div>
      ) : terminal.isError ? (
        <div className="register-message error-message" role="alert">
          {terminal.error.message}
        </div>
      ) : (
        <div className="planner-grid">
          <form className="planner-form" onSubmit={submitRoute}>
            <div className="planner-form-heading">
              <span className="eyebrow">SINGLE OPERATION</span>
              <strong>Route request</strong>
            </div>
            <label>
              Direction
              <select
                value={form.direction}
                onChange={(event) =>
                  updateField('direction', event.target.value as PlannerFormState['direction'])
                }
              >
                <option value="IN">Inbound</option>
                <option value="OUT">Outbound</option>
                <option value="TRANSFER">Transfer</option>
              </select>
            </label>
            <label>
              Product
              <select
                required
                value={form.productId}
                onChange={(event) => updateField('productId', event.target.value)}
              >
                <option value="">Select product</option>
                {productChoices.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Source
              <select
                required
                value={form.sourceId}
                onChange={(event) => updateField('sourceId', event.target.value)}
              >
                <option value="">Select source</option>
                {nodeChoices.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.name ?? node.id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Destination
              <select
                required
                value={form.destinationId}
                onChange={(event) => updateField('destinationId', event.target.value)}
              >
                <option value="">Select destination</option>
                {nodeChoices.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.name ?? node.id}
                  </option>
                ))}
              </select>
            </label>
            <div className="planner-number-fields">
              <label>
                Volume (m³)
                <input
                  min="0.1"
                  step="any"
                  required
                  type="number"
                  value={form.volume}
                  onChange={(event) => updateField('volume', event.target.value)}
                />
              </label>
              <label>
                Rate (m³/h)
                <input
                  min="0.1"
                  step="any"
                  required
                  type="number"
                  value={form.rate}
                  onChange={(event) => updateField('rate', event.target.value)}
                />
              </label>
            </div>
            <label>
              Window starts
              <input
                required
                type="datetime-local"
                value={form.windowFrom}
                onChange={(event) => updateField('windowFrom', event.target.value)}
              />
            </label>
            <label>
              Window ends
              <input
                type="datetime-local"
                value={form.windowTo}
                onChange={(event) => updateField('windowTo', event.target.value)}
              />
            </label>
            <section
              className="planner-constraints"
              aria-label="Constraints applied to this request"
            >
              <strong>Criteria in force</strong>
              <dl>
                <div>
                  <dt>Rate</dt>
                  <dd>
                    {form.rate || '—'} m³/h minimum
                    {endpointRateLimit != null && ` · endpoint limit ${endpointRateLimit} m³/h`}
                    {selectedProduct?.max_velocity != null &&
                      ` · ${selectedProduct.max_velocity} m/s velocity cap`}
                  </dd>
                </div>
                <div>
                  <dt>Endpoints</dt>
                  <dd>
                    {selectedSource
                      ? `${selectedSource.id}: ${selectedSource.type === 'TANK' ? `${selectedSource.stock_m3 ?? 0} m³ stock` : 'source direction and product certification'}`
                      : 'Select a source'}
                    {' · '}
                    {selectedDestination
                      ? `${selectedDestination.id}: ${selectedDestination.type === 'TANK' ? `${Math.max(0, (selectedDestination.capacity_m3 ?? 0) - (selectedDestination.stock_m3 ?? 0))} m³ free` : 'destination direction and product certification'}`
                      : 'select a destination'}
                  </dd>
                </div>
                <div>
                  <dt>Equipment</dt>
                  <dd>
                    Product certification and availability are enforced for the full job window.
                    {curvePumps.length > 0 &&
                      ` Curve pumps require an in-range operating point and NPSHa at least NPSHr plus margin (${curvePumps.map((pump) => `${pump.id}: ${pump.npsh_required_m ?? 'unset'} + ${pump.npsh_margin_m ?? 0.5} m`).join('; ')}).`}
                  </dd>
                </div>
              </dl>
            </section>
            {curvePumps.length > 0 && (
              <div className="planner-suction-inputs">
                <strong>Curve pump suction</strong>
                {curvePumps.map((pump) => (
                  <label key={pump.id}>
                    {pump.id} · available NPSH (m)
                    <input
                      min="0"
                      step="any"
                      type="number"
                      value={pumpSuctionInputs[pump.id] ?? ''}
                      onChange={(event) =>
                        setPumpSuctionInputs((current) => ({
                          ...current,
                          [pump.id]: event.target.value,
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
            )}
            <button
              className="primary-action planner-submit"
              disabled={search.isPending || !terminal.data}
              type="submit"
            >
              {search.isPending ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <RouteIcon size={16} />
              )}
              Find feasible routes
            </button>
            {search.isError && (
              <p className="form-error" role="alert">
                {search.error.message}
              </p>
            )}
          </form>
          <section className="planner-results" aria-label="Route results" aria-live="polite">
            <div className="planner-results-heading">
              <div>
                <span className="eyebrow">FEASIBILITY SHORTLIST</span>
                <strong>{result ? `${result.routes.length} routes` : 'No request yet'}</strong>
              </div>
              {result && (
                <span>
                  V{result.terminal_version} · Engine {result.engine_version}
                </span>
              )}
            </div>
            {!result ? (
              <p className="planner-empty">
                Choose the operation endpoints and product to calculate a route.
              </p>
            ) : result.routes.length === 0 ? (
              <div className="no-route-result">
                <strong>{result.no_route?.message ?? 'No feasible route found.'}</strong>
                {(result.no_route?.blockers.length ? result.no_route.blockers : result.exclusions)
                  .length > 0 && (
                  <details className="route-exclusions" open>
                    <summary>
                      Review {result.no_route?.blockers.length || result.exclusions.length} rejected
                      criteria
                    </summary>
                    {(result.no_route?.blockers.length
                      ? result.no_route.blockers
                      : result.exclusions
                    ).map((exclusion, index) => (
                      <RouteExclusionDetail
                        exclusion={exclusion}
                        key={`${exclusion.element_id ?? exclusion.node_id ?? 'issue'}-${index}`}
                        onFocus={(elementId) =>
                          setFocusedRoute({ terminalId, elementIds: [elementId] })
                        }
                      />
                    ))}
                  </details>
                )}
              </div>
            ) : (
              <>
                <div className="route-shortlist">
                  {result.routes.map((route) => (
                    <button
                      aria-pressed={selectedRank === route.rank}
                      className={`route-choice${selectedRank === route.rank ? ' is-selected' : ''}`}
                      key={`${route.rank}-${route.source_id}-${route.destination_id}`}
                      type="button"
                      onClick={() => {
                        setSelectedRank(route.rank);
                        setConfirmationMessage('');
                        setFocusedRoute({
                          terminalId,
                          elementIds: route.steps.map((step) => step.element_id),
                        });
                      }}
                    >
                      <span className="route-choice-rank">
                        {String(route.rank).padStart(2, '0')}
                      </span>
                      <span className="route-choice-body">
                        <strong>
                          {route.metrics.total_min} min · {route.source_id} to{' '}
                          {route.destination_id}
                        </strong>
                        <span>{route.steps.map((step) => step.element_id).join(' → ')}</span>
                      </span>
                      <span className="route-choice-metrics">
                        <span>Flush {route.metrics.flush_volume_m3} m³</span>
                        <span>
                          {route.metrics.valves} valves · {route.metrics.common_headers} shared
                        </span>
                        {route.metrics.operating_flow_m3h != null && (
                          <span>Operating {route.metrics.operating_flow_m3h.toFixed(1)} m³/h</span>
                        )}
                        {route.metrics.pump_head_m != null && (
                          <span>Pump {route.metrics.pump_head_m.toFixed(1)} m head</span>
                        )}
                        {route.metrics.system_head_m != null && (
                          <span>System {route.metrics.system_head_m.toFixed(1)} m head</span>
                        )}
                        {route.metrics.suction_margin_m != null && (
                          <span>Suction margin {route.metrics.suction_margin_m.toFixed(1)} m</span>
                        )}
                        {route.metrics.pump_speed_ratio != null && (
                          <span>Speed {(route.metrics.pump_speed_ratio * 100).toFixed(0)}%</span>
                        )}
                      </span>
                    </button>
                  ))}
                </div>
                {result.exclusions.length > 0 && (
                  <details className="route-exclusions">
                    <summary>{result.exclusions.length} excluded items · view criteria</summary>
                    {result.exclusions.map((exclusion, index) => (
                      <RouteExclusionDetail
                        exclusion={exclusion}
                        key={`${exclusion.element_id ?? exclusion.node_id ?? 'issue'}-${index}`}
                        onFocus={(elementId) =>
                          setFocusedRoute({ terminalId, elementIds: [elementId] })
                        }
                      />
                    ))}
                  </details>
                )}
                {selectedRoute && (
                  <div className="route-confirm-bar">
                    <span>
                      Route {selectedRoute.rank} selected ·{' '}
                      {selectedRoute.metrics.head_margin_m.toFixed(1)} m head margin
                    </span>
                    <button
                      className="primary-action"
                      disabled={confirm.isPending}
                      type="button"
                      onClick={() => confirm.mutate()}
                    >
                      {confirm.isPending ? (
                        <LoaderCircle className="spin" size={15} />
                      ) : (
                        <Save size={15} />
                      )}
                      Confirm route
                    </button>
                  </div>
                )}
                {confirmationMessage && (
                  <p className="version-status" role="status">
                    {confirmationMessage}
                  </p>
                )}
                {confirm.isError && (
                  <p className="form-error" role="alert">
                    {confirm.error.message}
                  </p>
                )}
              </>
            )}
          </section>
        </div>
      )}
      {confirmedRoutes.data && confirmedRoutes.data.length > 0 && (
        <section className="confirmed-routes" aria-label="Confirmed routes">
          <div className="confirmed-routes-heading">
            <strong>Confirmed routes</strong>
            <span>{confirmedRoutes.data.length}</span>
          </div>
          {confirmedRoutes.data.map((confirmed) => (
            <button
              className="confirmed-route-row"
              key={confirmed.id}
              type="button"
              onClick={() =>
                setFocusedRoute({
                  terminalId: terminalId!,
                  elementIds: confirmed.route.steps.map((step) => step.element_id),
                })
              }
            >
              <strong>Route {confirmed.route.rank}</strong>
              <span>
                V{confirmed.terminal_version} · {confirmed.route.metrics.total_min} min
              </span>
              {confirmed.outdated && <span className="confirmed-outdated">OUTDATED</span>}
              <time dateTime={confirmed.created_at}>
                {new Date(confirmed.created_at).toLocaleString()}
              </time>
            </button>
          ))}
        </section>
      )}
    </>
  );
}

const NODE_TYPES: TerminalNode['type'][] = [
  'TANK',
  'JETTY',
  'LOADING_POINT',
  'RAIL_PLATFORM',
  'RAIL_CAR',
  'MANIFOLD',
  'JUNCTION',
];
const PIPE_TYPES: TerminalElement['type'][] = ['LINE', 'SEGMENT', 'COMMON_HEADER', 'TANK_HEADER'];
const INLINE_COMPONENTS: TerminalElement['type'][] = ['PUMP', 'VALVE'];

function DesignerEntry() {
  const activeTerminalId = useWorkspaceStore((state) => state.activeTerminalId);
  return activeTerminalId ? (
    <Navigate to={`/designer/${activeTerminalId}`} replace />
  ) : (
    <Navigate to="/terminals" replace />
  );
}

function TerminalDesigner() {
  const { terminalId = '' } = useParams();
  const setActiveTerminal = useWorkspaceStore((state) => state.setActiveTerminal);
  const terminal = useQuery({
    queryKey: ['terminal', terminalId],
    queryFn: () => getTerminal(terminalId),
  });

  // The designer only ever edits the session's active terminal: the URL is the explicit choice,
  // so record it once (persisted) and keep the topbar and designer in agreement.
  useEffect(() => {
    if (terminalId && useWorkspaceStore.getState().activeTerminalId !== terminalId) {
      setActiveTerminal(terminalId);
    }
  }, [terminalId, setActiveTerminal]);

  if (terminal.isLoading)
    return (
      <div className="register-message">
        <LoaderCircle className="spin" size={18} /> Loading terminal
      </div>
    );
  if (terminal.isError) {
    return (
      <div className="register-message error-message" role="alert">
        <CircleAlert size={18} /> {terminal.error.message}
        <Link className="text-action" to="/terminals">
          Terminal register
        </Link>
      </div>
    );
  }
  if (!terminal.data)
    return <div className="register-message">Terminal document is unavailable.</div>;

  return (
    <TerminalEditor
      key={terminalId}
      terminalId={terminalId}
      name={terminal.data.name}
      initialDocument={terminal.data.document}
      version={terminal.data.version}
    />
  );
}

function layoutMap(document: TerminalDocument, key: string): Record<string, string> {
  const value = document.layout?.[key];
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, string>)
    : {};
}

type Point = { x: number; y: number };
type ConceptualLink = { id: string; from: string; to: string; label: string; color: string };
type PanOrigin = {
  clientX: number;
  clientY: number;
  scaleX: number;
  scaleY: number;
  viewX: number;
  viewY: number;
};

function layoutList<T>(document: TerminalDocument, key: string): T[] {
  const value = document.layout?.[key];
  return Array.isArray(value) ? (value as T[]) : [];
}

function equipmentPorts(type: TerminalNode['type']): Point[] {
  switch (type) {
    case 'MANIFOLD':
      return [
        { x: -29, y: 0 },
        { x: 29, y: 0 },
        { x: -14, y: -17 },
        { x: 14, y: -17 },
        { x: 0, y: 17 },
      ];
    case 'JUNCTION':
      return [
        { x: -38, y: 0 },
        { x: 38, y: 0 },
        { x: 0, y: -27 },
        { x: 0, y: 27 },
      ];
    case 'JETTY':
    case 'LOADING_POINT':
      return [
        { x: -43, y: 0 },
        { x: 43, y: 0 },
        { x: 0, y: -20 },
      ];
    case 'RAIL_PLATFORM':
      return [
        { x: -50, y: 0 },
        { x: 50, y: 0 },
      ];
    case 'RAIL_CAR':
      return [
        { x: -38, y: 0 },
        { x: 38, y: 0 },
      ];
    default:
      return [
        { x: -34, y: 0 },
        { x: 34, y: 0 },
        { x: 0, y: -18 },
        { x: 0, y: 18 },
      ];
  }
}

function nearestPort(node: TerminalNode, position: Point, target: Point): Point {
  return equipmentPorts(node.type)
    .map((port) => ({ x: position.x + port.x, y: position.y + port.y }))
    .sort(
      (left, right) =>
        Math.hypot(left.x - target.x, left.y - target.y) -
        Math.hypot(right.x - target.x, right.y - target.y),
    )[0];
}

function EquipmentGlyph({ type, color }: { type: TerminalNode['type']; color: string }) {
  const common = { fill: color, stroke: '#532a85', strokeWidth: 2 };
  switch (type) {
    case 'TANK':
      return (
        <g className="glyph-tank" {...common}>
          <rect x="-34" y="-17" width="68" height="37" />
          <ellipse cx="0" cy="-17" rx="34" ry="9" />
          <ellipse cx="0" cy="20" rx="34" ry="9" />
          <path d="M-24 -17v37M24 -17v37" fill="none" />
          <ellipse cx="0" cy="-17" rx="24" ry="5" fill="#eef0f6" />
        </g>
      );
    case 'JETTY':
      return (
        <g className="glyph-jetty" {...common}>
          <path d="M-42 -17h84v14h-84zM-30 -3v28M0 -3v28M30 -3v28" />
          <path d="M-48 26h96M-44 31h88" fill="none" />
          <path d="M-10 -17v-16h24v16M6 -33h14" fill="none" strokeWidth="3" />
        </g>
      );
    case 'LOADING_POINT':
      return (
        <g className="glyph-loading" {...common}>
          <path d="M-38 18h76v9h-76zM-29 18v-25h12v25M-17 -7h40l14 12" />
          <circle cx="37" cy="6" r="5" fill="#eef0f6" />
          <path d="M-23 27v8M23 27v8" fill="none" />
        </g>
      );
    case 'RAIL_PLATFORM':
      return (
        <g className="glyph-platform" {...common}>
          <path d="M-48 -5h96v12h-96zM-39 7v18M39 7v18M-52 26h104M-44 31h88" />
          <path d="M-35 14h70M-30 18h60" fill="none" stroke="#532a85" />
        </g>
      );
    case 'RAIL_CAR':
      return (
        <g className="glyph-car" {...common}>
          <path d="M-39 -4h78v23h-78zM-30 -4v-13h18v13M-8 -4v-13h18v13M14 -4v-13h17v13" />
          <circle cx="-23" cy="23" r="6" fill="#532a85" />
          <circle cx="23" cy="23" r="6" fill="#532a85" />
        </g>
      );
    case 'MANIFOLD':
      return (
        <g className="glyph-manifold" {...common}>
          <path d="M-40 0h80M-20 0v-23M0 0v23M20 0v-23" fill="none" strokeWidth="7" />
          <circle cx="-20" cy="-25" r="5" />
          <circle cx="0" cy="25" r="5" />
          <circle cx="20" cy="-25" r="5" />
        </g>
      );
    default:
      return (
        <g className="glyph-junction" {...common}>
          <path d="M-38 0h76M0 -27v54" fill="none" strokeWidth="7" />
          <circle cx="0" cy="0" r="12" />
        </g>
      );
  }
}

function TerminalGraphLayers({
  graph,
  availabilityWindows,
  zoom,
  labelScale,
  routeElementIds,
}: {
  graph: TerminalGraph;
  availabilityWindows: AvailabilityWindow[];
  zoom: number;
  labelScale: number;
  routeElementIds: string[];
}) {
  const positions = graph.nodes.map((node, index) => ({
    node,
    x: typeof node.x === 'number' ? node.x : 100 + (index % 6) * 170,
    y: typeof node.y === 'number' ? node.y : 100 + Math.floor(index / 6) * 135,
  }));
  const positionById = new Map(positions.map(({ node, x, y }) => [node.id, { x, y }]));
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const availabilityByElement = new Map<string, AvailabilityWindow[]>();
  for (const window of availabilityWindows) {
    const existing = availabilityByElement.get(window.element_id) ?? [];
    existing.push(window);
    availabilityByElement.set(window.element_id, existing);
  }
  const arcsByElement = new Map<string, TerminalGraph['arcs']>();
  for (const arc of graph.arcs) {
    const arcs = arcsByElement.get(arc.element_id) ?? [];
    arcs.push(arc);
    arcsByElement.set(arc.element_id, arcs);
  }
  const parallelGroups = new Map<string, TerminalElement[]>();
  for (const element of graph.elements) {
    const endpoints = [element.from, element.to].sort();
    const key = `${endpoints[0]}|${endpoints[1]}`;
    const group = parallelGroups.get(key) ?? [];
    group.push(element);
    parallelGroups.set(key, group);
  }
  const parallelOffsets = new Map<string, number>();
  for (const group of parallelGroups.values()) {
    [...group]
      .sort((left, right) => left.id.localeCompare(right.id))
      .forEach((element, index) => {
        parallelOffsets.set(element.id, (index - (group.length - 1) / 2) * 36);
      });
  }
  const now = Date.now();
  const availabilityLabels: Record<AvailabilityStatus, string> = {
    AVAILABLE: 'OK',
    MAINTENANCE: 'MAINT',
    FLUSHING: 'FLUSH',
    CLEANING: 'CLEAN',
    OUT_OF_SERVICE: 'OFF',
  };

  return (
    <g className="terminal-graph-layers">
      <defs>
        <marker
          id="graph-arrow"
          markerHeight="8"
          markerWidth="8"
          markerUnits="userSpaceOnUse"
          orient="auto-start-reverse"
          refX="7"
          refY="4"
          viewBox="0 0 8 8"
        >
          <path d="M0 0L8 4L0 8Z" fill="#532a85" />
        </marker>
      </defs>
      {graph.elements.map((element) => {
        const fromCenter = positionById.get(element.from);
        const toCenter = positionById.get(element.to);
        const fromNode = nodeById.get(element.from);
        const toNode = nodeById.get(element.to);
        if (!fromCenter || !toCenter || !fromNode || !toNode) return null;
        const from = nearestPort(fromNode, fromCenter, toCenter);
        const to = nearestPort(toNode, toCenter, fromCenter);
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const length = Math.hypot(dx, dy) || 1;
        const offset = parallelOffsets.get(element.id) ?? 0;
        const middleX = (from.x + to.x) / 2 - (dy / length) * offset;
        const middleY = (from.y + to.y) / 2 + (dx / length) * offset;
        const edgeArcs = arcsByElement.get(element.id) ?? [];
        const forward = edgeArcs.find((arc) => !arc.reversed);
        const reverse = edgeArcs.find((arc) => arc.reversed);
        if (!forward) return null;
        const windows = availabilityByElement.get(element.id) ?? [];
        const activeWindow = windows.find((window) => {
          const start = Date.parse(window.from);
          const end = window.to ? Date.parse(window.to) : Number.POSITIVE_INFINITY;
          return start <= now && now < end;
        });
        const nextWindow = windows
          .filter((window) => Date.parse(window.from) > now)
          .sort((left, right) => Date.parse(left.from) - Date.parse(right.from))[0];
        const visibleWindow = activeWindow ?? nextWindow;
        const unavailableNow = activeWindow !== undefined && activeWindow.status !== 'AVAILABLE';
        const color =
          element.type === 'PUMP' ? '#d98a00' : element.type === 'VALVE' ? '#5d57a2' : '#5d57a2';
        return (
          <g
            className={`graph-edge${routeElementIds.includes(element.id) ? ' is-route-highlight' : ''}`}
            key={element.id}
          >
            <path
              d={`M ${from.x} ${from.y} Q ${middleX} ${middleY} ${to.x} ${to.y}`}
              markerEnd={forward.traversable ? 'url(#graph-arrow)' : undefined}
              markerStart={reverse?.traversable ? 'url(#graph-arrow)' : undefined}
              stroke={unavailableNow ? '#a43d31' : color}
            />
            {visibleWindow && (
              <g
                className={`graph-availability-marker${unavailableNow ? ' is-active' : ' is-scheduled'}`}
                transform={`translate(${middleX} ${middleY + 18})`}
              >
                <title>
                  {visibleWindow.status.replaceAll('_', ' ')} ·{' '}
                  {visibleWindow.reason || 'No reason supplied'} ·{' '}
                  {new Date(visibleWindow.from).toLocaleString()}
                </title>
                <rect x="-22" y="-7" width="44" height="14" rx="2" />
                <text textAnchor="middle" y="3">
                  {availabilityLabels[visibleWindow.status]}
                </text>
              </g>
            )}
            {zoom >= 0.55 && (
              <text
                className="graph-edge-label"
                x={middleX}
                y={middleY - 8}
                style={{ fontSize: 9 * labelScale }}
              >
                <title>
                  {element.type}: {element.id}
                </title>
                {element.id.replace(/^element-/, '').slice(0, 5)}
              </text>
            )}
            {reverse && !reverse.traversable && (
              <g className="graph-restriction" transform={`translate(${middleX} ${middleY})`}>
                <title>Reverse flow blocked by one-way pump</title>
                <circle r="10" />
                <path d="M-4 -4L4 4M4 -4L-4 4" />
              </g>
            )}
          </g>
        );
      })}
      {positions.map(({ node, x, y }) => (
        <g className="graph-node" key={node.id} transform={`translate(${x}, ${y})`}>
          <EquipmentGlyph type={node.type} color="#c8d4e1" />
          <text className="node-name" x="0" y="51" style={{ fontSize: 13 * labelScale }}>
            {node.name ?? node.id}
          </text>
        </g>
      ))}
    </g>
  );
}

function initialSceneView(document: TerminalDocument): { x: number; y: number; zoom: number } {
  if (document.nodes.length === 0) return { x: 0, y: 0, zoom: 1 };
  const positions = document.nodes.map((node, index) => ({
    x: typeof node.x === 'number' ? node.x : 100 + (index % 6) * 170,
    y: typeof node.y === 'number' ? node.y : 100 + Math.floor(index / 6) * 135,
  }));
  const minX = Math.min(...positions.map(({ x }) => x - 80));
  const maxX = Math.max(...positions.map(({ x }) => x + 80));
  const minY = Math.min(...positions.map(({ y }) => y - 80));
  const maxY = Math.max(...positions.map(({ y }) => y + 90));
  const width = maxX - minX + 80;
  const height = maxY - minY + 80;
  const zoom = Math.max(0.12, Math.min(1, 1020 / width, 560 / height));
  return {
    x: (minX + maxX - 1100 / zoom) / 2,
    y: (minY + maxY - 620 / zoom) / 2,
    zoom,
  };
}

function sceneViewBoxSize(aspectRatio: number, zoom: number) {
  const aspect = aspectRatio > 0 ? aspectRatio : 1100 / 620;
  return {
    width: Math.max(1100, 620 * aspect) / zoom,
    height: Math.max(620, 1100 / aspect) / zoom,
  };
}

function fitTerminalScene(document: TerminalDocument, aspectRatio: number) {
  if (document.nodes.length === 0) return { x: 0, y: 0, zoom: 1 };
  const positions = document.nodes.map((node, index) => ({
    x: typeof node.x === 'number' ? node.x : 100 + (index % 6) * 170,
    y: typeof node.y === 'number' ? node.y : 100 + Math.floor(index / 6) * 135,
  }));
  const minX = Math.min(...positions.map(({ x }) => x - 80));
  const maxX = Math.max(...positions.map(({ x }) => x + 80));
  const minY = Math.min(...positions.map(({ y }) => y - 80));
  const maxY = Math.max(...positions.map(({ y }) => y + 90));
  const contentWidth = maxX - minX + 80;
  const contentHeight = maxY - minY + 80;
  const aspect = aspectRatio > 0 ? aspectRatio : 1100 / 620;
  const baseWidth = Math.max(1100, 620 * aspect);
  const baseHeight = Math.max(620, 1100 / aspect);
  const zoom = Math.min(
    5,
    Math.max(
      0.12,
      Math.min((baseWidth * 0.88) / contentWidth, (baseHeight * 0.84) / contentHeight),
    ),
  );
  const viewBox = sceneViewBoxSize(aspect, zoom);
  return {
    x: (minX + maxX - viewBox.width) / 2,
    y: (minY + maxY - viewBox.height) / 2,
    zoom,
  };
}

function TerminalEditor({
  terminalId,
  name,
  initialDocument,
  version,
}: {
  terminalId: string;
  name: string;
  initialDocument: TerminalDocument;
  version: number;
}) {
  const queryClient = useQueryClient();
  const focusedRoute = useWorkspaceStore((state) => state.focusedRoute);
  const [history, setHistory] = useState(() => createHistory(structuredClone(initialDocument)));
  const document = history.present;
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [selectedConceptualLinkId, setSelectedConceptualLinkId] = useState<string | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragPreview, setDragPreview] = useState<{ x: number; y: number } | null>(null);
  const dragStartPosition = useRef<{ x: number; y: number } | null>(null);
  const suppressNodeClick = useRef(false);
  const popoverRef = useRef<HTMLElement>(null);
  const sceneRef = useRef<SVGSVGElement>(null);
  const panStart = useRef<PanOrigin | null>(null);
  const [validationIssues, setValidationIssues] = useState<ValidationIssue[]>([]);
  const [validationOpen, setValidationOpen] = useState(false);
  const [validationPending, setValidationPending] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [sceneView, setSceneView] = useState(() => initialSceneView(initialDocument));
  const [canvasAspect, setCanvasAspect] = useState(1100 / 620);
  const [connectFrom, setConnectFrom] = useState<string | null>(null);
  const [drawingMode, setDrawingMode] = useState<'pipeline' | 'component' | 'conceptual' | null>(
    null,
  );
  const [pipelineType, setPipelineType] = useState<TerminalElement['type']>('LINE');
  const [componentType, setComponentType] = useState<TerminalElement['type']>('PUMP');
  const [snapToGrid, setSnapToGrid] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [editorMessage, setEditorMessage] = useState('');
  const [savedVersion, setSavedVersion] = useState(version);
  const [viewMode, setViewMode] = useState<'layout' | 'graph'>('layout');
  const terminalGraph = useQuery({
    queryKey: ['terminal-graph', terminalId, savedVersion],
    queryFn: () => getTerminalGraph(terminalId, savedVersion),
    enabled: viewMode === 'graph',
  });
  const graphAvailability = useQuery({
    queryKey: ['availability', terminalId],
    queryFn: () => listAvailabilityWindows(terminalId),
    enabled: viewMode === 'graph',
  });
  useEffect(() => {
    const svg = sceneRef.current;
    if (!svg) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) setCanvasAspect(width / height);
    });
    observer.observe(svg);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (viewMode === 'graph') setSceneView(fitTerminalScene(document, canvasAspect));
  }, [canvasAspect, document, viewMode]);
  const save = useMutation({
    mutationFn: () => saveTerminalDocument(terminalId, document, 'Designer changes'),
    onSuccess: async (result) => {
      setSavedVersion(result.version);
      setDirty(false);
      await queryClient.invalidateQueries({ queryKey: ['terminal', terminalId] });
      await queryClient.invalidateQueries({ queryKey: ['terminal-graph', terminalId] });
      await queryClient.invalidateQueries({ queryKey: ['terminals'] });
    },
  });

  function commitDocument(next: TerminalDocument) {
    setHistory((current) => commitHistory(current, next));
    setDirty(true);
  }

  const nodePositions = document.nodes.map((node, index) => ({
    node,
    x:
      node.id === draggingNodeId && dragPreview
        ? dragPreview.x
        : typeof node.x === 'number'
          ? node.x
          : 100 + (index % 6) * 170,
    y:
      node.id === draggingNodeId && dragPreview
        ? dragPreview.y
        : typeof node.y === 'number'
          ? node.y
          : 100 + Math.floor(index / 6) * 135,
  }));
  const positionById = new Map(nodePositions.map(({ node, x, y }) => [node.id, { x, y }]));
  const selectedNode = document.nodes.find((node) => node.id === selectedNodeId);
  const selectedElement = document.elements.find((element) => element.id === selectedElementId);
  const nodeColors = layoutMap(document, 'node_colors');
  const elementColors = layoutMap(document, 'element_colors');
  const elementLabels = layoutMap(document, 'element_labels');
  const conceptualLinks = layoutList<ConceptualLink>(document, 'conceptual_links');
  const selectedConceptualLink = conceptualLinks.find(
    (link) => link.id === selectedConceptualLinkId,
  );
  const nodeById = new Map(document.nodes.map((node) => [node.id, node]));
  const routeElementIds = focusedRoute?.terminalId === terminalId ? focusedRoute.elementIds : [];
  const elementGroups = new Map<string, TerminalElement[]>();
  for (const element of document.elements) {
    const endpoints = [element.from, element.to].sort();
    const key = `${endpoints[0]}|${endpoints[1]}`;
    const group = elementGroups.get(key) ?? [];
    group.push(element);
    elementGroups.set(key, group);
  }
  const parallelOffsets = new Map<string, number>();
  for (const group of elementGroups.values()) {
    const ordered = [...group].sort((left, right) => left.id.localeCompare(right.id));
    ordered.forEach((element, index) => {
      parallelOffsets.set(element.id, (index - (ordered.length - 1) / 2) * 18);
    });
  }
  const selectedAnchor = selectedNode
    ? positionById.get(selectedNode.id)
    : selectedElement
      ? (() => {
          const from = positionById.get(selectedElement.from);
          const to = positionById.get(selectedElement.to);
          return from && to ? { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 } : null;
        })()
      : selectedConceptualLink
        ? (() => {
            const from = positionById.get(selectedConceptualLink.from);
            const to = positionById.get(selectedConceptualLink.to);
            return from && to ? { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 } : null;
          })()
        : null;
  const popoverPosition = (() => {
    const svg = sceneRef.current;
    const bounds = svg?.getBoundingClientRect();
    const matrix = svg?.getScreenCTM();
    if (!svg || !bounds || !matrix || !selectedAnchor) return { left: 8, top: 8 };
    const point = svg.createSVGPoint();
    point.x = selectedAnchor.x;
    point.y = selectedAnchor.y;
    const screenPoint = point.matrixTransform(matrix);
    const cardWidth = Math.min(620, bounds.width - 16);
    const preferredLeft = screenPoint.x - bounds.left + 14;
    const left =
      preferredLeft + cardWidth <= bounds.width - 8
        ? preferredLeft
        : screenPoint.x - bounds.left - cardWidth - 14;
    const top = Math.max(8, Math.min(bounds.height - 280, screenPoint.y - bounds.top - 24));
    return {
      left: Math.max(8, Math.min(bounds.width - cardWidth - 8, left)),
      top,
    };
  })();

  useEffect(() => {
    if (!selectedNodeId && !selectedElementId && !selectedConceptualLinkId) return;
    function dismissOutside(event: PointerEvent) {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (popoverRef.current?.contains(target)) return;
      if (target.closest('.equipment-node, .network-object, .conceptual-object')) return;
      setSelectedNodeId(null);
      setSelectedElementId(null);
      setSelectedConceptualLinkId(null);
    }
    window.addEventListener('pointerdown', dismissOutside);
    return () => window.removeEventListener('pointerdown', dismissOutside);
  }, [selectedNodeId, selectedElementId, selectedConceptualLinkId]);

  useEffect(() => {
    let current = true;
    const timer = window.setTimeout(() => {
      setValidationPending(true);
      validateTerminalDocument(terminalId, document)
        .then((result) => {
          if (!current) return;
          setValidationIssues(result.issues);
          setValidationError('');
        })
        .catch((error: unknown) => {
          if (current)
            setValidationError(error instanceof Error ? error.message : 'Validation failed');
        })
        .finally(() => {
          if (current) setValidationPending(false);
        });
    }, 280);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [document, terminalId]);

  function addNode(type: TerminalNode['type']) {
    const count = document.nodes.filter((node) => node.type === type).length + 1;
    const x = sceneView.x + 1100 / sceneView.zoom / 2 + ((count % 3) - 1) * 35;
    const y = sceneView.y + 620 / sceneView.zoom / 2 + ((count % 2) - 0.5) * 45;
    const node: TerminalNode = {
      id: `node-${crypto.randomUUID()}`,
      type,
      name: `${type.replaceAll('_', ' ')} ${count}`,
      x,
      y,
      ...(type === 'TANK' ? { stock_m3: 0, capacity_m3: 5000, min_heel_m3: 0 } : {}),
    };
    commitDocument({ ...document, nodes: [...document.nodes, node] });
    setSelectedNodeId(node.id);
    setSelectedElementId(null);
    setSelectedConceptualLinkId(null);
  }

  function selectNode(node: TerminalNode) {
    if (drawingMode) {
      if (!connectFrom) {
        setConnectFrom(node.id);
        return;
      }
      if (connectFrom !== node.id) {
        if (drawingMode === 'conceptual') {
          const link: ConceptualLink = {
            id: `association-${crypto.randomUUID()}`,
            from: connectFrom,
            to: node.id,
            label: 'Association',
            color: '#7d8b98',
          };
          commitDocument({
            ...document,
            layout: {
              ...(document.layout ?? {}),
              conceptual_links: [...conceptualLinks, link],
            },
          });
          setEditorMessage('Conceptual association added. It will not affect route calculations.');
          setConnectFrom(null);
          setDrawingMode(null);
          return;
        }
        const source = document.nodes.find((item) => item.id === connectFrom);
        const pipelineNeedsTank =
          drawingMode === 'pipeline' && ['TANK_HEADER', 'SEGMENT'].includes(pipelineType);
        const tankEndpoints = [source, node].filter((item) => item?.type === 'TANK');
        if (pipelineNeedsTank && tankEndpoints.length !== 1) {
          setEditorMessage(`${pipelineType.replaceAll('_', ' ')} must connect exactly one tank.`);
          setConnectFrom(null);
          return;
        }
        const type = drawingMode === 'pipeline' ? pipelineType : componentType;
        const element: TerminalElement = {
          id: `element-${crypto.randomUUID()}`,
          type,
          from: connectFrom,
          to: node.id,
          length_m: drawingMode === 'component' ? 0 : 120,
          diameter_mm: 300,
          installation: 'ABOVEGROUND',
          ...(drawingMode === 'pipeline' && ['TANK_HEADER', 'SEGMENT'].includes(type)
            ? { tank_id: tankEndpoints[0]?.id }
            : {}),
          ...(type === 'PUMP' ? { head_m: 20, max_flow_m3h: 1000 } : {}),
          ...(type === 'VALVE' ? { operate_min: 3, state: 'OPEN' as const } : {}),
        };
        commitDocument({ ...document, elements: [...document.elements, element] });
        setSelectedElementId(element.id);
        setSelectedNodeId(null);
        setSelectedConceptualLinkId(null);
      }
      setConnectFrom(null);
      setDrawingMode(null);
      setEditorMessage('');
      return;
    }
    setSelectedNodeId(node.id);
    setSelectedElementId(null);
    setSelectedConceptualLinkId(null);
  }

  function updateNode(patch: Partial<TerminalNode>) {
    if (!selectedNodeId) return;
    commitDocument({
      ...document,
      nodes: document.nodes.map((node) =>
        node.id === selectedNodeId ? { ...node, ...patch } : node,
      ),
    });
  }

  function updateElement(patch: Partial<TerminalElement>) {
    if (!selectedElementId) return;
    commitDocument({
      ...document,
      elements: document.elements.map((element) =>
        element.id === selectedElementId ? { ...element, ...patch } : element,
      ),
    });
  }

  function updatePumpCurve(curve: PerformanceCurve | undefined) {
    if (!selectedElementId) return;
    commitDocument({
      ...document,
      schema_version: '1.1',
      elements: document.elements.map((element) =>
        element.id === selectedElementId ? { ...element, performance_curve: curve } : element,
      ),
    });
  }

  function updatePumpElement(patch: Partial<TerminalElement>) {
    if (!selectedElementId) return;
    commitDocument({
      ...document,
      schema_version: '1.1',
      elements: document.elements.map((element) =>
        element.id === selectedElementId ? { ...element, ...patch } : element,
      ),
    });
  }

  function updateSelectedPumpTrain(
    memberPumpIds: string[],
    arrangement?: PumpTrain['arrangement'],
  ) {
    if (!selectedElement || selectedElement.type !== 'PUMP') return;
    const trains = document.pump_trains ?? [];
    const existing = trains.find((train) => train.member_pump_ids.includes(selectedElement.id));
    const otherTrains = trains.filter((train) => train.id !== existing?.id);
    const uniqueMembers = [...new Set(memberPumpIds)];
    const nextTrains =
      uniqueMembers.length < 2
        ? otherTrains
        : [
            ...otherTrains,
            {
              id: existing?.id ?? `train-${selectedElement.id}`,
              arrangement: arrangement ?? existing?.arrangement ?? 'PARALLEL',
              member_pump_ids: uniqueMembers,
            },
          ];
    commitDocument({
      ...document,
      schema_version: '1.1',
      pump_trains: nextTrains,
    });
  }

  function updateLayoutMap(key: string, objectId: string, value: string) {
    const nextMap = { ...layoutMap(document, key), [objectId]: value };
    commitDocument({
      ...document,
      layout: { ...(document.layout ?? {}), [key]: nextMap },
    });
  }

  function updateConceptualLink(patch: Partial<ConceptualLink>) {
    if (!selectedConceptualLinkId) return;
    commitDocument({
      ...document,
      layout: {
        ...(document.layout ?? {}),
        conceptual_links: conceptualLinks.map((link) =>
          link.id === selectedConceptualLinkId ? { ...link, ...patch } : link,
        ),
      },
    });
  }

  function deleteSelection() {
    if (selectedNodeId) {
      commitDocument({
        ...document,
        nodes: document.nodes.filter((node) => node.id !== selectedNodeId),
        elements: document.elements.filter(
          (element) => element.from !== selectedNodeId && element.to !== selectedNodeId,
        ),
      });
      setSelectedNodeId(null);
    } else if (selectedElementId) {
      commitDocument({
        ...document,
        elements: document.elements.filter((element) => element.id !== selectedElementId),
        pump_trains: (document.pump_trains ?? [])
          .map((train) => ({
            ...train,
            member_pump_ids: train.member_pump_ids.filter((pumpId) => pumpId !== selectedElementId),
          }))
          .filter((train) => train.member_pump_ids.length >= 2),
      });
      setSelectedElementId(null);
    } else if (selectedConceptualLinkId) {
      commitDocument({
        ...document,
        layout: {
          ...(document.layout ?? {}),
          conceptual_links: conceptualLinks.filter((link) => link.id !== selectedConceptualLinkId),
        },
      });
      setSelectedConceptualLinkId(null);
    }
  }

  function duplicateSelectedNode() {
    if (!selectedNode) return;
    const duplicate: TerminalNode = {
      ...selectedNode,
      id: `node-${crypto.randomUUID()}`,
      name: `${selectedNode.name ?? selectedNode.type} copy`,
      x: (selectedNode.x ?? 115) + 40,
      y: (selectedNode.y ?? 105) + 40,
    };
    commitDocument({ ...document, nodes: [...document.nodes, duplicate] });
    setSelectedNodeId(duplicate.id);
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        target.closest('input, select, textarea, [contenteditable="true"]')
      ) {
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
        if (event.shiftKey ? history.future.length === 0 : history.past.length === 0) return;
        event.preventDefault();
        setHistory((current) => (event.shiftKey ? redoHistory(current) : undoHistory(current)));
        setDirty(true);
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'y') {
        if (history.future.length === 0) return;
        event.preventDefault();
        setHistory(redoHistory);
        setDirty(true);
      } else if (event.key === 'Delete' || event.key === 'Backspace') {
        event.preventDefault();
        deleteSelection();
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [
    document,
    history,
    selectedNode,
    selectedElementId,
    selectedNodeId,
    selectedConceptualLinkId,
  ]);

  function undo() {
    if (history.past.length === 0) return;
    setHistory(undoHistory);
    setDirty(true);
  }

  function redo() {
    if (history.future.length === 0) return;
    setHistory(redoHistory);
    setDirty(true);
  }

  function finishDrag() {
    const moved =
      dragPreview &&
      dragStartPosition.current &&
      (Math.abs(dragPreview.x - dragStartPosition.current.x) > 1 ||
        Math.abs(dragPreview.y - dragStartPosition.current.y) > 1);
    if (draggingNodeId && dragPreview && moved) {
      commitDocument({
        ...document,
        nodes: document.nodes.map((node) =>
          node.id === draggingNodeId ? { ...node, x: dragPreview.x, y: dragPreview.y } : node,
        ),
      });
    }
    dragStartPosition.current = null;
    setDraggingNodeId(null);
    setDragPreview(null);
  }

  function scenePoint(
    event: React.PointerEvent<SVGSVGElement> | React.WheelEvent<SVGSVGElement>,
  ): Point {
    const matrix = event.currentTarget.getScreenCTM();
    if (!matrix) return { x: 0, y: 0 };
    const point = event.currentTarget.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const mapped = point.matrixTransform(matrix.inverse());
    return { x: mapped.x, y: mapped.y };
  }

  function adjustZoom(factor: number, anchor?: Point) {
    const zoom = Math.max(0.12, Math.min(5, sceneView.zoom * factor));
    const currentSize = sceneViewBoxSize(canvasAspect, sceneView.zoom);
    const nextSize = sceneViewBoxSize(canvasAspect, zoom);
    const width = currentSize.width;
    const height = currentSize.height;
    const anchorX = anchor?.x ?? sceneView.x + width / 2;
    const anchorY = anchor?.y ?? sceneView.y + height / 2;
    const xRatio = (anchorX - sceneView.x) / width;
    const yRatio = (anchorY - sceneView.y) / height;
    setSceneView({
      x: anchorX - nextSize.width * xRatio,
      y: anchorY - nextSize.height * yRatio,
      zoom,
    });
  }

  function fitScene() {
    const bounds = sceneRef.current?.getBoundingClientRect();
    const aspect = bounds && bounds.height > 0 ? bounds.width / bounds.height : canvasAspect;
    setSceneView(fitTerminalScene(document, aspect));
  }

  function panCanvas(event: React.PointerEvent<SVGSVGElement>) {
    if (event.target !== event.currentTarget) return;
    event.preventDefault();
    const matrix = event.currentTarget.getScreenCTM();
    if (!matrix) return;
    panStart.current = {
      clientX: event.clientX,
      clientY: event.clientY,
      scaleX: matrix.a,
      scaleY: matrix.d,
      viewX: sceneView.x,
      viewY: sceneView.y,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function moveCanvas(event: React.PointerEvent<SVGSVGElement>) {
    if (panStart.current) {
      const start = panStart.current;
      setSceneView((current) => ({
        ...current,
        x: start.viewX - (event.clientX - start.clientX) / start.scaleX,
        y: start.viewY - (event.clientY - start.clientY) / start.scaleY,
      }));
      return;
    }
    if (!draggingNodeId) return;
    const grid = snapToGrid ? 20 : 1;
    const { x, y } = scenePoint(event);
    const dragOrigin = dragStartPosition.current;
    if (dragOrigin && (Math.abs(x - dragOrigin.x) > 3 || Math.abs(y - dragOrigin.y) > 3)) {
      suppressNodeClick.current = true;
    }
    setDragPreview({ x: Math.round(x / grid) * grid, y: Math.round(y / grid) * grid });
  }

  function finishCanvasPointer() {
    panStart.current = null;
    finishDrag();
  }

  function focusValidationIssue(issue: ValidationIssue) {
    const node = issue.node_id ? nodeById.get(issue.node_id) : undefined;
    const element = issue.element_id
      ? document.elements.find((item) => item.id === issue.element_id)
      : undefined;
    const nodePosition = node ? positionById.get(node.id) : undefined;
    const from = element ? positionById.get(element.from) : undefined;
    const to = element ? positionById.get(element.to) : undefined;
    const focus =
      nodePosition ?? (from && to ? { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 } : null);
    if (node) {
      setSelectedNodeId(node.id);
      setSelectedElementId(null);
      setSelectedConceptualLinkId(null);
    } else if (element) {
      setSelectedElementId(element.id);
      setSelectedNodeId(null);
      setSelectedConceptualLinkId(null);
    }
    if (focus) {
      setSceneView((current) => ({
        ...current,
        x: focus.x - 550 / current.zoom,
        y: focus.y - 310 / current.zoom,
      }));
    }
    setValidationOpen(false);
  }

  return (
    <div className="terminal-editor">
      <PageHeading
        compact
        eyebrow="TERMINAL DESIGNER"
        title={name}
        summary={`V${savedVersion} · ${document.nodes.length} equipment · ${document.elements.length} network · ${conceptualLinks.length} links`}
      />
      <div className="designer-toolbar">
        <button
          aria-label="Save version"
          className="toolbar-save-button"
          disabled={save.isPending}
          title="Save a new version"
          type="button"
          onClick={() => save.mutate()}
        >
          {save.isPending ? <LoaderCircle className="spin" size={16} /> : <Save size={16} />}
        </button>
        <span className="toolbar-divider" aria-hidden="true" />
        <div className="design-actions" role="group" aria-label="Edit actions">
          <button
            aria-label="Undo"
            disabled={viewMode === 'graph' || history.past.length === 0}
            title="Undo (Ctrl+Z)"
            type="button"
            onClick={undo}
          >
            <Undo2 size={17} />
          </button>
          <button
            aria-label="Redo"
            disabled={viewMode === 'graph' || history.future.length === 0}
            title="Redo (Ctrl+Y)"
            type="button"
            onClick={redo}
          >
            <Redo2 size={17} />
          </button>
          <button
            aria-label="Duplicate equipment"
            disabled={viewMode === 'graph' || !selectedNode}
            title="Duplicate selected equipment"
            type="button"
            onClick={duplicateSelectedNode}
          >
            <Copy size={16} />
          </button>
          <button
            aria-label="Delete selected object"
            disabled={viewMode === 'graph' || (!selectedNodeId && !selectedElementId)}
            title="Delete (Delete)"
            type="button"
            onClick={deleteSelection}
          >
            <Trash2 size={16} />
          </button>
        </div>
        <div className="view-mode-switch" role="group" aria-label="Designer view">
          <button
            aria-pressed={viewMode === 'layout'}
            className={viewMode === 'layout' ? 'is-active' : ''}
            type="button"
            onClick={() => setViewMode('layout')}
          >
            Layout
          </button>
          <button
            aria-pressed={viewMode === 'graph'}
            className={viewMode === 'graph' ? 'is-active' : ''}
            type="button"
            onClick={() => {
              setViewMode('graph');
              fitScene();
              setDrawingMode(null);
              setConnectFrom(null);
              setSelectedNodeId(null);
              setSelectedElementId(null);
              setSelectedConceptualLinkId(null);
            }}
          >
            <GitBranch size={14} /> Graph
          </button>
        </div>
        <label className="toolbar-select compact-select">
          <span className="sr-only">Place equipment</span>
          <select
            aria-label="Place equipment"
            disabled={viewMode === 'graph'}
            defaultValue=""
            onChange={(event) => {
              if (event.target.value) addNode(event.target.value as TerminalNode['type']);
              event.target.value = '';
            }}
          >
            <option value="" disabled>
              + Equipment
            </option>
            {NODE_TYPES.map((type) => (
              <option key={type} value={type}>
                {type.replaceAll('_', ' ')}
              </option>
            ))}
          </select>
        </label>
        <label className="toolbar-select">
          <span className="sr-only">Pipeline type</span>
          <select
            disabled={viewMode === 'graph'}
            value={pipelineType}
            onChange={(event) => setPipelineType(event.target.value as TerminalElement['type'])}
          >
            {PIPE_TYPES.map((type) => (
              <option key={type} value={type}>
                {type.replaceAll('_', ' ')}
              </option>
            ))}
          </select>
        </label>
        <button
          aria-label={drawingMode === 'pipeline' ? 'Cancel pipeline' : 'Draw pipeline'}
          className={`tool-button${drawingMode === 'pipeline' ? ' is-selected' : ''}`}
          disabled={viewMode === 'graph'}
          title={drawingMode === 'pipeline' ? 'Cancel pipeline' : 'Draw pipeline'}
          type="button"
          onClick={() => {
            setDrawingMode((mode) => (mode === 'pipeline' ? null : 'pipeline'));
            setConnectFrom(null);
            setEditorMessage('');
          }}
        >
          <GitBranch size={16} />
        </button>
        <label className="toolbar-select">
          <span className="sr-only">Inline component type</span>
          <select
            disabled={viewMode === 'graph'}
            value={componentType}
            onChange={(event) => setComponentType(event.target.value as TerminalElement['type'])}
          >
            {INLINE_COMPONENTS.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
        <button
          aria-label={drawingMode === 'component' ? 'Cancel component' : 'Insert component'}
          className={`tool-button${drawingMode === 'component' ? ' is-selected' : ''}`}
          disabled={viewMode === 'graph'}
          title={drawingMode === 'component' ? 'Cancel component' : 'Insert inline component'}
          type="button"
          onClick={() => {
            setDrawingMode((mode) => (mode === 'component' ? null : 'component'));
            setConnectFrom(null);
            setEditorMessage('');
          }}
        >
          <Wrench size={16} />
        </button>
        <button
          aria-label={drawingMode === 'conceptual' ? 'Cancel conceptual link' : 'Link equipment'}
          className={`tool-button${drawingMode === 'conceptual' ? ' is-selected' : ''}`}
          disabled={viewMode === 'graph'}
          title="Create non-routing conceptual link"
          type="button"
          onClick={() => {
            setDrawingMode((mode) => (mode === 'conceptual' ? null : 'conceptual'));
            setConnectFrom(null);
            setEditorMessage('Conceptual links do not affect route calculations.');
          }}
        >
          <GitBranch size={16} />
        </button>
        <button
          aria-pressed={snapToGrid}
          className={`tool-button snap-button${snapToGrid ? ' is-selected' : ''}`}
          disabled={viewMode === 'graph'}
          aria-label="Toggle snap to grid"
          title="Toggle snap to grid"
          type="button"
          onClick={() => setSnapToGrid((enabled) => !enabled)}
        >
          {snapToGrid ? <span className="snap-dot is-on" /> : <span className="snap-dot" />}
          <span>Snap</span>
        </button>
        <button
          aria-expanded={validationOpen}
          aria-label={`Validation: ${validationIssues.length} issues`}
          className={`tool-button validation-toggle${validationIssues.some((issue) => issue.severity === 'ERROR') ? ' has-errors' : ''}`}
          title="Show validation issues"
          type="button"
          onClick={() => setValidationOpen((open) => !open)}
        >
          <CircleAlert size={15} />
          <span>{validationPending ? '…' : validationIssues.length}</span>
        </button>
        <span
          className="save-state toolbar-save-state"
          role={save.isError || editorMessage ? 'alert' : 'status'}
          title={editorMessage || ''}
        >
          {save.isError
            ? save.error.message
            : editorMessage || (dirty ? 'Unsaved' : `V${savedVersion}`)}
        </span>
      </div>
      <div className="designer-workspace">
        <section className="canvas-frame" aria-label="Terminal layout canvas">
          {viewMode === 'layout' && document.nodes.length === 0 && (
            <div className="canvas-empty">
              <Boxes size={30} />
              <strong>Start your terminal layout</strong>
              <p>Place equipment in the toolbar, then draw pipelines or link objects.</p>
            </div>
          )}
          <svg
            ref={sceneRef}
            className="terminal-canvas"
            viewBox={`${sceneView.x} ${sceneView.y} ${sceneViewBoxSize(canvasAspect, sceneView.zoom).width} ${sceneViewBoxSize(canvasAspect, sceneView.zoom).height}`}
            preserveAspectRatio="xMidYMid meet"
            role="application"
            aria-label="Terminal equipment and connections"
            onPointerDown={panCanvas}
            onPointerMove={moveCanvas}
            onPointerUp={finishCanvasPointer}
            onPointerCancel={finishCanvasPointer}
            onWheel={(event) => {
              event.preventDefault();
              adjustZoom(event.deltaY < 0 ? 1.12 : 1 / 1.12, scenePoint(event));
            }}
          >
            {viewMode === 'graph' ? (
              terminalGraph.data && (
                <TerminalGraphLayers
                  graph={terminalGraph.data}
                  availabilityWindows={graphAvailability.data ?? []}
                  zoom={sceneView.zoom}
                  routeElementIds={routeElementIds}
                  labelScale={
                    sceneViewBoxSize(canvasAspect, 1).width /
                    ((sceneRef.current?.clientWidth || 1100) * sceneView.zoom)
                  }
                />
              )
            ) : (
              <g className="layout-layers">
                {document.elements.map((element) => {
                  const fromCenter = positionById.get(element.from);
                  const toCenter = positionById.get(element.to);
                  const fromNode = nodeById.get(element.from);
                  const toNode = nodeById.get(element.to);
                  if (!fromCenter || !toCenter || !fromNode || !toNode) return null;
                  const from = nearestPort(fromNode, fromCenter, toCenter);
                  const to = nearestPort(toNode, toCenter, fromCenter);
                  const middleX = (from.x + to.x) / 2;
                  const middleY = (from.y + to.y) / 2;
                  const laneY = middleY + (parallelOffsets.get(element.id) ?? 0);
                  const path = `M ${from.x} ${from.y} H ${middleX} V ${laneY} H ${to.x} V ${to.y}`;
                  const isComponent = INLINE_COMPONENTS.includes(element.type);
                  const elementColor = elementColors[element.id] ?? '#5d57a2';
                  const label = elementLabels[element.id] ?? element.type.replaceAll('_', ' ');
                  const width = Math.max(3, Math.min(10, (element.diameter_mm ?? 300) / 80));
                  return (
                    <g
                      key={element.id}
                      className={`network-object${selectedElementId === element.id ? ' is-selected' : ''}${routeElementIds.includes(element.id) ? ' is-route-highlight' : ''}`}
                      onClick={() => {
                        setSelectedElementId(element.id);
                        setSelectedNodeId(null);
                        setSelectedConceptualLinkId(null);
                      }}
                    >
                      <path className="network-hitarea" d={path} />
                      <path
                        className={`pipeline-path${element.installation === 'UNDERGROUND' ? ' is-underground' : ''}`}
                        d={path}
                        stroke={elementColor}
                        strokeWidth={width}
                        vectorEffect="non-scaling-stroke"
                      />
                      {isComponent && element.type === 'PUMP' && (
                        <g className="inline-pump" transform={`translate(${middleX} ${middleY})`}>
                          <circle r="19" fill="#fff" stroke={elementColor} strokeWidth="4" />
                          <path d="M-6 -9 L10 0 L-6 9 Z" fill={elementColor} />
                        </g>
                      )}
                      {isComponent && element.type === 'VALVE' && (
                        <g className="inline-valve" transform={`translate(${middleX} ${middleY})`}>
                          <path
                            d="M-18 -14 L0 0 L-18 14 Z M18 -14 L0 0 L18 14 Z"
                            fill="#fff"
                            stroke={elementColor}
                            strokeWidth="3"
                          />
                        </g>
                      )}
                      {sceneView.zoom >= 0.5 && (
                        <text
                          className="network-label"
                          x={middleX}
                          y={middleY - (isComponent ? 24 : 10)}
                        >
                          {label}
                        </text>
                      )}
                    </g>
                  );
                })}
                {conceptualLinks.map((link) => {
                  const fromCenter = positionById.get(link.from);
                  const toCenter = positionById.get(link.to);
                  const fromNode = nodeById.get(link.from);
                  const toNode = nodeById.get(link.to);
                  if (!fromCenter || !toCenter || !fromNode || !toNode) return null;
                  const from = nearestPort(fromNode, fromCenter, toCenter);
                  const to = nearestPort(toNode, toCenter, fromCenter);
                  const middleX = (from.x + to.x) / 2;
                  const middleY = (from.y + to.y) / 2;
                  return (
                    <g
                      key={link.id}
                      className={`conceptual-object${selectedConceptualLinkId === link.id ? ' is-selected' : ''}`}
                      onClick={() => {
                        setSelectedConceptualLinkId(link.id);
                        setSelectedNodeId(null);
                        setSelectedElementId(null);
                      }}
                    >
                      <path d={`M ${from.x} ${from.y} H ${middleX} V ${to.y} H ${to.x}`} />
                      {sceneView.zoom >= 0.4 && (
                        <text x={middleX} y={middleY - 6}>
                          {link.label}
                        </text>
                      )}
                    </g>
                  );
                })}
                {nodePositions.map(({ node, x, y }) => (
                  <g
                    aria-label={`${node.type}: ${node.name ?? node.id}`}
                    className={`equipment-node${selectedNodeId === node.id ? ' is-selected' : ''}${connectFrom === node.id ? ' is-connect-start' : ''}`}
                    key={node.id}
                    onClick={() => {
                      if (suppressNodeClick.current) {
                        suppressNodeClick.current = false;
                        return;
                      }
                      selectNode(node);
                    }}
                    onPointerDown={(event) => {
                      if (drawingMode) return;
                      event.preventDefault();
                      suppressNodeClick.current = false;
                      setSelectedNodeId(null);
                      setSelectedElementId(null);
                      setSelectedConceptualLinkId(null);
                      setDraggingNodeId(node.id);
                      dragStartPosition.current = { x, y };
                      setDragPreview({ x, y });
                      event.currentTarget.setPointerCapture(event.pointerId);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') selectNode(node);
                    }}
                    role="button"
                    tabIndex={0}
                    transform={`translate(${x}, ${y})`}
                  >
                    <rect
                      className="node-hitarea"
                      x="-64"
                      y="-46"
                      width="128"
                      height="100"
                      rx="4"
                    />
                    {selectedNodeId === node.id && (
                      <rect
                        className="node-selection"
                        x="-64"
                        y="-46"
                        width="128"
                        height="100"
                        rx="4"
                      />
                    )}
                    {node.type === 'MANIFOLD' ? (
                      <g transform="scale(0.72)">
                        <EquipmentGlyph type={node.type} color={nodeColors[node.id] ?? '#c8d4e1'} />
                      </g>
                    ) : (
                      <EquipmentGlyph type={node.type} color={nodeColors[node.id] ?? '#c8d4e1'} />
                    )}
                    {(drawingMode !== null || selectedNodeId === node.id) &&
                      equipmentPorts(node.type).map((port, index) => (
                        <circle
                          key={`${node.id}-port-${index}`}
                          className="equipment-port"
                          cx={port.x}
                          cy={port.y}
                          r="4"
                        />
                      ))}
                    {sceneView.zoom >= 0.35 && (
                      <text className="node-name" x="0" y="51">
                        {node.name ?? node.id}
                      </text>
                    )}
                  </g>
                ))}
              </g>
            )}
          </svg>
          {viewMode === 'graph' && (
            <div className="graph-readout" role="status" aria-live="polite">
              {terminalGraph.isPending ? (
                <span>Loading graph…</span>
              ) : terminalGraph.isError ? (
                <span className="graph-readout-error">{terminalGraph.error.message}</span>
              ) : terminalGraph.data ? (
                <>
                  <strong>GRAPH · V{terminalGraph.data.terminal_version}</strong>
                  <span>
                    {terminalGraph.data.nodes.length} nodes · {terminalGraph.data.elements.length}{' '}
                    elements · {terminalGraph.data.arcs.filter((arc) => arc.traversable).length}{' '}
                    traversable arcs
                  </span>
                  {terminalGraph.data.issues.length > 0 && (
                    <span className="graph-readout-warning">
                      {terminalGraph.data.issues.length} validation issue
                      {terminalGraph.data.issues.length === 1 ? '' : 's'}
                    </span>
                  )}
                  {dirty && (
                    <span className="graph-readout-warning">
                      Unsaved edits; showing saved graph
                    </span>
                  )}
                  <span className="graph-readout-legend">
                    Arrows show flow direction · X marks blocked pump reverse flow
                  </span>
                </>
              ) : null}
            </div>
          )}
          <div className="canvas-zoom" role="group" aria-label="Canvas zoom">
            <button
              aria-label="Zoom out"
              title="Zoom out"
              type="button"
              onClick={() => adjustZoom(1 / 1.2)}
            >
              <ZoomOut size={15} />
            </button>
            <output>{Math.round(sceneView.zoom * 100)}%</output>
            <button
              aria-label="Zoom in"
              title="Zoom in"
              type="button"
              onClick={() => adjustZoom(1.2)}
            >
              <ZoomIn size={15} />
            </button>
            <button aria-label="Fit scene" title="Fit all objects" type="button" onClick={fitScene}>
              <Maximize size={15} />
            </button>
          </div>
          {validationOpen && (
            <aside className="validation-tray" aria-label="Terminal validation issues">
              <div className="validation-tray-heading">
                <strong>Validation</strong>
                <span>
                  {validationPending
                    ? 'Checking…'
                    : `${validationIssues.filter((issue) => issue.severity === 'ERROR').length} errors · ${validationIssues.filter((issue) => issue.severity === 'WARNING').length} warnings`}
                </span>
                <button
                  aria-label="Close validation issues"
                  type="button"
                  onClick={() => setValidationOpen(false)}
                >
                  <X size={14} />
                </button>
              </div>
              {validationError ? (
                <p className="validation-empty error-message">{validationError}</p>
              ) : validationPending && validationIssues.length === 0 ? (
                <p className="validation-empty">Checking terminal…</p>
              ) : validationIssues.length === 0 ? (
                <p className="validation-empty">No issues found.</p>
              ) : (
                <div className="validation-issues">
                  {validationIssues.map((issue, index) => (
                    <button
                      className={`validation-issue is-${issue.severity.toLowerCase()}`}
                      key={`${issue.code}-${issue.node_id ?? issue.element_id ?? index}-${index}`}
                      type="button"
                      onClick={() => focusValidationIssue(issue)}
                    >
                      <span className="issue-severity">{issue.severity}</span>
                      <span className="issue-main">
                        <strong>{issue.code.replaceAll('_', ' ')}</strong>
                        <span>{issue.message}</span>
                        {issue.fix_hint && <small>{issue.fix_hint}</small>}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </aside>
          )}
          {viewMode === 'layout' &&
            (selectedNode || selectedElement || selectedConceptualLink) &&
            selectedAnchor && (
              <aside
                ref={popoverRef}
                className="object-popover"
                aria-label="Selected object properties"
                style={{ left: `${popoverPosition.left}px`, top: `${popoverPosition.top}px` }}
              >
                <div className="panel-heading">
                  <span className="eyebrow">PROPERTIES</span>
                  <strong>
                    {selectedConceptualLink
                      ? 'CONCEPTUAL LINK'
                      : selectedNode
                        ? selectedNode.type.replaceAll('_', ' ')
                        : selectedElement
                          ? selectedElement.type === 'PUMP' || selectedElement.type === 'VALVE'
                            ? `INLINE ${selectedElement.type}`
                            : 'PIPELINE'
                          : 'OBJECT'}
                  </strong>
                  <button
                    aria-label="Close properties"
                    className="popover-close"
                    type="button"
                    onClick={() => {
                      setSelectedNodeId(null);
                      setSelectedElementId(null);
                      setSelectedConceptualLinkId(null);
                    }}
                  >
                    <X size={15} />
                  </button>
                </div>
                {selectedConceptualLink ? (
                  <div className="property-fields">
                    <label>
                      Association ID
                      <input readOnly value={selectedConceptualLink.id} />
                    </label>
                    <label>
                      Label
                      <input
                        value={selectedConceptualLink.label}
                        onChange={(event) => updateConceptualLink({ label: event.target.value })}
                      />
                    </label>
                    <label>
                      Line color
                      <input
                        aria-label="Association color"
                        type="color"
                        value={selectedConceptualLink.color}
                        onChange={(event) => updateConceptualLink({ color: event.target.value })}
                      />
                    </label>
                    <p className="conceptual-note">
                      Visual only · excluded from route calculations
                    </p>
                  </div>
                ) : selectedNode ? (
                  <div className="property-fields">
                    <label>
                      Tag / ID
                      <input readOnly value={selectedNode.id} />
                    </label>
                    <label>
                      Label
                      <input
                        value={selectedNode.name ?? ''}
                        onChange={(event) => updateNode({ name: event.target.value })}
                      />
                    </label>
                    <label>
                      Symbol color
                      <input
                        aria-label="Equipment color"
                        type="color"
                        value={nodeColors[selectedNode.id] ?? '#c8d4e1'}
                        onChange={(event) =>
                          updateLayoutMap('node_colors', selectedNode.id, event.target.value)
                        }
                      />
                    </label>
                    {selectedNode.type === 'TANK' && (
                      <>
                        <label>
                          Capacity (m³)
                          <input
                            min="0"
                            type="number"
                            value={selectedNode.capacity_m3 ?? 0}
                            onChange={(event) =>
                              updateNode({ capacity_m3: Number(event.target.value) })
                            }
                          />
                        </label>
                        <label>
                          Stock (m³)
                          <input
                            min="0"
                            type="number"
                            value={selectedNode.stock_m3 ?? 0}
                            onChange={(event) =>
                              updateNode({ stock_m3: Number(event.target.value) })
                            }
                          />
                        </label>
                      </>
                    )}
                    {selectedNode.type === 'JETTY' && (
                      <label>
                        Max rate (m³/h)
                        <input
                          min="0"
                          type="number"
                          value={selectedNode.max_rate_m3h ?? 0}
                          onChange={(event) =>
                            updateNode({ max_rate_m3h: Number(event.target.value) })
                          }
                        />
                      </label>
                    )}
                    {selectedNode.type === 'RAIL_PLATFORM' && (
                      <>
                        <label>
                          Track sides
                          <input
                            min="1"
                            type="number"
                            value={selectedNode.side_count ?? 1}
                            onChange={(event) =>
                              updateNode({ side_count: Number(event.target.value) })
                            }
                          />
                        </label>
                        <label>
                          Cars per side
                          <input
                            min="1"
                            type="number"
                            value={selectedNode.cars_per_side ?? 1}
                            onChange={(event) =>
                              updateNode({ cars_per_side: Number(event.target.value) })
                            }
                          />
                        </label>
                      </>
                    )}
                    {selectedNode.type === 'RAIL_CAR' && (
                      <>
                        <label>
                          Capacity (m³)
                          <input
                            min="0"
                            type="number"
                            value={selectedNode.capacity_m3 ?? 0}
                            onChange={(event) =>
                              updateNode({ capacity_m3: Number(event.target.value) })
                            }
                          />
                        </label>
                        <label>
                          Stock (m³)
                          <input
                            min="0"
                            type="number"
                            value={selectedNode.stock_m3 ?? 0}
                            onChange={(event) =>
                              updateNode({ stock_m3: Number(event.target.value) })
                            }
                          />
                        </label>
                      </>
                    )}
                  </div>
                ) : selectedElement ? (
                  <div className="property-fields">
                    <label>
                      Object ID
                      <input readOnly value={selectedElement.id} />
                    </label>
                    <label>
                      Label
                      <input
                        value={elementLabels[selectedElement.id] ?? ''}
                        placeholder={selectedElement.type.replaceAll('_', ' ')}
                        onChange={(event) =>
                          updateLayoutMap('element_labels', selectedElement.id, event.target.value)
                        }
                      />
                    </label>
                    <label>
                      Object color
                      <input
                        aria-label="Object color"
                        type="color"
                        value={elementColors[selectedElement.id] ?? '#5d57a2'}
                        onChange={(event) =>
                          updateLayoutMap('element_colors', selectedElement.id, event.target.value)
                        }
                      />
                    </label>
                    {PIPE_TYPES.includes(selectedElement.type) && (
                      <>
                        <label>
                          Diameter (mm)
                          <input
                            min="1"
                            type="number"
                            value={selectedElement.diameter_mm ?? 300}
                            onChange={(event) =>
                              updateElement({ diameter_mm: Number(event.target.value) })
                            }
                          />
                        </label>
                        <label>
                          Length (m)
                          <input
                            min="0"
                            type="number"
                            value={selectedElement.length_m ?? 0}
                            onChange={(event) =>
                              updateElement({ length_m: Number(event.target.value) })
                            }
                          />
                        </label>
                        <label>
                          Installation
                          <select
                            value={selectedElement.installation ?? 'ABOVEGROUND'}
                            onChange={(event) =>
                              updateElement({
                                installation: event.target.value as TerminalElement['installation'],
                              })
                            }
                          >
                            <option value="ABOVEGROUND">Above ground</option>
                            <option value="UNDERGROUND">Underground</option>
                          </select>
                        </label>
                      </>
                    )}
                    {selectedElement.type === 'PUMP' && (
                      <>
                        <label>
                          Head (m)
                          <input
                            min="0"
                            type="number"
                            value={selectedElement.head_m ?? 0}
                            onChange={(event) =>
                              updateElement({ head_m: Number(event.target.value) })
                            }
                          />
                        </label>
                        <label>
                          Max flow (m³/h)
                          <input
                            min="0"
                            type="number"
                            value={selectedElement.max_flow_m3h ?? 0}
                            onChange={(event) =>
                              updateElement({ max_flow_m3h: Number(event.target.value) })
                            }
                          />
                        </label>
                        <label>
                          Performance curve
                          <select
                            value={selectedElement.performance_curve?.model ?? ''}
                            onChange={(event) => {
                              if (!event.target.value) {
                                updatePumpCurve(undefined);
                              } else if (event.target.value === 'QUADRATIC') {
                                updatePumpCurve({
                                  model: 'QUADRATIC',
                                  min_flow_m3h: 100,
                                  max_flow_m3h: 1000,
                                  shutoff_head_m: 60,
                                  quadratic_coefficient: 0.00005,
                                  speed_ratio_min: 1,
                                  speed_ratio_max: 1,
                                });
                              } else {
                                updatePumpCurve({
                                  model: 'TABULAR',
                                  min_flow_m3h: 100,
                                  max_flow_m3h: 1000,
                                  points: [
                                    { flow_m3h: 100, head_m: 60 },
                                    { flow_m3h: 1000, head_m: 30 },
                                  ],
                                  speed_ratio_min: 1,
                                  speed_ratio_max: 1,
                                });
                              }
                            }}
                          >
                            <option value="">Constant head</option>
                            <option value="QUADRATIC">Quadratic</option>
                            <option value="TABULAR">Tabular</option>
                          </select>
                        </label>
                        {selectedElement.performance_curve && (
                          <>
                            <label>
                              Curve min flow (m³/h)
                              <input
                                min="0"
                                step="any"
                                type="number"
                                value={selectedElement.performance_curve.min_flow_m3h}
                                onChange={(event) =>
                                  updatePumpCurve({
                                    ...selectedElement.performance_curve!,
                                    min_flow_m3h: Number(event.target.value),
                                  })
                                }
                              />
                            </label>
                            <label>
                              Curve max flow (m³/h)
                              <input
                                min="0"
                                step="any"
                                type="number"
                                value={selectedElement.performance_curve.max_flow_m3h}
                                onChange={(event) =>
                                  updatePumpCurve({
                                    ...selectedElement.performance_curve!,
                                    max_flow_m3h: Number(event.target.value),
                                  })
                                }
                              />
                            </label>
                            <div className="pump-curve-speed-fields">
                              <label>
                                Min speed ratio
                                <input
                                  min="0.01"
                                  max="1"
                                  step="any"
                                  type="number"
                                  value={selectedElement.performance_curve.speed_ratio_min}
                                  onChange={(event) =>
                                    updatePumpCurve({
                                      ...selectedElement.performance_curve!,
                                      speed_ratio_min: Number(event.target.value),
                                    })
                                  }
                                />
                              </label>
                              <label>
                                Max speed ratio
                                <input
                                  min="0.01"
                                  max="1"
                                  step="any"
                                  type="number"
                                  value={selectedElement.performance_curve.speed_ratio_max}
                                  onChange={(event) =>
                                    updatePumpCurve({
                                      ...selectedElement.performance_curve!,
                                      speed_ratio_max: Number(event.target.value),
                                    })
                                  }
                                />
                              </label>
                            </div>
                            {selectedElement.performance_curve.model === 'QUADRATIC' ? (
                              <>
                                <label>
                                  Shutoff head (m)
                                  <input
                                    min="0"
                                    step="any"
                                    type="number"
                                    value={selectedElement.performance_curve.shutoff_head_m ?? 0}
                                    onChange={(event) =>
                                      updatePumpCurve({
                                        ...selectedElement.performance_curve!,
                                        shutoff_head_m: Number(event.target.value),
                                      })
                                    }
                                  />
                                </label>
                                <label>
                                  Quadratic coefficient
                                  <input
                                    min="0"
                                    step="any"
                                    type="number"
                                    value={
                                      selectedElement.performance_curve.quadratic_coefficient ?? 0
                                    }
                                    onChange={(event) =>
                                      updatePumpCurve({
                                        ...selectedElement.performance_curve!,
                                        quadratic_coefficient: Number(event.target.value),
                                      })
                                    }
                                  />
                                </label>
                              </>
                            ) : (
                              <div className="pump-curve-points">
                                <strong>Flow/head points</strong>
                                {(selectedElement.performance_curve.points ?? []).map(
                                  (point, index) => (
                                    <div
                                      className="pump-curve-point"
                                      key={`${index}-${point.flow_m3h}`}
                                    >
                                      <input
                                        aria-label={`Point ${index + 1} flow (m³/h)`}
                                        min="0"
                                        step="any"
                                        type="number"
                                        value={point.flow_m3h}
                                        onChange={(event) =>
                                          updatePumpCurve({
                                            ...selectedElement.performance_curve!,
                                            points: (
                                              selectedElement.performance_curve?.points ?? []
                                            ).map((item, itemIndex) =>
                                              itemIndex === index
                                                ? { ...item, flow_m3h: Number(event.target.value) }
                                                : item,
                                            ),
                                          })
                                        }
                                      />
                                      <input
                                        aria-label={`Point ${index + 1} head (m)`}
                                        min="0"
                                        step="any"
                                        type="number"
                                        value={point.head_m}
                                        onChange={(event) =>
                                          updatePumpCurve({
                                            ...selectedElement.performance_curve!,
                                            points: (
                                              selectedElement.performance_curve?.points ?? []
                                            ).map((item, itemIndex) =>
                                              itemIndex === index
                                                ? { ...item, head_m: Number(event.target.value) }
                                                : item,
                                            ),
                                          })
                                        }
                                      />
                                      <button
                                        aria-label={`Remove point ${index + 1}`}
                                        disabled={
                                          (selectedElement.performance_curve?.points?.length ??
                                            0) <= 2
                                        }
                                        title="Remove curve point"
                                        type="button"
                                        onClick={() =>
                                          updatePumpCurve({
                                            ...selectedElement.performance_curve!,
                                            points: (
                                              selectedElement.performance_curve?.points ?? []
                                            ).filter((_item, itemIndex) => itemIndex !== index),
                                          })
                                        }
                                      >
                                        <Trash2 size={13} />
                                      </button>
                                    </div>
                                  ),
                                )}
                                <button
                                  className="secondary-action"
                                  type="button"
                                  onClick={() => {
                                    const points = selectedElement.performance_curve?.points ?? [];
                                    const last = points.at(-1) ?? { flow_m3h: 100, head_m: 60 };
                                    updatePumpCurve({
                                      ...selectedElement.performance_curve!,
                                      points: [
                                        ...points,
                                        { flow_m3h: last.flow_m3h + 100, head_m: last.head_m },
                                      ],
                                    });
                                  }}
                                >
                                  <Plus size={13} /> Add point
                                </button>
                              </div>
                            )}
                            <label>
                              Required NPSH (m)
                              <input
                                min="0"
                                step="any"
                                type="number"
                                value={selectedElement.npsh_required_m ?? 0}
                                onChange={(event) =>
                                  updatePumpElement({ npsh_required_m: Number(event.target.value) })
                                }
                              />
                            </label>
                            <label>
                              Suction margin (m)
                              <input
                                min="0"
                                step="any"
                                type="number"
                                value={selectedElement.npsh_margin_m ?? 0.5}
                                onChange={(event) =>
                                  updatePumpElement({ npsh_margin_m: Number(event.target.value) })
                                }
                              />
                            </label>
                          </>
                        )}
                        <div className="pump-train-editor">
                          <strong>Pump train</strong>
                          <span>Select another pump to group it with this pump.</span>
                          {document.elements
                            .filter(
                              (element) =>
                                element.type === 'PUMP' && element.id !== selectedElement.id,
                            )
                            .map((pump) => {
                              const train = (document.pump_trains ?? []).find((item) =>
                                item.member_pump_ids.includes(selectedElement.id),
                              );
                              const members = train?.member_pump_ids ?? [selectedElement.id];
                              const belongsToAnotherTrain = (document.pump_trains ?? []).some(
                                (item) =>
                                  item.id !== train?.id && item.member_pump_ids.includes(pump.id),
                              );
                              return (
                                <label className="pump-train-member" key={pump.id}>
                                  <input
                                    checked={members.includes(pump.id)}
                                    disabled={belongsToAnotherTrain}
                                    type="checkbox"
                                    onChange={(event) =>
                                      updateSelectedPumpTrain(
                                        event.target.checked
                                          ? [...members, pump.id]
                                          : members.filter((memberId) => memberId !== pump.id),
                                      )
                                    }
                                  />
                                  {pump.id}
                                  {belongsToAnotherTrain && (
                                    <small>Assigned to another train</small>
                                  )}
                                </label>
                              );
                            })}
                          {(document.pump_trains ?? []).some((train) =>
                            train.member_pump_ids.includes(selectedElement.id),
                          ) && (
                            <label>
                              Arrangement
                              <select
                                value={
                                  (document.pump_trains ?? []).find((train) =>
                                    train.member_pump_ids.includes(selectedElement.id),
                                  )?.arrangement ?? 'PARALLEL'
                                }
                                onChange={(event) => {
                                  const train = (document.pump_trains ?? []).find((item) =>
                                    item.member_pump_ids.includes(selectedElement.id),
                                  );
                                  if (train) {
                                    updateSelectedPumpTrain(
                                      train.member_pump_ids,
                                      event.target.value as PumpTrain['arrangement'],
                                    );
                                  }
                                }}
                              >
                                <option value="SERIES">Series</option>
                                <option value="PARALLEL">Parallel</option>
                              </select>
                            </label>
                          )}
                        </div>
                      </>
                    )}
                    {selectedElement.type === 'VALVE' && (
                      <>
                        <label>
                          Operation time (min)
                          <input
                            min="0"
                            type="number"
                            value={selectedElement.operate_min ?? 0}
                            onChange={(event) =>
                              updateElement({ operate_min: Number(event.target.value) })
                            }
                          />
                        </label>
                        <label>
                          Valve state
                          <select
                            value={selectedElement.state ?? 'OPEN'}
                            onChange={(event) =>
                              updateElement({
                                state: event.target.value as TerminalElement['state'],
                              })
                            }
                          >
                            <option value="OPEN">Open</option>
                            <option value="CLOSED">Closed</option>
                          </select>
                        </label>
                      </>
                    )}
                  </div>
                ) : null}
              </aside>
            )}
        </section>
      </div>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<AppFrame />}>
        <Route index element={<Navigate to="/terminals" replace />} />
        <Route path="terminals" element={<TerminalRegister />} />
        <Route path="designer" element={<DesignerEntry />} />
        <Route path="designer/:terminalId" element={<TerminalDesigner />} />
        <Route path="planner" element={<RoutePlannerPage />} />
        <Route path="optimization" element={<OptimizationPage />} />
        <Route path="availability" element={<AvailabilityPage />} />
        <Route path="versions" element={<VersionsPage />} />
        <Route path="*" element={<Navigate to="/terminals" replace />} />
      </Route>
    </Routes>
  );
}
