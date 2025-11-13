import { useState } from 'react';

const days = [
  { label: 'Lunes', value: 1 },
  { label: 'Martes', value: 2 },
  { label: 'Miércoles', value: 3 },
  { label: 'Jueves', value: 4 },
  { label: 'Viernes', value: 5 },
];

export const PlanBuilder = () => {
  const [baseDay, setBaseDay] = useState(1);
  const [time, setTime] = useState('15:00');
  const [duplicates, setDuplicates] = useState<number[]>([3, 5]);

  const toggleDuplicate = (value: number) => {
    setDuplicates((prev) =>
      prev.includes(value) ? prev.filter((day) => day !== value) : [...prev, value]
    );
  };

  return (
    <div className="card">
      <h3>Asistente de horarios</h3>
      <p style={{ color: 'var(--text-muted)', marginTop: 0 }}>
        Selecciona un bloque y duplícalo en otros días que compartan la misma hora.
      </p>
      <div className="split-columns">
        <label>
          Día base
          <select value={baseDay} onChange={(event) => setBaseDay(Number(event.target.value))}>
            {days.map((day) => (
              <option key={day.value} value={day.value}>
                {day.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Hora
          <input type="time" value={time} onChange={(event) => setTime(event.target.value)} />
        </label>
      </div>
      <div style={{ marginTop: '1rem' }}>
        <p style={{ fontWeight: 600 }}>Duplicar en:</p>
        <div className="tag-cloud">
          {days
            .filter((day) => day.value !== baseDay)
            .map((day) => (
              <button
                key={day.value}
                className={duplicates.includes(day.value) ? 'primary' : 'secondary'}
                onClick={() => toggleDuplicate(day.value)}
              >
                {day.label}
              </button>
            ))}
        </div>
      </div>
      <div className="card" style={{ marginTop: '1rem', background: 'var(--surface-muted)' }}>
        <p style={{ margin: 0 }}>Previsualización:</p>
        <ul>
          {[baseDay, ...duplicates]
            .sort((a, b) => a - b)
            .map((day) => (
              <li key={day}>
                {days.find((d) => d.value === day)?.label} • {time}
              </li>
            ))}
        </ul>
      </div>
    </div>
  );
};
