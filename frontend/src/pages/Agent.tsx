import type { FormEvent } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { isAxiosError } from 'axios';
import { AlertTriangle, BotMessageSquare, Loader2, RotateCw, Send, Trash2 } from 'lucide-react';
import { api } from '../lib/api';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { MarkdownMessage } from '../components/ui/MarkdownMessage';
import { useAuth } from '../contexts/useAuth';

const suggestions = [
  'Cuales son los 10 siniestros con mayor riesgo?',
  'Que proveedores concentran mas alertas rojas?',
  'Genera un resumen ejecutivo de los casos criticos.',
  'Que documentos faltan en los casos criticos?',
];

type AgentMessage = { role: 'user' | 'agent'; content: string; source?: string; isError?: boolean };

function readStoredMessages(storageKey: string): AgentMessage[] {
  try {
    const raw = localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function visibleSource(source?: string) {
  if (!source || source.startsWith('Herramientas locales') || source === 'Sesion local') return '';
  if (source.startsWith('Offline')) return 'Offline';
  return source;
}

function describeAgentError(error: unknown): string {
  if (isAxiosError(error)) {
    if (error.code === 'ECONNABORTED') return 'La consulta tardo demasiado en responder (timeout). Intenta de nuevo.';
    if (!error.response) return 'No se pudo conectar con el servidor. Verifica tu conexion o que la API este activa.';
    if (error.response.status === 429) return 'Demasiadas preguntas seguidas; espera unos segundos y vuelve a intentar.';
    if (error.response.status === 401) return 'Tu sesion expiro. Vuelve a iniciar sesion.';
    return `El servidor respondio con un error (${error.response.status}). Intenta de nuevo.`;
  }
  return 'Ocurrio un error inesperado. Intenta de nuevo.';
}

export function Agent() {
  const { user } = useAuth();
  const storageKey = useMemo(() => `fraudia.agent.messages.${user?.email ?? 'anonymous'}`, [user?.email]);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<AgentMessage[]>(() => readStoredMessages(storageKey));
  const [loading, setLoading] = useState(false);
  const pendingRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(messages));
  }, [messages, storageKey]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, loading]);

  const ask = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || pendingRef.current) return;
    pendingRef.current = true;
    const next = [...messages, { role: 'user' as const, content: text }];
    setMessages(next);
    setQuestion('');
    setLoading(true);
    try {
      const response = await api.post('/agent/question', { question: trimmed, scope: 'global' });
      setMessages([...next, { role: 'agent', content: response.data.answer, source: response.data.source }]);
    } catch (error) {
      setMessages([...next, { role: 'agent', content: describeAgentError(error), isError: true }]);
    } finally {
      pendingRef.current = false;
      setLoading(false);
    }
  };

  const clearChat = () => {
    localStorage.removeItem(storageKey);
    setMessages([]);
    setQuestion('');
  };

  const handleSend = (event: FormEvent) => {
    event.preventDefault();
    ask(question);
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col space-y-5 lg:h-[calc(100dvh-9rem)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-black text-navy-950">Agente IA</h1>
          <p className="text-sm text-navy-500">Consulta casos, alertas y patrones con evidencia para revision humana.</p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={clearChat} disabled={messages.length === 0 || loading}>
          <Trash2 className="mr-2 h-4 w-4" />
          Limpiar chat
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {suggestions.map((item) => (
          <button
            key={item}
            onClick={() => ask(item)}
            disabled={loading}
            className="rounded-full border border-navy-200 bg-white px-3 py-1.5 text-xs font-semibold text-navy-700 transition hover:bg-cyan-50 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-white"
          >
            {item}
          </button>
        ))}
      </div>

      <Card className="flex min-h-[28rem] flex-1 flex-col lg:min-h-0">
        <CardContent className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          {messages.length === 0 && (
            <div className="grid h-full place-items-center text-center text-navy-400">
              <div><BotMessageSquare className="mx-auto mb-4 h-16 w-16 opacity-50" /><p>Haz una pregunta ejecutiva sobre riesgo, proveedores, documentos o un caso SINxxxxx.</p></div>
            </div>
          )}
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[82%] rounded-3xl p-4 text-sm ${
                  message.role === 'user'
                    ? 'rounded-br-sm bg-cyan-700 text-white'
                    : message.isError
                      ? 'rounded-bl-sm border border-red-200 bg-red-50 text-red-800'
                      : 'rounded-bl-sm border border-navy-100 bg-navy-50 text-navy-900'
                }`}
              >
                {message.isError && (
                  <div className="mb-2 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span className="font-semibold">No se pudo responder</span>
                  </div>
                )}
                {message.role === 'agent' ? <MarkdownMessage content={message.content} /> : <div className="whitespace-pre-wrap">{message.content}</div>}
                {visibleSource(message.source) && <p className="mt-3 text-xs font-semibold text-cyan-700">Fuente: {visibleSource(message.source)}</p>}
                {message.isError && (
                  <button
                    type="button"
                    onClick={() => {
                      const lastUser = [...messages].slice(0, index).reverse().find((m) => m.role === 'user');
                      if (lastUser) ask(lastUser.content);
                    }}
                    className="mt-2 flex items-center gap-1 text-xs font-semibold text-red-700 underline hover:text-red-900"
                  >
                    <RotateCw className="h-3 w-3" /> Reintentar
                  </button>
                )}
              </div>
            </div>
          ))}
          {loading && <Loader2 className="h-5 w-5 animate-spin text-cyan-700" />}
          <div ref={messagesEndRef} />
        </CardContent>
        <form onSubmit={handleSend} className="flex gap-2 border-t border-navy-100 bg-white p-3 sm:p-4">
          <input value={question} onChange={(event) => setQuestion(event.target.value)} disabled={loading} placeholder="Escribe tu pregunta..." className="flex-1 rounded-xl border border-navy-200 px-4 py-2 outline-none focus:ring-2 focus:ring-cyan-400 disabled:cursor-not-allowed disabled:bg-navy-50 disabled:text-navy-400" />
          <Button type="submit" disabled={loading || !question.trim()}><Send className="h-4 w-4" /></Button>
        </form>
      </Card>
    </div>
  );
}
