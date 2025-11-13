import dayjs from '../utils/dayjs';
import { NotificationItem, PilatesProgress, StudentProfile, Subscription, TimelineEvent } from '../types';

interface PortalViewProps {
  student: StudentProfile;
  subscription?: Subscription;
  notifications: NotificationItem[];
  timeline: TimelineEvent[];
  progress: PilatesProgress[];
}

export const PortalView = ({ student, subscription, notifications, timeline, progress }: PortalViewProps) => {
  return (
    <div className="card">
      <h3>Portal — {student.fullName}</h3>
      {subscription ? (
        <div className="card" style={{ background: 'var(--surface-muted)', marginTop: '1rem' }}>
          <p style={{ margin: 0 }}>Plan actual: {subscription.planId}</p>
          <strong>{subscription.status === 'active' ? 'Activo' : subscription.status}</strong>
          <p style={{ margin: 0 }}>Clases disponibles: {subscription.remainingClasses}</p>
          <p style={{ margin: 0 }}>Vence {dayjs(subscription.expirationDate).format('DD MMM')}</p>
        </div>
      ) : (
        <p>Sin plan activo</p>
      )}
      <div className="split-columns" style={{ marginTop: '1rem' }}>
        <div>
          <h4>Notificaciones</h4>
          {notifications.map((notification) => (
            <div key={notification.id} className="list-row">
              <div>
                <strong>{notification.message}</strong>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  {dayjs(notification.createdAt).fromNow()}
                </p>
              </div>
              {!notification.read && <span className="badge warning">Nueva</span>}
            </div>
          ))}
        </div>
        <div>
          <h4>Evolución</h4>
          <div className="timeline">
            {timeline.map((item) => (
              <div key={item.id} className="timeline-item">
                <small>{dayjs(item.date).format('DD MMM YYYY')}</small>
                <strong>{item.title}</strong>
                <p style={{ margin: 0 }}>{item.description}</p>
              </div>
            ))}
          </div>
          <div className="progress-grid" style={{ marginTop: '1rem' }}>
            {progress.map((entry) => (
              <div key={entry.id} className="card" style={{ background: 'var(--surface-muted)' }}>
                <strong>{dayjs(entry.date).format('DD MMM')}</strong>
                <p style={{ margin: 0 }}>{entry.notes}</p>
                <div className="tag-cloud">
                  {entry.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
