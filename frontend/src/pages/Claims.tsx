import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Loader2, Search } from 'lucide-react';
import { api, money, type ClaimRisk, type RiskLevel } from '../lib/api';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';

const PAGE_SIZE = 20;

export function Claims() {
  const [level, setLevel] = useState<RiskLevel | ''>('');
  const [ramo, setRamo] = useState('');
  const [city, setCity] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const navigate = useNavigate();

  // Reset to page 0 whenever a real (backend) filter changes, so pagination
  // never points past the end of a newly-filtered result set. Per React's
  // guidance for "adjusting state when a dependency changes", this compares
  // against the previous filter snapshot during render rather than in a
  // useEffect, avoiding an extra render pass.
  const activeFilters = { level, ramo, city, minScore };
  const [prevFilters, setPrevFilters] = useState(activeFilters);
  if (
    prevFilters.level !== activeFilters.level ||
    prevFilters.ramo !== activeFilters.ramo ||
    prevFilters.city !== activeFilters.city ||
    prevFilters.minScore !== activeFilters.minScore
  ) {
    setPrevFilters(activeFilters);
    setPage(0);
  }

  const { data: filterOptions } = useQuery({
    queryKey: ['claims-filter-options'],
    queryFn: async () => (await api.get<{ ramos: string[]; ciudades: string[] }>('/claims/filter-options')).data,
  });

  const { data: page_, isLoading, isError, refetch } = useQuery({
    queryKey: ['claims', level, ramo, city, minScore, page],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(page * PAGE_SIZE) });
      if (level) params.set('level', level);
      if (ramo) params.set('ramo', ramo);
      if (city) params.set('ciudad', city);
      if (minScore > 0) params.set('min_score', String(minScore));
      const response = await api.get<ClaimRisk[]>(`/claims/risk?${params.toString()}`);
      const totalHeader = Number(response.headers['x-total-count'] ?? response.data.length);
      return { rows: response.data, total: Number.isFinite(totalHeader) ? totalHeader : response.data.length };
    },
  });
  const rows = page_?.rows ?? [];

  // Search only ever narrows the page already fetched from the backend — it
  // is not a global filter, since the backend has no free-text search param.
  const visible = search
    ? rows.filter((claim) => `${claim.id_siniestro} ${claim.proveedor}`.toLowerCase().includes(search.toLowerCase()))
    : rows;

  const totalCount = page_?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const rangeStart = totalCount === 0 ? 0 : page * PAGE_SIZE + 1;
  const rangeEnd = Math.min((page + 1) * PAGE_SIZE, totalCount);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-black text-navy-950">Bandeja de revision</h1>
        <p className="mt-1 text-sm text-navy-500">Filtra y abre expedientes priorizados por score explicable.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Filtros</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-5">
          <Select value={level} onChange={(value) => setLevel(value as RiskLevel | '')} options={['', 'Rojo', 'Amarillo', 'Verde']} label="Nivel" />
          <Select value={ramo} onChange={setRamo} options={['', ...(filterOptions?.ramos ?? [])]} label="Ramo" />
          <Select value={city} onChange={setCity} options={['', ...(filterOptions?.ciudades ?? [])]} label="Ciudad" />
          <label className="text-sm font-semibold text-navy-700">
            Score minimo
            <input value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} type="number" min={0} max={100} className="mt-1 w-full rounded-xl border border-navy-200 px-3 py-2" />
          </label>
          <label className="text-sm font-semibold text-navy-700">
            Buscar en esta pagina
            <div className="relative mt-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-navy-400" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} className="w-full rounded-xl border border-navy-200 py-2 pl-9 pr-3" placeholder="ID o proveedor" />
            </div>
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>
              {totalCount === 0 ? '0 casos' : `Mostrando ${rangeStart}-${rangeEnd} de ${totalCount} casos`}
            </CardTitle>
            {pageCount > 1 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="rounded-lg border border-navy-200 p-1.5 text-navy-600 disabled:opacity-30"
                  aria-label="Pagina anterior"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs font-semibold text-navy-500">Pagina {page + 1} de {pageCount}</span>
                <button
                  onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                  disabled={page >= pageCount - 1}
                  className="rounded-lg border border-navy-200 p-1.5 text-navy-600 disabled:opacity-30"
                  aria-label="Pagina siguiente"
                >
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
              <p className="mb-3 text-sm font-semibold text-red-600">No se pudieron cargar los casos.</p>
              <button onClick={() => refetch()} className="rounded-xl border border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100">
                Reintentar
              </button>
            </div>
          ) : visible.length === 0 ? (
            <p className="p-8 text-center text-sm text-navy-400">Sin casos que coincidan con estos filtros.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-navy-50 text-xs uppercase text-navy-500">
                <tr>
                  <th className="px-6 py-3">Caso</th><th>Nivel</th><th>Score</th><th>Ramo</th><th>Ciudad</th><th>Monto</th><th>Proveedor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-100">
                {visible.map((claim) => (
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
