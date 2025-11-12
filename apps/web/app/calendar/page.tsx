import { CapacityCalendar } from '@/components/calendar/CapacityCalendar';

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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Agenda semanal</h2>
          <p className="text-sm text-slate-400">
            Visualiza la ocupación por clase con control de cupos y cancelaciones.
          </p>
        </div>
        <a
          href="/app/api/suggest-slots"
          className="rounded-md border border-brand/40 px-3 py-1.5 text-sm text-brand hover:bg-brand/10"
        >
          Sugerir recuperos
        </a>
      </div>
      <CapacityCalendar occurrences={demoOccurrences} />
    </div>
  );
}
