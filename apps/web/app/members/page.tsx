import {
  Avatar,
  Button,
  Card,
  CardBody,
  CardHeader,
  Chip,
  Divider,
  ScrollShadow,
  Table,
  TableBody,
  TableCell,
  TableColumn,
  TableHeader,
  TableRow,
  Tab,
  Tabs
} from '@heroui/react';
import { UserPlus } from 'lucide-react';

const members = [
  { name: 'Ana Torres', plan: 'Máximo 3×/sem', status: 'Activa', nextClass: 'Lunes 15:00', makeups: 1 },
  { name: 'Pedro Díaz', plan: 'Básico 1×/sem', status: 'Activa', nextClass: 'Miércoles 18:00', makeups: 0 },
  { name: 'Laura Ruiz', plan: 'Kine 8 sesiones', status: 'En pausa', nextClass: 'Por reprogramar', makeups: 0 }
];

const recoveries = [
  { name: 'Ana Torres', available: 1, suggestion: 'Miércoles · 15:00' },
  { name: 'Pedro Díaz', available: 0, suggestion: 'Solicitar excepción' }
];

export default function MembersPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 rounded-2xl border border-divider bg-content1/80 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div>
          <h1 className="text-2xl font-semibold">Miembros y pacientes</h1>
          <p className="text-sm text-foreground/60">
            Gestiona suscripciones, recuperos mensuales y acceso al portal del alumno desde un flujo móvil primero.
          </p>
        </div>
        <Button color="primary" startContent={<UserPlus className="h-4 w-4" />} size="sm">
          Nuevo miembro
        </Button>
      </header>

      <Tabs aria-label="Gestión de miembros" color="primary" variant="underlined">
        <Tab key="activos" title="Activos">
          <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
              <h3 className="text-base font-semibold">Suscripciones activas</h3>
              <p className="text-xs text-foreground/60">Sincronizamos con Supabase para respetar RLS por tenant.</p>
            </CardHeader>
            <Divider />
            <CardBody className="px-0 pb-4 pt-0 sm:px-0">
              <ScrollShadow className="max-h-[320px]">
                <Table aria-label="Listado de miembros" removeWrapper className="min-w-full">
                  <TableHeader>
                    <TableColumn>Miembro</TableColumn>
                    <TableColumn>Plan</TableColumn>
                    <TableColumn>Estado</TableColumn>
                    <TableColumn>Próxima clase</TableColumn>
                    <TableColumn>Recuperos</TableColumn>
                  </TableHeader>
                  <TableBody emptyContent="Aún no hay miembros cargados" items={members}>
                    {(member) => (
                      <TableRow key={member.name}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <Avatar name={member.name} size="sm" color="primary" />
                            <span className="font-medium">{member.name}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-foreground/70">{member.plan}</TableCell>
                        <TableCell>
                          <Chip
                            size="sm"
                            color={member.status === 'Activa' ? 'success' : member.status === 'En pausa' ? 'warning' : 'default'}
                            variant="flat"
                          >
                            {member.status}
                          </Chip>
                        </TableCell>
                        <TableCell className="text-foreground/70">{member.nextClass}</TableCell>
                        <TableCell>
                          <Chip size="sm" variant="bordered" color={member.makeups > 0 ? 'warning' : 'default'}>
                            {member.makeups}
                          </Chip>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </ScrollShadow>
            </CardBody>
          </Card>
        </Tab>
        <Tab key="recuperos" title="Recuperos">
          <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
            <CardHeader className="flex flex-col gap-1 px-4 pt-4 sm:px-6">
              <h3 className="text-base font-semibold">Saldo mensual</h3>
              <p className="text-xs text-foreground/60">Los recuperos se reinician por cron y respetan el tope del plan.</p>
            </CardHeader>
            <Divider />
            <CardBody className="space-y-3 px-4 py-4 text-sm text-foreground/70 sm:px-6">
              {recoveries.map((item) => (
                <div
                  key={item.name}
                  className="flex flex-col gap-2 rounded-xl border border-divider/70 bg-content2/60 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold">{item.name}</span>
                    <span className="text-xs text-foreground/60">{item.available} recupero(s) disponible(s)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Chip size="sm" color={item.available > 0 ? 'primary' : 'default'} variant="flat">
                      {item.suggestion}
                    </Chip>
                    <Button size="sm" variant="light" color="primary">
                      Asignar
                    </Button>
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
