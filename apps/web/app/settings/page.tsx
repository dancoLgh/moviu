import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Input,
  Select,
  SelectItem,
  Switch,
  Tab,
  Tabs,
  Textarea
} from '@heroui/react';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 rounded-2xl border border-divider bg-content1/80 p-4 sm:p-6">
        <h1 className="text-2xl font-semibold">Configuración del estudio</h1>
        <p className="text-sm text-foreground/60">
          Actualiza datos generales, zona horaria e integra notificaciones para cada rol dentro del tenant.
        </p>
      </header>

      <Tabs aria-label="Configuración" color="primary" variant="underlined">
        <Tab key="general" title="Generales">
          <Card as="form" radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="px-4 pt-4 sm:px-6">
              <h3 className="text-base font-semibold">Datos principales</h3>
            </CardHeader>
            <Divider />
            <CardBody className="flex flex-col gap-4 px-4 py-6 sm:px-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input label="Nombre del estudio" defaultValue="Elementos Pilates & Kine" variant="bordered" />
                <Input label="Email de facturación" defaultValue="billing@elementos.test" variant="bordered" />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Select label="Zona horaria" variant="bordered" defaultSelectedKeys={['America/Asuncion']}>
                  <SelectItem key="America/Asuncion">America/Asuncion</SelectItem>
                  <SelectItem key="America/Buenos_Aires">America/Buenos_Aires</SelectItem>
                </Select>
                <Select label="Idioma" variant="bordered" defaultSelectedKeys={['es-PY']}>
                  <SelectItem key="es-PY">Español (PY)</SelectItem>
                  <SelectItem key="en-US">English</SelectItem>
                </Select>
              </div>
              <Textarea
                label="Política de cancelación por defecto"
                minRows={3}
                placeholder="Describe la política por defecto aplicada a nuevos planes"
                variant="bordered"
              />
              <div className="flex flex-col gap-2 text-xs text-foreground/60">
                <p>
                  Las actualizaciones se propagan automáticamente a las políticas RLS y a las notificaciones del portal.
                </p>
                <p>
                  Los cambios de idioma aplican a nuevos usuarios; los existentes pueden elegir su preferencia en el portal.
                </p>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
                <Button color="primary" type="submit" className="w-full sm:w-auto">
                  Guardar cambios
                </Button>
              </div>
            </CardBody>
          </Card>
        </Tab>
        <Tab key="notificaciones" title="Notificaciones">
          <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="px-4 pt-4 sm:px-6">
              <h3 className="text-base font-semibold">Preferencias por rol</h3>
            </CardHeader>
            <Divider />
            <CardBody className="flex flex-col gap-4 px-4 py-6 sm:px-6">
              <PreferenceRow label="Recordatorios 24h" description="Notifica a miembros y profesionales 24h antes de cada clase." />
              <PreferenceRow label="Recordatorios 2h" description="Aviso corto previo a la clase con enlace para cancelar." />
              <PreferenceRow label="Finanzas semanales" description="Resumen de ingresos privados por profesional." />
            </CardBody>
          </Card>
        </Tab>
      </Tabs>
    </div>
  );
}

function PreferenceRow({ label, description }: { label: string; description: string }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-divider/70 bg-content2/60 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-1">
        <span className="text-sm font-semibold">{label}</span>
        <span className="text-xs text-foreground/60">{description}</span>
      </div>
      <Switch defaultSelected size="sm">
        Activo
      </Switch>
    </div>
  );
}
