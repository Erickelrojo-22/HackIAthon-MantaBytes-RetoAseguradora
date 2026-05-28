import type { FormEvent } from 'react';
import { useState } from 'react';
import { BotMessageSquare, Loader2, Send } from 'lucide-react';
import { api } from '../lib/api';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';

const suggestions = [
  'Cuales son los 10 siniestros con mayor riesgo?',
  'Que proveedores concentran mas alertas rojas?',
  'Genera un resumen ejecutivo de los casos criticos.',
  'Que documentos faltan en los casos criticos?',
];

export function Agent() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<{ role: 'user' | 'agent'; content: string; source?: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const ask = async (text: string) => {
    if (!text.trim()) return;
    const next = [...messages, { role: 'user' as const, content: text }];
    setMessages(next);
    setQuestion('');
    setLoading(true);
    try {
      const response = await api.post('/agent/question', { question: text, scope: 'global' });
      setMessages([...next, { role: 'agent', content: response.data.answer, source: response.data.source }]);
    } catch {
      setMessages([...next, { role: 'agent', content: 'No pude conectar con el agente. Verifica que FastAPI este activo.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = (event: FormEvent) => {
    event.preventDefault();
    ask(question);
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-5xl flex-col space-y-5">
      <div>
        <h1 className="text-3xl font-black text-navy-950">Agente IA</h1>
        <p className="text-sm text-navy-500">Responde con herramientas locales y fallback offline si OpenAI no esta configurado.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {suggestions.map((item) => <button key={item} onClick={() => ask(item)} className="rounded-full border border-navy-200 bg-white px-3 py-1.5 text-xs font-semibold text-navy-700 transition hover:bg-cyan-50">{item}</button>)}
      </div>

      <Card className="flex min-h-0 flex-1 flex-col">
        <CardContent className="min-h-0 flex-1 space-y-4 overflow-y-auto p-6">
          {messages.length === 0 && (
            <div className="grid h-full place-items-center text-center text-navy-400">
              <div><BotMessageSquare className="mx-auto mb-4 h-16 w-16 opacity-50" /><p>Haz una pregunta ejecutiva sobre riesgo, proveedores, documentos o un caso SINxxxxx.</p></div>
            </div>
          )}
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[82%] rounded-3xl p-4 text-sm ${message.role === 'user' ? 'rounded-br-sm bg-cyan-700 text-white' : 'rounded-bl-sm border border-navy-100 bg-navy-50 text-navy-900'}`}>
                <div className="whitespace-pre-wrap">{message.content}</div>
                {message.source && <p className="mt-3 text-xs font-semibold text-cyan-700">Fuente: {message.source}</p>}
              </div>
            </div>
          ))}
          {loading && <Loader2 className="h-5 w-5 animate-spin text-cyan-700" />}
        </CardContent>
        <form onSubmit={handleSend} className="flex gap-2 border-t border-navy-100 bg-white p-4">
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Escribe tu pregunta..." className="flex-1 rounded-xl border border-navy-200 px-4 py-2 outline-none focus:ring-2 focus:ring-cyan-400" />
          <Button type="submit" disabled={loading || !question.trim()}><Send className="h-4 w-4" /></Button>
        </form>
      </Card>
    </div>
  );
}
