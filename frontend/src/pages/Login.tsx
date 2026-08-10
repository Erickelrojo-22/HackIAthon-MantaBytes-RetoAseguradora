import type { FormEvent } from 'react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { Loader2, Lock, User } from 'lucide-react';
import { api, type LoginResponse } from '../lib/api';
import { useAuth } from '../contexts/useAuth';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { Disclaimer } from '../components/ui/Disclaimer';
import mantaBytesLogo from '../assets/manta-bytes-logo.svg';

const accessAccounts = [
  { label: 'Analista', email: 'analista@fraudia.demo' },
  { label: 'Jefatura', email: 'jefatura@fraudia.demo' },
  { label: 'Auditoria', email: 'auditoria@fraudia.demo' },
];

export function Login() {
  const [email, setEmail] = useState('analista@fraudia.demo');
  const [password, setPassword] = useState('demo123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  // El backend corre en el plan free de Render: si estuvo inactivo se "duerme"
  // y la primera solicitud puede tardar 30-60s en responder mientras arranca.
  // Sin este aviso, esa espera se ve identica a una falla real.
  const [serverWaking, setServerWaking] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const wakeTimer = setTimeout(() => {
      if (!cancelled) setServerWaking(true);
    }, 1500);
    api
      .get('/health')
      .catch(() => undefined)
      .finally(() => {
        cancelled = true;
        clearTimeout(wakeTimer);
        setServerWaking(false);
      });
    return () => {
      cancelled = true;
      clearTimeout(wakeTimer);
    };
  }, []);

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await api.post<LoginResponse>('/auth/login', { email, password });
      login(response.data.access_token, response.data.user);
      navigate('/');
    } catch (err) {
      if (isAxiosError(err)) {
        if (err.response?.status === 401) {
          setError('Credenciales invalidas.');
        } else if (err.response?.status === 429) {
          setError('Demasiados intentos. Espera unos segundos y vuelve a intentar.');
        } else if (err.code === 'ECONNABORTED') {
          setError('El servidor esta tardando en responder (puede estar iniciandose tras un periodo sin uso). Espera unos segundos y vuelve a intentar.');
        } else if (!err.response) {
          setError('No se pudo conectar con el servidor. Verifica tu conexion a internet y vuelve a intentar en unos segundos.');
        } else {
          setError(`Error inesperado del servidor (${err.response.status}). Intenta de nuevo.`);
        }
      } else {
        setError('Error inesperado. Intenta de nuevo.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative grid min-h-dvh place-items-center overflow-hidden bg-navy-950 px-4 py-10">
      <div className="absolute -left-28 -top-28 h-96 w-96 rounded-full bg-cyan-500/20 blur-3xl" />
      <div className="absolute -bottom-28 -right-28 h-[28rem] w-[28rem] rounded-full bg-blue-900/40 blur-3xl" />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 text-center">
          <img src={mantaBytesLogo} alt="Manta Bytes" className="mx-auto mb-5 h-28 w-28 rounded-[2rem] bg-white object-contain p-2 shadow-2xl ring-1 ring-cyan-300/30" />
          <h1 className="text-3xl font-black tracking-tight text-white">FraudIA Claims</h1>
          <p className="mt-2 text-sm text-navy-300">Centro de mando para revision de siniestros</p>
        </div>

        <Card className="border-white/10 bg-white/10 shadow-2xl backdrop-blur-xl">
          <CardContent className="p-8">
            <form className="space-y-5" onSubmit={handleLogin}>
              {serverWaking && !error && (
                <div className="flex items-center gap-2 rounded-xl border border-cyan-400/30 bg-cyan-400/10 p-3 text-center text-sm text-cyan-100">
                  <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin" />
                  <span>Conectando con el servidor. El primer ingreso tras un rato de inactividad puede tardar unos segundos.</span>
                </div>
              )}
              {error && <div className="rounded-xl border border-red-400/50 bg-red-500/10 p-3 text-center text-sm text-red-200">{error}</div>}

              <div>
                <label className="mb-2 block text-sm font-semibold text-navy-100">Correo</label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-5 w-5 text-navy-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-navy-900/80 py-2.5 pl-10 pr-3 text-sm text-white outline-none ring-cyan-400 transition placeholder:text-navy-500 focus:ring-2"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-navy-100">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-5 w-5 text-navy-400" />
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-navy-900/80 py-2.5 pl-10 pr-3 text-sm text-white outline-none ring-cyan-400 transition placeholder:text-navy-500 focus:ring-2"
                  />
                </div>
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-navy-300">Acceso por rol</p>
                <div className="grid grid-cols-3 gap-2">
                  {accessAccounts.map((item) => (
                    <button
                      key={item.email}
                      type="button"
                      onClick={() => setEmail(item.email)}
                      className="rounded-xl border border-white/10 bg-white/5 px-2 py-2 text-xs font-semibold text-navy-200 transition hover:bg-cyan-400/10 hover:text-cyan-200"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              <Button type="submit" variant="secondary" className="w-full" disabled={loading}>
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Ingresar al centro de mando'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Disclaimer className="mt-5 border-white/10 bg-white/10 text-navy-100" />
      </div>
    </div>
  );
}
