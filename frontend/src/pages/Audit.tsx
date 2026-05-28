import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { api, dateTime, type AuditEvent } from '../lib/api';
import { useAuth } from '../contexts/useAuth';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

export function Audit() {
  const { user } = useAuth();
  const [action, setAction] = useState('');
  const [resourceId, setResourceId] = useState('');
  const allowed = user?.role === 'Jefatura' || user?.role === 'Auditoria';

  const { data = [], isLoading, error } = useQuery({
    queryKey: ['audit', action, resourceId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (action) params.set('action', action);
      if (resourceId) params.set('resource_id', resourceId);
      return (await api.get<AuditEvent[]>(`/audit-log?${params.toString()}`)).data;
    },
    enabled: allowed,
  });

  if (!allowed) return <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center text-red-700">Acceso denegado. Se requiere rol de Jefatura o Auditoria.</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-black text-navy-950">Auditoria</h1>
        <p className="text-sm text-navy-500">Trazabilidad de consultas, decisiones humanas y acciones del agente.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Filtros</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <input value={action} onChange={(event) => setAction(event.target.value)} placeholder="Accion, ej. review_decision.created" className="rounded-xl border border-navy-200 px-3 py-2" />
          <input value={resourceId} onChange={(event) => setResourceId(event.target.value)} placeholder="Resource ID, ej. SIN00001" className="rounded-xl border border-navy-200 px-3 py-2" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Eventos del sistema</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto p-0">
          {isLoading ? <div className="grid h-64 place-items-center"><Loader2 className="h-8 w-8 animate-spin text-cyan-700" /></div> : error ? <div className="p-8 text-red-600">Error cargando auditoria.</div> : (
            <table className="w-full text-left text-sm">
              <thead className="bg-navy-50 text-xs uppercase text-navy-500"><tr><th className="px-6 py-3">Fecha</th><th>Usuario</th><th>Rol</th><th>Accion</th><th>Recurso</th><th>Metadata</th></tr></thead>
              <tbody className="divide-y divide-navy-100">
                {data.map((event) => (
                  <tr key={event.id_event} className="bg-white">
                    <td className="px-6 py-4">{dateTime(event.created_at)}</td>
                    <td>{event.actor_email}</td>
                    <td><Badge variant="info">{event.actor_role}</Badge></td>
                    <td className="font-mono text-xs">{event.action}</td>
                    <td className="font-mono text-xs">{event.resource_type}:{event.resource_id}</td>
                    <td className="max-w-sm truncate text-xs text-navy-500">{JSON.stringify(event.metadata)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
