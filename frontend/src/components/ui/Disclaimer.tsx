import { AlertCircle } from 'lucide-react';
import { cn } from '../../lib/cn';

export function Disclaimer({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-start rounded-xl border border-cyan-200 bg-cyan-50/80 p-4 text-sm text-navy-700', className)}>
      <AlertCircle className="mr-3 mt-0.5 h-5 w-5 flex-shrink-0 text-cyan-700" />
      <div>
        <strong>Aviso etico:</strong> FraudIA Claims prioriza casos para revision humana. La IA no acusa fraude, no rechaza reclamos y no toma decisiones automaticas de pago.
      </div>
    </div>
  );
}
