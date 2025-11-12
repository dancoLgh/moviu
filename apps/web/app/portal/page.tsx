import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Chip,
  Divider,
  ScrollShadow,
  Tab,
  Tabs
} from '@heroui/react';
import { CalendarClock, RefreshCcw } from 'lucide-react';

const upcoming = [
  { service: 'Pilates grupal', date: 'Lunes 15:00', status: 'Programada', canRecover: true },
  { service: 'Pilates grupal', date: 'Miércoles 15:00', status: 'Recupero sugerido', canRecover: true },
  { service: 'Kinesiología', date: 'Jueves 11:00', status: 'Confirmada', canRecover: false }
];

const timeline = [
  { date: '10/10', note: 'Evolución postural cargada', tags: ['Foto', 'Antes/Después'] },
  { date: '05/10', note: 'Sesión Kine con liberación miofascial', tags: ['Kine'] }
];

export default function PortalPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 rounded-2xl border border-divider bg-content1/80 p-4 sm:p-6">
        <h1 className="text-2xl font-semibold">Portal del alumno</h1>
        <p className="text-sm text-foreground/60">
          Gestiona clases programadas, cancelaciones dentro de la política y recuperos disponibles con experiencia mobile first.
        </p>
      </header>

      <Tabs aria-label="Portal" color="primary" variant="underlined">
        <Tab key="agenda" title="Agenda">
          <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="flex flex-col gap-2 px-4 pt-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div>
                <h2 className="text-base font-semibold">Mi plan actual</h2>
                <p className="text-xs text-foreground/60">Máximo 3×/semana · Vigente hasta 30/11</p>
              </div>
              <Chip size="sm" color="primary" variant="flat">
                Recuperos disponibles: 1
              </Chip>
            </CardHeader>
            <Divider />
            <CardBody className="space-y-3 px-4 py-4 text-sm text-foreground/70 sm:px-6">
              <p>Recordá cancelar con al menos 6 horas de anticipación para conservar tu recupero.</p>
              <p>Los cambios offline se sincronizan automáticamente cuando vuelvas a tener conexión.</p>
            </CardBody>
          </Card>
          <Card radius="lg" shadow="sm" className="mt-4 border border-divider bg-content1">
            <CardHeader className="flex items-center gap-2 px-4 pt-4 sm:px-6">
              <CalendarClock className="h-4 w-4 text-primary" />
              <h3 className="text-base font-semibold">Próximas clases</h3>
            </CardHeader>
            <Divider />
            <CardBody className="px-0 pb-4 pt-0 sm:px-0">
              <ScrollShadow className="max-h-[320px]">
                <div className="flex flex-col gap-3 px-4 py-4">
                  {upcoming.map((item) => (
                    <div
                      key={item.date}
                      className="flex flex-col gap-3 rounded-xl border border-divider/70 bg-content2/60 p-4 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="flex flex-col gap-1">
                        <p className="text-sm font-semibold text-foreground">{item.service}</p>
                        <p className="text-xs text-foreground/60">{item.date}</p>
                      </div>
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                        <Chip size="sm" color={item.status.includes('Recupero') ? 'warning' : 'success'} variant="flat">
                          {item.status}
                        </Chip>
                        <div className="flex flex-1 justify-end gap-2">
                          <Button variant="bordered" color="default" size="sm" className="flex-1 sm:flex-none">
                            Cancelar
                          </Button>
                          <Button
                            color="primary"
                            size="sm"
                            className="flex-1 sm:flex-none"
                            isDisabled={!item.canRecover}
                            startContent={<RefreshCcw className="h-4 w-4" />}
                          >
                            Recuperar
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollShadow>
            </CardBody>
          </Card>
        </Tab>
        <Tab key="timeline" title="Evolución">
          <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
              <h3 className="text-base font-semibold">Mi progreso</h3>
              <p className="text-xs text-foreground/60">Subí fotos de evolución y documentos clínicos desde el portal.</p>
            </CardHeader>
            <Divider />
            <CardBody className="space-y-3 px-4 py-4 sm:px-6">
              {timeline.map((item) => (
                <div key={item.date} className="flex flex-col gap-2 rounded-xl border border-divider/70 bg-content2/60 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">{item.note}</span>
                    <Chip size="sm" variant="flat" color="secondary">
                      {item.date}
                    </Chip>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {item.tags.map((tag) => (
                      <Chip key={tag} size="sm" variant="bordered">
                        {tag}
                      </Chip>
                    ))}
                  </div>
                </div>
              ))}
            </CardBody>
          </Card>
        </Tab>
      </Tabs>
    </div>
  );
}
