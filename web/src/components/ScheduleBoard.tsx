import { ScheduleBlock } from '../types';
import { professionals, services } from '../data/mockData';

const weekdays = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

interface Props {
  blocks: ScheduleBlock[];
}

export const ScheduleBoard = ({ blocks }: Props) => {
  return (
    <div className="card">
      <h3>Agenda semanal</h3>
      <div className="split-columns" style={{ marginTop: '1rem' }}>
        {weekdays.map((day, index) => (
          <div key={day} className="mini-card">
            <p style={{ fontWeight: 600, marginBottom: '0.35rem' }}>{day}</p>
            {blocks.filter((block) => block.weekday === index).length === 0 && (
              <p style={{ color: 'var(--text-muted)' }}>Sin bloques</p>
            )}
            {blocks
              .filter((block) => block.weekday === index)
              .map((block) => {
                const service = services.find((svc) => svc.id === block.serviceId);
                const pro = professionals.find((p) => p.id === block.professionalId);
                return (
                  <div key={block.id} style={{ marginBottom: '0.75rem' }}>
                    <strong>
                      {block.start} - {block.end}
                    </strong>
                    <p style={{ margin: 0, fontSize: '0.85rem' }}>
                      {service?.name}
                      <br />
                      Cupo {block.capacity} • {pro?.name}
                    </p>
                  </div>
                );
              })}
          </div>
        ))}
      </div>
    </div>
  );
};
