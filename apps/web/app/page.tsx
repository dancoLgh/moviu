import Link from 'next/link';
import {
  Avatar,
  AvatarGroup,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  Chip,
  Divider,
  Progress
} from '@heroui/react';
import { navigationItems } from '@/components/layout/navigation';

const stats = [
  { label: 'Clases hoy', value: '6', trend: '+2', tone: 'success' as const },
  { label: 'Capacidad ocupada', value: '75%', trend: '-5%', tone: 'warning' as const },
  { label: 'Ingresos semanal', value: 'PYG 2.1M', trend: '+8%', tone: 'success' as const },
  { label: 'Recuperos disponibles', value: '9', trend: 'restan 5 días', tone: 'primary' as const }
];

const agendaPreview = [
  { label: 'Pilates grupal', slot: 'Hoy · 15:00', occupancy: 80 },
  { label: 'Pilates individual', slot: 'Hoy · 18:00', occupancy: 40 },
  { label: 'Kinesiología', slot: 'Mañana · 10:30', occupancy: 100 }
];

const clinicalFocus = [
  { member: 'Ana Torres', action: 'Reevaluación de postura', due: 'Miércoles 17:00' },
  { member: 'Pedro Díaz', action: 'Adjuntar estudio lumbar', due: 'Viernes 09:00' }
];

const financeQuick = [
  { label: 'Ingresos privados', amount: 'PYG 4.500.000', note: 'Últimos 30 días' },
  { label: 'Egresos compartidos', amount: 'PYG 1.200.000', note: 'Prorrateo de alquiler' }
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 rounded-2xl border border-primary/10 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent px-4 py-6 sm:px-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Panel del estudio</h1>
            <p className="text-sm text-foreground/70">
              Supervisa agenda, suscripciones y salud financiera con una vista móvil primero.
            </p>
          </div>
          <Button as={Link} href="/plans" color="primary" size="sm" radius="md">
            Crear nueva suscripción
          </Button>
        </div>
        <div className="flex items-center gap-3 text-xs text-foreground/60">
          <AvatarGroup size="sm" max={3} total={12} renderCount={(count) => `+${count}`}>
            <Avatar name="María" color="primary" />
            <Avatar name="Juan" color="secondary" />
            <Avatar name="Ana" color="success" />
          </AvatarGroup>
          <span>Profesionales activos hoy</span>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => (
          <Card key={item.label} radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardBody className="gap-1 px-4 py-4">
              <span className="text-xs uppercase tracking-wide text-foreground/50">{item.label}</span>
              <span className="text-2xl font-semibold text-foreground">{item.value}</span>
              <Chip size="sm" color={item.tone} variant="flat" className="self-start text-[11px]">
                {item.trend}
              </Chip>
            </CardBody>
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="border border-divider bg-content1 lg:col-span-7" radius="lg" shadow="sm">
          <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
            <h2 className="text-lg font-semibold">Agenda inmediata</h2>
            <p className="text-sm text-foreground/60">Capacidad y buffers vigilados en los próximos turnos.</p>
          </CardHeader>
          <Divider />
          <CardBody className="space-y-4 px-4 py-4 sm:px-6">
            {agendaPreview.map((item) => (
              <div key={item.label} className="flex flex-col gap-2 rounded-xl border border-divider/80 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold">{item.label}</p>
                    <p className="text-xs text-foreground/60">{item.slot}</p>
                  </div>
                  <Chip size="sm" color={item.occupancy >= 100 ? 'danger' : item.occupancy >= 80 ? 'warning' : 'success'}>
                    {item.occupancy}%
                  </Chip>
                </div>
                <Progress value={item.occupancy} aria-label={`Ocupación ${item.label}`} color="primary" />
              </div>
            ))}
          </CardBody>
          <CardFooter className="flex flex-col gap-2 px-4 pb-4 pt-0 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <Button as={Link} href="/calendar" size="sm" color="primary" variant="flat">
              Abrir agenda completa
            </Button>
            <p className="text-xs text-foreground/60">Validamos buffers y cupos antes de confirmar recuperos.</p>
          </CardFooter>
        </Card>

        <div className="flex flex-col gap-4 lg:col-span-5">
          <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
              <h3 className="text-base font-semibold">Clínica y evolución</h3>
              <p className="text-sm text-foreground/60">Tareas pendientes para Kinesiología y Pilates.</p>
            </CardHeader>
            <Divider />
            <CardBody className="space-y-3 px-4 py-4 sm:px-6">
              {clinicalFocus.map((item) => (
                <div key={item.member} className="rounded-xl border border-divider/80 bg-content2/60 p-4">
                  <p className="text-sm font-semibold text-foreground">{item.member}</p>
                  <p className="text-xs text-foreground/60">{item.action}</p>
                  <Chip size="sm" variant="flat" color="secondary" className="mt-2">
                    {item.due}
                  </Chip>
                </div>
              ))}
            </CardBody>
          </Card>

          <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
              <h3 className="text-base font-semibold">Finanzas exprés</h3>
              <p className="text-sm text-foreground/60">Seguimiento rápido del flujo de caja del estudio.</p>
            </CardHeader>
            <Divider />
            <CardBody className="space-y-3 px-4 py-4 sm:px-6">
              {financeQuick.map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-xl border border-divider/80 px-4 py-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-sm font-semibold">{item.label}</span>
                    <span className="text-xs text-foreground/60">{item.note}</span>
                  </div>
                  <span className="text-sm font-semibold text-foreground">{item.amount}</span>
                </div>
              ))}
            </CardBody>
          </Card>
        </div>
      </section>

      <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
        <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <h3 className="text-base font-semibold">Atajos operativos</h3>
            <p className="text-sm text-foreground/60">Accesos rápidos a los módulos críticos del día a día.</p>
          </div>
          <Chip size="sm" variant="flat" color="primary">
            Optimizado para mobile
          </Chip>
        </CardHeader>
        <Divider />
        <CardBody className="grid grid-cols-1 gap-3 px-4 py-4 sm:grid-cols-2 lg:grid-cols-3 sm:px-6">
          {navigationItems.slice(0, 6).map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.href} as="article" radius="lg" shadow="none" className="border border-divider bg-content2">
                <CardBody className="gap-2">
                  <Icon className="h-5 w-5 text-primary" />
                  <div className="flex flex-col gap-1">
                    <h4 className="text-sm font-semibold">{item.label}</h4>
                    <p className="text-xs text-foreground/60">{item.description}</p>
                  </div>
                  <Button as={Link} href={item.href} color="primary" variant="light" size="sm" className="self-start">
                    Abrir
                  </Button>
                </CardBody>
              </Card>
            );
          })}
        </CardBody>
      </Card>
    </div>
  );
}
