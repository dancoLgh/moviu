import { Plan, Service } from '../types';

interface Props {
  services: Service[];
  plans: Plan[];
}

export const ServicePlanGrid = ({ services, plans }: Props) => {
  return (
    <div className="card">
      <h3>Servicios y planes</h3>
      <div className="card-grid" style={{ marginTop: '1rem' }}>
        {services.map((service) => (
          <div key={service.id} className="card" style={{ background: 'var(--surface-muted)' }}>
            <h4>{service.name}</h4>
            <p style={{ margin: 0 }}>{service.type === 'pilates' ? 'Grupal' : 'Individual'}</p>
            <p style={{ margin: 0 }}>Duración {service.durationMinutes} min</p>
            <p style={{ margin: 0 }}>Cupo {service.capacity}</p>
            <div className="tag-cloud">
              <span>{service.policies.cancelWindowHours}h cancelación</span>
              <span>{service.policies.recoveriesPerMonth} recuperos</span>
            </div>
          </div>
        ))}
      </div>
      <h4 className="section-title">Planes</h4>
      <div className="card-grid">
        {plans.map((plan) => (
          <div key={plan.id} className="card">
            <h4>{plan.name}</h4>
            <p style={{ margin: 0 }}>{plan.description}</p>
            <strong>PYG {plan.price.toLocaleString('es-PY')}</strong>
            <p style={{ margin: 0 }}>{plan.sessionsPerWeek} veces/semana</p>
          </div>
        ))}
      </div>
    </div>
  );
};
