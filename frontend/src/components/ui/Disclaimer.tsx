import { AlertCircle } from 'lucide-react';
import { cn } from './Card';

export function Disclaimer({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-start p-4 bg-navy-50 border border-navy-200 rounded-lg text-sm text-navy-700", className)}>
      <AlertCircle className="w-5 h-5 text-navy-500 mr-3 flex-shrink-0 mt-0.5" />
      <div>
        <strong>Aviso Ético:</strong> Este sistema prioriza casos para revisión humana. La IA no acusa de fraude, no rechaza reclamos y no toma decisiones automáticas de pago. El score es puramente orientativo.
      </div>
    </div>
  );
}
