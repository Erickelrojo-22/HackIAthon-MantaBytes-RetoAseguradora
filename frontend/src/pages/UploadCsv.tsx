import type { FormEvent } from 'react';
import { useState } from 'react';
import { FileUp, Loader2 } from 'lucide-react';
import { api, type CsvUploadResult } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

export function UploadCsv() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<CsvUploadResult | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await api.post<CsvUploadResult>('/claims/upload-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(response.data);
    } catch {
      setError('No se pudo validar el CSV. Revisa formato, columnas y que el backend este activo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-navy-950 p-8 text-white shadow-2xl">
        <Badge variant="info" className="mb-4 border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Validacion de datos</Badge>
        <h1 className="text-3xl font-black">Carga CSV controlada</h1>
        <p className="mt-3 max-w-3xl text-navy-200">
          Valida estructura de archivos sinteticos sin reemplazar tablas persistidas. Cada carga queda auditada.
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle>Subir archivo</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-cyan-200 bg-cyan-50/60 p-8 text-center transition hover:bg-cyan-50">
              <FileUp className="mb-3 h-10 w-10 text-cyan-700" />
              <span className="font-bold text-navy-900">{file ? file.name : 'Selecciona un CSV sintetico'}</span>
              <span className="mt-1 text-sm text-navy-500">Ejemplo: siniestros.csv, documentos.csv, polizas.csv</span>
              <input type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </label>
            {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</div>}
            <Button type="submit" disabled={!file || loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
              Validar CSV
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader><CardTitle>Reporte de calidad</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              <Info label="Archivo" value={result.filename} />
              <Info label="Tabla detectada" value={result.table_detected ?? 'No reconocida'} />
              <Info label="Filas" value={String(result.rows)} />
              <div>
                <p className="text-sm text-navy-500">Estado</p>
                <Badge variant={result.status === 'ok' ? 'success' : result.status === 'no_reconocido' ? 'Amarillo' : 'danger'}>
                  {result.status}
                </Badge>
              </div>
            </div>
            <p className={result.status === 'no_reconocido' ? 'text-sm font-semibold text-yellow-700' : 'text-sm text-navy-600'}>{result.message}</p>
            {result.missing_columns.length > 0 && (
              <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
                <strong>Columnas faltantes:</strong> {result.missing_columns.join(', ')}
              </div>
            )}
            <div className="rounded-xl bg-navy-50 p-4 text-xs text-navy-500">
              Columnas leidas: {result.columns.join(', ')}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><p className="text-sm text-navy-500">{label}</p><p className="font-bold text-navy-950">{value}</p></div>;
}
