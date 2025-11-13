import { SubscriptionsTable } from '../components/SubscriptionsTable';
import { useMoviu } from '../state/MoviuProvider';

export const SubscriptionsPage = () => {
  const { subscriptions, plans, students, toggleSubscriptionStatus } = useMoviu();
  return (
    <SubscriptionsTable subscriptions={subscriptions} plans={plans} students={students} onToggle={toggleSubscriptionStatus} />
  );
};
