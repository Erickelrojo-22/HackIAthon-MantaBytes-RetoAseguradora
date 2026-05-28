import type { FormEvent } from 'react';
import { useState } from 'react';
import { AlertTriangle, BotMessageSquare, Loader2 } from 'lucide-react';
import { api, money } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

const defaultCase = {
  ramo: 'Vehiculos',
  cobertura: 'Perdida Total por Robo',
  monto_reclamado: 29500,
  suma_asegurada: 30000,
  dias_desde_inicio_poliza: 1,
  dias_desde_fin_poliza: 364,
  dias_entre_ocurrencia_reporte: 5,
  denuncia_horas: 120,
  documentos_completos: false,
  documentos_inconsistentes: true,
  tercero_identificado: false,
};

interface CandidateAlert {
  codigo: string;
  descripcion: string;
  puntos: number;
}

interface CandidateScore {
  score_final: number;
  nivel_riesgo: 'Verde' | 'Amarillo' | 'Rojo';
  explicacion_resumen: string;
  alertas: CandidateAlert[];
}

export function JuryTest() {
  const [formData, setFormData] = useState(defaultCase);
  const [result, setResult] = useState<CandidateScore | null>(null);
  const [aiAnswer, setAiAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await api.post<CandidateScore>('/score-candidate', formData);
      setResult(response.data);
      setAiAnswer('');
    } finally {
      setLoading(false);
    }
  };

  const explain = async () => {
    if (!result) return;
    const response = await api.post('/agent/question', {
      question: `Explica este caso temporal para el jurado. Score ${result.score_final}, nivel ${result.nivel_riesgo}.`,
      scope: 'jury-test',
    });
    setAiAnswer(response.data.answer);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-black text-navy-950">Prueba del jurado</h1>
        <p className="mt-1 text-sm text-navy-500">Caso critico prellenado para demostrar score temporal, explicabilidad y etica.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Caso temporal</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <Field label="Ramo" value={formData.ramo} onChange={(value) => setFormData({ ...formData, ramo: value })} />
                <Field label="Cobertura" value={formData.cobertura} onChange={(value) => setFormData({ ...formData, cobertura: value })} />
                <NumberField label="Monto reclamado" value={formData.monto_reclamado} onChange={(value) => setFormData({ ...formData, monto_reclamado: value })} />
                <NumberField label="Suma asegurada" value={formData.suma_asegurada} onChange={(value) => setFormData({ ...formData, suma_asegurada: value })} />
                <NumberField label="Dias desde inicio" value={formData.dias_desde_inicio_poliza} onChange={(value) => setFormData({ ...formData, dias_desde_inicio_poliza: value })} />
                <NumberField label="Horas hasta denuncia" value={formData.denuncia_horas} onChange={(value) => setFormData({ ...formData, denuncia_horas: value })} />
              </div>
              <div className="rounded-2xl border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-900">
                <AlertTriangle className="mr-2 inline h-4 w-4" />
                Este caso no se guarda en la base historica. Sirve solo para explicar priorizacion humana.
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Ejecutar score temporal'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="bg-navy-950 text-white">
          <CardHeader className="border-white/10 bg-white/5"><CardTitle className="text-white">Resultado</CardTitle></CardHeader>
          <CardContent className="space-y-5">
            {!result && <p className="text-navy-300">Ejecuta el score para ver el resultado temporal.</p>}
            {result && (
              <>
                <div className="text-center">
                  <p className="text-sm text-navy-300">Score final</p>
                  <p className="text-6xl font-black text-cyan-300">{result.score_final}</p>
                  <Badge variant={result.nivel_riesgo} className="mt-3">{result.nivel_riesgo}</Badge>
                </div>
                <p className="text-sm text-navy-200">{result.explicacion_resumen}</p>
                <div className="space-y-2">
                  {result.alertas?.map((alert) => (
                    <div key={alert.codigo + alert.descripcion} className="rounded-xl bg-white/5 p-3 text-sm">
                      <strong>{alert.codigo}:</strong> {alert.descripcion} ({alert.puntos} pts)
                    </div>
                  ))}
                </div>
                <Button variant="secondary" onClick={explain}>
                  <BotMessageSquare className="h-4 w-4" />
                  Explicar con IA
                </Button>
                {aiAnswer && <div className="whitespace-pre-wrap rounded-2xl bg-white/10 p-4 text-sm text-navy-100">{aiAnswer}</div>}
                <p className="text-xs text-navy-300">No constituye acusacion ni decision automatica. Monto: {money(formData.monto_reclamado)}.</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="text-sm font-semibold text-navy-700">{label}<input value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-xl border border-navy-200 px-3 py-2" /></label>;
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <label className="text-sm font-semibold text-navy-700">{label}<input type="number" value={value} onChange={(event) => onChange(Number(event.target.value))} className="mt-1 w-full rounded-xl border border-navy-200 px-3 py-2" /></label>;
}
