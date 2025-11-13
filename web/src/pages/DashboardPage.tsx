import { useMemo } from 'react';
import { useMoviu } from '../state/MoviuProvider';
import { StatCard } from '../components/StatCard';
import { ReservationList } from '../components/ReservationList';
import dayjs from '../utils/dayjs';

export const DashboardPage = () => {
  const { reservations, subscriptions, notifications, cancelReservation, toggleAttendance } = useMoviu();

  const upcoming = useMemo(
    () =>
      reservations
        .filter((reservation) => dayjs(reservation.datetime).isAfter(dayjs().subtract(1, 'day')))
        .sort((a, b) => dayjs(a.datetime).valueOf() - dayjs(b.datetime).valueOf())
        .slice(0, 5),
    [reservations]
  );

  const attendanceRate = useMemo(() => {
    const confirmed = reservations.filter((reservation) => reservation.status === 'confirmed');
    const completed = reservations.filter((reservation) => reservation.status === 'completed');
    return confirmed.length === 0 ? 0 : Math.round((completed.length / confirmed.length) * 100);
  }, [reservations]);

  return (
    <div>
      <div className="card-grid">
        <StatCard label="Clases confirmadas (7d)" value={`${upcoming.length}`} trend="+2 vs. semana pasada" />
        <StatCard
          label="Suscripciones activas"
          value={`${subscriptions.filter((subscription) => subscription.status === 'active').length}`}
          trend="92% al día"
        />
        <StatCard label="Notificaciones enviadas" value={`${notifications.length}`} trend="Automatizadas" />
        <StatCard label="Asistencia" value={`${attendanceRate}%`} status={attendanceRate > 80 ? 'success' : 'warning'} />
      </div>

      <div className="card-grid" style={{ marginTop: '1.5rem' }}>
        <ReservationList reservations={upcoming} onCancel={cancelReservation} onToggleAttendance={toggleAttendance} />
        <div className="card">
          <h3>Alertas</h3>
          {subscriptions
            .filter((subscription) => dayjs(subscription.expirationDate).diff(dayjs(), 'day') <= 5)
            .map((subscription) => (
              <div key={subscription.id} className="list-row">
                <div>
                  <strong>Plan por vencer</strong>
                  <p style={{ margin: 0 }}>Suscripción vence el {dayjs(subscription.expirationDate).format('DD MMM')}</p>
                </div>
                <button className="ghost">Notificar</button>
              </div>
            ))}
          {notifications.length === 0 && <p>No hay alertas pendientes.</p>}
        </div>
      </div>
    </div>
  );
};
