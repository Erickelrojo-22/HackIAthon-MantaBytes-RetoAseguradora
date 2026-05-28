import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { Loader2, TrendingUp, AlertTriangle, ShieldCheck, DollarSign } from 'lucide-react';

const COLORS = ['#ef4444', '#eab308', '#22c55e'];

export function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-kpis'],
    queryFn: async () => {
      const res = await api.get('/dashboard/kpis');
      return res.data;
    }
  });

  if (isLoading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-cyan-600" /></div>;
  
  if (!data) return <div>No hay datos disponibles</div>;

  const kpis = data.kpis;
  const pieData = [
    { name: 'Rojo', value: kpis.casos_rojos },
    { name: 'Amarillo', value: kpis.casos_amarillos },
    { name: 'Verde', value: kpis.total_siniestros - kpis.casos_rojos - kpis.casos_amarillos },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
         <h1 className="text-2xl font-bold text-navy-900">Centro de Mando</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Total Siniestros" value={kpis.total_siniestros} icon={<ShieldCheck className="w-8 h-8 text-cyan-600" />} />
        <MetricCard title="Casos Críticos" value={kpis.casos_rojos} icon={<AlertTriangle className="w-8 h-8 text-red-500" />} />
        <MetricCard title="Monto Expuesto" value={`$${kpis.monto_expuesto.toLocaleString()}`} icon={<DollarSign className="w-8 h-8 text-yellow-500" />} />
        <MetricCard title="Ahorro Potencial" value={`$${kpis.ahorro_potencial.toLocaleString()}`} icon={<TrendingUp className="w-8 h-8 text-green-500" />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>Distribución de Riesgo</CardTitle></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {pieData.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Proveedores Críticos</CardTitle></CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.proveedores_criticos} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <XAxis type="number" />
                <YAxis dataKey="proveedor" type="category" width={100} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="cantidad" fill="#ef4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon }: { title: string, value: string | number, icon: React.ReactNode }) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="flex items-center p-6">
        <div className="p-3 rounded-full bg-navy-50 mr-4">
          {icon}
        </div>
        <div>
          <p className="text-sm font-medium text-navy-500">{title}</p>
          <p className="text-2xl font-bold text-navy-900">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}
