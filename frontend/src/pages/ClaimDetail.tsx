import type { FormEvent } from 'react';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { AlertTriangle, BotMessageSquare, FileText, Loader2, Send } from 'lucide-react';
import { api, dateTime, money, type ClaimDetail as ClaimDetailType, type ReviewDecision, type ReviewStatus } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { MarkdownMessage } from '../components/ui/MarkdownMessage';

const reviewStatuses: ReviewStatus[] = ['En revision', 'Descartado', 'Escalado', 'Confirmado para investigacion'];

function visibleSource(source?: string) {
  if (!source || source.startsWith('Herramientas locales') || source === 'Sesion local') return '';
  return source;
}

export function ClaimDetail() {
  const { id = '' } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ReviewStatus>('En revision');
  const [comment, setComment] = useState('');
  const [aiAnswer, setAiAnswer] = useState('');

  const { data: claim, isLoading } = useQuery({
    queryKey: ['claim', id],
    queryFn: async () => (await api.get<ClaimDetailType>(`/claims/${id}`)).data,
  });
  const { data: history = [] } = useQuery({
    queryKey: ['claim-history', id],
    queryFn: async () => (await api.get<ReviewDecision[]>(`/claims/${id}/review-history`)).data,
  });
  const { data: suggested } = useQuery({
    queryKey: ['suggested-questions', id],
    queryFn: async () => (await api.get<{ questions: string[] }>(`/agent/suggested-questions/${id}`)).data,
  });

  const reviewMutation = useMutation({
    mutationFn: async () => api.post(`/claims/${id}/review-decision`, { status, comentario: comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claim-history', id] });
      setComment('');
    },
  });

  const aiMutation = useMutation({
    mutationFn: async (question: string) => (await api.post('/agent/question', { question, id_siniestro: id, scope: 'claim' })).data,
    onSuccess: (data) => {
      const source = visibleSource(data.source);
      setAiAnswer(source ? `${data.answer}\n\nFuente: ${source}` : data.answer);
    },
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    reviewMutation.mutate();
  };

  if (isLoading) return <div className="grid h-72 place-items-center"><Loader2 className="h-9 w-9 animate-spin text-cyan-700" /></div>;
  if (!claim || 'error' in claim) return <div className="rounded-2xl border bg-white p-8 text-center">No encontrado.</div>;

  const city = claim.ciudad ?? claim.sucursal ?? 'N/A';

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-3xl bg-navy-950 p-7 text-white shadow-2xl md:flex-row md:items-center">
        <div>
          <Badge variant={claim.nivel_riesgo} className="mb-3">{claim.nivel_riesgo}</Badge>
          <h1 className="text-3xl font-black">Expediente {claim.id_siniestro}</h1>
          <p className="mt-2 text-navy-200">{claim.ramo} / {claim.cobertura} / {city}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-navy-300">Score final</p>
          <p className="text-5xl font-black text-cyan-300">{claim.score_final}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <Card>
            <CardHeader><CardTitle>Score dividido</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <ScorePart label="Reglas" value={claim.score_reglas} />
              <ScorePart label="Anomalias" value={claim.score_anomalia} />
              <ScorePart label="NLP" value={claim.score_nlp} />
              <ScorePart label="Modelo" value={claim.score_modelo} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Alertas con evidencia</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {claim.alertas.map((alert) => (
                <div key={`${alert.codigo}-${alert.evidencia}`} className="rounded-2xl border border-red-100 bg-red-50/60 p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
                    <div>
                      <p className="font-bold text-navy-950">{alert.codigo}: {alert.descripcion}</p>
                      <p className="mt-1 text-sm text-navy-600">{alert.evidencia}</p>
                      <p className="mt-2 text-xs font-semibold text-red-700">{alert.puntos} puntos / {alert.severidad}</p>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Documentos observados</CardTitle></CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-navy-500"><tr><th>Documento</th><th>Entregado</th><th>Legible</th><th>Inconsistencia</th><th>Adulteracion</th></tr></thead>
                <tbody className="divide-y divide-navy-100">
                  {claim.documentos.map((doc) => (
                    <tr key={doc.tipo_documento}>
                      <td className="py-3 font-semibold">{doc.tipo_documento}</td>
                      <td>{String(Boolean(doc.entregado))}</td>
                      <td>{String(Boolean(doc.legible))}</td>
                      <td>{String(Boolean(doc.inconsistencia_detectada))}</td>
                      <td>{String(Boolean(doc.adulteracion_confirmada))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Agente IA del expediente</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Button onClick={() => aiMutation.mutate(`Explica el siniestro ${id} para revision humana ejecutiva.`)} disabled={aiMutation.isPending}>
                {aiMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <BotMessageSquare className="h-4 w-4" />}
                Explicar este caso con IA
              </Button>
              {aiAnswer && <div className="rounded-2xl border border-cyan-100 bg-cyan-50 p-4 text-sm text-navy-800"><MarkdownMessage content={aiAnswer} /></div>}
              <div className="grid gap-2 md:grid-cols-2">
                {suggested?.questions?.map((question) => (
                  <button key={question} onClick={() => aiMutation.mutate(question)} className="rounded-xl border border-navy-200 bg-white p-3 text-left text-sm transition hover:bg-navy-50">
                    {question}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Resumen operativo</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm text-navy-700">
              <p><strong>Monto:</strong> {money(claim.monto_reclamado)}</p>
              <p><strong>Proveedor:</strong> {claim.proveedor_nombre ?? claim.proveedor}</p>
              <p><strong>Accion sugerida:</strong> {claim.accion_sugerida}</p>
              <p><strong>Similar:</strong> {claim.siniestro_similar || 'N/A'}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Timeline</CardTitle></CardHeader>
            <CardContent className="space-y-4 text-sm">
              <TimelineItem label="Ocurrencia" value={claim.fecha_ocurrencia ?? 'N/A'} />
              <TimelineItem label="Reporte" value={claim.fecha_reporte ?? 'N/A'} />
              <TimelineItem label="Scoring" value={`Score ${claim.score_final} / ${claim.nivel_riesgo}`} />
              {history.slice(0, 3).map((item) => <TimelineItem key={item.id_decision} label={item.status} value={dateTime(item.created_at)} />)}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Decision humana</CardTitle></CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <select value={status} onChange={(event) => setStatus(event.target.value as ReviewStatus)} className="w-full rounded-xl border border-navy-200 bg-white px-3 py-2 text-sm">
                  {reviewStatuses.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
                <textarea value={comment} onChange={(event) => setComment(event.target.value)} required rows={4} className="w-full rounded-xl border border-navy-200 px-3 py-2 text-sm" placeholder="Comentario del analista..." />
                <Button type="submit" className="w-full" disabled={reviewMutation.isPending}>
                  <Send className="h-4 w-4" />
                  Guardar decision
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Historial de revision</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {history.length === 0 && <p className="text-sm text-navy-500">Sin decisiones humanas registradas.</p>}
              {history.map((item) => (
                <div key={item.id_decision} className="border-l-2 border-cyan-500 pl-3 text-sm">
                  <p className="font-bold text-navy-950">{item.status}</p>
                  <p className="text-navy-600">{item.comentario}</p>
                  <p className="mt-1 text-xs text-navy-400">{dateTime(item.created_at)} / {item.reviewer_role}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function ScorePart({ label, value }: { label: string; value: number }) {
  return <div className="rounded-2xl bg-navy-50 p-4"><p className="text-xs font-semibold uppercase text-navy-500">{label}</p><p className="mt-2 text-3xl font-black text-navy-950">{value}</p></div>;
}

function TimelineItem({ label, value }: { label: string; value: string }) {
  return <div className="flex gap-3"><FileText className="h-5 w-5 text-cyan-700" /><div><p className="font-semibold text-navy-900">{label}</p><p className="text-navy-500">{value}</p></div></div>;
}
