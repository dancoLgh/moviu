export type ServiceType = 'pilates_group' | 'pilates_individual' | 'kinesio_individual';

export type PlanSummary = {
  id: string;
  name: string;
  times_per_week: number;
  max_makeups_per_month: number;
};
