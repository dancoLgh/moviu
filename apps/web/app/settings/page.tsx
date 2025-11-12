import { Button, Card, CardBody, CardHeader, Divider, Input, Select, SelectItem } from '@heroui/react';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold">Configuración del estudio</h2>
        <p className="text-sm text-foreground/60">
          Actualiza datos generales, zona horaria por defecto e idiomas disponibles para el portal.
        </p>
      </header>
      <Card as="form" radius="lg" shadow="sm" className="border border-divider bg-content1">
        <CardHeader className="px-4 pt-4 sm:px-6">
          <h3 className="text-base font-semibold">Datos principales</h3>
        </CardHeader>
        <Divider />
        <CardBody className="flex flex-col gap-4 px-4 py-6 sm:px-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label="Nombre del estudio"
              defaultValue="Elementos Pilates & Kine"
              variant="bordered"
            />
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
    </div>
  );
}
