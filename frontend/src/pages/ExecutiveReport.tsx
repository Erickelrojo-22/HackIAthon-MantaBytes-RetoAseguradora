import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Loader2 } from 'lucide-react';
import { isAxiosError } from 'axios';
import { api, money, type ExecutiveReport, type ClaimRisk } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

export function ExecutiveReportPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['executive-report'],
    queryFn: async () => (await api.get<ExecutiveReport>('/report/summary')).data,
  });
  const [downloadError, setDownloadError] = useState('');
  const [downloading, setDownloading] = useState(false);

  const download = async () => {
    setDownloadError('');
    setDownloading(true);
    try {
      // El backend genera el reporte completo (incluye matriz ramo/nivel,
      // ciudades observadas y documentos criticos, secciones que esta pagina
      // no muestra en pantalla). Antes esta funcion reimplementaba su propia
      // version reducida en el cliente; ahora se descarga la misma version
      // "rica" que ya existia en reports.py pero no estaba expuesta.
      const response = await api.get<string>('/report/html', { responseType: 'text' });
      const blob = new Blob([response.data], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'reporte-ejecutivo-fraudia.html';
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setDownloadError(
        isAxiosError(err) && err.response?.status === 403
          ? 'Tu rol no tiene permiso para descargar el reporte.'
          : 'No se pudo generar el archivo del reporte. Intenta nuevamente.',
      );
    } finally {
      setDownloading(false);
    }
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
        <div className="flex flex-col items-end gap-2">
          <Button variant="secondary" onClick={download} disabled={!data || downloading}>
            {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Descargar HTML
          </Button>
          {downloadError && <p className="max-w-xs text-right text-xs font-semibold text-red-300">{downloadError}</p>}
        </div>
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
            <div className="space-y-3">
              <SimpleTable title="Metricas del modelo demo" rows={data.metricas_modelo} />
              <p className="rounded-2xl border border-yellow-200 bg-yellow-50 p-3 text-xs text-yellow-900">
                <strong>Nota de interpretacion:</strong> la etiqueta es sintetica y comparte generador con otras variables
                del dataset (monto, demora de reporte, etc.). Valores de precision/recall/AUC cercanos a 1.0 confirman que
                el pipeline reproduce la etiqueta simulada, no que detecte fraude real.
              </p>
            </div>
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
