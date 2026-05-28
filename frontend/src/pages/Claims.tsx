import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Loader2 } from 'lucide-react';

export function Claims() {
  const [level, setLevel] = useState('');
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['claims', level],
    queryFn: async () => {
      const url = level ? `/claims/risk?limit=50&level=${level}` : '/claims/risk?limit=50';
      const res = await api.get(url);
      return res.data;
    }
  });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-navy-900">Bandeja de Revisión</h1>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
           <CardTitle>Filtros</CardTitle>
           <div className="flex gap-2">
              <select 
                 className="bg-white border border-navy-300 text-sm rounded-lg focus:ring-cyan-500 focus:border-cyan-500 block p-2"
                 value={level}
                 onChange={(e) => setLevel(e.target.value)}
              >
                 <option value="">Todos los niveles</option>
                 <option value="Rojo">Rojo</option>
                 <option value="Amarillo">Amarillo</option>
                 <option value="Verde">Verde</option>
              </select>
           </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="w-8 h-8 animate-spin text-cyan-600" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-navy-500">
                <thead className="text-xs text-navy-700 uppercase bg-navy-50">
                  <tr>
                    <th className="px-6 py-3">ID Siniestro</th>
                    <th className="px-6 py-3">Nivel</th>
                    <th className="px-6 py-3">Score</th>
                    <th className="px-6 py-3">Ramo</th>
                    <th className="px-6 py-3">Monto</th>
                    <th className="px-6 py-3">Proveedor</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.map((claim: any) => (
                    <tr 
                      key={claim.id_siniestro} 
                      className="bg-white border-b border-navy-100 hover:bg-navy-50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/claims/${claim.id_siniestro}`)}
                    >
                      <td className="px-6 py-4 font-medium text-navy-900 whitespace-nowrap">{claim.id_siniestro}</td>
                      <td className="px-6 py-4"><Badge variant={claim.nivel_riesgo as any}>{claim.nivel_riesgo}</Badge></td>
                      <td className="px-6 py-4">{claim.score_final}</td>
                      <td className="px-6 py-4">{claim.ramo}</td>
                      <td className="px-6 py-4">${claim.monto_reclamado}</td>
                      <td className="px-6 py-4">{claim.proveedor}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(!data || data.length === 0) && (
                 <div className="text-center py-8 text-navy-400">No se encontraron casos</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
