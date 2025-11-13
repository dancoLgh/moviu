import { FinancePanel } from '../components/FinancePanel';
import { useMoviu } from '../state/MoviuProvider';

export const FinancesPage = () => {
  const { incomes, expenses } = useMoviu();
  return <FinancePanel incomes={incomes} expenses={expenses} />;
};
