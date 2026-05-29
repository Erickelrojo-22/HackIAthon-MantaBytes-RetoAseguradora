import axios from 'axios';

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

export type Role = 'Analista' | 'Jefatura' | 'Auditoria';
export type RiskLevel = 'Verde' | 'Amarillo' | 'Rojo';
export type ReviewStatus = 'En revision' | 'Descartado' | 'Escalado' | 'Confirmado para investigacion';

export interface User {
  email: string;
  name: string;
  role: Role;
}

export interface LoginResponse {
  access_token: string;
  user: User;
}

export interface ClaimRisk {
  id_siniestro: string;
  score_final: number;
  nivel_riesgo: RiskLevel;
  ramo: string;
  cobertura: string;
  ciudad: string;
  monto_reclamado: number;
  proveedor: string;
  explicacion_resumen: string;
}

export interface Alert {
  codigo: string;
  categoria: string;
  severidad: string;
  puntos: number;
  descripcion: string;
  evidencia: string;
  es_critica: boolean;
}

export interface DocumentFinding {
  tipo_documento: string;
  entregado: number | boolean;
  legible: number | boolean;
  inconsistencia_detectada: number | boolean;
  adulteracion_confirmada: number | boolean;
  observacion?: string;
}

export interface ClaimDetail extends ClaimRisk {
  score_reglas: number;
  score_anomalia: number;
  score_nlp: number;
  score_modelo: number;
  probabilidad_modelo: number;
  accion_sugerida: string;
  similitud_narrativa?: number;
  siniestro_similar?: string;
  proveedor_nombre?: string;
  proveedor_tipo?: string;
  fecha_ocurrencia?: string;
  fecha_reporte?: string;
  sucursal?: string;
  descripcion?: string;
  alertas: Alert[];
  documentos: DocumentFinding[];
}

export interface ReviewDecision {
  id_decision: string;
  id_siniestro: string;
  status: ReviewStatus;
  comentario: string;
  reviewer_email: string;
  reviewer_role: Role;
  created_at: string;
}

export interface AuditEvent {
  id_event: string;
  actor_email: string;
  actor_role: Role;
  action: string;
  resource_type: string;
  resource_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface DashboardKpis {
  total_siniestros: number;
  casos_rojos: number;
  casos_amarillos: number;
  casos_priorizados: number;
  porcentaje_priorizado: number;
  porcentaje_rojo: number;
  monto_expuesto: number;
  monto_priorizado: number;
  ahorro_potencial_simulado: number;
  score_promedio: number;
}

export const api = axios.create({ baseURL: API_URL, timeout: 30000 });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const money = (value: number | string | null | undefined) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(Number(value ?? 0));

export const percent = (value: number | string | null | undefined) =>
  `${Number(value ?? 0).toFixed(1)}%`;

export const dateTime = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleString() : 'N/A';
