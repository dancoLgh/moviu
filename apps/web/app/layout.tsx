import './globals.css';
import type { ReactNode } from 'react';
import { Providers } from './providers';
import { AppNavbar } from '@/components/layout/AppNavbar';
import { MobileDock } from '@/components/layout/MobileDock';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 text-foreground">
        <Providers>
          <div className="flex min-h-screen flex-col">
            <AppNavbar />
            <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 pb-24 pt-6 sm:px-6 lg:px-8 lg:pb-12">
              {children}
            </main>
            <MobileDock />
          </div>
        </Providers>
      </body>
    </html>
  );
}
