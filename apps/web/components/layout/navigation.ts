import type { LucideIcon } from 'lucide-react';
import {
  CalendarDays,
  ClipboardList,
  HandCoins,
  HeartPulse,
  LayoutDashboard,
  Settings,
  UsersRound
} from 'lucide-react';

export type NavigationItem = {
  label: string;
  description: string;
  href: string;
  icon: LucideIcon;
};

export const navigationItems: NavigationItem[] = [
  {
    label: 'Panel',
    description: 'Resumen del estudio y accesos rápidos',
    href: '/dashboard',
    icon: LayoutDashboard
  },
  {
    label: 'Agenda',
    description: 'Cupos, buffers y cancelaciones en tiempo real',
    href: '/calendar',
    icon: CalendarDays
  },
  {
    label: 'Planes',
    description: 'Duplicar días, políticas y vigencias',
    href: '/plans',
    icon: ClipboardList
  },
  {
    label: 'Miembros',
    description: 'Gestión de alumnos y pacientes',
    href: '/members',
    icon: UsersRound
  },
  {
    label: 'Finanzas',
    description: 'Ingresos privados y egresos compartidos',
    href: '/finances',
    icon: HandCoins
  },
  {
    label: 'Portal',
    description: 'Vista del alumno para cancelaciones y recuperos',
    href: '/portal',
    icon: HeartPulse
  },
  {
    label: 'Configuración',
    description: 'Preferencias, notificaciones y RLS',
    href: '/settings',
    icon: Settings
  }
];
