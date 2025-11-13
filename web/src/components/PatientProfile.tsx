import dayjs from '../utils/dayjs';
import { KineRecord, StudentProfile } from '../types';

interface Props {
  student: StudentProfile;
  record?: KineRecord;
}

export const PatientProfile = ({ student, record }: Props) => {
  if (!record) {
    return (
      <div className="card">
        <h3>{student.fullName}</h3>
        <p>Sin ficha clínica registrada.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>Ficha kine — {student.fullName}</h3>
      <div className="split-columns">
        <div>
          <p style={{ margin: 0 }}>Diagnóstico</p>
          <strong>{record.diagnosis}</strong>
          <p style={{ color: 'var(--text-muted)' }}>{record.therapeuticPlan}</p>
          <h4>Dolor</h4>
          <p>
            {record.pain.location} • EVA {record.pain.eva}/10 • {record.pain.type}
            <br />
            Desencadenantes: {record.pain.triggers}
          </p>
          <h4>Antecedentes</h4>
          <ul>
            {record.history.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h4>Sesiones</h4>
          {record.sessions.map((session) => (
            <div key={session.id} className="list-row">
              <div>
                <strong>{dayjs(session.date).format('DD MMM')}</strong>
                <p style={{ margin: 0 }}>{session.techniques.join(', ')}</p>
              </div>
              <span className="badge success">EVA {session.evaPost}</span>
            </div>
          ))}
          <h4>Estudios adjuntos</h4>
          <div className="tag-cloud">
            {record.studies.map((study) => (
              <span key={study.name}>{study.name}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
