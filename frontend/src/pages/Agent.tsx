import React, { useState } from 'react';
import { api } from '../lib/api';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Loader2, BotMessageSquare, Send } from 'lucide-react';

export function Agent() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<{role: 'user'|'agent', content: string}[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    const newMsgs = [...messages, { role: 'user' as const, content: question }];
    setMessages(newMsgs);
    setQuestion('');
    setLoading(true);

    try {
      const res = await api.post('/agent/question', { question, id_siniestro: null, scope: 'global' });
      setMessages([...newMsgs, { role: 'agent', content: res.data.answer }]);
    } catch (err) {
      setMessages([...newMsgs, { role: 'agent', content: 'Lo siento, ocurrió un error de conexión.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-12rem)] flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-navy-900">Agente IA</h1>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardContent className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-navy-400 mt-10">
              <BotMessageSquare className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>Hola, soy tu asistente IA de fraude. ¿En qué te puedo ayudar hoy?</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl p-4 flex gap-3 ${msg.role === 'user' ? 'bg-cyan-600 text-white rounded-br-none' : 'bg-navy-50 text-navy-900 border border-navy-100 rounded-bl-none'}`}>
                 {msg.role === 'agent' && <BotMessageSquare className="w-5 h-5 mt-1 flex-shrink-0 text-cyan-600" />}
                 <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
              </div>
            </div>
          ))}
          {loading && (
             <div className="flex justify-start">
               <div className="bg-navy-50 text-navy-900 border border-navy-100 rounded-2xl rounded-bl-none p-4 flex gap-3 items-center">
                 <BotMessageSquare className="w-5 h-5 text-cyan-600" />
                 <Loader2 className="w-4 h-4 animate-spin" />
               </div>
             </div>
          )}
        </CardContent>
        <div className="p-4 bg-white border-t border-navy-100">
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Escribe tu pregunta (ej: top riesgos, resumen ejecutivo)..."
              className="flex-1 border border-navy-300 rounded-lg px-4 py-2 focus:ring-cyan-500 focus:border-cyan-500"
            />
            <Button type="submit" disabled={loading || !question.trim()}>
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
