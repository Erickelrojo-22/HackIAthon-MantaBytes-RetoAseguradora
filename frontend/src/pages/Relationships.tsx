import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GitBranch, Loader2, Network } from 'lucide-react';
import { api, type RelationshipEdge, type RelationshipNetwork, type RelationshipNode } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

type GraphFilter = 'Todos' | 'Solo rojos' | 'Vehiculos' | 'Salud' | 'Hogar';

interface PositionedNode extends RelationshipNode {
  x: number;
  y: number;
  degree: number;
}

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

export function Relationships() {
  const [filter, setFilter] = useState<GraphFilter>('Todos');
  const [limit, setLimit] = useState(60);
  const [selectedNodeId, setSelectedNodeId] = useState<string>('');
  const { data, isLoading, error } = useQuery({
    queryKey: ['relationships', limit],
    queryFn: async () => (await api.get<RelationshipNetwork>(`/relationships?limit=${limit}`)).data,
  });

  const graph = useMemo(() => buildGraph(data, filter), [data, filter]);
  const selectedNode = graph.nodes.find((node) => node.id === selectedNodeId) ?? graph.nodes[0];
  const graphHeight = graph.graphHeight;

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-navy-950 p-8 text-white shadow-2xl">
        <Badge variant="info" className="mb-4 border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Red explicable</Badge>
        <h1 className="text-3xl font-black">Relaciones entre asegurados, siniestros y proveedores</h1>
        <p className="mt-3 max-w-3xl text-navy-200">
          Visualizacion de conexiones para priorizar revision humana. La red muestra patrones operativos; no acusa fraude ni decide pagos.
        </p>
      </div>

      {isLoading ? (
        <div className="grid h-72 place-items-center"><Loader2 className="h-9 w-9 animate-spin text-cyan-700" /></div>
      ) : error ? (
        <Card><CardContent className="text-red-600">No fue posible cargar la red de relaciones.</CardContent></Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
            <Metric title="Nodos visibles" value={graph.nodes.length} />
            <Metric title="Relaciones visibles" value={graph.edges.length} />
            <Metric title="Siniestros" value={graph.counts.claims} />
            <Metric title="Proveedores" value={graph.counts.providers} />
          </div>

          <Card>
            <CardHeader className="gap-4">
              <div>
                <CardTitle>Grafo de relaciones</CardTitle>
                <p className="mt-1 text-sm text-navy-500">Asegurado anonimo {'->'} siniestro {'->'} proveedor vinculado</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {filters.map((item) => (
                  <button
                    key={item}
                    onClick={() => {
                      setFilter(item);
                      setSelectedNodeId('');
                    }}
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
                    onChange={(event) => {
                      setLimit(Number(event.target.value));
                      setSelectedNodeId('');
                    }}
                    className="rounded-full border border-navy-200 bg-white px-2 py-1.5 text-xs font-bold text-navy-700"
                  >
                    {limitOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <Legend />
              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="overflow-x-auto rounded-3xl border border-navy-200 bg-white">
                  <svg width={graphWidth} height={graphHeight} viewBox={`0 0 ${graphWidth} ${graphHeight}`} role="img" aria-label="Grafo de relaciones de siniestros">
                    <defs>
                      <filter id="node-shadow" x="-30%" y="-30%" width="160%" height="160%">
                        <feDropShadow dx="0" dy="5" stdDeviation="5" floodOpacity="0.16" />
                      </filter>
                    </defs>
                    <GraphColumns graphHeight={graphHeight} />
                    {graph.edges.map((edge, index) => (
                      <GraphLine key={`${edge.source}-${edge.target}-${index}`} edge={edge} nodesById={graph.nodesById} />
                    ))}
                    {graph.nodes.map((node) => (
                      <GraphNode
                        key={node.id}
                        node={node}
                        isSelected={(selectedNode?.id ?? '') === node.id}
                        onSelect={() => setSelectedNodeId(node.id)}
                      />
                    ))}
                  </svg>
                </div>
                <NodeDetail node={selectedNode} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>
                Relaciones principales
                {graph.edges.length > 35 && (
                  <span className="ml-2 text-xs font-normal text-navy-400">(mostrando 35 de {graph.edges.length})</span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto p-0">
              <table className="w-full text-left text-sm">
                <thead className="bg-navy-50 text-xs uppercase text-navy-500">
                  <tr><th className="px-6 py-3">Origen</th><th>Relacion</th><th>Destino</th></tr>
                </thead>
                <tbody className="divide-y divide-navy-100">
                  {graph.edges.slice(0, 35).map((edge, index) => (
                    <tr key={`${edge.source}-${edge.target}-${index}`} className="bg-white">
                      <td className="px-6 py-3 font-mono text-xs">{labelFor(edge.source, graph.nodesById)}</td>
                      <td><Badge variant="info">{edge.relacion}</Badge></td>
                      <td className="font-mono text-xs">{labelFor(edge.target, graph.nodesById)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
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

function GraphLine({ edge, nodesById }: { edge: RelationshipEdge; nodesById: Map<string, PositionedNode> }) {
  const source = nodesById.get(edge.source);
  const target = nodesById.get(edge.target);
  if (!source || !target) return null;
  const claim = source.tipo === 'Siniestro' ? source : target.tipo === 'Siniestro' ? target : undefined;
  const stroke = claim?.nivel === 'Rojo' ? '#ef4444' : claim?.nivel === 'Amarillo' ? '#eab308' : claim?.nivel === 'Verde' ? '#22c55e' : '#94a3b8';
  const width = 1.4 + Math.min((claim?.score ?? 0) / 45, 2);
  return (
    <line
      x1={source.x}
      y1={source.y}
      x2={target.x}
      y2={target.y}
      stroke={stroke}
      strokeWidth={width}
      strokeOpacity={0.28}
    />
  );
}

function GraphNode({ node, isSelected, onSelect }: { node: PositionedNode; isSelected: boolean; onSelect: () => void }) {
  const radius = node.tipo === 'Siniestro' ? 18 : 14;
  const fill = nodeFill(node);
  return (
    <g className="cursor-pointer" onClick={onSelect} onKeyDown={(event) => event.key === 'Enter' && onSelect()} tabIndex={0} role="button" aria-label={`Seleccionar ${node.label}`}>
      <circle
        cx={node.x}
        cy={node.y}
        r={radius + Math.min(node.degree, 5)}
        fill={fill}
        stroke={isSelected ? '#0f172a' : '#ffffff'}
        strokeWidth={isSelected ? 4 : 3}
        filter="url(#node-shadow)"
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
        Selecciona un nodo para ver su detalle.
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

function Metric({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-cyan-50 text-cyan-700"><Network className="h-5 w-5" /></div>
        <div><p className="text-sm text-navy-500">{title}</p><p className="text-2xl font-black text-navy-950">{value}</p></div>
      </CardContent>
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
