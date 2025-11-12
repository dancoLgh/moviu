const incomes = [
  { professional: 'María Gómez', amount: 'PYG 1.200.000', concept: 'Clases grupales' },
  { professional: 'Juan López', amount: 'PYG 800.000', concept: 'Sesiones kine' }
];

const expenses = [
  { concept: 'Alquiler estudio', amount: 'PYG 1.000.000', shared: 'Equal (50/50)' },
  { concept: 'Luz y agua', amount: 'PYG 320.000', shared: 'Percent (60/40)' }
];

export default function FinancesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Finanzas</h2>
        <p className="text-sm text-slate-400">
          Registra ingresos privados por profesional y egresos compartidos con prorrateo automático.
        </p>
      </div>
      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-emerald-700/30 bg-emerald-500/5 p-4">
          <h3 className="text-sm font-semibold text-emerald-200">Ingresos</h3>
          <ul className="mt-3 space-y-2 text-sm text-emerald-100">
            {incomes.map((income) => (
              <li key={income.professional} className="flex justify-between">
                <span>{income.professional}</span>
                <span className="font-medium">{income.amount}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-rose-700/30 bg-rose-500/5 p-4">
          <h3 className="text-sm font-semibold text-rose-200">Egresos compartidos</h3>
          <ul className="mt-3 space-y-2 text-sm text-rose-100">
            {expenses.map((expense) => (
              <li key={expense.concept}>
                <div className="flex justify-between">
                  <span>{expense.concept}</span>
                  <span className="font-medium">{expense.amount}</span>
                </div>
                <p className="text-xs text-rose-200/70">{expense.shared}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
