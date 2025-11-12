import Link from 'next/link';
import { Button, Card, CardBody, CardHeader, Divider } from '@heroui/react';

export default function DashboardPage() {
  const summary = [
    { label: 'Clases hoy', value: '6' },
    { label: 'Cupo ocupado', value: '75%' },
    { label: 'Ingresos semana', value: 'PYG 2.100.000' },
    { label: 'Recuperos pendientes', value: '4' }
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold">Panel general</h2>
        <p className="text-sm text-foreground/60">
          Una vista compacta de agenda, finanzas y salud de las suscripciones del estudio.
        </p>
      </div>
      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {summary.map((item) => (
          <Card key={item.label} radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardBody className="gap-1 px-4 py-5 sm:px-5">
              <span className="text-xs font-medium uppercase tracking-wide text-foreground/50">{item.label}</span>
              <span className="text-2xl font-semibold text-foreground">{item.value}</span>
            </CardBody>
          </Card>
        ))}
      </section>
      <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
        <CardHeader className="flex flex-col items-start gap-1 px-4 pt-4 sm:px-6">
          <h3 className="text-lg font-semibold">Accesos rápidos</h3>
          <p className="text-sm text-foreground/60">Acciones frecuentes para mantener agenda y finanzas al día.</p>
        </CardHeader>
        <Divider />
        <CardBody className="grid grid-cols-1 gap-3 px-4 py-4 sm:grid-cols-2 lg:grid-cols-3 sm:px-6">
          <QuickLink href="/plans" title="Crear plan" description="Configura reglas de duplicado y recuperos." />
          <QuickLink href="/calendar" title="Ver agenda" description="Monitorea cupos, buffers y cancelaciones." />
          <QuickLink href="/finances" title="Registrar ingreso" description="Carga cobros privados y egresos compartidos." />
        </CardBody>
      </Card>
    </div>
  );
}

function QuickLink({ href, title, description }: { href: string; title: string; description: string }) {
  return (
    <Card as="article" radius="lg" shadow="none" className="border border-divider bg-content2">
      <CardBody className="gap-2">
        <div className="flex flex-col gap-1">
          <h4 className="text-sm font-semibold">{title}</h4>
          <p className="text-xs text-foreground/60">{description}</p>
        </div>
        <Button
          as={Link}
          href={href}
          color="primary"
          variant="light"
          size="sm"
          className="self-start"
        >
          Abrir
        </Button>
      </CardBody>
    </Card>
  );
}
