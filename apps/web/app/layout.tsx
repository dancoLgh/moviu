import './globals.css';
import type { ReactNode } from 'react';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-slate-950 text-slate-50">
        <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 p-6">
          <header className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h1 className="text-2xl font-semibold text-brand">moviu</h1>
              <p className="text-sm text-slate-400">Suite para estudios de Pilates &amp; Kinesiología</p>
            </div>
            <nav className="flex gap-3 text-sm text-slate-300">
              <a href="/dashboard">Dashboard</a>
              <a href="/calendar">Agenda</a>
              <a href="/plans">Planes</a>
              <a href="/services">Servicios</a>
              <a href="/members">Miembros</a>
              <a href="/finances">Finanzas</a>
              <a href="/settings">Configuración</a>
              <a href="/portal">Portal</a>
            </nav>
          </header>
          <main className="flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
