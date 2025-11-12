# moviu

MVP para la gestión de un estudio de Pilates y Kinesiología construido sobre Next.js 16 y Supabase.

## Requisitos

- Node.js 20+
- pnpm 9+
- Supabase CLI 1.200+

## Instalación

```bash
pnpm install
pnpm --filter web install
```

## Desarrollo web

```bash
pnpm dev
```

## Base de datos

```bash
supabase db reset
supabase db seed --file supabase/seeds/000_demo.sql
```

## Edge Functions

```bash
supabase functions serve cancel-class
supabase functions serve book-makeup
supabase functions serve suggest-slots
supabase functions serve schedule-reminders
```

## Tests E2E

```bash
pnpm test:e2e
```
