export type ServiceType = 'pilates' | 'kine';

export interface Professional {
  id: string;
  name: string;
  specialty: ServiceType;
  bio: string;
}

export interface Service {
  id: string;
  name: string;
  type: ServiceType;
  durationMinutes: number;
  capacity: number;
  recurrence?: 'weekly' | 'monthly' | 'single';
  policies: {
    cancelWindowHours: number;
    recoveriesPerMonth: number;
  };
  professionalIds: string[];
}

export interface Plan {
  id: string;
  serviceId: string;
  name: string;
  price: number;
  sessionsPerWeek: number;
  description: string;
}

export interface ScheduleBlock {
  id: string;
  professionalId: string;
  weekday: number; // 0 = Sunday
  start: string; // HH:mm
  end: string; // HH:mm
  capacity: number;
  serviceId: string;
}

export interface Reservation {
  id: string;
  studentId: string;
  serviceId: string;
  professionalId: string;
  datetime: string;
  status: 'confirmed' | 'cancelled' | 'completed';
  type: 'single' | 'recurring' | 'recovery';
  recurrenceId?: string;
}

export interface Attendance {
  reservationId: string;
  present: boolean;
  notes?: string;
}

export interface Subscription {
  id: string;
  studentId: string;
  planId: string;
  status: 'active' | 'paused' | 'cancelled';
  startDate: string;
  expirationDate: string;
  remainingClasses: number;
  recoveriesAvailable: number;
}

export interface StudentProfile {
  id: string;
  fullName: string;
  document: string;
  birthDate: string;
  sex: 'F' | 'M' | 'X';
  email: string;
  phone: string;
  address: string;
  emergencyContact: string;
  notes?: string;
}

export interface KineRecord {
  id: string;
  studentId: string;
  diagnosis: string;
  history: string[];
  pain: {
    location: string;
    eva: number;
    type: string;
    triggers: string;
  };
  studies: { name: string; type: string }[];
  therapeuticPlan: string;
  sessions: KineSession[];
}

export interface KineSession {
  id: string;
  recordId: string;
  date: string;
  techniques: string[];
  evaPre: number;
  evaPost: number;
  response: string;
}

export interface PilatesProgress {
  id: string;
  studentId: string;
  date: string;
  tags: string[];
  notes: string;
  metrics?: Record<string, number>;
  mediaUrl?: string;
}

export interface NotificationItem {
  id: string;
  userId: string;
  type:
    | 'class-reminder'
    | 'appointment-reminder'
    | 'plan-expiration'
    | 'cancellation'
    | 'recovery';
  message: string;
  createdAt: string;
  read: boolean;
}

export interface Expense {
  id: string;
  professionalId?: string;
  label: string;
  amount: number;
  shared: boolean;
  category: string;
}

export interface Income {
  id: string;
  professionalId: string;
  label: string;
  amount: number;
  date: string;
}

export interface TimelineEvent {
  id: string;
  studentId: string;
  date: string;
  title: string;
  description: string;
  kind: 'pilates' | 'kine' | 'finance';
}
