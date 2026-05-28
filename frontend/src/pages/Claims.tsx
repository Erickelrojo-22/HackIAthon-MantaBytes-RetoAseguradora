import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Loader2, Search } from 'lucide-react';
import { api, money, type ClaimRisk, type RiskLevel } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

export function Claims() {
  const [level, setLevel] = useState<RiskLevel | ''>('');
  const [ramo, setRamo] = useState('');
  const [city, setCity] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  const { data = [], isLoading } = useQuery({
    queryKey: ['claims', level],
    queryFn: async () => {
      const suffix = level ? `&level=${level}` : '';
      return (await api.get<ClaimRisk[]>(`/claims/risk?limit=100${suffix}`)).data;
    },
  });

  const ramos = [...new Set(data.map((claim) => claim.ramo))].sort();
  const cities = [...new Set(data.map((claim) => claim.ciudad))].sort();
  const filtered = useMemo(
    () =>
      data.filter((claim) => {
        const haystack = `${claim.id_siniestro} ${claim.proveedor} ${claim.ramo} ${claim.ciudad}`.toLowerCase();
        return (
          (!ramo || claim.ramo === ramo) &&
          (!city || claim.ciudad === city) &&
          claim.score_final >= minScore &&
          (!search || haystack.includes(search.toLowerCase()))
        );
      }),
    [data, ramo, city, minScore, search],
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-black text-navy-950">Bandeja de revision</h1>
        <p className="mt-1 text-sm text-navy-500">Filtra y abre expedientes priorizados por score explicable.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Filtros visuales</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-5">
          <Select value={level} onChange={(value) => setLevel(value as RiskLevel | '')} options={['', 'Rojo', 'Amarillo', 'Verde']} label="Nivel" />
          <Select value={ramo} onChange={setRamo} options={['', ...ramos]} label="Ramo" />
          <Select value={city} onChange={setCity} options={['', ...cities]} label="Ciudad" />
          <label className="text-sm font-semibold text-navy-700">
            Score minimo
            <input value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} type="number" min={0} max={100} className="mt-1 w-full rounded-xl border border-navy-200 px-3 py-2" />
          </label>
          <label className="text-sm font-semibold text-navy-700">
            Buscar
            <div className="relative mt-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-navy-400" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} className="w-full rounded-xl border border-navy-200 py-2 pl-9 pr-3" placeholder="ID o proveedor" />
            </div>
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>{filtered.length} casos encontrados</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto p-0">
          {isLoading ? (
            <div className="grid h-64 place-items-center"><Loader2 className="h-8 w-8 animate-spin text-cyan-700" /></div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-navy-50 text-xs uppercase text-navy-500">
                <tr>
                  <th className="px-6 py-3">Caso</th><th>Nivel</th><th>Score</th><th>Ramo</th><th>Ciudad</th><th>Monto</th><th>Proveedor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-100">
                {filtered.map((claim) => (
                  <tr key={claim.id_siniestro} onClick={() => navigate(`/claims/${claim.id_siniestro}`)} className="cursor-pointer bg-white transition hover:bg-cyan-50/60">
                    <td className="px-6 py-4 font-bold text-navy-950">{claim.id_siniestro}</td>
                    <td><Badge variant={claim.nivel_riesgo}>{claim.nivel_riesgo}</Badge></td>
                    <td className="font-semibold">{claim.score_final}</td>
                    <td>{claim.ramo}</td>
                    <td>{claim.ciudad}</td>
                    <td>{money(claim.monto_reclamado)}</td>
                    <td>{claim.proveedor}</td>
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

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="text-sm font-semibold text-navy-700">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-xl border border-navy-200 bg-white px-3 py-2">
        {options.map((option) => <option key={option} value={option}>{option || 'Todos'}</option>)}
      </select>
    </label>
  );
}
