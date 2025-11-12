import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Chip,
  Divider,
  Progress,
  Tab,
  Tabs
} from '@heroui/react';
import { FileSpreadsheet, HandCoins, PiggyBank } from 'lucide-react';

const incomes = [
  { professional: 'María Gómez', amount: 'PYG 1.200.000', concept: 'Clases grupales', trend: '+12%' },
  { professional: 'Juan López', amount: 'PYG 800.000', concept: 'Sesiones kine', trend: '+5%' }
];

const expenses = [
  { concept: 'Alquiler estudio', amount: 'PYG 1.000.000', shared: 'Equal (50/50)' },
  { concept: 'Luz y agua', amount: 'PYG 320.000', shared: 'Percent (60/40)' }
];

export default function FinancesPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 rounded-2xl border border-divider bg-content1/80 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div>
          <h1 className="text-2xl font-semibold">Finanzas del estudio</h1>
          <p className="text-sm text-foreground/60">
            Registra ingresos privados por profesional y egresos compartidos con reglas de prorrateo, manteniendo visibilidad móvil primero.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button color="primary" startContent={<HandCoins className="h-4 w-4" />} size="sm">
            Registrar ingreso
          </Button>
          <Button variant="bordered" startContent={<FileSpreadsheet className="h-4 w-4" />} size="sm">
            Exportar CSV
          </Button>
        </div>
      </header>

      <Tabs aria-label="Resumen financiero" color="primary" variant="bordered">
        <Tab key="overview" title="Resumen">
          <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card radius="lg" shadow="sm" className="border border-divider bg-content1 lg:col-span-2">
              <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
                <h2 className="text-base font-semibold">Ingresos privados</h2>
                <p className="text-xs text-foreground/60">Visible sólo para cada profesional y el tenant admin.</p>
              </CardHeader>
              <Divider />
              <CardBody className="gap-3 px-4 py-5 text-sm sm:px-6">
                {incomes.map((income) => (
                  <div key={income.professional} className="flex flex-col gap-1 rounded-xl border border-success/40 bg-success/5 p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-foreground">{income.professional}</span>
                      <span className="font-semibold text-success">{income.amount}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs text-foreground/60">
                      <span>{income.concept}</span>
                      <Chip size="sm" color="success" variant="flat">
                        {income.trend}
                      </Chip>
                    </div>
                  </div>
                ))}
              </CardBody>
            </Card>
            <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
              <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
                <h2 className="text-base font-semibold">Balance del mes</h2>
                <p className="text-xs text-foreground/60">Se actualiza con los registros diarios.</p>
              </CardHeader>
              <Divider />
              <CardBody className="space-y-4 px-4 py-5 sm:px-6">
                <div className="flex flex-col gap-1">
                  <span className="text-xs uppercase tracking-wide text-foreground/50">Margen estimado</span>
                  <span className="text-xl font-semibold text-foreground">PYG 1.280.000</span>
                  <Progress value={68} color="primary" aria-label="Margen mensual" />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-foreground/60">Ingresos del mes</span>
                  <span className="font-medium text-success">PYG 5.200.000</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-foreground/60">Egresos compartidos</span>
                  <span className="font-medium text-danger">PYG 3.920.000</span>
                </div>
                <Chip startContent={<PiggyBank className="h-4 w-4" />} variant="flat" color="primary">
                  Objetivo de ahorro alcanzado 68%
                </Chip>
              </CardBody>
            </Card>
          </section>
        </Tab>
        <Tab key="expenses" title="Egresos">
          <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
              <h2 className="text-base font-semibold">Egresos compartidos</h2>
              <p className="text-xs text-foreground/60">Distribuye automáticamente según regla configurada.</p>
            </CardHeader>
            <Divider />
            <CardBody className="gap-3 px-4 py-5 text-sm sm:px-6">
              {expenses.map((expense) => (
                <div key={expense.concept} className="flex flex-col gap-2 rounded-xl border border-danger/40 bg-danger/5 p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-foreground">{expense.concept}</span>
                    <span className="font-semibold text-danger">{expense.amount}</span>
                  </div>
                  <span className="text-xs text-foreground/60">{expense.shared}</span>
                </div>
              ))}
            </CardBody>
          </Card>
        </Tab>
      </Tabs>
    </div>
  );
}
