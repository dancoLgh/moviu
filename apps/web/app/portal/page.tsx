const upcoming = [
  { service: 'Pilates grupal', date: 'Lunes 15:00', status: 'Programada' },
  { service: 'Pilates grupal', date: 'Miércoles 15:00', status: 'Recupero disponible' }
];

export default function PortalPage() {
  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold">Mi portal</h2>
        <p className="text-sm text-slate-400">
          Gestiona tus clases, cancela o recupera según la política del plan vigente.
        </p>
      </header>
      <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
        <h3 className="text-sm font-semibold text-slate-200">Mi plan</h3>
        <p className="text-xs text-slate-400">Máximo 3×/semana · Vigente hasta 30/11 · Recuperos restantes: 1</p>
      </section>
      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-200">Próximas clases</h3>
        {upcoming.map((item) => (
          <div
            key={item.date}
            className="flex flex-col gap-2 rounded-lg border border-slate-800 bg-slate-950/60 p-4 md:flex-row md:items-center md:justify-between"
          >
            <div>
              <p className="text-sm font-medium text-slate-100">{item.service}</p>
              <p className="text-xs text-slate-400">{item.date}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-emerald-400">{item.status}</span>
              <button className="rounded-md border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-brand">
                Cancelar
              </button>
              <button className="rounded-md bg-brand/80 px-3 py-1 text-xs font-semibold text-brand-foreground hover:bg-brand">
                Recuperar
              </button>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
