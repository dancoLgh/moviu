'use client';

import { HeroUIProvider } from '@heroui/react';
import { ThemeProvider } from 'next-themes';
import { useRouter } from 'next/navigation';
import type { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  const router = useRouter();

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <HeroUIProvider navigate={router.push}>{children}</HeroUIProvider>
    </ThemeProvider>
  );
}
