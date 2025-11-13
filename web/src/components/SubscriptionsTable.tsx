import dayjs from '../utils/dayjs';
import { Plan, StudentProfile, Subscription } from '../types';

interface Props {
  subscriptions: Subscription[];
  plans: Plan[];
  students: StudentProfile[];
  onToggle: (id: string) => void;
}

export const SubscriptionsTable = ({ subscriptions, plans, students, onToggle }: Props) => {
  return (
    <div className="card">
      <h3>Suscripciones activas</h3>
      <table className="table-list" style={{ marginTop: '1rem' }}>
        <thead>
          <tr>
            <th>Alumno</th>
            <th>Plan</th>
            <th>Clases</th>
            <th>Vence</th>
            <th>Recuperos</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {subscriptions.map((subscription) => {
            const plan = plans.find((item) => item.id === subscription.planId);
            const student = students.find((item) => item.id === subscription.studentId);
            return (
              <tr key={subscription.id}>
                <td>
                  <strong>{student?.fullName}</strong>
                  <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.8rem' }}>{subscription.status}</p>
                </td>
                <td>{plan?.name}</td>
                <td>{subscription.remainingClasses}</td>
                <td>{dayjs(subscription.expirationDate).format('DD/MM')}</td>
                <td>{subscription.recoveriesAvailable}</td>
                <td>
                  <button className="secondary" onClick={() => onToggle(subscription.id)}>
                    {subscription.status === 'active' ? 'Pausar' : 'Reactivar'}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
