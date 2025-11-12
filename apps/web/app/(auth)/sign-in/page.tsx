import { Button, Card, CardBody, CardHeader, Input } from '@heroui/react';

export default function SignInPage() {
  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4 py-10">
      <Card as="form" radius="lg" shadow="sm" className="w-full max-w-sm border border-divider bg-content1">
        <CardHeader className="flex flex-col gap-2 px-6 pt-6 text-center">
          <h1 className="text-xl font-semibold">Ingresa a moviu</h1>
          <p className="text-sm text-foreground/60">Recibirás un enlace seguro en tu correo registrado.</p>
        </CardHeader>
        <CardBody className="gap-4 px-6 pb-6">
          <Input type="email" label="Email" placeholder="tu@email.com" variant="bordered" isRequired />
          <Button color="primary" type="submit" className="w-full">
            Enviar enlace
          </Button>
        </CardBody>
      </Card>
    </div>
  );
}
