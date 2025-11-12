'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Button,
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  NavbarMenu,
  NavbarMenuItem,
  NavbarMenuToggle
} from '@heroui/react';

const navigation = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Agenda', href: '/calendar' },
  { label: 'Planes', href: '/plans' },
  { label: 'Servicios', href: '/services' },
  { label: 'Miembros', href: '/members' },
  { label: 'Finanzas', href: '/finances' },
  { label: 'Configuración', href: '/settings' },
  { label: 'Portal', href: '/portal' }
];

export function AppNavbar() {
  const pathname = usePathname();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const active = useMemo(() => {
    if (!pathname) return '';
    const match = navigation.find((item) => pathname.startsWith(item.href));
    return match?.href ?? '';
  }, [pathname]);

  return (
    <Navbar
      maxWidth="2xl"
      isMenuOpen={isMenuOpen}
      onMenuOpenChange={setIsMenuOpen}
      className="border-b border-divider bg-background/80 backdrop-blur-xl"
    >
      <NavbarContent justify="start">
        <NavbarMenuToggle aria-label={isMenuOpen ? 'Cerrar menú' : 'Abrir menú'} className="sm:hidden" />
        <NavbarBrand className="flex flex-col items-start">
          <span className="text-base font-semibold text-brand">moviu</span>
          <span className="text-[11px] font-medium text-foreground/60">
            Pilates &amp; Kinesiología
          </span>
        </NavbarBrand>
      </NavbarContent>
      <NavbarContent className="hidden gap-3 sm:flex" justify="end">
        {navigation.map((item) => (
          <NavbarItem key={item.href} isActive={active === item.href}>
            <Button
              as={Link}
              href={item.href}
              variant={active === item.href ? 'solid' : 'light'}
              color={active === item.href ? 'primary' : 'default'}
              size="sm"
            >
              {item.label}
            </Button>
          </NavbarItem>
        ))}
      </NavbarContent>
      <NavbarMenu className="gap-2">
        {navigation.map((item) => (
          <NavbarMenuItem key={item.href} isActive={active === item.href}>
            <Button
              as={Link}
              href={item.href}
              variant={active === item.href ? 'solid' : 'light'}
              color={active === item.href ? 'primary' : 'default'}
              size="md"
              fullWidth
              onPress={() => setIsMenuOpen(false)}
            >
              {item.label}
            </Button>
          </NavbarMenuItem>
        ))}
      </NavbarMenu>
    </Navbar>
  );
}
