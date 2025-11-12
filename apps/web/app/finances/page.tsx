import { Card, CardBody, CardHeader, Chip, Divider } from '@heroui/react';

const incomes = [
  { professional: 'María Gómez', amount: 'PYG 1.200.000', concept: 'Clases grupales' },
  { professional: 'Juan López', amount: 'PYG 800.000', concept: 'Sesiones kine' }
];

const expenses = [
  { concept: 'Alquiler estudio', amount: 'PYG 1.000.000', shared: 'Equal (50/50)' },
  { concept: 'Luz y agua', amount: 'PYG 320.000', shared: 'Percent (60/40)' }
];

export default function FinancesPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold">Finanzas</h2>
        <p className="text-sm text-foreground/60">
          Registra ingresos privados por profesional y egresos compartidos con reglas de prorrateo.
        </p>
      </header>
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
          <CardHeader className="flex items-center justify-between px-4 pt-4 sm:px-6">
            <div>
              <h3 className="text-base font-semibold">Ingresos privados</h3>
              <p className="text-xs text-foreground/60">Visible sólo para cada profesional y tenant admin.</p>
            </div>
            <Chip size="sm" color="success" variant="flat">
              {incomes.length} registros
            </Chip>
          </CardHeader>
          <Divider />
          <CardBody className="gap-3 px-4 py-5 text-sm sm:px-6">
            {incomes.map((income) => (
              <div key={income.professional} className="flex flex-col gap-1 rounded-lg bg-success/10 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">{income.professional}</span>
                  <span className="font-semibold text-success">{income.amount}</span>
                </div>
                <p className="text-xs text-foreground/60">{income.concept}</p>
              </div>
            ))}
          </CardBody>
        </Card>
        <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
          <CardHeader className="flex items-center justify-between px-4 pt-4 sm:px-6">
            <div>
              <h3 className="text-base font-semibold">Egresos compartidos</h3>
              <p className="text-xs text-foreground/60">Distribuye automáticamente según regla configurada.</p>
            </div>
            <Chip size="sm" color="danger" variant="flat">
              {expenses.length} registros
            </Chip>
          </CardHeader>
          <Divider />
          <CardBody className="gap-3 px-4 py-5 text-sm sm:px-6">
            {expenses.map((expense) => (
              <div key={expense.concept} className="flex flex-col gap-1 rounded-lg bg-danger/10 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">{expense.concept}</span>
                  <span className="font-semibold text-danger">{expense.amount}</span>
                </div>
                <p className="text-xs text-foreground/60">{expense.shared}</p>
              </div>
            ))}
          </CardBody>
        </Card>
      </section>
    </div>
  );
}
