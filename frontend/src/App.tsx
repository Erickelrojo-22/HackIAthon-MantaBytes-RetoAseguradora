import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthProvider';
import { useAuth } from './contexts/useAuth';
import { AppLayout } from './components/layout/AppLayout';

import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Claims } from './pages/Claims';
import { ClaimDetail } from './pages/ClaimDetail';
import { JuryTest } from './pages/JuryTest';
import { Agent } from './pages/Agent';
import { Audit } from './pages/Audit';
import { Relationships } from './pages/Relationships';
import { ExecutiveReportPage } from './pages/ExecutiveReport';
import { UploadCsv } from './pages/UploadCsv';
import { Vision } from './pages/Vision';

const queryClient = new QueryClient();

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="claims" element={<Claims />} />
        <Route path="claims/:id" element={<ClaimDetail />} />
        <Route path="jury-test" element={<JuryTest />} />
        <Route path="relationships" element={<Relationships />} />
        <Route path="report" element={<ExecutiveReportPage />} />
        <Route path="upload-csv" element={<UploadCsv />} />
        <Route path="vision" element={<Vision />} />
        <Route path="agent" element={<Agent />} />
        <Route path="audit" element={<Audit />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
