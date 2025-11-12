import Link from 'next/link';
import { CapacityCalendar } from '@/components/calendar/CapacityCalendar';
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Chip,
  Divider,
  Select,
  SelectItem,
  Tab,
  Tabs
} from '@heroui/react';
import { CalendarClock, CalendarPlus } from 'lucide-react';

const demoOccurrences = [
  {
    id: 'occ-1',
    start_ts: new Date().toISOString(),
    end_ts: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    professional: 'María Gómez',
    capacity: 8,
    booked: 6,
    status: 'scheduled' as const
  },
  {
    id: 'occ-2',
    start_ts: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
    end_ts: new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString(),
    professional: 'Juan López',
    capacity: 6,
    booked: 6,
    status: 'scheduled' as const
  },
  {
    id: 'occ-3',
    start_ts: new Date(Date.now() + 26 * 60 * 60 * 1000).toISOString(),
    end_ts: new Date(Date.now() + 27 * 60 * 60 * 1000).toISOString(),
    professional: 'María Gómez',
    capacity: 8,
    booked: 4,
    status: 'scheduled' as const
  }
];

const professionals = [
  { key: 'all', label: 'Todos los profesionales' },
  { key: 'maria', label: 'María Gómez' },
  { key: 'juan', label: 'Juan López' }
];

export default function CalendarPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Agenda y cupos</h1>
        <p className="text-sm text-foreground/60">
          Controla buffers, cancelaciones y recuperos sugeridos con una vista optimizada para móviles.
        </p>
      </header>

      <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
        <CardHeader className="flex flex-col gap-4 px-4 pt-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex flex-col gap-1">
            <h2 className="text-lg font-semibold">Semana en curso</h2>
            <p className="text-xs text-foreground/60">Los buffers del servicio se validan antes de publicar cada slot.</p>
          </div>
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <Select
              label="Profesional"
              selectedKeys={new Set(['all'])}
              size="sm"
              variant="bordered"
            >
              {professionals.map((item) => (
                <SelectItem key={item.key}>{item.label}</SelectItem>
              ))}
            </Select>
            <Button
              color="primary"
              variant="flat"
              size="sm"
              startContent={<CalendarPlus className="h-4 w-4" />}
            >
              Nuevo slot manual
            </Button>
          </div>
        </CardHeader>
        <Divider />
        <CardBody className="px-4 py-4 sm:px-6">
          <Tabs aria-label="Vistas de agenda" variant="underlined" color="primary">
            <Tab
              key="timeline"
              title={
                <div className="flex items-center gap-2 text-sm">
                  <CalendarClock className="h-4 w-4" />
                  Agenda
                </div>
              }
            >
              <CapacityCalendar occurrences={demoOccurrences} />
            </Tab>
            <Tab
              key="makeups"
              title={
                <div className="flex items-center gap-2 text-sm">
                  <Chip size="sm" color="warning" variant="flat">
                    Recuperos sugeridos
                  </Chip>
                </div>
              }
            >
              <div className="space-y-3 text-sm text-foreground/70">
                <p>
                  Filtramos automáticamente slots con cupo disponible respetando el horario del plan y la política de
                  recuperos. Al confirmar desde el portal del alumno se actualiza el contador mensual.
                </p>
                <Button
                  as={Link}
                  href="/app/api/suggest-slots"
                  variant="bordered"
                  size="sm"
                >
                  Llamar función de sugerencias
                </Button>
              </div>
            </Tab>
          </Tabs>
        </CardBody>
      </Card>
    </div>
  );
}
