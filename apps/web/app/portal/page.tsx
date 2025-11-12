import { Button, Card, CardBody, CardHeader, Chip, Divider } from '@heroui/react';

const upcoming = [
  { service: 'Pilates grupal', date: 'Lunes 15:00', status: 'Programada' },
  { service: 'Pilates grupal', date: 'Miércoles 15:00', status: 'Recupero disponible' }
];

export default function PortalPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold">Mi portal</h2>
        <p className="text-sm text-foreground/60">
          Gestiona clases programadas, cancelaciones dentro de la política y recuperos disponibles.
        </p>
      </header>
      <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
        <CardHeader className="flex flex-col gap-2 px-4 pt-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <h3 className="text-base font-semibold">Mi plan</h3>
            <p className="text-xs text-foreground/60">Máximo 3×/semana · Vigente hasta 30/11</p>
          </div>
          <Chip size="sm" color="primary" variant="flat">
            Recuperos disponibles: 1
          </Chip>
        </CardHeader>
        <Divider />
        <CardBody className="space-y-3 px-4 py-4 text-sm text-foreground/70 sm:px-6">
          <p>Recordá cancelar con al menos 6 horas de anticipación para conservar tu recupero.</p>
          <p>Los cambios realizados offline se sincronizan automáticamente cuando vuelvas a tener conexión.</p>
        </CardBody>
      </Card>
      <section className="space-y-3">
        <h3 className="text-base font-semibold">Próximas clases</h3>
        {upcoming.map((item) => (
          <Card
            key={item.date}
            radius="lg"
            shadow="sm"
            className="border border-divider bg-content1"
          >
            <CardBody className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div className="flex flex-col gap-1">
                <p className="text-sm font-semibold text-foreground">{item.service}</p>
                <p className="text-xs text-foreground/60">{item.date}</p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <Chip size="sm" color={item.status === 'Recupero disponible' ? 'warning' : 'success'} variant="flat">
                  {item.status}
                </Chip>
                <div className="flex flex-1 justify-end gap-2">
                  <Button variant="bordered" color="default" size="sm" className="flex-1 sm:flex-none">
                    Cancelar
                  </Button>
                  <Button color="primary" size="sm" className="flex-1 sm:flex-none">
                    Recuperar
                  </Button>
                </div>
              </div>
            </CardBody>
          </Card>
        ))}
      </section>
    </div>
  );
}
