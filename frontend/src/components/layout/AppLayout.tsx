import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LayoutDashboard, Inbox, Scale, FileText, UserCog, LogOut, BotMessageSquare } from 'lucide-react';
import { Disclaimer } from '../ui/Disclaimer';

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Centro de Mando' },
    { to: '/claims', icon: Inbox, label: 'Bandeja' },
    { to: '/jury-test', icon: Scale, label: 'Prueba del Jurado' },
    { to: '/agent', icon: BotMessageSquare, label: 'Agente IA' },
  ];

  if (user?.role === 'Jefatura' || user?.role === 'Auditoria') {
    navItems.push({ to: '/audit', icon: FileText, label: 'Auditoría' });
  }

  return (
    <div className="flex h-screen overflow-hidden bg-navy-50">
      <aside className="w-64 bg-navy-950 text-white flex flex-col shadow-xl z-20">
        <div className="h-16 flex items-center px-6 border-b border-navy-800">
          <span className="text-xl font-bold tracking-tight text-cyan-400">FraudIA Claims</span>
        </div>
        <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center px-3 py-2.5 rounded-lg transition-colors ${
                  isActive ? 'bg-cyan-900/50 text-cyan-300' : 'text-navy-300 hover:bg-navy-800 hover:text-white'
                }`
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              <span className="font-medium text-sm">{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-navy-800">
          <div className="flex items-center mb-4 px-2">
            <UserCog className="w-8 h-8 text-navy-400 mr-3" />
            <div className="overflow-hidden">
              <p className="text-sm font-medium text-white truncate">{user?.name}</p>
              <p className="text-xs text-cyan-500 truncate">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center px-3 py-2 text-sm font-medium text-navy-300 rounded-lg hover:bg-navy-800 hover:text-red-400 transition-colors"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Cerrar Sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 flex flex-col overflow-hidden relative">
        <header className="h-16 bg-white border-b border-navy-200 flex items-center justify-between px-8 shadow-sm z-10">
           <div className="text-navy-600 font-medium">Demo Empresarial</div>
           <div className="flex items-center">
              <div className="h-8 w-8 bg-cyan-100 rounded-full flex items-center justify-center text-cyan-800 font-bold">
                 {user?.name?.[0] || 'U'}
              </div>
           </div>
        </header>
        <div className="flex-1 overflow-auto p-8 bg-gradient-to-b from-navy-50 to-white">
          <div className="max-w-7xl mx-auto">
            <Outlet />
            <div className="mt-12">
              <Disclaimer />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
