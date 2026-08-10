import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, DollarSign, Loader2, ShieldCheck, TrendingUp } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, money, percent, type ClaimRisk, type DashboardResponse } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

const riskColors: Record<string, string> = { Rojo: '#ef4444', Amarillo: '#eab308', Verde: '#22c55e' };

export function Dashboard() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['dashboard-kpis'],
    queryFn: async () => (await api.get<DashboardResponse>('/dashboard/kpis')).data,
  });
  const { data: topCases = [], isLoading: casesLoading, isError: casesError } = useQuery({
    queryKey: ['top-cases'],
    queryFn: async () => (await api.get<ClaimRisk[]>('/claims/risk?limit=10')).data,
  });

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState onRetry={refetch} />;
  if (!data) return <EmptyState text="No hay datos disponibles." />;

  const kpis = data.kpis;
  const pieData = [
    { name: 'Rojo', value: kpis.casos_rojos },
    { name: 'Amarillo', value: kpis.casos_amarillos },
    { name: 'Verde', value: Math.max(kpis.total_siniestros - kpis.casos_rojos - kpis.casos_amarillos, 0) },
  ];
  const noSiniestros = kpis.total_siniestros === 0;

  const ramos = Array.from(new Set(data.matriz_riesgo.map((row) => row.ramo)));
  const matrizPorRamo = ramos.map((ramo) => {
    const rows = data.matriz_riesgo.filter((row) => row.ramo === ramo);
    const entry: Record<string, string | number> = { ramo };
    for (const nivel of ['Rojo', 'Amarillo', 'Verde']) {
      entry[nivel] = rows.find((row) => row.nivel_riesgo === nivel)?.total ?? 0;
    }
    return entry;
  });

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
        <MetricCard
          title="Ahorro potencial"
          value={money(kpis.ahorro_potencial_simulado)}
          icon={<TrendingUp />}
          tone="green"
          subtitle={`Simulado: 12% de ${money(kpis.monto_priorizado)} priorizado (Rojo+Amarillo)`}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Score promedio" value={kpis.score_promedio.toFixed(1)} icon={<ShieldCheck />} />
        <MetricCard title="Casos priorizados" value={kpis.casos_priorizados.toLocaleString()} icon={<AlertTriangle />} tone="yellow" />
        <MetricCard title="% priorizado" value={percent(kpis.porcentaje_priorizado)} icon={<TrendingUp />} tone="yellow" />
        <MetricCard title="% rojo" value={percent(kpis.porcentaje_rojo)} icon={<AlertTriangle />} tone="red" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Distribucion por nivel</CardTitle></CardHeader>
          <CardContent className="h-80">
            {noSiniestros ? (
              <EmptyState text="Sin siniestros cargados todavia." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={68} outerRadius={98} paddingAngle={5}>
                    {pieData.map((entry) => <Cell key={entry.name} fill={riskColors[entry.name]} />)}
                  </Pie>
                  <Tooltip formatter={(value) => Number(value).toLocaleString()} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Proveedores criticos</CardTitle></CardHeader>
          <CardContent className="h-80">
            {data.proveedores_criticos.length === 0 ? (
              <EmptyState text="Sin proveedores con alertas rojas concentradas." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.proveedores_criticos} layout="vertical" margin={{ left: 28 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" />
                  <YAxis dataKey="proveedor" type="category" width={130} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(value, name) => [value, name]}
                    labelFormatter={(_, payload) => {
                      const row = payload?.[0]?.payload as { proveedor: string; tipo: string; total_siniestros: number } | undefined;
                      return row ? `${row.proveedor} (${row.tipo}, ${row.total_siniestros} casos)` : '';
                    }}
                  />
                  <Bar dataKey="alertas_rojas" fill="#ef4444" radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Matriz de riesgo por ramo</CardTitle></CardHeader>
        <CardContent className="h-80">
          {matrizPorRamo.length === 0 ? (
            <EmptyState text="Sin datos de matriz de riesgo." />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={matrizPorRamo}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="ramo" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="Verde" stackId="riesgo" fill={riskColors.Verde} />
                <Bar dataKey="Amarillo" stackId="riesgo" fill={riskColors.Amarillo} />
                <Bar dataKey="Rojo" stackId="riesgo" fill={riskColors.Rojo} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader><CardTitle>Top 10 casos para revision</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            {casesError ? (
              <p className="p-4 text-sm text-red-600">No se pudieron cargar los casos.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-navy-500">
                  <tr><th className="py-2">Caso</th><th>Nivel</th><th>Score</th><th>Ramo</th><th>Monto</th><th>Proveedor</th></tr>
                </thead>
                <tbody className="divide-y divide-navy-100">
                  {casesLoading && (
                    <tr><td colSpan={6} className="py-6 text-center text-navy-400">Cargando...</td></tr>
                  )}
                  {!casesLoading && topCases.length === 0 && (
                    <tr><td colSpan={6} className="py-6 text-center text-navy-400">Sin casos para revisar.</td></tr>
                  )}
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
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Ciudades con concentracion</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {data.ciudades_criticas.length === 0 ? (
              <EmptyState text="Sin ciudades con concentracion relevante." />
            ) : (
              data.ciudades_criticas.map((city) => (
                <div key={city.ciudad} title={`${city.total_siniestros} siniestros, score promedio ${city.score_promedio}`}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="font-semibold text-navy-800">{city.ciudad}</span>
                    <span className="text-navy-500">{percent(city.porcentaje_revision)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-navy-100">
                    <div className="h-2 rounded-full bg-cyan-600" style={{ width: `${Math.min(city.porcentaje_revision, 100)}%` }} />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  icon,
  tone = 'cyan',
  subtitle,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  tone?: 'cyan' | 'red' | 'yellow' | 'green';
  subtitle?: string;
}) {
  const tones = {
    cyan: 'bg-cyan-50 text-cyan-700',
    red: 'bg-red-50 text-red-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    green: 'bg-green-50 text-green-600',
  };
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className={`grid h-12 w-12 shrink-0 place-items-center rounded-2xl ${tones[tone]}`}>{icon}</div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-navy-500">{title}</p>
          <p className="text-2xl font-black text-navy-950">{value}</p>
          {subtitle && <p className="mt-0.5 truncate text-xs text-navy-400" title={subtitle}>{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function LoadingState() {
  return <div className="grid h-72 place-items-center"><Loader2 className="h-9 w-9 animate-spin text-cyan-700" /></div>;
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center text-red-700">
      <p className="font-semibold">No se pudo cargar el centro de mando.</p>
      <button onClick={() => onRetry()} className="mt-3 rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100">
        Reintentar
      </button>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="grid h-full place-items-center rounded-2xl border border-navy-100 bg-navy-50/50 p-8 text-center text-sm text-navy-400">{text}</div>;
}
