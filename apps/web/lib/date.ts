import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';

export function formatShort(date: string | Date) {
  const input = typeof date === 'string' ? parseISO(date) : date;
  return format(input, "d MMM, HH:mm", { locale: es });
}
