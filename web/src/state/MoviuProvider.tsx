import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import dayjs from '../utils/dayjs';
import {
  Attendance,
  Expense,
  Income,
  KineRecord,
  NotificationItem,
  PilatesProgress,
  Plan,
  Reservation,
  ScheduleBlock,
  Service,
  StudentProfile,
  Subscription,
  TimelineEvent,
} from '../types';
import {
  expenses as expenseSeed,
  incomes as incomeSeed,
  kineRecords as kineSeed,
  notifications as notificationSeed,
  pilatesProgress as pilatesSeed,
  plans as planSeed,
  reservations as reservationSeed,
  scheduleBlocks as scheduleSeed,
  services as serviceSeed,
  students,
  subscriptions as subscriptionSeed,
  timeline as timelineSeed,
} from '../data/mockData';

interface MoviuContextValue {
  services: Service[];
  plans: Plan[];
  schedule: ScheduleBlock[];
  reservations: Reservation[];
  subscriptions: Subscription[];
  students: StudentProfile[];
  notifications: NotificationItem[];
  timeline: TimelineEvent[];
  incomes: Income[];
  expenses: Expense[];
  kineRecords: KineRecord[];
  pilatesProgress: PilatesProgress[];
  attendance: Record<string, Attendance>;
  bookReservation: (payload: Omit<Reservation, 'id'>) => void;
  cancelReservation: (id: string) => void;
  toggleAttendance: (reservationId: string) => void;
  toggleSubscriptionStatus: (id: string) => void;
  logFinance: (entry: Income | Expense) => void;
  addNotification: (notification: NotificationItem) => void;
}

const MoviuContext = createContext<MoviuContextValue | undefined>(undefined);

export const MoviuProvider = ({ children }: { children: React.ReactNode }) => {
  const [services] = useState(serviceSeed);
  const [plans] = useState(planSeed);
  const [schedule] = useState(scheduleSeed);
  const [reservations, setReservations] = useState(reservationSeed);
  const [subscriptions, setSubscriptions] = useState(subscriptionSeed);
  const [notifications, setNotifications] = useState(notificationSeed);
  const [timeline, setTimeline] = useState(timelineSeed);
  const [incomes, setIncomes] = useState(incomeSeed);
  const [expenses, setExpenses] = useState(expenseSeed);
  const [kineRecords] = useState(kineSeed);
  const [pilatesProgress] = useState(pilatesSeed);
  const [attendance, setAttendance] = useState<Record<string, Attendance>>({});

  const bookReservation = useCallback(
    (payload: Omit<Reservation, 'id'>) => {
      setReservations((prev) => [
        ...prev,
        {
          ...payload,
          id: `res-${prev.length + 1}`,
        },
      ]);
      setNotifications((prev) => [
        ...prev,
        {
          id: `ntf-${prev.length + 1}`,
          userId: payload.studentId,
          type: 'class-reminder',
          message: 'Reserva creada y notificación enviada automáticamente',
          createdAt: dayjs().toISOString(),
          read: false,
        },
      ]);
    },
    []
  );

  const cancelReservation = useCallback((id: string) => {
    setReservations((prev) =>
      prev.map((reservation) =>
        reservation.id === id
          ? {
              ...reservation,
              status: 'cancelled',
            }
          : reservation
      )
    );
    setTimeline((prev) => [
      ...prev,
      {
        id: `tl-${prev.length + 1}`,
        studentId: reservations.find((res) => res.id === id)?.studentId ?? 'stu-1',
        date: dayjs().toISOString(),
        title: 'Cancelación registrada',
        description: 'La clase liberó cupo para recupero',
        kind: 'pilates',
      },
    ]);
  }, [reservations]);

  const toggleAttendance = useCallback((reservationId: string) => {
    setAttendance((prev) => {
      const current = prev[reservationId];
      const updated: Attendance = {
        reservationId,
        present: !(current?.present ?? false),
        notes: current?.notes,
      };
      return { ...prev, [reservationId]: updated };
    });
  }, []);

  const toggleSubscriptionStatus = useCallback((id: string) => {
    setSubscriptions((prev) =>
      prev.map((subscription) =>
        subscription.id === id
          ? {
              ...subscription,
              status: subscription.status === 'active' ? 'paused' : 'active',
            }
          : subscription
      )
    );
  }, []);

  const logFinance = useCallback((entry: Income | Expense) => {
    if ('date' in entry) {
      setIncomes((prev) => [...prev, entry as Income]);
    } else {
      setExpenses((prev) => [...prev, entry as Expense]);
    }
  }, []);

  const addNotification = useCallback((notification: NotificationItem) => {
    setNotifications((prev) => [...prev, notification]);
  }, []);

  const value: MoviuContextValue = useMemo(
    () => ({
      services,
      plans,
      schedule,
      reservations,
      subscriptions,
      students,
      notifications,
      timeline,
      incomes,
      expenses,
      kineRecords,
      pilatesProgress,
      attendance,
      bookReservation,
      cancelReservation,
      toggleAttendance,
      toggleSubscriptionStatus,
      logFinance,
      addNotification,
    }),
    [
      services,
      plans,
      schedule,
      reservations,
      subscriptions,
      notifications,
      timeline,
      incomes,
      expenses,
      kineRecords,
      pilatesProgress,
      attendance,
      bookReservation,
      cancelReservation,
      toggleAttendance,
      toggleSubscriptionStatus,
      logFinance,
      addNotification,
    ]
  );

  return <MoviuContext.Provider value={value}>{children}</MoviuContext.Provider>;
};

export const useMoviu = () => {
  const context = useContext(MoviuContext);
  if (!context) {
    throw new Error('useMoviu debe usarse dentro de MoviuProvider');
  }
  return context;
};
