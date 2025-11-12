'use client';

import { useMemo } from 'react';
import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';
import { Card, CardBody, Chip, Progress } from '@heroui/react';

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
        const occupancy = Math.round((occ.booked / Math.max(occ.capacity, 1)) * 100);
        const start = parseISO(occ.start_ts);
        const end = parseISO(occ.end_ts);
        return {
          ...occ,
          occupancy,
          day: format(start, "EEEE d 'de' MMMM", { locale: es }),
          range: `${format(start, 'HH:mm')} · ${format(end, 'HH:mm')}`
        };
      });
  }, [occurrences]);

  if (!items.length) {
    return <p className="text-sm text-foreground/60">No hay clases programadas en la semana.</p>;
  }

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const isFull = item.booked >= item.capacity;
        const statusLabel =
          item.status === 'cancelled' ? 'Cancelada' : isFull ? 'Cupo completo' : `${item.occupancy}% ocupado`;
        const progressColor = item.status === 'cancelled' ? 'danger' : isFull ? 'warning' : 'success';

        return (
          <Card key={item.id} shadow="sm" className="border border-divider bg-content1">
            <CardBody className="flex flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div>
                <p className="text-sm font-semibold capitalize">{item.day}</p>
                <p className="text-xs text-foreground/60">
                  {item.range} · {item.professional}
                </p>
              </div>
              <div className="flex w-full flex-col gap-2 sm:w-auto sm:min-w-[220px]">
                <div className="flex items-center justify-between text-xs text-foreground/60">
                  <span>Cupo reservado</span>
                  <span>
                    {item.booked}/{item.capacity}
                  </span>
                </div>
                <Progress
                  value={Math.min(item.occupancy, 100)}
                  color={progressColor}
                  aria-label={`Ocupación ${item.occupancy}%`}
                />
                <div className="flex items-center gap-2">
                  <Chip size="sm" color={progressColor} variant="flat" className="capitalize">
                    {statusLabel}
                  </Chip>
                </div>
              </div>
            </CardBody>
          </Card>
        );
      })}
    </div>
  );
}
