import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { api, dateTime, type AuditEvent } from '../lib/api';
import { useAuth } from '../contexts/useAuth';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

const PAGE_SIZE = 50;

export function Audit() {
  const { user } = useAuth();
  const [action, setAction] = useState('');
  const [resourceId, setResourceId] = useState('');
  const [actorEmail, setActorEmail] = useState('');
  const [resourceType, setResourceType] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(0);
  const allowed = user?.role === 'Jefatura' || user?.role === 'Auditoria';

  const filters = { action, resourceId, actorEmail, resourceType, dateFrom, dateTo };
  const [prevFilters, setPrevFilters] = useState(filters);
  const filtersChanged = Object.keys(filters).some((key) => filters[key as keyof typeof filters] !== prevFilters[key as keyof typeof filters]);
  if (filtersChanged) {
    setPrevFilters(filters);
    setPage(0);
  }

  const { data: page_, isLoading, isError, refetch } = useQuery({
    queryKey: ['audit', action, resourceId, actorEmail, resourceType, dateFrom, dateTo, page],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(page * PAGE_SIZE) });
      if (action) params.set('action', action);
      if (resourceId) params.set('resource_id', resourceId);
      if (actorEmail) params.set('actor_email', actorEmail);
      if (resourceType) params.set('resource_type', resourceType);
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);
      const response = await api.get<AuditEvent[]>(`/audit-log?${params.toString()}`);
      const totalHeader = Number(response.headers['x-total-count'] ?? response.data.length);
      return { rows: response.data, total: Number.isFinite(totalHeader) ? totalHeader : response.data.length };
    },
    enabled: allowed,
  });
  const rows = page_?.rows ?? [];
  const total = page_?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const rangeStart = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const rangeEnd = Math.min((page + 1) * PAGE_SIZE, total);

  if (!allowed) return <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center text-red-700">Acceso denegado. Se requiere rol de Jefatura o Auditoria.</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-black text-navy-950">Auditoria</h1>
        <p className="text-sm text-navy-500">Trazabilidad de consultas, decisiones humanas y acciones del agente.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Filtros</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <input value={action} onChange={(event) => setAction(event.target.value)} placeholder="Accion, ej. review_decision.created" className="rounded-xl border border-navy-200 px-3 py-2" />
          <input value={resourceId} onChange={(event) => setResourceId(event.target.value)} placeholder="Resource ID, ej. SIN00001" className="rounded-xl border border-navy-200 px-3 py-2" />
          <input value={resourceType} onChange={(event) => setResourceType(event.target.value)} placeholder="Tipo de recurso, ej. claim" className="rounded-xl border border-navy-200 px-3 py-2" />
          <input value={actorEmail} onChange={(event) => setActorEmail(event.target.value)} placeholder="Usuario, ej. analista@fraudia.demo" className="rounded-xl border border-navy-200 px-3 py-2" />
          <label className="text-xs font-semibold text-navy-500">
            Desde
            <input type="datetime-local" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="mt-1 w-full rounded-xl border border-navy-200 px-3 py-2 text-sm text-navy-900" />
          </label>
          <label className="text-xs font-semibold text-navy-500">
            Hasta
            <input type="datetime-local" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="mt-1 w-full rounded-xl border border-navy-200 px-3 py-2 text-sm text-navy-900" />
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>{total === 0 ? '0 eventos' : `Mostrando ${rangeStart}-${rangeEnd} de ${total} eventos`}</CardTitle>
            {pageCount > 1 && (
              <div className="flex items-center gap-2">
                <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="rounded-lg border border-navy-200 p-1.5 text-navy-600 disabled:opacity-30" aria-label="Pagina anterior">
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs font-semibold text-navy-500">Pagina {page + 1} de {pageCount}</span>
                <button onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))} disabled={page >= pageCount - 1} className="rounded-lg border border-navy-200 p-1.5 text-navy-600 disabled:opacity-30" aria-label="Pagina siguiente">
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto p-0">
          {isLoading ? (
            <div className="grid h-64 place-items-center"><Loader2 className="h-8 w-8 animate-spin text-cyan-700" /></div>
          ) : isError ? (
            <div className="p-8 text-center">
              <p className="mb-3 text-sm font-semibold text-red-600">Error cargando auditoria.</p>
              <button onClick={() => refetch()} className="rounded-xl border border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100">Reintentar</button>
            </div>
          ) : rows.length === 0 ? (
            <p className="p-8 text-center text-sm text-navy-400">Sin eventos que coincidan con estos filtros.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-navy-50 text-xs uppercase text-navy-500"><tr><th className="px-6 py-3">Fecha</th><th>Usuario</th><th>Rol</th><th>Accion</th><th>Recurso</th><th>Metadata</th></tr></thead>
              <tbody className="divide-y divide-navy-100">
                {rows.map((event) => (
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
