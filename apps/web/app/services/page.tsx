import { Card, CardBody, CardHeader, Chip, Divider } from '@heroui/react';

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
      <header className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold">Servicios</h2>
        <p className="text-sm text-foreground/60">
          Define duración, buffers, políticas de cancelación y cupos disponibles para cada servicio.
        </p>
      </header>
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {services.map((service) => (
          <Card key={service.name} radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="flex flex-col gap-3 px-4 pt-4 sm:px-6">
              <div className="flex items-start justify-between">
                <h3 className="text-lg font-semibold">{service.name}</h3>
                <Chip size="sm" color="primary" variant="flat">
                  {service.capacity} cupo{service.capacity === 1 ? '' : 's'}
                </Chip>
              </div>
              <p className="text-xs text-foreground/60">{service.notes}</p>
            </CardHeader>
            <Divider />
            <CardBody className="gap-2 px-4 py-5 text-sm text-foreground/70 sm:px-6">
              <div className="flex items-center justify-between text-xs uppercase tracking-wide text-foreground/50">
                <span>Duración</span>
                <span className="text-foreground">{service.duration}</span>
              </div>
              <div className="flex items-center justify-between text-xs uppercase tracking-wide text-foreground/50">
                <span>Precio base</span>
                <span className="text-foreground">{service.price}</span>
              </div>
            </CardBody>
          </Card>
        ))}
      </section>
    </div>
  );
}
