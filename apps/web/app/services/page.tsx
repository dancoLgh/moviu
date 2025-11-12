const services = [
  {
    name: 'Pilates grupal',
    duration: '60 min',
    capacity: 8,
    price: 'PYG 80.000',
    notes: 'Buffer de 10 minutos antes y después.'
  },
  {
    name: 'Pilates individual',
    duration: '55 min',
    capacity: 1,
    price: 'PYG 180.000',
    notes: 'Sesión personalizada con evaluación de progreso.'
  },
  {
    name: 'Kinesiología individual',
    duration: '45 min',
    capacity: 1,
    price: 'PYG 160.000',
    notes: 'Incluye registro de ficha clínica digital.'
  }
];

export default function ServicesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Servicios</h2>
        <p className="text-sm text-slate-400">Define duración, buffers, políticas de cancelación y cupos.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {services.map((service) => (
          <div key={service.name} className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
            <h3 className="text-sm font-semibold text-slate-100">{service.name}</h3>
            <dl className="mt-2 space-y-1 text-xs text-slate-400">
              <div className="flex justify-between"><dt>Duración</dt><dd>{service.duration}</dd></div>
              <div className="flex justify-between"><dt>Cupo</dt><dd>{service.capacity}</dd></div>
              <div className="flex justify-between"><dt>Precio base</dt><dd>{service.price}</dd></div>
            </dl>
            <p className="mt-2 text-xs text-slate-500">{service.notes}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
