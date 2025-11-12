import { Button, Card, CardBody, CardHeader, Input } from '@heroui/react';

export default function SignUpPage() {
  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4 py-10">
      <Card as="form" radius="lg" shadow="sm" className="w-full max-w-sm border border-divider bg-content1">
        <CardHeader className="flex flex-col gap-2 px-6 pt-6 text-center">
          <h1 className="text-xl font-semibold">Crear cuenta de estudio</h1>
          <p className="text-sm text-foreground/60">Configura tu tenant y comienza a agendar en minutos.</p>
        </CardHeader>
        <CardBody className="gap-4 px-6 pb-6">
          <Input label="Nombre del estudio" placeholder="Elementos Pilates" variant="bordered" isRequired />
          <Input type="email" label="Email" placeholder="contacto@estudio.test" variant="bordered" isRequired />
          <Button color="primary" type="submit" className="w-full">
            Crear tenant
          </Button>
        </CardBody>
      </Card>
    </div>
  );
}
