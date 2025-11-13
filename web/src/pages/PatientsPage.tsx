import { useState } from 'react';
import { PatientProfile } from '../components/PatientProfile';
import { useMoviu } from '../state/MoviuProvider';

export const PatientsPage = () => {
  const { students, kineRecords } = useMoviu();
  const [selectedStudentId, setSelectedStudentId] = useState(students[1]?.id ?? students[0]?.id ?? '');
  const student = students.find((item) => item.id === selectedStudentId) ?? students[0];
  const record = kineRecords.find((item) => item.studentId === student?.id);

  if (!student) {
    return <p>Sin pacientes.</p>;
  }

  return (
    <div>
      <label>
        Selecciona paciente
        <select value={student.id} onChange={(event) => setSelectedStudentId(event.target.value)}>
          {students.map((item) => (
            <option key={item.id} value={item.id}>
              {item.fullName}
            </option>
          ))}
        </select>
      </label>
      <PatientProfile student={student} record={record} />
    </div>
  );
};
