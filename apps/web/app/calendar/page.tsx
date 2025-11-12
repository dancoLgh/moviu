import { CapacityCalendar } from '@/components/calendar/CapacityCalendar';
import { Button, Card, CardBody, CardHeader, Divider } from '@heroui/react';

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
  }
];

export default function CalendarPage() {
  return (
    <div className="space-y-6">
      <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
        <CardHeader className="flex flex-col gap-3 px-4 pt-4 sm:flex-row sm:items-start sm:justify-between sm:px-6">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-semibold">Agenda semanal</h2>
            <p className="text-sm text-foreground/60">
              Visualiza cupos, buffers y cancelaciones para coordinar clases y recuperos.
            </p>
          </div>
          <Button as="a" href="/app/api/suggest-slots" color="primary" variant="flat" size="sm">
            Sugerir recuperos
          </Button>
        </CardHeader>
        <Divider />
        <CardBody className="px-4 py-4 sm:px-6">
          <CapacityCalendar occurrences={demoOccurrences} />
        </CardBody>
      </Card>
    </div>
  );
}
