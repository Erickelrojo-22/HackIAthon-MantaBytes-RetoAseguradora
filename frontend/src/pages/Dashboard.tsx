import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, DollarSign, Loader2, ShieldCheck, TrendingUp } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, money, percent, type ClaimRisk, type DashboardKpis } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

const riskColors: Record<string, string> = { Rojo: '#ef4444', Amarillo: '#eab308', Verde: '#22c55e' };

interface DashboardResponse {
  kpis: DashboardKpis;
  proveedores_criticos: Array<{ proveedor: string; alertas_rojas: number; score_promedio: number; monto_priorizado: number }>;
  ciudades_criticas: Array<{ ciudad: string; casos_revision: number; porcentaje_revision: number; score_promedio: number }>;
  matriz_riesgo: Array<{ ramo: string; nivel_riesgo: string; total: number; monto_reclamado: number }>;
}

export function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-kpis'],
    queryFn: async () => (await api.get<DashboardResponse>('/dashboard/kpis')).data,
  });
  const { data: topCases = [] } = useQuery({
    queryKey: ['top-cases'],
    queryFn: async () => (await api.get<ClaimRisk[]>('/claims/risk?limit=10')).data,
  });

  if (isLoading) return <LoadingState />;
  if (!data) return <EmptyState text="No hay datos disponibles." />;

  const kpis = data.kpis;
  const pieData = [
    { name: 'Rojo', value: kpis.casos_rojos },
    { name: 'Amarillo', value: kpis.casos_amarillos },
    { name: 'Verde', value: Math.max(kpis.total_siniestros - kpis.casos_rojos - kpis.casos_amarillos, 0) },
  ];

  return (
    <div className="space-y-7">
      <div className="rounded-3xl bg-navy-950 p-8 text-white shadow-2xl">
        <div className="max-w-3xl">
          <Badge variant="info" className="mb-4 border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Centro de mando</Badge>
          <h1 className="text-3xl font-black tracking-tight">Priorizacion ejecutiva de siniestros</h1>
          <p className="mt-3 text-navy-200">
            Vista consolidada para revisar exposicion, concentracion operativa y casos que requieren atencion humana.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Total siniestros" value={kpis.total_siniestros.toLocaleString()} icon={<ShieldCheck />} />
        <MetricCard title="Casos rojos" value={kpis.casos_rojos.toLocaleString()} icon={<AlertTriangle />} tone="red" />
        <MetricCard title="Monto expuesto" value={money(kpis.monto_expuesto)} icon={<DollarSign />} tone="yellow" />
        <MetricCard title="Ahorro potencial" value={money(kpis.ahorro_potencial_simulado)} icon={<TrendingUp />} tone="green" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Distribucion por nivel</CardTitle></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={68} outerRadius={98} paddingAngle={5}>
                  {pieData.map((entry) => <Cell key={entry.name} fill={riskColors[entry.name]} />)}
                </Pie>
                <Tooltip formatter={(value) => Number(value).toLocaleString()} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Proveedores criticos</CardTitle></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.proveedores_criticos} layout="vertical" margin={{ left: 28 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis dataKey="proveedor" type="category" width={130} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="alertas_rojas" fill="#ef4444" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader><CardTitle>Top 10 casos para revision</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-navy-500">
                <tr><th className="py-2">Caso</th><th>Nivel</th><th>Score</th><th>Ramo</th><th>Monto</th><th>Proveedor</th></tr>
              </thead>
              <tbody className="divide-y divide-navy-100">
                {topCases.map((claim) => (
                  <tr key={claim.id_siniestro} className="text-navy-700">
                    <td className="py-3 font-semibold text-navy-950">{claim.id_siniestro}</td>
                    <td><Badge variant={claim.nivel_riesgo}>{claim.nivel_riesgo}</Badge></td>
                    <td>{claim.score_final}</td>
                    <td>{claim.ramo}</td>
                    <td>{money(claim.monto_reclamado)}</td>
                    <td>{claim.proveedor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Ciudades con concentracion</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {data.ciudades_criticas.map((city) => (
              <div key={city.ciudad}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="font-semibold text-navy-800">{city.ciudad}</span>
                  <span className="text-navy-500">{percent(city.porcentaje_revision)}</span>
                </div>
                <div className="h-2 rounded-full bg-navy-100">
                  <div className="h-2 rounded-full bg-cyan-600" style={{ width: `${Math.min(city.porcentaje_revision, 100)}%` }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon, tone = 'cyan' }: { title: string; value: string; icon: React.ReactNode; tone?: 'cyan' | 'red' | 'yellow' | 'green' }) {
  const tones = {
    cyan: 'bg-cyan-50 text-cyan-700',
    red: 'bg-red-50 text-red-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    green: 'bg-green-50 text-green-600',
  };
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className={`grid h-12 w-12 place-items-center rounded-2xl ${tones[tone]}`}>{icon}</div>
        <div>
          <p className="text-sm font-medium text-navy-500">{title}</p>
          <p className="text-2xl font-black text-navy-950">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function LoadingState() {
  return <div className="grid h-72 place-items-center"><Loader2 className="h-9 w-9 animate-spin text-cyan-700" /></div>;
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-2xl border border-navy-200 bg-white p-8 text-center text-navy-500">{text}</div>;
}
