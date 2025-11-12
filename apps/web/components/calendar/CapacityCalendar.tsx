'use client';

import { useMemo } from 'react';
import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';

type Occurrence = {
  id: string;
  start_ts: string;
  end_ts: string;
  professional: string;
  capacity: number;
  booked: number;
  status: 'scheduled' | 'cancelled' | 'completed';
};

type Props = {
  occurrences: Occurrence[];
};

export function CapacityCalendar({ occurrences }: Props) {
  const items = useMemo(() => {
    return occurrences
      .slice()
      .sort((a, b) => new Date(a.start_ts).getTime() - new Date(b.start_ts).getTime())
      .map((occ) => {
        const occupancy = Math.round((occ.booked / occ.capacity) * 100);
        const start = parseISO(occ.start_ts);
        const end = parseISO(occ.end_ts);
        return {
          ...occ,
          occupancy,
          day: format(start, 'EEEE d', { locale: es }),
          range: `${format(start, 'HH:mm')} - ${format(end, 'HH:mm')}`
        };
      });
  }, [occurrences]);

  if (!items.length) {
    return <p className="text-sm text-slate-400">No hay clases programadas en la semana.</p>;
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div
          key={item.id}
          className="flex flex-col gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-4 md:flex-row md:items-center md:justify-between"
        >
          <div>
            <p className="text-sm font-semibold text-slate-100">{item.day}</p>
            <p className="text-xs text-slate-400">
              {item.range} · {item.professional}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wide text-slate-400">Cupo</span>
            <div className="h-2 w-32 rounded-full bg-slate-800">
              <div
                className={`h-2 rounded-full ${item.occupancy >= 100 ? 'bg-rose-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.min(item.occupancy, 100)}%` }}
              />
            </div>
            <span className="text-sm font-medium text-slate-100">
              {item.booked}/{item.capacity}
            </span>
            <span className="text-xs text-slate-400">{item.status === 'cancelled' ? 'Cancelada' : `${item.occupancy}%`}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
