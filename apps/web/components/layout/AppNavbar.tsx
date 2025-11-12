'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Avatar,
  Button,
  Divider,
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  NavbarMenu,
  NavbarMenuItem,
  NavbarMenuToggle
} from '@heroui/react';
import { ChevronRight, MoonStar, SunMedium } from 'lucide-react';
import { useTheme } from 'next-themes';
import { navigationItems } from './navigation';

export function AppNavbar() {
  const pathname = usePathname();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { theme, resolvedTheme, setTheme } = useTheme();

  const active = useMemo(() => {
    if (!pathname) return '';
    const match = navigationItems.find((item) => pathname.startsWith(item.href));
    return match?.href ?? '';
  }, [pathname]);

  const toggleTheme = () => {
    const nextTheme = (resolvedTheme ?? theme) === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
  };

  return (
    <Navbar
      maxWidth="2xl"
      isMenuOpen={isMenuOpen}
      onMenuOpenChange={setIsMenuOpen}
      className="sticky top-0 z-40 border-b border-divider bg-background/80 backdrop-blur-xl"
    >
      <NavbarContent justify="start">
        <NavbarMenuToggle
          aria-label={isMenuOpen ? 'Cerrar menú' : 'Abrir menú'}
          className="sm:hidden"
        />
        <NavbarBrand className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <span className="text-lg font-semibold">m</span>
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-sm font-semibold uppercase tracking-wide">moviu</span>
            <span className="text-[11px] text-foreground/60">Pilates &amp; Kine Studio</span>
          </div>
        </NavbarBrand>
      </NavbarContent>

      <NavbarContent className="hidden gap-2 md:flex" justify="center">
        {navigationItems.slice(0, 5).map((item) => {
          const Icon = item.icon;
          const isActive = active === item.href;
          return (
            <NavbarItem key={item.href} isActive={isActive}>
              <Button
                as={Link}
                href={item.href}
                size="sm"
                variant={isActive ? 'flat' : 'light'}
                color={isActive ? 'primary' : 'default'}
                startContent={<Icon className="h-4 w-4" />}
              >
                {item.label}
              </Button>
            </NavbarItem>
          );
        })}
      </NavbarContent>

      <NavbarContent justify="end">
        <Button
          isIconOnly
          variant="light"
          size="sm"
          onPress={toggleTheme}
          aria-label="Cambiar tema"
        >
          {(resolvedTheme ?? theme) === 'dark' ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
        </Button>
        <Dropdown placement="bottom-end">
          <DropdownTrigger>
            <Avatar
              as="button"
              size="sm"
              className="transition-transform hover:scale-105"
              name="María"
              color="primary"
            />
          </DropdownTrigger>
          <DropdownMenu aria-label="Opciones de cuenta" variant="flat">
            <DropdownItem key="profile" className="gap-2">
              <div>
                <p className="text-sm font-semibold">María Gómez</p>
                <p className="text-xs text-foreground/50">tenant_admin</p>
              </div>
            </DropdownItem>
            <DropdownItem key="settings" as={Link} href="/settings">
              Preferencias
            </DropdownItem>
            <DropdownItem key="logout" className="text-danger" color="danger">
              Cerrar sesión
            </DropdownItem>
          </DropdownMenu>
        </Dropdown>
      </NavbarContent>

      <NavbarMenu className="gap-2">
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.href;
          return (
            <NavbarMenuItem key={item.href} isActive={isActive}>
              <Button
                as={Link}
                href={item.href}
                variant={isActive ? 'solid' : 'light'}
                color={isActive ? 'primary' : 'default'}
                size="md"
                fullWidth
                endContent={<ChevronRight className="h-4 w-4" />}
                startContent={<Icon className="h-4 w-4" />}
                onPress={() => setIsMenuOpen(false)}
              >
                {item.label}
              </Button>
              <p className="pt-2 text-start text-xs text-foreground/60">{item.description}</p>
              <Divider className="my-3" />
            </NavbarMenuItem>
          );
        })}
      </NavbarMenu>
    </Navbar>
  );
}
