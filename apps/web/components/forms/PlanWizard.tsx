'use client';

import { useEffect, useMemo, useState } from 'react';
import { addDays, format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';
import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  Chip,
  Divider,
  Input,
  Select,
  SelectItem
} from '@heroui/react';

const weekdays = [
  { value: 1, label: 'Lunes' },
  { value: 2, label: 'Martes' },
  { value: 3, label: 'Miércoles' },
  { value: 4, label: 'Jueves' },
  { value: 5, label: 'Viernes' },
  { value: 6, label: 'Sábado' }
];

type WizardState = {
  startDate: string;
  baseWeekday: number;
  hour: string;
  duplicates: number[];
};

export function PlanWizard() {
  const [state, setState] = useState<WizardState>({
    startDate: '',
    baseWeekday: 1,
    hour: '15:00',
    duplicates: []
  });
  const [preview, setPreview] = useState<string[]>([]);

  useEffect(() => {
    const today = new Date();
    setState((prev) => ({ ...prev, startDate: format(today, 'yyyy-MM-dd') }));
  }, []);

  const baseWeekdayKey = useMemo(() => new Set([String(state.baseWeekday)]), [state.baseWeekday]);

  function toggleDuplicate(day: number) {
    setState((prev) => {
      const exists = prev.duplicates.includes(day);
      return {
        ...prev,
        duplicates: exists ? prev.duplicates.filter((d) => d !== day) : [...prev.duplicates, day]
      };
    });
  }

  function buildPreview() {
    if (!state.startDate) return;
    const origin = parseISO(state.startDate);
    const slots: string[] = [];
    const selectedDays = [state.baseWeekday, ...state.duplicates]
      .filter((value, index, array) => array.indexOf(value) === index)
      .sort();

    for (let i = 0; i < 4; i += 1) {
      selectedDays.forEach((weekday) => {
        const current = addDays(origin, ((weekday + 7 - origin.getDay()) % 7) + i * 7);
        slots.push(`${format(current, "EEEE d 'de' MMMM", { locale: es })} · ${state.hour}`);
      });
    }
    setPreview(slots);
  }

  return (
    <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
      <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
        <h3 className="text-lg font-semibold">Plan recurrente con duplicar días</h3>
        <p className="text-sm text-foreground/70">
          Define el día base, horarios y días duplicados antes de generar la agenda recurrente.
        </p>
      </CardHeader>
      <Divider />
      <CardBody className="flex flex-col gap-5 px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Select
            label="Día base"
            variant="bordered"
            size="sm"
            selectedKeys={baseWeekdayKey}
            onSelectionChange={(selection) => {
              if (selection === 'all') return;
              const [value] = Array.from(selection);
              if (!value) return;
              const numeric = Number(value);
              setState((prev) => ({
                ...prev,
                baseWeekday: numeric,
                duplicates: prev.duplicates.filter((day) => day !== numeric)
              }));
            }}
          >
            {weekdays.map((day) => (
              <SelectItem key={day.value} textValue={day.label}>
                {day.label}
              </SelectItem>
            ))}
          </Select>
          <Input
            type="time"
            label="Hora"
            size="sm"
            variant="bordered"
            value={state.hour}
            onChange={(event) => setState((prev) => ({ ...prev, hour: event.target.value }))}
          />
          <Input
            type="date"
            label="Fecha de inicio"
            size="sm"
            variant="bordered"
            value={state.startDate}
            onChange={(event) => setState((prev) => ({ ...prev, startDate: event.target.value }))}
          />
        </div>
        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium">Duplicar horario a</p>
          <div className="flex flex-wrap gap-2">
            {weekdays
              .filter((day) => day.value !== state.baseWeekday)
              .map((day) => {
                const active = state.duplicates.includes(day.value);
                return (
                  <Chip
                    key={day.value}
                    variant={active ? 'solid' : 'bordered'}
                    color={active ? 'primary' : 'default'}
                    radius="full"
                    onPress={() => toggleDuplicate(day.value)}
                  >
                    {day.label}
                  </Chip>
                );
              })}
          </div>
        </div>
        <Card className="bg-content2/60" radius="lg" shadow="none">
          <CardBody className="gap-2 text-xs text-foreground/70">
            <p className="font-medium text-sm text-foreground">Detalles operativos</p>
            <p>Los duplicados respetan buffers configurados en el servicio y validan cupo antes de confirmarse.</p>
            <p>El asistente puede ajustar manualmente conflictos de sala o profesional durante la revisión.</p>
          </CardBody>
        </Card>
      </CardBody>
      <Divider />
      <CardFooter className="flex flex-col gap-4 px-4 pb-4 pt-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <Button color="primary" radius="md" onPress={buildPreview} className="w-full sm:w-auto">
          Generar ocurrencias
        </Button>
        <p className="text-xs text-foreground/60">
          Genera un borrador de cuatro semanas para confirmar antes de publicar en la agenda.
        </p>
      </CardFooter>
      {preview.length > 0 && (
        <>
          <Divider />
          <CardBody className="px-4 pb-6 pt-4 sm:px-6">
            <p className="text-sm font-semibold">Ocurrencias sugeridas</p>
            <ul className="mt-3 space-y-2 text-sm text-foreground/80">
              {preview.map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-primary" aria-hidden />
                  {item}
                </li>
              ))}
            </ul>
          </CardBody>
        </>
      )}
    </Card>
  );
}
