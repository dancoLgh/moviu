'use client';

import { useEffect, useState } from 'react';
import { addDays, format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';

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
    const selectedDays = [state.baseWeekday, ...state.duplicates].sort();
    for (let i = 0; i < 4; i += 1) {
      selectedDays.forEach((weekday) => {
        const current = addDays(origin, ((weekday + 7 - origin.getDay()) % 7) + i * 7);
        slots.push(`${format(current, "EEEE d MMMM", { locale: es })} · ${state.hour}`);
      });
    }
    setPreview(slots);
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
      <h3 className="text-lg font-semibold text-slate-100">Plan recurrente con duplicar días</h3>
      <p className="mt-1 text-sm text-slate-400">
        Selecciona el día base y duplica rápidamente el horario a otros días disponibles.
      </p>
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <label className="flex flex-col gap-2 text-sm">
          Día base
          <select
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            value={state.baseWeekday}
            onChange={(event) => setState((prev) => ({ ...prev, baseWeekday: Number(event.target.value) }))}
          >
            {weekdays.map((day) => (
              <option key={day.value} value={day.value}>
                {day.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-2 text-sm">
          Hora
          <input
            type="time"
            value={state.hour}
            onChange={(event) => setState((prev) => ({ ...prev, hour: event.target.value }))}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-2 text-sm">
          Fecha de inicio
          <input
            type="date"
            value={state.startDate}
            onChange={(event) => setState((prev) => ({ ...prev, startDate: event.target.value }))}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
          />
        </label>
      </div>
      <div className="mt-6 rounded-lg border border-slate-800 bg-slate-950/60 p-4">
        <p className="text-sm font-medium text-slate-200">Duplicar a</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {weekdays
            .filter((day) => day.value !== state.baseWeekday)
            .map((day) => {
              const active = state.duplicates.includes(day.value);
              return (
                <button
                  key={day.value}
                  type="button"
                  onClick={() => toggleDuplicate(day.value)}
                  className={`rounded-full border px-4 py-1 text-xs font-medium transition ${
                    active ? 'border-brand bg-brand/20 text-brand' : 'border-slate-700 text-slate-300 hover:border-brand'
                  }`}
                >
                  {day.label}
                </button>
              );
            })}
        </div>
      </div>
      <div className="mt-6 flex items-center justify-between">
        <button
          type="button"
          onClick={buildPreview}
          className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-brand-foreground"
        >
          Generar ocurrencias
        </button>
        <p className="text-xs text-slate-500">
          Duplicar día respeta buffers y capacidad durante la generación de ocurrencias.
        </p>
      </div>
      {preview.length > 0 && (
        <div className="mt-6 space-y-2 rounded-lg border border-emerald-700/40 bg-emerald-500/10 p-4 text-sm text-emerald-200">
          <p className="font-medium">Ocurrencias sugeridas</p>
          <ul className="list-disc pl-4">
            {preview.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
