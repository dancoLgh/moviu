import { ServicePlanGrid } from '../components/ServicePlanGrid';
import { PlanBuilder } from '../components/PlanBuilder';
import { useMoviu } from '../state/MoviuProvider';

export const ServicesPage = () => {
  const { services, plans } = useMoviu();
  return (
    <div className="card-grid">
      <ServicePlanGrid services={services} plans={plans} />
      <PlanBuilder />
    </div>
  );
};
