import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ChevronRight, GitBranch, Link2, Loader2, Network, Search, X } from 'lucide-react';
import { api, type RelationshipEdge, type RelationshipNetwork, type RelationshipNode } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

type GraphFilter = 'Todos' | 'Solo rojos' | 'Vehiculos' | 'Salud' | 'Hogar';
type EntityType = 'Proveedor' | 'Asegurado';

interface PositionedNode extends RelationshipNode {
  x: number;
  y: number;
  degree: number;
}

interface EntityConcentration {
  id: string;
  label: string;
  tipo: EntityType;
  totalCasos: number;
  rojo: number;
  amarillo: number;
  verde: number;
  scoreSum: number;
  scorePromedio: number;
  ramos: string[];
  counterpartCount: number;
  claimIds: string[];
}

interface ConcentrationSummary {
  providers: EntityConcentration[];
  insureds: EntityConcentration[];
}

interface EgoNetwork {
  focus: PositionedNode;
  hop1: PositionedNode[];
  hop2: PositionedNode[];
  edges: RelationshipEdge[];
  hop1Total: number;
  hop1Truncated: boolean;
  graphHeight: number;
}

type BuiltGraph = ReturnType<typeof buildGraph>;

const filters: GraphFilter[] = ['Todos', 'Solo rojos', 'Vehiculos', 'Salud', 'Hogar'];
const limitOptions = [10, 20, 40, 60, 80, 100, 120];
const graphWidth = 1180;
const minGraphHeight = 480;
// Minimum vertical space per node so circles (up to r=23 with high-degree
// bonus) and their labels below them don't visually merge into each other.
const minNodeSpacing = 48;
const columnX: Record<string, number> = {
  Asegurado: 150,
  Siniestro: 590,
  Proveedor: 1030,
};
const FULL_MAP_CAP = 40;
const EGO_HOP_CAP = 15;
const LIST_PREVIEW_SIZE = 8;
const RISK_TABLE_SIZE = 15;

export function Relationships() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [filter, setFilter] = useState<GraphFilter>('Todos');
  const [limit, setLimit] = useState(60);
  const [activeTab, setActiveTab] = useState<EntityType>('Proveedor');
  const [focusId, setFocusId] = useState<string>(() => searchParams.get('focus') ?? '');
  const [listExpanded, setListExpanded] = useState(false);
  const [hop1Expanded, setHop1Expanded] = useState(false);
  const [showAllInFullMap, setShowAllInFullMap] = useState(false);
  const egoRef = useRef<HTMLDivElement>(null);

  // Reinicia "ver todos los hop1" cuando cambia el foco, ajustando el estado
  // durante el render (en vez de un useEffect) siguiendo el patron ya usado
  // en Claims.tsx/Audit.tsx para este mismo tipo de reset.
  const [prevFocusId, setPrevFocusId] = useState(focusId);
  if (focusId !== prevFocusId) {
    setPrevFocusId(focusId);
    setHop1Expanded(false);
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ['relationships', limit],
    queryFn: async () => (await api.get<RelationshipNetwork>(`/relationships?limit=${limit}`)).data,
  });

  const graph = useMemo(() => buildGraph(data, filter), [data, filter]);
  const concentration = useMemo(() => buildConcentrations(graph), [graph]);
  const fullMap = useMemo(() => capGraphForFullMap(graph, FULL_MAP_CAP, showAllInFullMap), [graph, showAllInFullMap]);
  const riskRows = useMemo(() => buildRiskRows(graph, RISK_TABLE_SIZE), [graph]);

  const focusExists = focusId ? graph.nodesById.has(focusId) : false;
  const ego = useMemo(
    () => (focusId && focusExists ? buildEgoNetwork(graph, focusId, EGO_HOP_CAP, hop1Expanded) : undefined),
    [graph, focusId, focusExists, hop1Expanded],
  );

  // Keep the URL's ?focus= in sync so the current selection is shareable /
  // deep-linkable (e.g. desde ClaimDetail hacia un proveedor especifico).
  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (focusId) next.set('focus', focusId);
    else next.delete('focus');
    if (next.toString() !== searchParams.toString()) setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusId]);

  const selectFocus = (id: string) => {
    setFocusId(id);
    requestAnimationFrame(() => egoRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  };

  const activeList = activeTab === 'Proveedor' ? concentration.providers : concentration.insureds;
  const topProvider = concentration.providers[0];
  const providersEnAlerta = concentration.providers.filter((entry) => entry.rojo >= 2).length;

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-navy-950 p-8 text-white shadow-2xl">
        <Badge variant="info" className="mb-4 border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Red explicable</Badge>
        <h1 className="text-3xl font-black">Relaciones entre asegurados, siniestros y proveedores</h1>
        <p className="mt-3 max-w-3xl text-navy-200">
          Radar de concentracion para priorizar revision humana. La red muestra patrones operativos; no acusa fraude ni decide pagos.
        </p>
      </div>

      {isLoading ? (
        <div className="grid h-72 place-items-center"><Loader2 className="h-9 w-9 animate-spin text-cyan-700" /></div>
      ) : error ? (
        <Card><CardContent className="text-red-600">No fue posible cargar la red de relaciones.</CardContent></Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
            <Metric title="Siniestros analizados" value={graph.counts.claims} />
            <Metric title="Proveedores en alerta" value={providersEnAlerta} />
            <Metric title="Asegurados repetidores" value={concentration.insureds.length} />
            <Metric
              title="Mayor concentracion"
              value={topProvider ? `${topProvider.rojo} rojos` : 'N/A'}
              subtitle={topProvider ? truncate(topProvider.label, 22) : 'Sin datos'}
              onClick={topProvider ? () => { setActiveTab('Proveedor'); selectFocus(topProvider.id); } : undefined}
            />
          </div>

          <Card>
            <CardHeader className="gap-4">
              <div>
                <CardTitle>Radar de concentracion</CardTitle>
                <p className="mt-1 text-sm text-navy-500">Proveedores y asegurados ordenados por alertas rojas conectadas.</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {filters.map((item) => (
                  <button
                    key={item}
                    onClick={() => setFilter(item)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-bold transition ${
                      filter === item ? 'border-cyan-500 bg-cyan-100 text-cyan-800' : 'border-navy-200 bg-white text-navy-600 hover:bg-navy-50'
                    }`}
                  >
                    {item}
                  </button>
                ))}
                <label className="ml-2 flex items-center gap-2 text-xs font-bold text-navy-600">
                  Casos a cargar
                  <select
                    value={limit}
                    onChange={(event) => setLimit(Number(event.target.value))}
                    className="rounded-full border border-navy-200 bg-white px-2 py-1.5 text-xs font-bold text-navy-700"
                  >
                    {limitOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="inline-flex rounded-xl border border-navy-200 bg-navy-50 p-1">
                {(['Proveedor', 'Asegurado'] as EntityType[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`rounded-lg px-4 py-1.5 text-xs font-bold transition ${
                      activeTab === tab ? 'bg-white text-navy-900 shadow-sm' : 'text-navy-500 hover:text-navy-700'
                    }`}
                  >
                    {tab === 'Proveedor' ? 'Proveedores' : 'Asegurados'}
                  </button>
                ))}
              </div>
              <p className="text-xs text-navy-400">
                {activeTab === 'Proveedor'
                  ? 'Un proveedor repartido entre muchos asegurados distintos es senal de posible red; un solo asegurado con muchas alertas es un reclamante serial.'
                  : 'Asegurados con 2 o mas siniestros cargados en este rango.'}
              </p>

              <Callout activeTab={activeTab} list={activeList} />

              {activeList.length === 0 ? (
                <div className="rounded-2xl border border-navy-100 bg-navy-50 p-6 text-center text-sm text-navy-500">
                  {activeTab === 'Proveedor'
                    ? 'No hay proveedores conectados con este filtro.'
                    : 'No hay asegurados con multiples siniestros en el rango cargado.'}
                </div>
              ) : (
                <div className={listExpanded ? 'max-h-[520px] space-y-2 overflow-y-auto pr-1' : 'space-y-2'}>
                  {(listExpanded ? activeList : activeList.slice(0, LIST_PREVIEW_SIZE)).map((entry, index) => (
                    <ConcentrationRow
                      key={entry.id}
                      entry={entry}
                      rank={index + 1}
                      maxTotal={activeList[0]?.totalCasos ?? 1}
                      counterpartNoun={activeTab === 'Proveedor' ? 'asegurados' : 'proveedores'}
                      isActive={entry.id === focusId}
                      onSelect={() => selectFocus(entry.id)}
                    />
                  ))}
                </div>
              )}

              {activeList.length > LIST_PREVIEW_SIZE && (
                <button
                  onClick={() => setListExpanded((value) => !value)}
                  className="text-xs font-bold text-cyan-700 hover:text-cyan-900"
                >
                  {listExpanded ? 'Mostrar menos' : `Mostrar todas (${activeList.length})`}
                </button>
              )}
            </CardContent>
          </Card>

          <div ref={egoRef}>
            <EgoNetworkPanel
              graph={graph}
              ego={ego}
              focusId={focusId}
              focusExists={focusExists}
              onFocus={selectFocus}
              onClear={() => setFocusId('')}
              onNavigateClaim={(id) => navigate(`/claims/${id}`)}
              hop1Expanded={hop1Expanded}
              onExpandHop1={() => setHop1Expanded(true)}
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Relaciones de alto riesgo</CardTitle>
              <p className="mt-1 text-sm text-navy-500">Pares individuales ordenados por score del siniestro conectado (top {RISK_TABLE_SIZE}).</p>
            </CardHeader>
            <CardContent className="overflow-x-auto p-0">
              {riskRows.length === 0 ? (
                <p className="p-8 text-center text-sm text-navy-400">No hay relaciones de riesgo alto/medio en el rango cargado.</p>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="bg-navy-50 text-xs uppercase text-navy-500">
                    <tr><th className="px-6 py-3">Origen</th><th>Relacion</th><th>Destino</th><th>Score</th></tr>
                  </thead>
                  <tbody className="divide-y divide-navy-100">
                    {riskRows.map((row, index) => (
                      <tr
                        key={`${row.edge.source}-${row.edge.target}-${index}`}
                        className="cursor-pointer bg-white transition hover:bg-cyan-50/60"
                        onClick={() => selectFocus(row.claim.id)}
                      >
                        <td className="px-6 py-3 font-mono text-xs">{labelFor(row.edge.source, graph.nodesById)}</td>
                        <td><Badge variant="info">{row.edge.relacion}</Badge></td>
                        <td className="font-mono text-xs">{labelFor(row.edge.target, graph.nodesById)}</td>
                        <td className="font-bold text-navy-800">{row.claim.score ?? 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>

          <details className="group rounded-2xl border border-navy-200 bg-white">
            <summary className="cursor-pointer list-none rounded-2xl p-5 transition hover:bg-navy-50">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-bold text-navy-900">Ver mapa completo de relaciones (avanzado)</p>
                  <p className="mt-1 text-xs text-navy-500">Vista tecnica de todos los nodos cargados — util para auditoria, no para triage rapido.</p>
                </div>
                <ChevronRight className="h-5 w-5 shrink-0 text-navy-400 transition group-open:rotate-90" />
              </div>
            </summary>
            <div className="space-y-5 border-t border-navy-100 p-5">
              <Legend />
              {fullMap.truncated && (
                <label className="flex items-center gap-2 text-xs font-semibold text-navy-600">
                  <input type="checkbox" checked={showAllInFullMap} onChange={(event) => setShowAllInFullMap(event.target.checked)} />
                  Mostrar todos los nodos cargados ({fullMap.totalBeforeCap}) — puede saturarse
                </label>
              )}
              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="overflow-x-auto rounded-3xl border border-navy-200 bg-white">
                  <svg width={graphWidth} height={fullMap.graphHeight} viewBox={`0 0 ${graphWidth} ${fullMap.graphHeight}`} role="img" aria-label="Mapa completo de relaciones">
                    <defs>
                      <filter id="node-shadow" x="-30%" y="-30%" width="160%" height="160%">
                        <feDropShadow dx="0" dy="5" stdDeviation="5" floodOpacity="0.16" />
                      </filter>
                    </defs>
                    <GraphColumns graphHeight={fullMap.graphHeight} />
                    {fullMap.edges.map((edge, index) => (
                      <GraphLine
                        key={`${edge.source}-${edge.target}-${index}`}
                        edge={edge}
                        nodesById={fullMap.nodesById}
                        dimUnless={focusId ? new Set([focusId]) : undefined}
                      />
                    ))}
                    {fullMap.nodes.map((node) => (
                      <GraphNode
                        key={node.id}
                        node={node}
                        isSelected={node.id === focusId}
                        onSelect={() => selectFocus(node.id)}
                        dimmed={Boolean(focusId) && node.id !== focusId && !fullMap.edges.some((e) => (e.source === focusId && e.target === node.id) || (e.target === focusId && e.source === node.id))}
                      />
                    ))}
                  </svg>
                </div>
                <NodeDetail node={fullMap.nodesById.get(focusId)} />
              </div>
            </div>
          </details>
        </>
      )}
    </div>
  );
}

function Callout({ activeTab, list }: { activeTab: EntityType; list: EntityConcentration[] }) {
  const top = list[0];
  if (!top) return null;
  const counterpartNoun = activeTab === 'Proveedor' ? 'asegurados' : 'proveedores';
  if (top.rojo > 0) {
    return (
      <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
        <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
        <p>
          <strong>{top.label}</strong> concentra <strong>{top.rojo} siniestros rojos</strong> de {top.totalCasos} conectados
          {top.counterpartCount > 0 && <> vinculado a <strong>{top.counterpartCount} {counterpartNoun} distintos</strong></>} — revisar primero.
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-navy-200 bg-navy-50 p-4 text-sm text-navy-600">
      Sin concentracion critica en esta carga — el caso con mas alertas es <strong>{top.label}</strong> ({top.amarillo} amarillos).
    </div>
  );
}

function ConcentrationRow({
  entry,
  rank,
  maxTotal,
  counterpartNoun,
  isActive,
  onSelect,
}: {
  entry: EntityConcentration;
  rank: number;
  maxTotal: number;
  counterpartNoun: string;
  isActive: boolean;
  onSelect: () => void;
}) {
  const isTop = rank === 1;
  const trackWidthPct = Math.max(12, Math.round((entry.totalCasos / Math.max(maxTotal, 1)) * 100));
  const dominantTint = entry.rojo > 0 ? 'bg-red-50/70 border-red-200' : entry.amarillo > 0 ? 'bg-yellow-50/70 border-yellow-200' : 'border-navy-100';
  return (
    <button
      onClick={onSelect}
      className={`flex w-full items-center gap-3 rounded-2xl border p-3 text-left transition hover:border-cyan-300 hover:bg-cyan-50/40 ${
        isActive ? 'border-cyan-500 bg-cyan-50 ring-1 ring-cyan-300' : isTop ? dominantTint : 'border-navy-100 bg-white'
      }`}
    >
      <span className="w-5 shrink-0 text-center text-xs font-black text-navy-400">{rank}</span>
      <span
        className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-black text-white"
        style={{ backgroundColor: entry.tipo === 'Proveedor' ? '#0891b2' : '#64748b' }}
      >
        {entry.tipo === 'Proveedor' ? 'P' : 'A'}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className={`truncate font-bold text-navy-950 ${isTop ? 'text-base' : 'text-sm'}`}>{entry.label}</span>
          {entry.ramos.slice(0, 2).map((ramo) => (
            <span key={ramo} className="rounded-full bg-navy-100 px-2 py-0.5 text-[10px] font-bold text-navy-600">{ramo}</span>
          ))}
          {entry.counterpartCount >= 3 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800">
              <Link2 className="h-3 w-3" /> compartido en {entry.counterpartCount} {counterpartNoun}
            </span>
          )}
        </span>
        <span className="mt-1.5 flex items-center gap-2">
          <span className="h-2 overflow-hidden rounded-full bg-navy-100" style={{ width: `${trackWidthPct}%`, minWidth: 60 }}>
            <span className="flex h-full w-full">
              {entry.rojo > 0 && <span style={{ flexGrow: entry.rojo, backgroundColor: '#ef4444' }} />}
              {entry.amarillo > 0 && <span style={{ flexGrow: entry.amarillo, backgroundColor: '#eab308' }} />}
              {entry.verde > 0 && <span style={{ flexGrow: entry.verde, backgroundColor: '#22c55e' }} />}
            </span>
          </span>
          <span className="whitespace-nowrap text-xs text-navy-500">{entry.rojo} rojo · {entry.amarillo} amarillo · {entry.verde} verde</span>
        </span>
      </span>
      <span className="shrink-0 text-right text-xs font-bold text-navy-500">Score prom.<br /><span className="text-sm text-navy-900">{entry.scorePromedio}</span></span>
    </button>
  );
}

function EgoNetworkPanel({
  graph,
  ego,
  focusId,
  focusExists,
  onFocus,
  onClear,
  onNavigateClaim,
  hop1Expanded,
  onExpandHop1,
}: {
  graph: BuiltGraph;
  ego?: EgoNetwork;
  focusId: string;
  focusExists: boolean;
  onFocus: (id: string) => void;
  onClear: () => void;
  onNavigateClaim: (id: string) => void;
  hop1Expanded: boolean;
  onExpandHop1: () => void;
}) {
  const [query, setQuery] = useState('');
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return graph.nodes.filter((node) => node.label.toLowerCase().includes(q) || node.id.toLowerCase().includes(q)).slice(0, 8);
  }, [graph, query]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Red del caso seleccionado</CardTitle>
        <p className="mt-1 text-sm text-navy-500">Conexiones directas de un proveedor, asegurado o siniestro especifico.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-navy-400" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar proveedor, asegurado o SIN..."
            className="w-full rounded-xl border border-navy-200 py-2 pl-9 pr-3 text-sm"
          />
          {matches.length > 0 && (
            <div className="absolute z-10 mt-1 w-full overflow-hidden rounded-xl border border-navy-200 bg-white shadow-lg">
              {matches.map((match) => (
                <button
                  key={match.id}
                  onClick={() => { onFocus(match.id); setQuery(''); }}
                  className="flex w-full items-center justify-between gap-2 px-4 py-2 text-left text-sm hover:bg-cyan-50"
                >
                  <span className="truncate">{match.label}</span>
                  <Badge variant="default" className="shrink-0">{match.tipo}</Badge>
                </button>
              ))}
            </div>
          )}
        </div>

        {!focusId ? (
          <div className="grid place-items-center rounded-3xl border-2 border-dashed border-navy-200 py-14 text-center">
            <Network className="mb-3 h-9 w-9 text-navy-300" />
            <p className="font-bold text-navy-700">Explora la red de un caso especifico</p>
            <p className="mt-1 max-w-sm text-sm text-navy-400">
              Selecciona un proveedor o asegurado del radar de arriba, o una relacion de la tabla, para ver su cadena de conexiones directas.
            </p>
          </div>
        ) : !focusExists || !ego ? (
          <div className="rounded-2xl border border-navy-200 bg-navy-50 p-6 text-center text-sm text-navy-500">
            El elemento seleccionado ya no tiene siniestros que cumplan este filtro.
            <button onClick={onClear} className="mt-2 block w-full text-xs font-bold text-cyan-700 hover:text-cyan-900">Limpiar seleccion</button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-navy-600">
                {ego.focus.tipo} <span className="text-navy-900">{ego.focus.label}</span>
              </p>
              <button onClick={onClear} className="flex items-center gap-1 rounded-lg border border-navy-200 px-2 py-1 text-xs font-bold text-navy-500 hover:bg-navy-50">
                <X className="h-3.5 w-3.5" /> Limpiar seleccion
              </button>
            </div>
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
              <div className="overflow-x-auto rounded-3xl border border-navy-200 bg-white">
                <svg width={graphWidth} height={ego.graphHeight} viewBox={`0 0 ${graphWidth} ${ego.graphHeight}`} role="img" aria-label="Red de conexiones directas">
                  <defs>
                    <filter id="node-shadow-ego" x="-30%" y="-30%" width="160%" height="160%">
                      <feDropShadow dx="0" dy="5" stdDeviation="5" floodOpacity="0.16" />
                    </filter>
                  </defs>
                  <GraphColumns graphHeight={ego.graphHeight} />
                  {ego.edges.map((edge, index) => {
                    const nodesById = new Map([ego.focus, ...ego.hop1, ...ego.hop2].map((node) => [node.id, node]));
                    return <GraphLine key={`${edge.source}-${edge.target}-${index}`} edge={edge} nodesById={nodesById} shadowId="node-shadow-ego" />;
                  })}
                  {[ego.focus, ...ego.hop1, ...ego.hop2].map((node) => (
                    <GraphNode
                      key={node.id}
                      node={node}
                      isSelected={node.id === ego.focus.id}
                      isFocus={node.id === ego.focus.id}
                      onSelect={() => onFocus(node.id)}
                      shadowId="node-shadow-ego"
                    />
                  ))}
                </svg>
                {ego.hop1Truncated && !hop1Expanded && (
                  <div className="border-t border-navy-100 p-3 text-center text-xs text-navy-500">
                    Mostrando {ego.hop1.length} de {ego.hop1Total} siniestros conectados (priorizando los de mayor riesgo).{' '}
                    <button onClick={onExpandHop1} className="font-bold text-cyan-700 hover:text-cyan-900">Ver todos ({ego.hop1Total})</button>
                  </div>
                )}
              </div>
              <EgoDetail focus={ego.focus} hop1={ego.hop1} onNavigateClaim={onNavigateClaim} />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function EgoDetail({ focus, hop1, onNavigateClaim }: { focus: PositionedNode; hop1: PositionedNode[]; onNavigateClaim: (id: string) => void }) {
  const claims = focus.tipo === 'Siniestro' ? [focus] : hop1.filter((node) => node.tipo === 'Siniestro');
  const rojo = claims.filter((claim) => claim.nivel === 'Rojo').length;
  const amarillo = claims.filter((claim) => claim.nivel === 'Amarillo').length;
  const verde = claims.filter((claim) => claim.nivel === 'Verde').length;
  const avgScore = claims.length ? Math.round(claims.reduce((sum, claim) => sum + (claim.score ?? 0), 0) / claims.length) : undefined;
  return (
    <div className="rounded-3xl border border-navy-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-2xl text-white" style={{ backgroundColor: nodeFill(focus) }}>
          <GitBranch className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-lg font-black text-navy-950">{focus.label}</p>
          <p className="text-sm text-navy-500">{focus.tipo}</p>
        </div>
      </div>
      <div className="space-y-3 text-sm">
        {focus.tipo !== 'Siniestro' && (
          <>
            <DetailRow label="Siniestros conectados" value={String(claims.length)} />
            <DetailRow label="Rojo / Amarillo / Verde" value={`${rojo} / ${amarillo} / ${verde}`} />
            {avgScore !== undefined && <DetailRow label="Score promedio" value={String(avgScore)} />}
          </>
        )}
        {focus.tipo === 'Siniestro' && (
          <>
            <DetailRow label="Ramo" value={focus.ramo ?? 'N/A'} />
            <DetailRow label="Score" value={focus.score !== undefined ? String(focus.score) : 'N/A'} />
            <div className="flex items-center justify-between"><span className="text-navy-500">Nivel</span>{focus.nivel ? <Badge variant={focus.nivel}>{focus.nivel}</Badge> : 'N/A'}</div>
          </>
        )}
      </div>
      {claims.length > 0 && (
        <div className="mt-4 space-y-1.5">
          <p className="text-xs font-bold uppercase text-navy-400">Siniestros conectados</p>
          <div className="flex flex-wrap gap-1.5">
            {claims.slice(0, 12).map((claim) => (
              <button
                key={claim.id}
                onClick={() => onNavigateClaim(claim.id)}
                className="inline-flex items-center gap-1.5 rounded-full border border-navy-200 px-2.5 py-1 text-xs font-semibold text-navy-700 hover:border-cyan-300 hover:bg-cyan-50"
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: nodeFill(claim) }} />
                {claim.label}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="mt-5 rounded-2xl bg-yellow-50 p-4 text-xs text-yellow-900">
        Esta conexion es una senal de priorizacion para revision humana, no una acusacion.
      </div>
    </div>
  );
}

function buildGraph(data: RelationshipNetwork | undefined, filter: GraphFilter) {
  const sourceNodes = data?.nodes ?? [];
  const sourceEdges = data?.edges ?? [];
  const originalNodeMap = new Map(sourceNodes.map((node) => [node.id, node]));

  const allowedClaimIds = new Set(
    sourceNodes
      .filter((node) => node.tipo === 'Siniestro')
      .filter((node) => {
        if (filter === 'Solo rojos') return node.nivel === 'Rojo';
        if (filter === 'Vehiculos' || filter === 'Salud' || filter === 'Hogar') return node.ramo === filter;
        return true;
      })
      .map((node) => node.id),
  );

  const edges = sourceEdges.filter((edge) => {
    const source = originalNodeMap.get(edge.source);
    const target = originalNodeMap.get(edge.target);
    const claim = source?.tipo === 'Siniestro' ? source : target?.tipo === 'Siniestro' ? target : undefined;
    return claim ? allowedClaimIds.has(claim.id) : true;
  });

  const includedIds = new Set<string>();
  edges.forEach((edge) => {
    includedIds.add(edge.source);
    includedIds.add(edge.target);
  });

  const degree = new Map<string, number>();
  edges.forEach((edge) => {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
  });

  const groups = {
    Asegurado: sourceNodes.filter((node) => includedIds.has(node.id) && node.tipo === 'Asegurado'),
    Siniestro: sourceNodes.filter((node) => includedIds.has(node.id) && node.tipo === 'Siniestro'),
    Proveedor: sourceNodes.filter((node) => includedIds.has(node.id) && node.tipo === 'Proveedor'),
  };

  // Scale height to the largest column so node spacing never drops below a
  // legible minimum, regardless of how many nodes are loaded (limit=10..120).
  const maxColumnSize = Math.max(1, groups.Asegurado.length, groups.Siniestro.length, groups.Proveedor.length);
  const graphHeight = Math.max(minGraphHeight, maxColumnSize * minNodeSpacing);

  const positioned = Object.entries(groups).flatMap(([type, nodes]) => positionGroup(type, nodes, degree, graphHeight));
  const nodesById = new Map(positioned.map((node) => [node.id, node]));

  return {
    nodes: positioned,
    edges: edges.filter((edge) => nodesById.has(edge.source) && nodesById.has(edge.target)),
    nodesById,
    graphHeight,
    counts: {
      claims: groups.Siniestro.length,
      providers: groups.Proveedor.length,
    },
  };
}

// Agrega el grafo ya filtrado por proveedor/asegurado: cuantos siniestros
// conecta cada uno, su composicion de riesgo y con cuantas contrapartes
// distintas del otro lado humano (asegurados para un proveedor, y viceversa)
// aparece -- esa ultima señal es la que mas se acerca a "posible red", en vez
// de solo "muchos casos".
function buildConcentrations(graph: BuiltGraph): ConcentrationSummary {
  const providerMap = new Map<string, EntityConcentration>();
  const insuredMap = new Map<string, EntityConcentration>();
  const providerCounterparts = new Map<string, Set<string>>();
  const insuredCounterparts = new Map<string, Set<string>>();
  const claimToInsured = new Map<string, string>();
  const claimToProviders = new Map<string, string[]>();

  graph.edges.forEach((edge) => {
    const source = graph.nodesById.get(edge.source);
    const target = graph.nodesById.get(edge.target);
    if (!source || !target) return;
    const claim = source.tipo === 'Siniestro' ? source : target.tipo === 'Siniestro' ? target : undefined;
    const other = source.tipo === 'Siniestro' ? target : source;
    if (!claim) return;
    if (other.tipo === 'Asegurado') claimToInsured.set(claim.id, other.id);
    if (other.tipo === 'Proveedor') {
      const list = claimToProviders.get(claim.id) ?? [];
      list.push(other.id);
      claimToProviders.set(claim.id, list);
    }
  });

  const bump = (map: Map<string, EntityConcentration>, entity: PositionedNode, claim: PositionedNode) => {
    const existing = map.get(entity.id) ?? {
      id: entity.id,
      label: entity.label,
      tipo: entity.tipo as EntityType,
      totalCasos: 0,
      rojo: 0,
      amarillo: 0,
      verde: 0,
      scoreSum: 0,
      scorePromedio: 0,
      ramos: [] as string[],
      counterpartCount: 0,
      claimIds: [] as string[],
    };
    existing.totalCasos += 1;
    if (claim.nivel === 'Rojo') existing.rojo += 1;
    else if (claim.nivel === 'Amarillo') existing.amarillo += 1;
    else if (claim.nivel === 'Verde') existing.verde += 1;
    existing.scoreSum += claim.score ?? 0;
    if (claim.ramo && !existing.ramos.includes(claim.ramo)) existing.ramos.push(claim.ramo);
    existing.claimIds.push(claim.id);
    map.set(entity.id, existing);
  };

  graph.edges.forEach((edge) => {
    const source = graph.nodesById.get(edge.source);
    const target = graph.nodesById.get(edge.target);
    if (!source || !target) return;
    const claim = source.tipo === 'Siniestro' ? source : target.tipo === 'Siniestro' ? target : undefined;
    const other = source.tipo === 'Siniestro' ? target : source;
    if (!claim) return;
    if (other.tipo === 'Proveedor') {
      bump(providerMap, other, claim);
      const insuredId = claimToInsured.get(claim.id);
      if (insuredId) {
        const set = providerCounterparts.get(other.id) ?? new Set<string>();
        set.add(insuredId);
        providerCounterparts.set(other.id, set);
      }
    }
    if (other.tipo === 'Asegurado') {
      bump(insuredMap, other, claim);
      const providerIds = claimToProviders.get(claim.id) ?? [];
      const set = insuredCounterparts.get(other.id) ?? new Set<string>();
      providerIds.forEach((id) => set.add(id));
      insuredCounterparts.set(other.id, set);
    }
  });

  const finalize = (map: Map<string, EntityConcentration>, counterparts: Map<string, Set<string>>) =>
    Array.from(map.values())
      .map((entry) => ({
        ...entry,
        scorePromedio: entry.totalCasos ? Math.round(entry.scoreSum / entry.totalCasos) : 0,
        counterpartCount: counterparts.get(entry.id)?.size ?? 0,
      }))
      .sort((a, b) => b.rojo - a.rojo || b.scoreSum - a.scoreSum || b.totalCasos - a.totalCasos || a.label.localeCompare(b.label));

  return {
    providers: finalize(providerMap, providerCounterparts),
    insureds: finalize(insuredMap, insuredCounterparts).filter((entry) => entry.totalCasos >= 2),
  };
}

function riskRank(nivel?: string): number {
  return nivel === 'Rojo' ? 0 : nivel === 'Amarillo' ? 1 : nivel === 'Verde' ? 2 : 3;
}

function sortByRisk(a: RelationshipNode, b: RelationshipNode) {
  return riskRank(a.nivel) - riskRank(b.nivel) || (b.score ?? 0) - (a.score ?? 0);
}

// Vecindad acotada de una entidad (foco), nunca mas de 1 + hop1Cap + hop2Cap
// nodos, sin importar cuantos datos esten cargados en total.
function buildEgoNetwork(graph: BuiltGraph, focusId: string, hopCap: number, expandHop1: boolean): EgoNetwork | undefined {
  const focus = graph.nodesById.get(focusId);
  if (!focus) return undefined;

  const connectedEdges = (nodeId: string) => graph.edges.filter((edge) => edge.source === nodeId || edge.target === nodeId);
  const otherEnd = (edge: RelationshipEdge, nodeId: string) => (edge.source === nodeId ? edge.target : edge.source);

  let hop1Nodes: PositionedNode[];
  let hop1Total: number;
  const edgesUsed: RelationshipEdge[] = [];

  if (focus.tipo === 'Siniestro') {
    const edges = connectedEdges(focus.id);
    hop1Nodes = edges
      .map((edge) => graph.nodesById.get(otherEnd(edge, focus.id)))
      .filter((node): node is PositionedNode => Boolean(node));
    hop1Total = hop1Nodes.length;
    edgesUsed.push(...edges);
  } else {
    const claimEdges = connectedEdges(focus.id).filter((edge) => graph.nodesById.get(otherEnd(edge, focus.id))?.tipo === 'Siniestro');
    const claimNodes = claimEdges
      .map((edge) => graph.nodesById.get(otherEnd(edge, focus.id)))
      .filter((node): node is PositionedNode => Boolean(node))
      .sort(sortByRisk);
    hop1Total = claimNodes.length;
    hop1Nodes = expandHop1 ? claimNodes : claimNodes.slice(0, hopCap);
    const shownIds = new Set(hop1Nodes.map((node) => node.id));
    edgesUsed.push(...claimEdges.filter((edge) => shownIds.has(otherEnd(edge, focus.id))));
  }

  let hop2Nodes: PositionedNode[] = [];
  if (focus.tipo !== 'Siniestro') {
    const seen = new Set<string>([focus.id, ...hop1Nodes.map((node) => node.id)]);
    const candidates: PositionedNode[] = [];
    hop1Nodes.forEach((claimNode) => {
      connectedEdges(claimNode.id).forEach((edge) => {
        const otherId = otherEnd(edge, claimNode.id);
        if (seen.has(otherId)) return;
        const otherNode = graph.nodesById.get(otherId);
        if (!otherNode || otherNode.tipo === 'Siniestro') return;
        seen.add(otherId);
        candidates.push(otherNode);
      });
    });
    hop2Nodes = candidates.sort(sortByRisk).slice(0, hopCap);
    const hop2Ids = new Set(hop2Nodes.map((node) => node.id));
    hop1Nodes.forEach((claimNode) => {
      connectedEdges(claimNode.id).forEach((edge) => {
        const otherId = otherEnd(edge, claimNode.id);
        if (hop2Ids.has(otherId)) edgesUsed.push(edge);
      });
    });
  }

  const allIds = new Set([focus.id, ...hop1Nodes.map((node) => node.id), ...hop2Nodes.map((node) => node.id)]);
  const byType: Record<string, PositionedNode[]> = { Asegurado: [], Siniestro: [], Proveedor: [] };
  [focus, ...hop1Nodes, ...hop2Nodes].forEach((node) => {
    if (byType[node.tipo]) byType[node.tipo].push(node);
  });
  const maxColumnSize = Math.max(1, byType.Asegurado.length, byType.Siniestro.length, byType.Proveedor.length);
  const graphHeight = Math.max(minGraphHeight, maxColumnSize * minNodeSpacing);
  const degree = new Map<string, number>();
  edgesUsed.forEach((edge) => {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
  });
  const repositioned = Object.entries(byType).flatMap(([type, nodes]) => positionGroup(type, nodes, degree, graphHeight));
  const repositionedById = new Map(repositioned.map((node) => [node.id, node]));
  const focusNode = repositionedById.get(focus.id);
  if (!focusNode) return undefined;

  return {
    focus: focusNode,
    hop1: hop1Nodes.map((node) => repositionedById.get(node.id)).filter((node): node is PositionedNode => Boolean(node)),
    hop2: hop2Nodes.map((node) => repositionedById.get(node.id)).filter((node): node is PositionedNode => Boolean(node)),
    edges: edgesUsed.filter((edge) => allIds.has(edge.source) && allIds.has(edge.target)),
    hop1Total,
    hop1Truncated: hop1Total > hop1Nodes.length,
    graphHeight,
  };
}

// El mapa completo (bajo el <details> de auditoria) reutiliza el grafo ya
// filtrado, pero re-posiciona un subconjunto capado por columna para que la
// altura/espaciado nunca dependa de cuantos casos se hayan cargado.
function capGraphForFullMap(graph: BuiltGraph, cap: number, showAll: boolean) {
  const byType: Record<string, PositionedNode[]> = { Asegurado: [], Siniestro: [], Proveedor: [] };
  graph.nodes.forEach((node) => {
    if (byType[node.tipo]) byType[node.tipo].push(node);
  });
  const truncated = !showAll && (byType.Asegurado.length > cap || byType.Siniestro.length > cap || byType.Proveedor.length > cap);
  const capped: Record<string, PositionedNode[]> = {
    Asegurado: showAll ? byType.Asegurado : byType.Asegurado.slice(0, cap),
    Siniestro: showAll ? byType.Siniestro : byType.Siniestro.slice(0, cap),
    Proveedor: showAll ? byType.Proveedor : byType.Proveedor.slice(0, cap),
  };
  const keptIds = new Set([...capped.Asegurado, ...capped.Siniestro, ...capped.Proveedor].map((node) => node.id));
  const edges = graph.edges.filter((edge) => keptIds.has(edge.source) && keptIds.has(edge.target));
  const maxColumnSize = Math.max(1, capped.Asegurado.length, capped.Siniestro.length, capped.Proveedor.length);
  const graphHeight = Math.max(minGraphHeight, maxColumnSize * minNodeSpacing);
  const degree = new Map<string, number>();
  edges.forEach((edge) => {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
  });
  const positioned = Object.entries(capped).flatMap(([type, nodes]) => positionGroup(type, nodes, degree, graphHeight));
  const nodesById = new Map(positioned.map((node) => [node.id, node]));
  return {
    nodes: positioned,
    edges: edges.filter((edge) => nodesById.has(edge.source) && nodesById.has(edge.target)),
    nodesById,
    graphHeight,
    truncated,
    totalBeforeCap: graph.nodes.length,
  };
}

// Tabla de relaciones individuales de mayor riesgo (complementa al radar de
// concentracion, que agrega por entidad): pares Asegurado-Siniestro-Proveedor
// puntuales, priorizando Rojo y completando con Amarillo/Verde si hace falta.
function buildRiskRows(graph: BuiltGraph, size: number) {
  const withClaim = graph.edges
    .map((edge) => {
      const source = graph.nodesById.get(edge.source);
      const target = graph.nodesById.get(edge.target);
      const claim = source?.tipo === 'Siniestro' ? source : target?.tipo === 'Siniestro' ? target : undefined;
      return claim ? { edge, claim } : undefined;
    })
    .filter((row): row is { edge: RelationshipEdge; claim: PositionedNode } => Boolean(row));

  return withClaim.sort((a, b) => riskRank(a.claim.nivel) - riskRank(b.claim.nivel) || (b.claim.score ?? 0) - (a.claim.score ?? 0)).slice(0, size);
}

function positionGroup(type: string, nodes: RelationshipNode[], degree: Map<string, number>, graphHeight: number): PositionedNode[] {
  const sorted = [...nodes].sort((a, b) => (b.score ?? 0) - (a.score ?? 0) || (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0));
  const top = 76;
  const bottom = graphHeight - 76;
  const step = sorted.length > 1 ? (bottom - top) / (sorted.length - 1) : 0;
  return sorted.map((node, index) => ({
    ...node,
    x: columnX[type],
    y: sorted.length === 1 ? graphHeight / 2 : top + step * index,
    degree: degree.get(node.id) ?? 0,
  }));
}

function GraphColumns({ graphHeight }: { graphHeight: number }) {
  const columns = [
    { x: columnX.Asegurado, label: 'Asegurados anonimos' },
    { x: columnX.Siniestro, label: 'Siniestros' },
    { x: columnX.Proveedor, label: 'Proveedores' },
  ];
  return (
    <g>
      {columns.map((column) => (
        <g key={column.label}>
          <line x1={column.x} x2={column.x} y1={44} y2={graphHeight - 38} stroke="#e2e8f0" strokeDasharray="6 8" />
          <text x={column.x} y={34} textAnchor="middle" className="fill-slate-500 text-[14px] font-bold uppercase tracking-wide">{column.label}</text>
        </g>
      ))}
    </g>
  );
}

function GraphLine({
  edge,
  nodesById,
  dimUnless,
  shadowId,
}: {
  edge: RelationshipEdge;
  nodesById: Map<string, PositionedNode>;
  dimUnless?: Set<string>;
  shadowId?: string;
}) {
  void shadowId;
  const source = nodesById.get(edge.source);
  const target = nodesById.get(edge.target);
  if (!source || !target) return null;
  const claim = source.tipo === 'Siniestro' ? source : target.tipo === 'Siniestro' ? target : undefined;
  const stroke = claim?.nivel === 'Rojo' ? '#ef4444' : claim?.nivel === 'Amarillo' ? '#eab308' : claim?.nivel === 'Verde' ? '#22c55e' : '#94a3b8';
  const width = 1.4 + Math.min((claim?.score ?? 0) / 45, 2);
  const dimmed = dimUnless ? !dimUnless.has(source.id) && !dimUnless.has(target.id) : false;
  return (
    <line
      x1={source.x}
      y1={source.y}
      x2={target.x}
      y2={target.y}
      stroke={stroke}
      strokeWidth={width}
      strokeOpacity={dimmed ? 0.06 : 0.28}
    />
  );
}

function GraphNode({
  node,
  isSelected,
  isFocus,
  onSelect,
  dimmed,
  shadowId = 'node-shadow',
}: {
  node: PositionedNode;
  isSelected: boolean;
  isFocus?: boolean;
  onSelect: () => void;
  dimmed?: boolean;
  shadowId?: string;
}) {
  const radius = node.tipo === 'Siniestro' ? 18 : 14;
  const fill = nodeFill(node);
  return (
    <g
      className="cursor-pointer"
      style={{ opacity: dimmed ? 0.08 : 1 }}
      onClick={onSelect}
      onKeyDown={(event) => event.key === 'Enter' && onSelect()}
      tabIndex={0}
      role="button"
      aria-label={`Seleccionar ${node.label}`}
    >
      {isFocus && <circle cx={node.x} cy={node.y} r={radius + Math.min(node.degree, 5) + 9} fill={fill} opacity={0.15} />}
      <circle
        cx={node.x}
        cy={node.y}
        r={radius + Math.min(node.degree, 5)}
        fill={fill}
        stroke={isSelected ? '#0f172a' : '#ffffff'}
        strokeWidth={isSelected ? 4 : 3}
        filter={`url(#${shadowId})`}
      />
      <text x={node.x} y={node.y + 4} textAnchor="middle" className="pointer-events-none fill-white text-[11px] font-black">
        {node.tipo === 'Siniestro' ? 'S' : node.tipo === 'Proveedor' ? 'P' : 'A'}
      </text>
      <text x={node.x} y={node.y + radius + 20} textAnchor="middle" className="pointer-events-none fill-slate-700 text-[11px] font-semibold">
        {truncate(node.label, 16)}
      </text>
    </g>
  );
}

function NodeDetail({ node }: { node?: PositionedNode }) {
  if (!node) {
    return (
      <div className="rounded-3xl border border-navy-200 bg-navy-50 p-5 text-sm text-navy-500">
        Selecciona un nodo del mapa para ver su detalle.
      </div>
    );
  }
  return (
    <div className="rounded-3xl border border-navy-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-2xl text-white" style={{ backgroundColor: nodeFill(node) }}>
          <GitBranch className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-lg font-black text-navy-950">{node.label}</p>
          <p className="text-sm text-navy-500">{node.tipo}</p>
        </div>
      </div>
      <div className="space-y-3 text-sm">
        <DetailRow label="Conexiones" value={String(node.degree)} />
        <DetailRow label="Ramo" value={node.ramo ?? 'N/A'} />
        <DetailRow label="Score" value={node.score ? String(node.score) : 'N/A'} />
        <div className="flex items-center justify-between">
          <span className="text-navy-500">Nivel</span>
          {node.nivel ? <Badge variant={node.nivel}>{node.nivel}</Badge> : <span className="font-semibold text-navy-800">N/A</span>}
        </div>
      </div>
      <div className="mt-5 rounded-2xl bg-yellow-50 p-4 text-xs text-yellow-900">
        Esta conexion es una senal de priorizacion para revision humana, no una acusacion.
      </div>
    </div>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-navy-50 p-4 text-xs font-semibold text-navy-600">
      <LegendItem color="#64748b" label="Asegurado anonimo" />
      <LegendItem color="#ef4444" label="Siniestro rojo" />
      <LegendItem color="#eab308" label="Siniestro amarillo" />
      <LegendItem color="#22c55e" label="Siniestro verde" />
      <LegendItem color="#0891b2" label="Proveedor" />
      <span className="ml-auto text-navy-500">Lineas = relaciones reporta / atiende</span>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return <span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />{label}</span>;
}

function Metric({ title, value, subtitle, onClick }: { title: string; value: number | string; subtitle?: string; onClick?: () => void }) {
  const content = (
    <CardContent className="flex items-center gap-4 p-5">
      <div className="grid h-11 w-11 place-items-center rounded-2xl bg-cyan-50 text-cyan-700"><Network className="h-5 w-5" /></div>
      <div className="min-w-0">
        <p className="text-sm text-navy-500">{title}</p>
        <p className="truncate text-2xl font-black text-navy-950">{value}</p>
        {subtitle && <p className="truncate text-xs text-navy-400">{subtitle}</p>}
      </div>
    </CardContent>
  );
  if (!onClick) return <Card>{content}</Card>;
  return (
    <Card className="cursor-pointer transition hover:border-cyan-300 hover:shadow-md" onClick={onClick}>
      {content}
    </Card>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return <div className="flex justify-between gap-4"><span className="text-navy-500">{label}</span><span className="font-semibold text-navy-800">{value}</span></div>;
}

function nodeFill(node: RelationshipNode) {
  if (node.tipo === 'Proveedor') return '#0891b2';
  if (node.tipo === 'Asegurado') return '#64748b';
  if (node.nivel === 'Rojo') return '#ef4444';
  if (node.nivel === 'Amarillo') return '#eab308';
  if (node.nivel === 'Verde') return '#22c55e';
  return '#0f172a';
}

function labelFor(id: string, nodesById: Map<string, PositionedNode>) {
  const node = nodesById.get(id);
  return node ? `${node.label} (${node.tipo})` : id;
}

function truncate(value: string, max: number) {
  return value.length > max ? `${value.slice(0, max - 1)}...` : value;
}
