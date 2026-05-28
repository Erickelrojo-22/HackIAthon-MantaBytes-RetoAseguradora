import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, User, Lock, Loader2 } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { api } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

export function Login() {
  const [email, setEmail] = useState('analista@fraudia.demo');
  const [password, setPassword] = useState('demo123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await api.post('/auth/login', { email, password });
      const { access_token, user } = response.data;
      login(access_token, user);
      navigate('/');
    } catch (err) {
      setError('Credenciales inválidas. Intente nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-cyan-900/20 rounded-full blur-3xl"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-navy-800/40 rounded-full blur-3xl"></div>
      
      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex justify-center">
          <ShieldAlert className="w-16 h-16 text-cyan-400" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
          FraudIA Claims
        </h2>
        <p className="mt-2 text-center text-sm text-navy-300">
          Demo Empresarial Aseguradora
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <Card className="bg-navy-900 border-navy-700 shadow-2xl">
          <CardContent className="py-8 px-4 sm:px-10">
            <form className="space-y-6" onSubmit={handleLogin}>
              {error && (
                <div className="bg-red-500/10 border border-red-500/50 rounded-md p-3 text-sm text-red-400 text-center">
                  {error}
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium text-navy-200">
                  Correo Electrónico
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="h-5 w-5 text-navy-400" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="focus:ring-cyan-500 focus:border-cyan-500 block w-full pl-10 sm:text-sm border-navy-700 bg-navy-800 text-white rounded-md py-2.5"
                    placeholder="analista@fraudia.demo"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-navy-200">
                  Contraseña
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-navy-400" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="focus:ring-cyan-500 focus:border-cyan-500 block w-full pl-10 sm:text-sm border-navy-700 bg-navy-800 text-white rounded-md py-2.5"
                    placeholder="•••••••"
                  />
                </div>
              </div>

              <div className="mt-6 flex flex-col space-y-2">
                 <p className="text-xs text-navy-400 mb-2">Usuarios Demo:</p>
                 <div className="flex gap-2">
                    <button type="button" onClick={() => setEmail('analista@fraudia.demo')} className="text-xs bg-navy-800 px-2 py-1 rounded text-navy-300 hover:text-white">Analista</button>
                    <button type="button" onClick={() => setEmail('jefatura@fraudia.demo')} className="text-xs bg-navy-800 px-2 py-1 rounded text-navy-300 hover:text-white">Jefatura</button>
                    <button type="button" onClick={() => setEmail('auditoria@fraudia.demo')} className="text-xs bg-navy-800 px-2 py-1 rounded text-navy-300 hover:text-white">Auditoría</button>
                 </div>
              </div>

              <div>
                <Button type="submit" variant="secondary" className="w-full" disabled={loading}>
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Ingresar'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
