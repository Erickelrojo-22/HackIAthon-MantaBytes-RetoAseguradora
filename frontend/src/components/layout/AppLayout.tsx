import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { BotMessageSquare, ClipboardCheck, FileText, Gauge, Image, Inbox, LogOut, Menu, Network, Scale, Upload, UserCog, X } from 'lucide-react';
import { useAuth } from '../../contexts/useAuth';
import { Disclaimer } from '../ui/Disclaimer';
import mantaBytesLogo from '../../assets/manta-bytes-logo.svg';

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { to: '/', icon: Gauge, label: 'Centro de Mando' },
    { to: '/claims', icon: Inbox, label: 'Bandeja' },
    { to: '/relationships', icon: Network, label: 'Red de relaciones' },
    { to: '/report', icon: FileText, label: 'Reporte ejecutivo' },
    { to: '/jury-test', icon: Scale, label: 'Prueba del Jurado' },
    { to: '/vision', icon: Image, label: 'Analisis visual' },
    ...(user?.role === 'Analista' || user?.role === 'Jefatura'
      ? [{ to: '/upload-csv', icon: Upload, label: 'Carga CSV' }]
      : []),
    { to: '/agent', icon: BotMessageSquare, label: 'Agente IA' },
    ...(user?.role === 'Jefatura' || user?.role === 'Auditoria'
      ? [{ to: '/audit', icon: ClipboardCheck, label: 'Auditoria' }]
      : []),
  ];

  const handleLogout = () => {
    setIsMobileMenuOpen(false);
    logout();
    navigate('/login');
  };

  const sidebarContent = (
    <>
      <div className="border-b border-white/10 px-5 py-5 sm:px-6">
        <div className="flex items-center gap-3">
          <img src={mantaBytesLogo} alt="Manta Bytes" className="h-14 w-14 rounded-2xl bg-white object-contain p-1.5 shadow-lg ring-1 ring-cyan-300/20" />
          <div className="min-w-0">
            <p className="truncate text-lg font-black tracking-tight">FraudIA Claims</p>
            <p className="text-xs text-cyan-300">Manta Bytes Command Center</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-2 overflow-y-auto px-4 py-6">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => setIsMobileMenuOpen(false)}
            className={({ isActive }) =>
              `flex items-center rounded-xl px-4 py-3 text-sm font-semibold transition ${
                isActive ? 'bg-cyan-400/15 text-cyan-200 ring-1 ring-cyan-300/20' : 'text-navy-200 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <item.icon className="mr-3 h-5 w-5 shrink-0" />
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 p-4">
        <div className="mb-4 rounded-2xl bg-white/5 p-3">
          <div className="flex items-center gap-3">
            <UserCog className="h-9 w-9 shrink-0 rounded-full bg-navy-800 p-2 text-cyan-300" />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{user?.name}</p>
              <p className="truncate text-xs text-cyan-300">{user?.role}</p>
            </div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center rounded-xl px-4 py-3 text-sm font-semibold text-navy-200 transition hover:bg-red-500/10 hover:text-red-300"
        >
          <LogOut className="mr-3 h-5 w-5 shrink-0" />
          Cerrar sesion
        </button>
      </div>
    </>
  );

  return (
    <div className="flex h-dvh overflow-hidden bg-navy-50">
      <aside className="z-20 hidden w-72 shrink-0 flex-col bg-navy-950 text-white shadow-2xl lg:flex">
        {sidebarContent}
      </aside>

      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-40 h-dvh lg:hidden" aria-modal="true" role="dialog">
          <button
            type="button"
            aria-label="Cerrar menu"
            className="absolute inset-0 bg-navy-950/60 backdrop-blur-sm"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <aside className="relative flex h-full w-[86vw] max-w-80 flex-col bg-navy-950 text-white shadow-2xl">
            <button
              type="button"
              aria-label="Cerrar menu"
              onClick={() => setIsMobileMenuOpen(false)}
              className="absolute right-4 top-4 z-10 rounded-xl bg-white/10 p-2 text-navy-100 transition hover:bg-white/20"
            >
              <X className="h-5 w-5" />
            </button>
            {sidebarContent}
          </aside>
        </div>
      )}

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-navy-200 bg-white/85 px-4 shadow-sm backdrop-blur sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              aria-label="Abrir menu"
              onClick={() => setIsMobileMenuOpen(true)}
              className="rounded-xl border border-navy-200 bg-white p-2 text-navy-700 shadow-sm transition hover:bg-navy-50 lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <img src={mantaBytesLogo} alt="" className="h-10 w-10 rounded-xl bg-white object-contain p-1 shadow-sm ring-1 ring-navy-100" />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-navy-900">Demo empresarial Manta Bytes</p>
              <p className="text-xs text-navy-500">Alertas explicables para revision humana</p>
            </div>
          </div>
          <div className="hidden items-center gap-3 text-sm text-navy-600 sm:flex">
            <ClipboardCheck className="h-5 w-5 text-cyan-700" />
            <span>API FastAPI + Frontend React</span>
          </div>
        </header>
        <div className="flex-1 overflow-auto bg-[radial-gradient(circle_at_top_right,#cffafe_0,#f8fafc_34%,#ffffff_70%)] p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
            <Disclaimer className="mt-10" />
          </div>
        </div>
      </main>
    </div>
  );
}
