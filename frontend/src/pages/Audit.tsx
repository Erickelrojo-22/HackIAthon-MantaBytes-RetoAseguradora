import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Loader2 } from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { useAuth } from '../contexts/AuthContext';

export function Audit() {
  const { user } = useAuth();
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['audit'],
    queryFn: async () => {
      const res = await api.get('/audit-log');
      return res.data;
    },
    enabled: user?.role === 'Jefatura' || user?.role === 'Auditoria'
  });

  if (user?.role === 'Analista') {
    return <div className="text-center p-12 text-red-500">Acceso denegado. Se requiere rol de Jefatura o Auditoría.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-navy-900">Registro de Auditoría</h1>
      </div>

      <Card>
        <CardHeader><CardTitle>Eventos del Sistema</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="w-8 h-8 animate-spin text-cyan-600" /></div>
          ) : error ? (
            <div className="text-red-500 text-center">Error cargando auditoría.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-navy-500">
                <thead className="text-xs text-navy-700 uppercase bg-navy-50">
                  <tr>
                    <th className="px-6 py-3">Fecha</th>
                    <th className="px-6 py-3">Usuario</th>
                    <th className="px-6 py-3">Acción</th>
                    <th className="px-6 py-3">Recurso</th>
                    <th className="px-6 py-3">Detalles</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.map((log: any, idx: number) => (
                    <tr key={idx} className="bg-white border-b border-navy-100 hover:bg-navy-50">
                      <td className="px-6 py-4 whitespace-nowrap">{new Date(log.timestamp || log.fecha).toLocaleString()}</td>
                      <td className="px-6 py-4">{log.actor_email || log.usuario}</td>
                      <td className="px-6 py-4">
                         <Badge variant={log.action === 'login' ? 'default' : 'Amarillo' as any}>{log.action || log.accion}</Badge>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs">{log.resource_type || '-'} {log.resource_id || ''}</td>
                      <td className="px-6 py-4 max-w-xs truncate">{JSON.stringify(log.metadata || {})}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
