import Link from 'next/link';

export default function DashboardPage() {
  const summary = [
    { label: 'Clases hoy', value: 6 },
    { label: 'Cupo ocupado', value: '75%' },
    { label: 'Ingresos semana', value: 'PYG 2.100.000' },
    { label: 'Recuperos pendientes', value: 4 }
  ];
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Dashboard</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {summary.map((item) => (
          <div key={item.label} className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
            <p className="text-sm text-slate-400">{item.label}</p>
            <p className="text-2xl font-semibold text-slate-100">{item.value}</p>
          </div>
        ))}
      </div>
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6">
        <h3 className="text-lg font-semibold text-slate-100">Accesos rápidos</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <QuickLink href="/plans" title="Crear plan" description="Configura suscripciones con duplicar días" />
          <QuickLink href="/calendar" title="Ver agenda" description="Controla cupos y cancelaciones" />
          <QuickLink href="/finances" title="Registrar ingreso" description="Actualiza el flujo financiero" />
        </div>
      </div>
    </div>
  );
}

function QuickLink({ href, title, description }: { href: string; title: string; description: string }) {
  return (
    <Link href={href} className="block rounded-lg border border-slate-800 bg-slate-950/60 p-4 hover:border-brand">
      <p className="text-sm font-medium text-slate-100">{title}</p>
      <p className="text-xs text-slate-400">{description}</p>
    </Link>
  );
}
