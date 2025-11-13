import dayjs from '../utils/dayjs';
import { Expense, Income } from '../types';

interface Props {
  incomes: Income[];
  expenses: Expense[];
}

export const FinancePanel = ({ incomes, expenses }: Props) => {
  const totalIncome = incomes.reduce((acc, curr) => acc + curr.amount, 0);
  const totalExpense = expenses.reduce((acc, curr) => acc + curr.amount, 0);
  const ratio = totalIncome === 0 ? 0 : ((totalIncome - totalExpense) / totalIncome) * 100;

  return (
    <div className="card">
      <h3>Ingresos/Egresos</h3>
      <div className="card-grid" style={{ marginTop: '1rem' }}>
        <div className="card" style={{ background: 'var(--surface-muted)' }}>
          <p>Ingresos</p>
          <strong>PYG {totalIncome.toLocaleString('es-PY')}</strong>
        </div>
        <div className="card" style={{ background: 'var(--surface-muted)' }}>
          <p>Egresos</p>
          <strong>PYG {totalExpense.toLocaleString('es-PY')}</strong>
        </div>
        <div className="card" style={{ background: 'var(--surface-muted)' }}>
          <p>Ratio</p>
          <strong>{ratio.toFixed(1)}%</strong>
        </div>
      </div>
      <div className="split-columns" style={{ marginTop: '1rem' }}>
        <div>
          <h4>Últimos ingresos</h4>
          {incomes.map((income) => (
            <div key={income.id} className="list-row">
              <div>
                <strong>{income.label}</strong>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  {dayjs(income.date).format('DD MMM')}
                </p>
              </div>
              <span>PYG {income.amount.toLocaleString('es-PY')}</span>
            </div>
          ))}
        </div>
        <div>
          <h4>Egresos</h4>
          {expenses.map((expense) => (
            <div key={expense.id} className="list-row">
              <div>
                <strong>{expense.label}</strong>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.8rem' }}>{expense.category}</p>
              </div>
              <span>PYG {expense.amount.toLocaleString('es-PY')}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
