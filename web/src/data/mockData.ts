import { Dayjs } from 'dayjs';
import dayjs from '../utils/dayjs';
import {
  Expense,
  Income,
  KineRecord,
  NotificationItem,
  PilatesProgress,
  Plan,
  Professional,
  Reservation,
  ScheduleBlock,
  Service,
  StudentProfile,
  Subscription,
  TimelineEvent,
} from '../types';

const baseDate = dayjs();

export const professionals: Professional[] = [
  {
    id: 'pro-1',
    name: 'María Fernández',
    specialty: 'pilates',
    bio: 'Instructora Peak Pilates especializada en movilidad y postura.',
  },
  {
    id: 'pro-2',
    name: 'Carlos Soto',
    specialty: 'kine',
    bio: 'Kinesiólogo deportivo, enfoque en rehabilitación de hombro.',
  },
  {
    id: 'pro-3',
    name: 'Lucía Álvarez',
    specialty: 'pilates',
    bio: 'Entrenadora funcional y especialista en poblaciones especiales.',
  },
];

export const services: Service[] = [
  {
    id: 'svc-pilates',
    name: 'Pilates Reformer',
    type: 'pilates',
    durationMinutes: 55,
    capacity: 6,
    recurrence: 'weekly',
    policies: { cancelWindowHours: 12, recoveriesPerMonth: 1 },
    professionalIds: ['pro-1', 'pro-3'],
  },
  {
    id: 'svc-kine',
    name: 'Kinesiología Deportiva',
    type: 'kine',
    durationMinutes: 45,
    capacity: 1,
    recurrence: 'single',
    policies: { cancelWindowHours: 6, recoveriesPerMonth: 0 },
    professionalIds: ['pro-2'],
  },
];

export const plans: Plan[] = [
  {
    id: 'plan-basic',
    serviceId: 'svc-pilates',
    name: 'Pilates Básico',
    price: 100000,
    sessionsPerWeek: 1,
    description: '1 vez por semana con recupero mensual',
  },
  {
    id: 'plan-max',
    serviceId: 'svc-pilates',
    name: 'Pilates Máximo',
    price: 350000,
    sessionsPerWeek: 3,
    description: '3 veces por semana, prioridad en cupos y métricas avanzadas',
  },
  {
    id: 'plan-kine',
    serviceId: 'svc-kine',
    name: 'Paquete Kine x8',
    price: 640000,
    sessionsPerWeek: 2,
    description: 'Plan de 8 sesiones individuales con seguimiento clínico',
  },
];

export const scheduleBlocks: ScheduleBlock[] = [
  {
    id: 'blk-1',
    professionalId: 'pro-1',
    weekday: 1,
    start: '15:00',
    end: '16:00',
    capacity: 6,
    serviceId: 'svc-pilates',
  },
  {
    id: 'blk-2',
    professionalId: 'pro-1',
    weekday: 3,
    start: '15:00',
    end: '16:00',
    capacity: 6,
    serviceId: 'svc-pilates',
  },
  {
    id: 'blk-3',
    professionalId: 'pro-3',
    weekday: 5,
    start: '08:00',
    end: '09:00',
    capacity: 6,
    serviceId: 'svc-pilates',
  },
  {
    id: 'blk-4',
    professionalId: 'pro-2',
    weekday: 2,
    start: '10:00',
    end: '10:45',
    capacity: 1,
    serviceId: 'svc-kine',
  },
  {
    id: 'blk-5',
    professionalId: 'pro-2',
    weekday: 4,
    start: '10:00',
    end: '10:45',
    capacity: 1,
    serviceId: 'svc-kine',
  },
];

export const students: StudentProfile[] = [
  {
    id: 'stu-1',
    fullName: 'Laura Benítez',
    document: '4829372',
    birthDate: '1992-10-12',
    sex: 'F',
    email: 'laura@example.com',
    phone: '+59598111111',
    address: 'Asunción, Barrio Villa Morra',
    emergencyContact: 'Sofía Benítez',
    notes: 'Operación de rodilla en 2021',
  },
  {
    id: 'stu-2',
    fullName: 'Diego Peralta',
    document: '5039312',
    birthDate: '1987-06-01',
    sex: 'M',
    email: 'diego@example.com',
    phone: '+59598122222',
    address: 'Luque',
    emergencyContact: 'Marcos Peralta',
  },
];

export const reservations: Reservation[] = Array.from({ length: 6 }).map((_, idx) => ({
  id: `res-${idx + 1}`,
  studentId: idx % 2 === 0 ? 'stu-1' : 'stu-2',
  serviceId: idx % 3 === 0 ? 'svc-kine' : 'svc-pilates',
  professionalId: idx % 3 === 0 ? 'pro-2' : 'pro-1',
  datetime: baseDate.add(idx, 'day').hour(15).minute(0).toISOString(),
  status: idx === 2 ? 'cancelled' : 'confirmed',
  type: idx % 3 === 0 ? 'single' : 'recurring',
  recurrenceId: idx % 3 === 0 ? undefined : 'rec-1',
}));

export const subscriptions: Subscription[] = [
  {
    id: 'sub-1',
    studentId: 'stu-1',
    planId: 'plan-max',
    status: 'active',
    startDate: baseDate.startOf('month').toISOString(),
    expirationDate: baseDate.add(1, 'month').toISOString(),
    remainingClasses: 7,
    recoveriesAvailable: 1,
  },
  {
    id: 'sub-2',
    studentId: 'stu-2',
    planId: 'plan-basic',
    status: 'paused',
    startDate: baseDate.subtract(1, 'month').toISOString(),
    expirationDate: baseDate.add(15, 'day').toISOString(),
    remainingClasses: 2,
    recoveriesAvailable: 0,
  },
];

export const timeline: TimelineEvent[] = [
  {
    id: 'tl-1',
    studentId: 'stu-1',
    date: baseDate.subtract(3, 'month').toISOString(),
    title: 'Alta programa pilates',
    description: 'Evaluación inicial y toma de medidas',
    kind: 'pilates',
  },
  {
    id: 'tl-2',
    studentId: 'stu-1',
    date: baseDate.subtract(1, 'month').toISOString(),
    title: 'Comparativa movilidad',
    description: '+8 cm en sit-and-reach, fotos antes/después',
    kind: 'pilates',
  },
  {
    id: 'tl-3',
    studentId: 'stu-2',
    date: baseDate.subtract(10, 'day').toISOString(),
    title: 'Sesión kine #3',
    description: 'Menor EVA y más rango de flexión',
    kind: 'kine',
  },
];

export const kineRecords: KineRecord[] = [
  {
    id: 'krec-1',
    studentId: 'stu-2',
    diagnosis: 'Tendinopatía manguito rotador',
    history: ['Luxación hombro 2022', 'Trabajo de escritorio'],
    pain: {
      location: 'Hombro derecho',
      eva: 7,
      type: 'punzante',
      triggers: 'Elevar brazo por encima de 90°',
    },
    studies: [
      { name: 'RM Hombro', type: 'PDF' },
      { name: 'Rx control 2023', type: 'JPG' },
    ],
    therapeuticPlan:
      '8 sesiones de terapia manual + neurodinamia + ejercicios de fortalecimiento escapular',
    sessions: [
      {
        id: 'ks-1',
        recordId: 'krec-1',
        date: baseDate.subtract(2, 'week').toISOString(),
        techniques: ['Liberación miofascial', 'Movilización glenohumeral'],
        evaPre: 7,
        evaPost: 5,
        response: 'Mejora inmediata en rotación externa',
      },
      {
        id: 'ks-2',
        recordId: 'krec-1',
        date: baseDate.subtract(1, 'week').toISOString(),
        techniques: ['Ejercicios isométricos', 'Neurodinamia mediano'],
        evaPre: 6,
        evaPost: 4,
        response: 'Dolor residual al final del día',
      },
    ],
  },
];

export const pilatesProgress: PilatesProgress[] = [
  {
    id: 'pp-1',
    studentId: 'stu-1',
    date: baseDate.subtract(2, 'month').toISOString(),
    tags: ['postura', 'movilidad'],
    notes: 'Comparativa con mejor alineación escapular',
    metrics: { sitAndReach: 34, plank: 90 },
    mediaUrl: '/progress/laura_2024-02.png',
  },
  {
    id: 'pp-2',
    studentId: 'stu-1',
    date: baseDate.subtract(1, 'week').toISOString(),
    tags: ['core', 'balance'],
    notes: 'Tiempo de plancha sostenido +30s respecto a enero',
    metrics: { plank: 120 },
  },
];

export const incomes: Income[] = [
  { id: 'inc-1', professionalId: 'pro-1', label: 'Plan Máximo Laura', amount: 350000, date: baseDate.startOf('month').toISOString() },
  { id: 'inc-2', professionalId: 'pro-3', label: 'Clases sueltas', amount: 150000, date: baseDate.subtract(5, 'day').toISOString() },
  { id: 'inc-3', professionalId: 'pro-2', label: 'Sesiones Kine', amount: 480000, date: baseDate.subtract(2, 'day').toISOString() },
];

export const expenses: Expense[] = [
  { id: 'exp-1', label: 'Alquiler estudio', amount: 1200000, shared: true, category: 'Infraestructura' },
  { id: 'exp-2', label: 'Insumos kinesio', amount: 180000, shared: false, professionalId: 'pro-2', category: 'Insumos' },
  { id: 'exp-3', label: 'Mantenimiento reformers', amount: 220000, shared: true, category: 'Equipamiento' },
];

export const availabilityMatrix = (date: Dayjs) => {
  const dayOfWeek = date.day();
  return scheduleBlocks.filter((block) => block.weekday === dayOfWeek);
};

export const notifications: NotificationItem[] = [
  {
    id: 'ntf-1',
    userId: 'stu-1',
    type: 'class-reminder',
    message: 'Recordatorio: Pilates miércoles 15:00 con María',
    createdAt: baseDate.subtract(1, 'day').toISOString(),
    read: false,
  },
  {
    id: 'ntf-2',
    userId: 'stu-2',
    type: 'recovery',
    message: 'Tienes 1 recupero disponible para usar antes del 30/04',
    createdAt: baseDate.subtract(2, 'day').toISOString(),
    read: true,
  },
  {
    id: 'ntf-3',
    userId: 'pro-1',
    type: 'cancellation',
    message: 'Diego canceló su clase del viernes, liberar cupo',
    createdAt: baseDate.subtract(6, 'hour').toISOString(),
    read: false,
  },
];
