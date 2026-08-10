// Casos temporales evaluados en esta pestaña (via /score-candidate en JuryTest)
// que el usuario nunca persiste en la base. Se guardan solo en sessionStorage
// (se pierden al cerrar la pestaña) y se reenvían en /agent/question para que
// el intent "session_case" ("el último caso evaluado en vivo") pueda
// responder sin que el usuario tenga que re-describir el caso. Antes de esto
// el intent existía en el backend pero nunca recibía datos desde la app web.
export interface SessionCaseAlert {
  codigo: string;
  descripcion: string;
  puntos: number;
}

export interface SessionCase {
  id_temporal: string;
  ramo: string;
  cobertura: string;
  score_final: number;
  nivel_riesgo: string;
  monto_reclamado: number;
  accion_sugerida: string;
  alertas: SessionCaseAlert[];
}

const STORAGE_KEY = 'fraudia.session_cases';
const MAX_CASES = 5;

export function getSessionCases(): SessionCase[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function addSessionCase(caseData: Omit<SessionCase, 'id_temporal'>): SessionCase {
  const withId: SessionCase = { ...caseData, id_temporal: `TMP-${Date.now().toString(36).toUpperCase()}` };
  const updated = [...getSessionCases(), withId].slice(-MAX_CASES);
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // sessionStorage puede no estar disponible (modo privado); el caso
    // simplemente no queda disponible para preguntas posteriores del agente.
  }
  return withId;
}
