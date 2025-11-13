import { useState } from 'react';
import { ScheduleBoard } from '../components/ScheduleBoard';
import { useMoviu } from '../state/MoviuProvider';
import dayjs from '../utils/dayjs';
import { availabilityMatrix } from '../data/mockData';

export const AgendaPage = () => {
  const { schedule, services } = useMoviu();
  const [selectedDate, setSelectedDate] = useState(dayjs().format('YYYY-MM-DD'));
  const availability = availabilityMatrix(dayjs(selectedDate));

  return (
    <div className="card-grid">
      <ScheduleBoard blocks={schedule} />
      <div className="card">
        <h3>Disponibilidad puntual</h3>
        <label style={{ display: 'block', marginBottom: '1rem' }}>
          Selecciona fecha
          <input type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} />
        </label>
        {availability.length === 0 && <p>Sin bloques disponibles ese día.</p>}
        {availability.map((slot) => (
          <div key={slot.id} className="list-row">
            <div>
              <strong>
                {slot.start} - {slot.end}
              </strong>
              <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                {services.find((service) => service.id === slot.serviceId)?.name}
              </p>
            </div>
            <span className="badge success">{slot.capacity} cupos</span>
          </div>
        ))}
      </div>
    </div>
  );
};
