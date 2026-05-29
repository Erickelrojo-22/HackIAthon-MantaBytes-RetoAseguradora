import type { FormEvent } from 'react';
import { useState } from 'react';
import { ImagePlus, Loader2 } from 'lucide-react';
import { api, type VisionResult } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

export function Vision() {
  const [file, setFile] = useState<File | null>(null);
  const [claimId, setClaimId] = useState('');
  const [preview, setPreview] = useState('');
  const [result, setResult] = useState<VisionResult | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const selectFile = (nextFile: File | null) => {
    setFile(nextFile);
    setResult(null);
    setError('');
    if (preview) URL.revokeObjectURL(preview);
    setPreview(nextFile ? URL.createObjectURL(nextFile) : '');
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await api.post<VisionResult>('/vision/analyze', formData, {
        params: claimId.trim() ? { id_siniestro: claimId.trim() } : undefined,
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(response.data);
    } catch {
      setError('No fue posible analizar la imagen. Verifica formato y conexion con FastAPI.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-navy-950 p-8 text-white shadow-2xl">
        <Badge variant="info" className="mb-4 border-cyan-300/20 bg-cyan-300/10 text-cyan-100">OpenAI Vision opcional</Badge>
        <h1 className="text-3xl font-black">Analisis visual auxiliar</h1>
        <p className="mt-3 max-w-3xl text-navy-200">
          Revisa fotos de siniestros como apoyo a la priorizacion. El resultado no modifica scores ni reemplaza peritaje humano.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Imagen del siniestro</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4">
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-cyan-200 bg-cyan-50/60 p-8 text-center transition hover:bg-cyan-50">
                <ImagePlus className="mb-3 h-10 w-10 text-cyan-700" />
                <span className="font-bold text-navy-900">{file ? file.name : 'Selecciona JPG, PNG o WEBP'}</span>
                <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(event) => selectFile(event.target.files?.[0] ?? null)} />
              </label>
              {preview && <img src={preview} alt="Vista previa" className="max-h-80 w-full rounded-2xl object-contain ring-1 ring-navy-100" />}
              <label className="block text-sm font-semibold text-navy-700">
                ID de siniestro opcional
                <input value={claimId} onChange={(event) => setClaimId(event.target.value)} placeholder="SIN00001" className="mt-1 w-full rounded-xl border border-navy-200 px-3 py-2" />
              </label>
              {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</div>}
              <Button type="submit" disabled={!file || loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImagePlus className="h-4 w-4" />}
                Analizar imagen
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Hallazgos visuales</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {!result && <p className="text-sm text-navy-500">Sube una imagen para ver hallazgos auxiliares.</p>}
            {result && (
              <>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <Info label="Estado" value={result.status} />
                  <Info label="Severidad" value={result.severidad_visual} />
                  <Info label="Confianza" value={`${Math.round((result.confianza ?? 0) * 100)}%`} />
                </div>
                <Section title="Observaciones" rows={result.observaciones} />
                <Section title="Anomalias potenciales" rows={result.anomalias_potenciales} />
                <div className="rounded-xl bg-cyan-50 p-4 text-sm text-cyan-900">
                  <strong>Accion sugerida:</strong> {result.accion_sugerida}
                </div>
                <div className="rounded-xl bg-yellow-50 p-4 text-sm text-yellow-900">{result.disclaimer}</div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><p className="text-sm text-navy-500">{label}</p><p className="font-bold text-navy-950">{value}</p></div>;
}

function Section({ title, rows }: { title: string; rows: string[] }) {
  return (
    <div>
      <h3 className="mb-2 font-bold text-navy-900">{title}</h3>
      {rows.length === 0 ? <p className="text-sm text-navy-500">Sin hallazgos reportados.</p> : (
        <ul className="space-y-2 text-sm text-navy-700">
          {rows.map((row, index) => <li key={index} className="rounded-xl bg-navy-50 p-3">{row}</li>)}
        </ul>
      )}
    </div>
  );
}
