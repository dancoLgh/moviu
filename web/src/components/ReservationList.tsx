import dayjs from '../utils/dayjs';
import { Reservation } from '../types';

interface ReservationListProps {
  reservations: Reservation[];
  onCancel: (id: string) => void;
  onToggleAttendance: (id: string) => void;
}

export const ReservationList = ({ reservations, onCancel, onToggleAttendance }: ReservationListProps) => {
  return (
    <div className="card">
      <div className="list-row" style={{ borderBottom: 'none', paddingBottom: 0 }}>
        <div>
          <h3>Próximas sesiones</h3>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>Hoy y próximos 7 días</p>
        </div>
      </div>
      {reservations.map((reservation) => (
        <div key={reservation.id} className="list-row">
          <div>
            <strong>{dayjs(reservation.datetime).format('ddd DD MMM HH:mm')}</strong>
            <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              {reservation.serviceId === 'svc-kine' ? 'Kinesiología' : 'Pilates'} • {reservation.type}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="secondary" onClick={() => onToggleAttendance(reservation.id)}>
              Check-in
            </button>
            {reservation.status === 'confirmed' && (
              <button className="ghost" onClick={() => onCancel(reservation.id)}>
                Cancelar
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
