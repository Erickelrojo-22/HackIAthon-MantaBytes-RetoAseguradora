import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { BotMessageSquare, ClipboardCheck, FileText, Gauge, Inbox, LogOut, Scale, UserCog } from 'lucide-react';
import { useAuth } from '../../contexts/useAuth';
import { Disclaimer } from '../ui/Disclaimer';
import mantaBytesLogo from '../../assets/manta-bytes-logo.svg';

const baseNav = [
  { to: '/', icon: Gauge, label: 'Centro de Mando' },
  { to: '/claims', icon: Inbox, label: 'Bandeja' },
  { to: '/jury-test', icon: Scale, label: 'Prueba del Jurado' },
  { to: '/agent', icon: BotMessageSquare, label: 'Agente IA' },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const navItems = [...baseNav];

  if (user?.role === 'Jefatura' || user?.role === 'Auditoria') {
    navItems.push({ to: '/audit', icon: FileText, label: 'Auditoria' });
  }

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-navy-50">
      <aside className="z-20 flex w-72 flex-col bg-navy-950 text-white shadow-2xl">
        <div className="border-b border-white/10 px-6 py-5">
          <div className="flex items-center gap-3">
            <img src={mantaBytesLogo} alt="Manta Bytes" className="h-14 w-14 rounded-2xl bg-white object-contain p-1.5 shadow-lg ring-1 ring-cyan-300/20" />
            <div>
              <p className="text-lg font-black tracking-tight">FraudIA Claims</p>
              <p className="text-xs text-cyan-300">Manta Bytes Command Center</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-2 overflow-y-auto px-4 py-6">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center rounded-xl px-4 py-3 text-sm font-semibold transition ${
                  isActive ? 'bg-cyan-400/15 text-cyan-200 ring-1 ring-cyan-300/20' : 'text-navy-200 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <item.icon className="mr-3 h-5 w-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 p-4">
          <div className="mb-4 rounded-2xl bg-white/5 p-3">
            <div className="flex items-center gap-3">
              <UserCog className="h-9 w-9 rounded-full bg-navy-800 p-2 text-cyan-300" />
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
            <LogOut className="mr-3 h-5 w-5" />
            Cerrar sesion
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b border-navy-200 bg-white/85 px-8 shadow-sm backdrop-blur">
          <div className="flex items-center gap-3">
            <img src={mantaBytesLogo} alt="" className="h-10 w-10 rounded-xl bg-white object-contain p-1 shadow-sm ring-1 ring-navy-100" />
            <div>
              <p className="text-sm font-semibold text-navy-900">Demo empresarial Manta Bytes</p>
              <p className="text-xs text-navy-500">Alertas explicables para revision humana</p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-sm text-navy-600">
            <ClipboardCheck className="h-5 w-5 text-cyan-700" />
            <span>API FastAPI + Frontend React</span>
          </div>
        </header>
        <div className="flex-1 overflow-auto bg-[radial-gradient(circle_at_top_right,#cffafe_0,#f8fafc_34%,#ffffff_70%)] p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
            <Disclaimer className="mt-10" />
          </div>
        </div>
      </main>
    </div>
  );
}
