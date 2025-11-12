'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Card, CardBody } from '@heroui/react';
import clsx from 'clsx';
import { navigationItems } from './navigation';

export function MobileDock() {
  const pathname = usePathname();

  return (
    <nav className="sticky bottom-0 z-40 border-t border-divider/70 bg-background/90 backdrop-blur-xl md:hidden">
      <Card radius="none" shadow="sm" className="bg-transparent">
        <CardBody className="flex items-center justify-around gap-1 px-2 py-2">
          {navigationItems.slice(0, 4).map((item) => {
            const Icon = item.icon;
            const isActive = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  'flex flex-1 flex-col items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-foreground/50 hover:bg-content2/80 hover:text-foreground'
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </CardBody>
      </Card>
    </nav>
  );
}
