import {
  Activity,
  ArrowUpRight,
  Boxes,
  CircleAlert,
  Copy,
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
  createTerminal,
  getTerminalGraph,
  getTerminal,
  listTerminals,
  saveTerminalDocument,
  validateTerminalDocument,
  type TerminalGraph,
  type ValidationIssue,
} from './api/terminals';
import type {
  Element as TerminalElement,
  Node as TerminalNode,
  TerminalDocument,
} from './api/types';
import { commitHistory, createHistory, redoHistory, undoHistory } from './editor/history';
import { useWorkspaceStore } from './store/workspace';

const navigation = [
  { to: '/terminals', label: 'Terminals', Icon: Boxes },
  { to: '/designer', label: 'Designer', Icon: GitBranch },
  { to: '/planner', label: 'Route planner', Icon: RouteIcon },
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
  const terminals = useQuery({ queryKey: ['terminals'], queryFn: listTerminals });
  const create = useMutation({
    mutationFn: createTerminal,
    onSuccess: async (terminal) => {
      setActiveTerminal(terminal.id);
      await queryClient.invalidateQueries({ queryKey: ['terminals'] });
      navigate(`/designer/${terminal.id}`);
    },
  });

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = terminalName.trim();
    if (name) create.mutate(name);
  }

  return (
    <>
      <PageHeading
        eyebrow="ASSET REGISTER"
        title="Terminals"
        summary="Terminal inventory"
        action={
          <button
            className="primary-action"
            type="button"
            onClick={() => setShowCreateForm((visible) => !visible)}
          >
            <Plus size={16} aria-hidden="true" /> New terminal
          </button>
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
      <section className="register" aria-label="Terminal inventory">
        <div className="register-head">
          <span>TERMINAL</span>
          <span>VERSION</span>
          <span>UPDATED</span>
          <span>OPEN</span>
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
              <Link
                className="terminal-row"
                key={terminal.id}
                onClick={() => setActiveTerminal(terminal.id)}
                to={`/designer/${terminal.id}`}
              >
                <strong>{terminal.name}</strong>
                <span className="table-number">V{terminal.current_version}</span>
                <time dateTime={terminal.updated_at}>
                  {new Date(terminal.updated_at).toLocaleString()}
                </time>
                <span className="row-open">
                  Design <ArrowUpRight size={15} />
                </span>
              </Link>
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
  const terminal = useQuery({
    queryKey: ['terminal', terminalId],
    queryFn: () => getTerminal(terminalId),
  });

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
  const common = { fill: color, stroke: '#31564d', strokeWidth: 2 };
  switch (type) {
    case 'TANK':
      return (
        <g className="glyph-tank" {...common}>
          <rect x="-34" y="-17" width="68" height="37" />
          <ellipse cx="0" cy="-17" rx="34" ry="9" />
          <ellipse cx="0" cy="20" rx="34" ry="9" />
          <path d="M-24 -17v37M24 -17v37" fill="none" />
          <ellipse cx="0" cy="-17" rx="24" ry="5" fill="#edf5f1" />
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
          <circle cx="37" cy="6" r="5" fill="#edf5f1" />
          <path d="M-23 27v8M23 27v8" fill="none" />
        </g>
      );
    case 'RAIL_PLATFORM':
      return (
        <g className="glyph-platform" {...common}>
          <path d="M-48 -5h96v12h-96zM-39 7v18M39 7v18M-52 26h104M-44 31h88" />
          <path d="M-35 14h70M-30 18h60" fill="none" stroke="#31564d" />
        </g>
      );
    case 'RAIL_CAR':
      return (
        <g className="glyph-car" {...common}>
          <path d="M-39 -4h78v23h-78zM-30 -4v-13h18v13M-8 -4v-13h18v13M14 -4v-13h17v13" />
          <circle cx="-23" cy="23" r="6" fill="#31564d" />
          <circle cx="23" cy="23" r="6" fill="#31564d" />
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
  zoom,
  labelScale,
}: {
  graph: TerminalGraph;
  zoom: number;
  labelScale: number;
}) {
  const positions = graph.nodes.map((node, index) => ({
    node,
    x: typeof node.x === 'number' ? node.x : 100 + (index % 6) * 170,
    y: typeof node.y === 'number' ? node.y : 100 + Math.floor(index / 6) * 135,
  }));
  const positionById = new Map(positions.map(({ node, x, y }) => [node.id, { x, y }]));
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
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
          <path d="M0 0L8 4L0 8Z" fill="#31564d" />
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
        const color =
          element.type === 'PUMP' ? '#bd7e20' : element.type === 'VALVE' ? '#46766c' : '#52796f';
        return (
          <g className="graph-edge" key={element.id}>
            <path
              d={`M ${from.x} ${from.y} Q ${middleX} ${middleY} ${to.x} ${to.y}`}
              markerEnd={forward.traversable ? 'url(#graph-arrow)' : undefined}
              markerStart={reverse?.traversable ? 'url(#graph-arrow)' : undefined}
              stroke={color}
            />
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
          <EquipmentGlyph type={node.type} color="#c3d8ce" />
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
            color: '#87958f',
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
        action={
          <button
            aria-label="Save version"
            className="primary-action"
            disabled={save.isPending}
            title="Save a new version"
            type="button"
            onClick={() => save.mutate()}
          >
            {save.isPending ? <LoaderCircle className="spin" size={16} /> : <Save size={16} />}
          </button>
        }
      />
      <div className="designer-toolbar">
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
                  zoom={sceneView.zoom}
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
                  const elementColor = elementColors[element.id] ?? '#52796f';
                  const label = elementLabels[element.id] ?? element.type.replaceAll('_', ' ');
                  const width = Math.max(3, Math.min(10, (element.diameter_mm ?? 300) / 80));
                  return (
                    <g
                      key={element.id}
                      className={`network-object${selectedElementId === element.id ? ' is-selected' : ''}`}
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
                        <EquipmentGlyph type={node.type} color={nodeColors[node.id] ?? '#b9d4c9'} />
                      </g>
                    ) : (
                      <EquipmentGlyph type={node.type} color={nodeColors[node.id] ?? '#b9d4c9'} />
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
                        value={nodeColors[selectedNode.id] ?? '#b9d4c9'}
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
                        value={elementColors[selectedElement.id] ?? '#52796f'}
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
        <Route
          path="planner"
          element={
            <ModulePage
              eyebrow="OPERATIONS PLANNING"
              title="Route planner"
              summary="Transfer route workspace"
              Icon={RouteIcon}
            />
          }
        />
        <Route
          path="availability"
          element={
            <ModulePage
              eyebrow="EQUIPMENT STATUS"
              title="Availability"
              summary="Maintenance and equipment windows"
              Icon={Activity}
            />
          }
        />
        <Route
          path="versions"
          element={
            <ModulePage
              eyebrow="CHANGE HISTORY"
              title="Versions"
              summary="Terminal document history"
              Icon={History}
            />
          }
        />
        <Route path="*" element={<Navigate to="/terminals" replace />} />
      </Route>
    </Routes>
  );
}
