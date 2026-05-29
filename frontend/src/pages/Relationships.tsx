import { useQuery } from '@tanstack/react-query';
import { GitBranch, Loader2, Network } from 'lucide-react';
import { api, type RelationshipNetwork, type RelationshipNode } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

const nodeTones: Record<string, string> = {
  Siniestro: 'border-red-200 bg-red-50',
  Proveedor: 'border-cyan-200 bg-cyan-50',
  Asegurado: 'border-navy-200 bg-navy-50',
};

export function Relationships() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['relationships'],
    queryFn: async () => (await api.get<RelationshipNetwork>('/relationships?limit=80')).data,
  });

  const nodes = data?.nodes ?? [];
  const edges = data?.edges ?? [];
  const claims = nodes.filter((node) => node.tipo === 'Siniestro');
  const providers = nodes.filter((node) => node.tipo === 'Proveedor');
  const insured = nodes.filter((node) => node.tipo === 'Asegurado');

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-navy-950 p-8 text-white shadow-2xl">
        <Badge variant="info" className="mb-4 border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Red explicable</Badge>
        <h1 className="text-3xl font-black">Relaciones entre siniestros, asegurados y proveedores</h1>
        <p className="mt-3 max-w-3xl text-navy-200">
          Esta vista ayuda a detectar concentraciones operativas para revision humana. No representa acusaciones ni conclusiones legales.
        </p>
      </div>

      {isLoading ? (
        <div className="grid h-72 place-items-center"><Loader2 className="h-9 w-9 animate-spin text-cyan-700" /></div>
      ) : error ? (
        <Card><CardContent className="text-red-600">No fue posible cargar la red de relaciones.</CardContent></Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
            <Metric title="Nodos" value={nodes.length} />
            <Metric title="Relaciones" value={edges.length} />
            <Metric title="Siniestros" value={claims.length} />
            <Metric title="Proveedores" value={providers.length} />
          </div>

          <Card>
            <CardHeader><CardTitle>Mapa visual simplificado</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-4 lg:grid-cols-3">
                <NodeColumn title="Asegurados anonimos" nodes={insured.slice(0, 12)} />
                <NodeColumn title="Siniestros priorizados" nodes={claims.slice(0, 12)} />
                <NodeColumn title="Proveedores vinculados" nodes={providers.slice(0, 12)} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Relaciones principales</CardTitle></CardHeader>
            <CardContent className="overflow-x-auto p-0">
              <table className="w-full text-left text-sm">
                <thead className="bg-navy-50 text-xs uppercase text-navy-500">
                  <tr><th className="px-6 py-3">Origen</th><th>Relacion</th><th>Destino</th></tr>
                </thead>
                <tbody className="divide-y divide-navy-100">
                  {edges.slice(0, 30).map((edge, index) => (
                    <tr key={`${edge.source}-${edge.target}-${index}`} className="bg-white">
                      <td className="px-6 py-3 font-mono text-xs">{edge.source}</td>
                      <td><Badge variant="info">{edge.relacion}</Badge></td>
                      <td className="font-mono text-xs">{edge.target}</td>
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

function NodeColumn({ title, nodes }: { title: string; nodes: RelationshipNode[] }) {
  return (
    <div className="space-y-3">
      <h3 className="font-bold text-navy-900">{title}</h3>
      {nodes.map((node) => (
        <div key={node.id} className={`rounded-2xl border p-3 ${nodeTones[node.tipo] ?? 'border-navy-200 bg-white'}`}>
          <div className="flex items-start gap-3">
            <GitBranch className="mt-1 h-4 w-4 text-cyan-700" />
            <div className="min-w-0">
              <p className="truncate font-bold text-navy-950">{node.label}</p>
              <p className="text-xs text-navy-500">{node.tipo}{node.ramo ? ` / ${node.ramo}` : ''}</p>
              {node.nivel && <Badge variant={node.nivel} className="mt-2">{node.nivel} {node.score ?? ''}</Badge>}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
