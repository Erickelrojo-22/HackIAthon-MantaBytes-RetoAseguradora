import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Loader2 } from 'lucide-react';
import { api, money, type ExecutiveReport, type ClaimRisk } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

export function ExecutiveReportPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['executive-report'],
    queryFn: async () => (await api.get<ExecutiveReport>('/report/summary')).data,
  });

  const html = useMemo(() => (data ? buildReportHtml(data) : ''), [data]);

  const download = () => {
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'reporte-ejecutivo-fraudia.html';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-3xl bg-navy-950 p-8 text-white shadow-2xl">
        <div>
          <Badge variant="info" className="mb-4 border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Entregable ejecutivo</Badge>
          <h1 className="text-3xl font-black">Reporte ejecutivo</h1>
          <p className="mt-3 max-w-3xl text-navy-200">
            Resumen para gerencia y auditoria con casos prioritarios, proveedores concentrados, exposicion y ahorro simulado.
          </p>
        </div>
        <Button variant="secondary" onClick={download} disabled={!data}>
          <Download className="h-4 w-4" />
          Descargar HTML
        </Button>
      </div>

      {isLoading ? (
        <div className="grid h-72 place-items-center"><Loader2 className="h-9 w-9 animate-spin text-cyan-700" /></div>
      ) : error || !data ? (
        <Card><CardContent className="text-red-600">No fue posible generar el reporte.</CardContent></Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
            <Metric title="Siniestros" value={String(data.resumen.total_siniestros ?? 0)} />
            <Metric title="Casos rojos" value={String(data.resumen.rojos ?? 0)} tone="red" />
            <Metric title="Monto revision" value={money(data.ahorro_potencial_simulado.base_revision_rojo_amarillo)} />
            <Metric title="Ahorro simulado" value={money(data.ahorro_potencial_simulado.monto_estimado)} tone="green" />
          </div>

          <Card>
            <CardHeader><CardTitle>Top 10 casos para revision</CardTitle></CardHeader>
            <CardContent className="overflow-x-auto p-0"><CasesTable rows={data.top_casos} /></CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <SimpleTable title="Proveedores que concentran alertas rojas" rows={data.proveedores_80_20} />
            <SimpleTable title="Metricas del modelo demo" rows={data.metricas_modelo} />
          </div>

          <Card>
            <CardContent className="text-sm text-navy-600">
              <strong>Disclaimer:</strong> reporte para priorizacion humana. No constituye acusacion, rechazo automatico ni decision de pago.
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function Metric({ title, value, tone = 'cyan' }: { title: string; value: string; tone?: 'cyan' | 'red' | 'green' }) {
  const tones = { cyan: 'text-cyan-700', red: 'text-red-600', green: 'text-green-600' };
  return (
    <Card><CardContent><p className="text-sm text-navy-500">{title}</p><p className={`mt-2 text-2xl font-black ${tones[tone]}`}>{value}</p></CardContent></Card>
  );
}

function CasesTable({ rows }: { rows: ClaimRisk[] }) {
  return (
    <table className="w-full text-left text-sm">
      <thead className="bg-navy-50 text-xs uppercase text-navy-500"><tr><th className="px-6 py-3">Caso</th><th>Nivel</th><th>Score</th><th>Ramo</th><th>Monto</th><th>Proveedor</th></tr></thead>
      <tbody className="divide-y divide-navy-100">
        {rows.map((row) => (
          <tr key={row.id_siniestro} className="bg-white">
            <td className="px-6 py-3 font-bold">{row.id_siniestro}</td>
            <td><Badge variant={row.nivel_riesgo}>{row.nivel_riesgo}</Badge></td>
            <td>{row.score_final}</td>
            <td>{row.ramo}</td>
            <td>{money(row.monto_reclamado)}</td>
            <td>{row.proveedor}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SimpleTable({ title, rows }: { title: string; rows: Array<Record<string, number | string | null>> }) {
  const columns = Object.keys(rows[0] ?? {}).slice(0, 6);
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="overflow-x-auto p-0">
        {rows.length === 0 ? <p className="p-6 text-sm text-navy-500">Sin datos disponibles.</p> : (
          <table className="w-full text-left text-sm">
            <thead className="bg-navy-50 text-xs uppercase text-navy-500"><tr>{columns.map((col) => <th key={col} className="px-4 py-3">{col}</th>)}</tr></thead>
            <tbody className="divide-y divide-navy-100">
              {rows.slice(0, 10).map((row, index) => (
                <tr key={index} className="bg-white">{columns.map((col) => <td key={col} className="px-4 py-3">{String(row[col] ?? '')}</td>)}</tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}

function buildReportHtml(report: ExecutiveReport) {
  const cases = report.top_casos.map((claim) => `<tr><td>${claim.id_siniestro}</td><td>${claim.nivel_riesgo}</td><td>${claim.score_final}</td><td>${claim.ramo}</td><td>${money(claim.monto_reclamado)}</td><td>${claim.proveedor}</td></tr>`).join('');
  return `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Reporte Ejecutivo FraudIA Claims</title><style>body{font-family:Arial,sans-serif;margin:32px;color:#172033}h1,h2{color:#08345f}.warning{background:#fff4d6;border-left:5px solid #d99a00;padding:12px}.metric{display:inline-block;margin:8px;padding:12px;background:#f3f7fb;border:1px solid #d9e6f2;border-radius:8px}table{border-collapse:collapse;width:100%;font-size:12px}th{background:#08345f;color:white;text-align:left}td,th{padding:7px;border-bottom:1px solid #e5e7eb}</style></head><body><h1>Reporte Ejecutivo FraudIA Claims</h1><div class="warning">FraudIA genera alertas para revision humana. No acusa fraude, no rechaza reclamos y no decide pagos.</div><h2>KPIs</h2><div class="metric">Siniestros: <strong>${report.resumen.total_siniestros ?? 0}</strong></div><div class="metric">Rojos: <strong>${report.resumen.rojos ?? 0}</strong></div><div class="metric">Ahorro simulado: <strong>${money(report.ahorro_potencial_simulado.monto_estimado)}</strong></div><h2>Top casos</h2><table><thead><tr><th>Caso</th><th>Nivel</th><th>Score</th><th>Ramo</th><th>Monto</th><th>Proveedor</th></tr></thead><tbody>${cases}</tbody></table><h2>Metodologia</h2><p>Score por reglas, anomalias, NLP y modelo demo. Datos sinteticos; resultado no decisorio.</p></body></html>`;
}
