import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Loader2, AlertTriangle } from 'lucide-react';

export function ClaimDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [decision, setDecision] = useState('En revision');
  const [comment, setComment] = useState('');
  
  const { data: claim, isLoading } = useQuery({
    queryKey: ['claim', id],
    queryFn: async () => {
      const res = await api.get(`/claims/${id}`);
      return res.data;
    }
  });

  const { data: history } = useQuery({
    queryKey: ['claim-history', id],
    queryFn: async () => {
      const res = await api.get(`/claims/${id}/review-history`);
      return res.data;
    }
  });

  const reviewMutation = useMutation({
    mutationFn: async (payload: { status: string, comentario: string }) => {
      await api.post(`/claims/${id}/review-decision`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claim-history', id] });
      setComment('');
    }
  });

  const handleDecision = (e: React.FormEvent) => {
    e.preventDefault();
    reviewMutation.mutate({ status: decision, comentario: comment });
  };

  if (isLoading) return <div className="flex justify-center p-12"><Loader2 className="w-8 h-8 animate-spin" /></div>;
  if (!claim) return <div>No encontrado</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">Expediente: {claim.id_siniestro}</h1>
          <p className="text-navy-500 mt-1">{claim.ramo} - {claim.cobertura}</p>
        </div>
        <Badge variant={claim.nivel_riesgo as any} className="text-sm px-3 py-1">{claim.nivel_riesgo} Riesgo</Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader><CardTitle>Detalles del Siniestro</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-navy-500">Monto:</span> <span className="font-semibold">${claim.monto_reclamado}</span></div>
                <div><span className="text-navy-500">Proveedor:</span> <span className="font-semibold">{claim.proveedor}</span></div>
                <div><span className="text-navy-500">Score Total:</span> <span className="font-semibold">{claim.score_final}/100</span></div>
                <div><span className="text-navy-500">Ciudad:</span> <span className="font-semibold">{claim.ciudad}</span></div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Alertas de IA</CardTitle></CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {claim.alertas?.map((alerta: string, i: number) => (
                  <li key={i} className="flex items-start bg-red-50 p-3 rounded-lg text-sm text-red-800">
                    <AlertTriangle className="w-5 h-5 mr-3 text-red-500 flex-shrink-0" />
                    {alerta}
                  </li>
                ))}
                {(!claim.alertas || claim.alertas.length === 0) && (
                   <div className="text-navy-500 text-sm">No hay alertas detectadas.</div>
                )}
              </ul>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Decisión Humana</CardTitle></CardHeader>
            <CardContent>
              <form onSubmit={handleDecision} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-navy-700 mb-1">Estado</label>
                  <select 
                    value={decision} 
                    onChange={(e) => setDecision(e.target.value)}
                    className="w-full bg-white border border-navy-300 rounded-md p-2 text-sm"
                  >
                    <option value="En revision">En revisión</option>
                    <option value="Escalado">Escalado</option>
                    <option value="Confirmado para investigacion">Confirmado para investigación</option>
                    <option value="Descartado">Descartado</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-navy-700 mb-1">Comentario</label>
                  <textarea 
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    className="w-full bg-white border border-navy-300 rounded-md p-2 text-sm"
                    rows={3}
                    required
                  />
                </div>
                <Button type="submit" className="w-full" disabled={reviewMutation.isPending}>
                  {reviewMutation.isPending ? 'Guardando...' : 'Guardar Decisión'}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Historial de Revisiones</CardTitle></CardHeader>
            <CardContent>
              <ul className="space-y-4">
                {history?.map((h: any, i: number) => (
                  <li key={i} className="text-sm border-l-2 border-navy-200 pl-3">
                    <p className="font-semibold text-navy-900">{h.status}</p>
                    <p className="text-navy-500 mt-1">{h.comentario}</p>
                    <p className="text-xs text-navy-400 mt-2">{new Date(h.fecha).toLocaleString()} por {h.usuario}</p>
                  </li>
                ))}
                {(!history || history.length === 0) && (
                   <p className="text-sm text-navy-400">Sin historial de revisión.</p>
                )}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
