import { useMemo, useState } from 'react';
import { PortalView } from '../components/PortalView';
import { useMoviu } from '../state/MoviuProvider';

export const PortalPage = () => {
  const { students, subscriptions, notifications, timeline, pilatesProgress } = useMoviu();
  const [selectedStudentId, setSelectedStudentId] = useState(students[0]?.id ?? '');

  const student = students.find((item) => item.id === selectedStudentId) ?? students[0];
  const subscription = subscriptions.find((item) => item.studentId === student?.id);
  const studentNotifications = notifications.filter((notification) => notification.userId === student?.id);
  const studentTimeline = timeline.filter((event) => event.studentId === student?.id);
  const studentProgress = useMemo(
    () => pilatesProgress.filter((entry) => entry.studentId === student?.id),
    [pilatesProgress, student?.id]
  );

  if (!student) {
    return <p>Sin alumnos cargados.</p>;
  }

  return (
    <div>
      <label>
        Selecciona alumno
        <select value={student.id} onChange={(event) => setSelectedStudentId(event.target.value)}>
          {students.map((item) => (
            <option key={item.id} value={item.id}>
              {item.fullName}
            </option>
          ))}
        </select>
      </label>
      <PortalView
        student={student}
        subscription={subscription}
        notifications={studentNotifications}
        timeline={studentTimeline}
        progress={studentProgress}
      />
    </div>
  );
};
