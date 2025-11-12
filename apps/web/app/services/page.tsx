import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  Chip,
  Divider,
  Tab,
  Tabs
} from '@heroui/react';
import { ClipboardPlus } from 'lucide-react';

const services = {
  pilates: [
    {
      name: 'Pilates grupal',
      duration: '60 min',
      capacity: 8,
      price: 'PYG 80.000',
      notes: 'Buffer de 10 minutos antes y después.',
      policy: 'Cancelación 6h · 1 recupero/mes'
    },
    {
      name: 'Pilates individual',
      duration: '55 min',
      capacity: 1,
      price: 'PYG 180.000',
      notes: 'Sesión personalizada con seguimiento fotográfico.',
      policy: 'Cancelación 12h · recupero manual'
    }
  ],
  kine: [
    {
      name: 'Kinesiología individual',
      duration: '45 min',
      capacity: 1,
      price: 'PYG 160.000',
      notes: 'Incluye ficha clínica digital y plan de tratamiento.',
      policy: 'Cancelación 24h · reagenda por profesional'
    }
  ]
};

export default function ServicesPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 rounded-2xl border border-divider bg-content1/80 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div>
          <h1 className="text-2xl font-semibold">Servicios y políticas</h1>
          <p className="text-sm text-foreground/60">
            Configura duración, buffers, políticas de cancelación y cupos disponibles para cada modalidad.
          </p>
        </div>
        <Button color="primary" startContent={<ClipboardPlus className="h-4 w-4" />} size="sm">
          Nuevo servicio
        </Button>
      </header>

      <Tabs aria-label="Tipo de servicio" color="primary" variant="solid" classNames={{ tabList: 'gap-2' }}>
        <Tab key="pilates" title="Pilates">
          <ServiceGrid services={services.pilates} />
        </Tab>
        <Tab key="kine" title="Kinesiología">
          <ServiceGrid services={services.kine} />
        </Tab>
      </Tabs>
    </div>
  );
}

type Service = {
  name: string;
  duration: string;
  capacity: number;
  price: string;
  notes: string;
  policy: string;
};

function ServiceGrid({ services }: { services: Service[] }) {
  return (
    <section className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {services.map((service) => (
        <Card key={service.name} radius="lg" shadow="sm" className="border border-divider bg-content1">
          <CardHeader className="flex flex-col gap-3 px-4 pt-4 sm:px-6">
            <div className="flex items-start justify-between gap-3">
              <div className="flex flex-col gap-1">
                <h3 className="text-lg font-semibold">{service.name}</h3>
                <Badge color="primary" variant="flat" className="w-max text-[11px] uppercase">
                  {service.policy}
                </Badge>
              </div>
              <Chip size="sm" color="primary" variant="flat">
                {service.capacity} cupo{service.capacity === 1 ? '' : 's'}
              </Chip>
            </div>
            <p className="text-xs text-foreground/60">{service.notes}</p>
          </CardHeader>
          <Divider />
          <CardBody className="gap-3 px-4 py-5 text-sm text-foreground/70 sm:px-6">
            <InfoRow label="Duración" value={service.duration} />
            <InfoRow label="Precio base" value={service.price} />
            <InfoRow label="Buffer operativo" value="10 min antes / después" />
          </CardBody>
        </Card>
      ))}
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-xs uppercase tracking-wide text-foreground/50">
      <span>{label}</span>
      <span className="text-foreground">{value}</span>
    </div>
  );
}
