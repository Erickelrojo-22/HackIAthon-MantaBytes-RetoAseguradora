import React, { useState } from 'react';
import { api } from '../lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Loader2, AlertTriangle } from 'lucide-react';

export function JuryTest() {
  const [formData, setFormData] = useState({
    ramo: 'Vehículos',
    cobertura: 'Pérdida Total por Robo',
    monto_reclamado: 29500,
    suma_asegurada: 30000,
    dias_desde_inicio_poliza: 1,
    dias_desde_fin_poliza: 364,
    dias_entre_ocurrencia_reporte: 5,
    denuncia_horas: 120,
    documentos_completos: false,
    documentos_inconsistentes: true,
    tercero_identificado: false
  });
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post('/score-candidate', formData);
      setResult(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-navy-900">Prueba del Jurado</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>Simulador de Siniestro</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-navy-700">Ramo</label>
                  <input type="text" value={formData.ramo} onChange={e => setFormData({...formData, ramo: e.target.value})} className="mt-1 block w-full rounded-md border-navy-300 shadow-sm focus:border-cyan-500 focus:ring-cyan-500 sm:text-sm p-2 border" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-navy-700">Monto Reclamado</label>
                  <input type="number" value={formData.monto_reclamado} onChange={e => setFormData({...formData, monto_reclamado: Number(e.target.value)})} className="mt-1 block w-full rounded-md border-navy-300 shadow-sm focus:border-cyan-500 focus:ring-cyan-500 sm:text-sm p-2 border" />
                </div>
                {/* ... (otros campos abreviados para que entre) ... */}
                <div className="col-span-2">
                   <p className="text-sm text-navy-500 mb-4 bg-yellow-50 p-3 rounded border border-yellow-200">
                     <AlertTriangle className="inline w-4 h-4 mr-1 text-yellow-600" />
                     Este formulario está prellenado con un caso crítico de prueba. Los datos enviados aquí <strong>no se guardan</strong> en la base de datos principal, es solo una simulación.
                   </p>
                </div>
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Ejecutar Score'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {result && (
          <Card className="bg-navy-900 text-white border-navy-700">
            <CardHeader className="border-navy-700 bg-navy-800"><CardTitle className="text-white">Resultado del Score</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="text-center py-6">
                <div className="text-6xl font-bold text-cyan-400">{result.score_total}/100</div>
                <div className="text-navy-300 mt-2 text-lg">Nivel: {result.nivel_riesgo}</div>
              </div>
              
              {result.alertas && result.alertas.length > 0 && (
                 <div>
                   <h4 className="font-semibold text-cyan-300 mb-2">Alertas Detectadas:</h4>
                   <ul className="space-y-2">
                      {result.alertas.map((alerta: string, idx: number) => (
                         <li key={idx} className="flex items-start text-sm">
                            <AlertTriangle className="w-4 h-4 mr-2 text-red-400 mt-0.5" />
                            {alerta}
                         </li>
                      ))}
                   </ul>
                 </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
