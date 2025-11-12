import { PlanWizard } from '@/components/forms/PlanWizard';
import { Badge, Card, CardBody, CardHeader, Chip, Divider } from '@heroui/react';

const demoPlans = [
  {
    name: 'Básico 1×/semana',
    price: 'PYG 100.000',
    times: '1 clase',
    makeups: '1 recupero/mes',
    policy: 'Aviso 12h'
  },
  {
    name: 'Máximo 3×/semana',
    price: 'PYG 350.000',
    times: '3 clases',
    makeups: '1 recupero/mes',
    policy: 'Aviso 6h'
  }
];

export default function PlansPage() {
  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-3 rounded-2xl border border-divider bg-content1/80 p-4 sm:p-6">
        <h1 className="text-2xl font-semibold">Planes de suscripción</h1>
        <p className="text-sm text-foreground/60">
          Define beneficios, reglas de recupero y duplicación automática de días por servicio con un flujo pensado para mobile.
        </p>
      </section>
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {demoPlans.map((plan) => (
          <Card key={plan.name} radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
              <div className="flex items-start justify-between">
                <div className="flex flex-col gap-1">
                  <h3 className="text-lg font-semibold">{plan.name}</h3>
                  <p className="text-xs text-foreground/60">{plan.times}</p>
                </div>
                <Badge color="primary" variant="flat" className="text-[11px] uppercase">
                  {plan.policy}
                </Badge>
              </div>
            </CardHeader>
            <Divider />
            <CardBody className="gap-3 px-4 py-5 sm:px-6">
              <p className="text-2xl font-semibold text-primary">{plan.price}</p>
              <Chip size="sm" color="warning" variant="flat" className="w-max">
                {plan.makeups}
              </Chip>
              <p className="text-xs text-foreground/50">
                Reglas recomendadas: aviso {plan.policy.includes('6') ? '6' : '12'}&nbsp;h, máximo un recupero mensual y buffers
                según servicio asignado.
              </p>
            </CardBody>
          </Card>
        ))}
      </section>
      <PlanWizard />
    </div>
  );
}
