import { PlanWizard } from '@/components/forms/PlanWizard';

const demoPlans = [
  { name: 'Básico 1×/semana', price: 'PYG 100.000', times: '1 clase', makeups: '1 recupero/mes' },
  { name: 'Máximo 3×/semana', price: 'PYG 350.000', times: '3 clases', makeups: '1 recupero/mes' }
];

export default function PlansPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Planes</h2>
        <p className="text-sm text-slate-400">
          Configura las reglas de suscripción, recuperos y duplicación de días por servicio.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {demoPlans.map((plan) => (
          <div key={plan.name} className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
            <p className="text-sm font-semibold text-slate-100">{plan.name}</p>
            <p className="text-xs text-slate-400">{plan.times}</p>
            <p className="mt-2 text-lg font-semibold text-brand">{plan.price}</p>
            <p className="text-xs text-slate-400">{plan.makeups}</p>
          </div>
        ))}
      </div>
      <PlanWizard />
    </div>
  );
}
