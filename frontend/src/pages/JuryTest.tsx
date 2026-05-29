import type { ClipboardEvent, FormEvent, KeyboardEvent } from 'react';
import { useMemo, useState } from 'react';
import { AlertTriangle, BotMessageSquare, Loader2 } from 'lucide-react';
import { api, money } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { MarkdownMessage } from '../components/ui/MarkdownMessage';

const candidateCoverages = {
  Vehiculos: ['Perdida Total por Robo', 'Robo', 'Robo de Accesorios', 'Choque', 'Cristales', 'Responsabilidad Civil'],
  Salud: ['Consulta Especializada', 'Emergencia', 'Hospitalizacion', 'Procedimiento Ambulatorio'],
  Hogar: ['Danio Agua', 'Incendio', 'Robo', 'Cristales', 'Responsabilidad Civil'],
} as const;

type Branch = keyof typeof candidateCoverages;
type RiskLevel = 'Verde' | 'Amarillo' | 'Rojo';

interface CandidateForm {
  ramo: Branch;
  cobertura: string;
  monto_reclamado: number;
  suma_asegurada: number;
  dias_desde_inicio_poliza: number;
  dias_desde_fin_poliza: number;
  dias_entre_ocurrencia_reporte: number;
  denuncia_horas: number;
  documentos_completos: boolean;
  documentos_inconsistentes: boolean;
  tercero_identificado: boolean;
  proveedor_lista_restrictiva: boolean;
  adulteracion_documental: boolean;
  dinamica_imposible: boolean;
  factura_duplicada: boolean;
  narrativa_clonada: boolean;
}

type NumericFieldName =
  | 'monto_reclamado'
  | 'suma_asegurada'
  | 'dias_desde_inicio_poliza'
  | 'dias_desde_fin_poliza'
  | 'dias_entre_ocurrencia_reporte'
  | 'denuncia_horas';

type FieldErrors = Partial<Record<keyof CandidateForm | 'vigencia', string>>;

const branchOptions = Object.keys(candidateCoverages) as Branch[];
const displayLabels: Record<string, string> = {
  Vehiculos: 'Vehículos',
  'Perdida Total por Robo': 'Pérdida total por robo',
  'Robo de Accesorios': 'Robo de accesorios',
  'Responsabilidad Civil': 'Responsabilidad civil',
  Hospitalizacion: 'Hospitalización',
  'Procedimiento Ambulatorio': 'Procedimiento ambulatorio',
  'Danio Agua': 'Daño por agua',
};
const displayLabel = (value: string) => displayLabels[value] ?? value;

const defaultCase: CandidateForm = {
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
  proveedor_lista_restrictiva: false,
  adulteracion_documental: false,
  dinamica_imposible: false,
  factura_duplicada: false,
  narrativa_clonada: false,
};

interface CandidateAlert {
  codigo: string;
  descripcion: string;
  puntos: number;
}

interface CandidateScore {
  score_final: number;
  nivel_riesgo: RiskLevel;
  explicacion_resumen: string;
  alertas: CandidateAlert[];
}

export function JuryTest() {
  const [formData, setFormData] = useState<CandidateForm>(defaultCase);
  const [result, setResult] = useState<CandidateScore | null>(null);
  const [aiAnswer, setAiAnswer] = useState('');
  const [apiError, setApiError] = useState('');
  const [aiError, setAiError] = useState('');
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);

  const validationErrors = useMemo(() => validateCandidate(formData), [formData]);
  const hasErrors = Object.keys(validationErrors).length > 0;
  const coverageOptions = candidateCoverages[formData.ramo];

  const updateForm = (patch: Partial<CandidateForm>) => {
    setFormData((current) => ({ ...current, ...patch }));
    setResult(null);
    setAiAnswer('');
    setApiError('');
    setAiError('');
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (hasErrors) return;
    setLoading(true);
    setApiError('');
    try {
      const response = await api.post<CandidateScore>('/score-candidate', formData);
      setResult(response.data);
      setAiAnswer('');
    } catch {
      setResult(null);
      setApiError('No se pudo calcular el score. Revisa los campos e intenta nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  const explain = async () => {
    if (!result || hasErrors) return;
    setAiLoading(true);
    setAiError('');
    try {
      const response = await api.post('/agent/question', {
        question: [
          'Explica este caso temporal para el jurado sin acusar fraude ni tomar decision automatica.',
          `Score ${result.score_final}, nivel ${result.nivel_riesgo}.`,
          `Ramo ${displayLabel(formData.ramo)}, cobertura ${displayLabel(formData.cobertura)}.`,
          `Monto reclamado ${formData.monto_reclamado}, suma asegurada ${formData.suma_asegurada}.`,
          `Dias desde inicio ${formData.dias_desde_inicio_poliza}, dias hasta fin ${formData.dias_desde_fin_poliza}, dias hasta reporte ${formData.dias_entre_ocurrencia_reporte}, horas hasta denuncia ${formData.denuncia_horas}.`,
          `Alertas: ${result.alertas.map((alert) => `${alert.codigo} ${alert.descripcion}`).join('; ') || 'sin alertas materiales'}.`,
        ].join('\n'),
        scope: 'jury-test',
      });
      setAiAnswer(response.data.answer);
    } catch {
      setAiError('No pude conectar con el agente. Verifica que FastAPI este activo.');
    } finally {
      setAiLoading(false);
    }
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
                <SelectField
                  label="Ramo"
                  value={formData.ramo}
                  options={branchOptions}
                  onChange={(value) => {
                    const ramo = value as Branch;
                    updateForm({ ramo, cobertura: candidateCoverages[ramo][0] });
                  }}
                  formatOption={displayLabel}
                  error={validationErrors.ramo}
                />
                <SelectField
                  label="Cobertura"
                  value={formData.cobertura}
                  options={[...coverageOptions]}
                  onChange={(value) => updateForm({ cobertura: value })}
                  formatOption={displayLabel}
                  error={validationErrors.cobertura}
                />
                <NumberField
                  label="Monto reclamado"
                  value={formData.monto_reclamado}
                  min={100}
                  max={100000}
                  error={validationErrors.monto_reclamado}
                  onChange={(value) => updateForm({ monto_reclamado: value })}
                />
                <NumberField
                  label="Suma asegurada"
                  value={formData.suma_asegurada}
                  min={500}
                  max={200000}
                  error={validationErrors.suma_asegurada}
                  onChange={(value) => updateForm({ suma_asegurada: value })}
                />
                <NumberField
                  label="Dias desde inicio"
                  value={formData.dias_desde_inicio_poliza}
                  min={0}
                  max={365}
                  error={validationErrors.dias_desde_inicio_poliza || validationErrors.vigencia}
                  onChange={(value) => updateForm({ dias_desde_inicio_poliza: value })}
                />
                <NumberField
                  label="Dias hasta fin"
                  value={formData.dias_desde_fin_poliza}
                  min={0}
                  max={365}
                  error={validationErrors.dias_desde_fin_poliza || validationErrors.vigencia}
                  onChange={(value) => updateForm({ dias_desde_fin_poliza: value })}
                />
                <NumberField
                  label="Dias hasta reporte"
                  value={formData.dias_entre_ocurrencia_reporte}
                  min={0}
                  max={365}
                  error={validationErrors.dias_entre_ocurrencia_reporte}
                  onChange={(value) => updateForm({ dias_entre_ocurrencia_reporte: value })}
                />
                <NumberField
                  label="Horas hasta denuncia"
                  value={formData.denuncia_horas}
                  min={0}
                  max={720}
                  error={validationErrors.denuncia_horas}
                  onChange={(value) => updateForm({ denuncia_horas: value })}
                />
              </div>

              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <ToggleField label="Documentos completos" checked={formData.documentos_completos} onChange={(value) => updateForm({ documentos_completos: value })} />
                <ToggleField label="Documentos inconsistentes" checked={formData.documentos_inconsistentes} onChange={(value) => updateForm({ documentos_inconsistentes: value })} />
                <ToggleField label="Tercero identificado" checked={formData.tercero_identificado} onChange={(value) => updateForm({ tercero_identificado: value })} />
                <ToggleField label="Proveedor restrictivo" checked={formData.proveedor_lista_restrictiva} onChange={(value) => updateForm({ proveedor_lista_restrictiva: value })} />
                <ToggleField label="Adulteracion documental" checked={formData.adulteracion_documental} onChange={(value) => updateForm({ adulteracion_documental: value })} />
                <ToggleField label="Dinamica imposible" checked={formData.dinamica_imposible} onChange={(value) => updateForm({ dinamica_imposible: value })} />
                <ToggleField label="Factura duplicada" checked={formData.factura_duplicada} onChange={(value) => updateForm({ factura_duplicada: value })} />
                <ToggleField label="Narrativa clonada" checked={formData.narrativa_clonada} onChange={(value) => updateForm({ narrativa_clonada: value })} />
              </div>

              {hasErrors && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">
                  <AlertTriangle className="mr-2 inline h-4 w-4" />
                  Corrige los campos marcados para ejecutar el score.
                </div>
              )}
              {apiError && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{apiError}</div>}

              <div className="rounded-2xl border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-900">
                <AlertTriangle className="mr-2 inline h-4 w-4" />
                Este caso no se guarda en la base historica. Sirve solo para explicar priorizacion humana.
              </div>
              <Button type="submit" className="w-full" disabled={loading || hasErrors}>
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
                <Button variant="secondary" onClick={explain} disabled={aiLoading || hasErrors || !result}>
                  {aiLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <BotMessageSquare className="h-4 w-4" />}
                  Explicar con IA
                </Button>
                {aiError && <div className="rounded-2xl bg-red-950/50 p-4 text-sm text-red-100">{aiError}</div>}
                {aiAnswer && (
                  <div className="rounded-2xl bg-white/10 p-4 text-sm text-navy-100">
                    <MarkdownMessage content={aiAnswer} />
                  </div>
                )}
                <p className="text-xs text-navy-300">No constituye acusacion ni decision automatica. Monto: {money(formData.monto_reclamado)}.</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function validateCandidate(data: CandidateForm): FieldErrors {
  const errors: FieldErrors = {};
  validateNumber(errors, data, 'monto_reclamado', 'Monto reclamado', 100, 100000);
  validateNumber(errors, data, 'suma_asegurada', 'Suma asegurada', 500, 200000);
  validateNumber(errors, data, 'dias_desde_inicio_poliza', 'Dias desde inicio', 0, 365);
  validateNumber(errors, data, 'dias_desde_fin_poliza', 'Dias hasta fin', 0, 365);
  validateNumber(errors, data, 'dias_entre_ocurrencia_reporte', 'Dias hasta reporte', 0, 365);
  validateNumber(errors, data, 'denuncia_horas', 'Horas hasta denuncia', 0, 720);

  const allowedCoverages = candidateCoverages[data.ramo] as readonly string[] | undefined;
  if (!allowedCoverages) {
    errors.ramo = 'Selecciona un ramo valido.';
  } else if (!allowedCoverages.includes(data.cobertura)) {
    errors.cobertura = `Selecciona una cobertura valida para ${data.ramo}.`;
  }
  if (Number.isFinite(data.monto_reclamado) && Number.isFinite(data.suma_asegurada) && data.monto_reclamado > data.suma_asegurada) {
    errors.monto_reclamado = 'No debe superar la suma asegurada.';
  }
  if (
    Number.isFinite(data.dias_desde_inicio_poliza)
    && Number.isFinite(data.dias_desde_fin_poliza)
    && data.dias_desde_inicio_poliza + data.dias_desde_fin_poliza > 366
  ) {
    errors.vigencia = 'La vigencia simulada no debe superar 366 dias.';
  }
  return errors;
}

function validateNumber(
  errors: FieldErrors,
  data: CandidateForm,
  field: NumericFieldName,
  label: string,
  min: number,
  max: number,
) {
  const value = data[field];
  if (!Number.isFinite(value)) {
    errors[field] = `${label} es requerido.`;
  } else if (value < min || value > max) {
    errors[field] = `${label} debe estar entre ${min} y ${max}.`;
  }
}

function SelectField({
  label,
  value,
  options,
  onChange,
  error,
  formatOption,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
  error?: string;
  formatOption?: (value: string) => string;
}) {
  return (
    <label className="text-sm font-semibold text-navy-700">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`mt-1 w-full rounded-xl border bg-white px-3 py-2 ${error ? 'border-red-300 ring-2 ring-red-100' : 'border-navy-200'}`}
      >
        {options.map((option) => <option key={option} value={option}>{formatOption ? formatOption(option) : option}</option>)}
      </select>
      {error && <span className="mt-1 block text-xs font-semibold text-red-600">{error}</span>}
    </label>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  onChange,
  error,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
  error?: string;
}) {
  const [entryError, setEntryError] = useState('');
  const shownError = entryError || error;
  const maxLength = String(max).length;

  const rejectInput = () => {
    setEntryError('Solo números. Ingresa el dato correctamente.');
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    const allowedKeys = ['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight', 'Home', 'End'];
    const isShortcut = event.ctrlKey || event.metaKey;
    if (allowedKeys.includes(event.key) || isShortcut) return;
    if (!/^\d$/.test(event.key)) {
      event.preventDefault();
      rejectInput();
      return;
    }
    setEntryError('');
  };

  const handlePaste = (event: ClipboardEvent<HTMLInputElement>) => {
    const pasted = event.clipboardData.getData('text');
    if (!/^\d+$/.test(pasted)) {
      event.preventDefault();
      rejectInput();
      return;
    }
    setEntryError('');
  };

  const handleChange = (raw: string) => {
    if (raw === '') {
      setEntryError('');
      onChange(Number.NaN);
      return;
    }
    if (!/^\d+$/.test(raw)) {
      rejectInput();
      const sanitized = raw.replace(/\D/g, '');
      onChange(sanitized ? Number(sanitized) : Number.NaN);
      return;
    }
    setEntryError('');
    onChange(Number(raw));
  };

  return (
    <label className="text-sm font-semibold text-navy-700">
      {label}
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        value={Number.isFinite(value) ? value : ''}
        minLength={String(min).length}
        maxLength={maxLength}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onChange={(event) => handleChange(event.target.value)}
        className={`mt-1 w-full rounded-xl border px-3 py-2 ${shownError ? 'border-red-300 ring-2 ring-red-100' : 'border-navy-200'}`}
      />
      {shownError && <span className="mt-1 block text-xs font-semibold text-red-600">{shownError}</span>}
    </label>
  );
}

function ToggleField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex min-h-11 items-center gap-3 rounded-xl border border-navy-200 bg-white px-3 py-2 text-sm font-semibold text-navy-700">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-navy-300 text-cyan-600 focus:ring-cyan-400"
      />
      <span>{label}</span>
    </label>
  );
}
