import { Card, CardBody, CardHeader, Chip, Table, TableBody, TableCell, TableColumn, TableHeader, TableRow } from '@heroui/react';

const members = [
  { name: 'Ana Torres', plan: 'Máximo 3×/sem', status: 'Activa', nextClass: 'Lunes 15:00' },
  { name: 'Pedro Díaz', plan: 'Básico 1×/sem', status: 'Activa', nextClass: 'Miércoles 18:00' }
];

export default function MembersPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold">Miembros</h2>
        <p className="text-sm text-foreground/60">
          Gestiona suscripciones, recuperos mensuales y acceso al portal del alumno.
        </p>
      </header>
      <Card radius="lg" shadow="sm" className="border border-divider bg-content1">
        <CardHeader className="px-4 pt-4 sm:px-6">
          <h3 className="text-base font-semibold">Suscripciones activas</h3>
        </CardHeader>
        <CardBody className="px-2 pb-4 pt-0 sm:px-4">
          <Table aria-label="Listado de miembros" removeWrapper>
            <TableHeader>
              <TableColumn>Nombre</TableColumn>
              <TableColumn>Plan</TableColumn>
              <TableColumn>Estado</TableColumn>
              <TableColumn>Próxima clase</TableColumn>
            </TableHeader>
            <TableBody emptyContent="Aún no hay miembros cargados" items={members}>
              {(member) => (
                <TableRow key={member.name}>
                  <TableCell className="font-medium">{member.name}</TableCell>
                  <TableCell className="text-foreground/70">{member.plan}</TableCell>
                  <TableCell>
                    <Chip size="sm" color="success" variant="flat">
                      {member.status}
                    </Chip>
                  </TableCell>
                  <TableCell className="text-foreground/70">{member.nextClass}</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardBody>
      </Card>
    </div>
  );
}
