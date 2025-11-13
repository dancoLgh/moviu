# Plataforma Moviu — Estudio de Pilates y Kinesiología

Este repositorio describe la arquitectura funcional y técnica de **Moviu**, una PWA móvil para gestionar un estudio de Pilates y Kinesiología. El objetivo es ofrecer una experiencia tipo "app nativa" para administradores, profesionales y alumnos/pacientes utilizando **React + HeroUI (TailwindCSS)** en el frontend y **Supabase** como backend (Auth, Postgres, Storage, Functions y Realtime).

> **Modelos principales**: Usuarios, Servicios, Planes, Suscripciones, Agenda/Reservas, Evolución (Pilates/Kine), Notificaciones, Ingresos/Egresos y fichas clínicas detalladas.

---

## 1. Funcionalidades del MVP

### 1.1 Servicios y planes
- Servicios disponibles: **Pilates (grupal)** y **Kinesiología (1:1)**.
- Definición de cupos, duración, recurrencia y políticas de cancelación/recupero.
- Planes de ejemplo: _Pilates Básico_ (1 vez/semana), _Pilates Máximo_ (3 veces/semana).
- Asistente de horarios que permite duplicar bloques en días que comparten la misma hora.

### 1.2 Agenda y calendario
- Disponibilidad por profesional mediante bloques configurables.
- Reservas únicas o recurrentes con validación de cupo/choques.
- Reprogramaciones individuales o masivas. Pilates notifica al grupo y habilita recupero.
- Políticas parametrizables: ventana de cancelación, recuperos mensuales, etc.

### 1.3 Suscripciones y recuperos
- Alta/baja/pausa de suscripciones con control de vencimientos.
- Contador de clases disponibles y saldo de recuperos con vencimiento.
- Cancelaciones devuelven saldo (según política) y habilitan calendario de recupero.

### 1.4 Portal del alumno/paciente
- Estado de suscripción, próximas clases y notificaciones.
- Cancelar clase, solicitar recupero y ver calendario libre.
- Línea de tiempo de evolución (fotos, notas, métricas).

### 1.5 Perfil y ficha clínica
- Datos básicos + contacto de emergencia.
- Kinesiología: ficha clínica completa (motivo, antecedentes, dolor, evaluación, adjuntos, plan terapéutico, sesiones, evolución).
- Pilates: evolución fotográfica, comparador antes/después y métricas opcionales.

### 1.6 Notificaciones
- Web Push (PWA) para recordatorios de clases/turnos, cambios, vencimientos y recuperos.

### 1.7 Egresos/Ingresos
- Registro por profesional, con egresos compartidos prorrateados y reportes mensuales.

---

## 2. Arquitectura

| Capa | Tecnología | Detalles |
|------|------------|----------|
| Frontend | React 18 + Vite, HeroUI v2, TailwindCSS 4 | PWA (Service Worker, manifest.json) con enfoque mobile-first. |
| Backend | Supabase (Postgres + Auth + Storage + Edge Functions + Realtime) | RLS por rol/propiedad, funciones para notificaciones, reservas y reportes. |
| Notificaciones | Supabase Edge Functions + Web Push | Programación de jobs para recordatorios y cambios. |
| Storage | Supabase Storage privado | Fotos de evolución y estudios médicos con URLs firmadas. |
| CI/CD | GitHub Actions (sugerido) | Lint, pruebas y despliegues automáticos a Vercel/Netlify. |

---

## 3. Configuración del entorno de desarrollo

### 3.1 Prerrequisitos
1. **Node.js 20+** y **pnpm 9+** (`corepack enable`).
2. **Supabase CLI** (`npm install -g supabase`).
3. Cuenta en [Supabase](https://supabase.com/) con un proyecto creado.
4. Opcional: **Docker** para ejecutar Supabase local (`supabase start`).

### 3.2 Variables de entorno
Crear un archivo `.env` en la raíz con la siguiente base:
```bash
VITE_SUPABASE_URL="https://<project>.supabase.co"
VITE_SUPABASE_ANON_KEY="<public-anon-key>"
VITE_SUPABASE_SERVICE_ROLE_KEY="<service-role-key>" # solo para funciones/CLI
VITE_WEB_PUSH_PUBLIC_KEY="<vapid-public>"
WEB_PUSH_PRIVATE_KEY="<vapid-private>"
WEB_PUSH_SUBJECT="mailto:soporte@example.com"
```
Para producción, utilizar `.env.production` o variables seguras en el proveedor (Vercel/Netlify/GitHub Actions).

### 3.3 Inicializar Supabase local
```bash
supabase init           # crea el directorio supabase/
supabase start          # levanta Postgres, Auth y Storage locales
supabase db reset       # aplica migraciones sql existentes
```

### 3.4 Instalación de dependencias frontend
```bash
pnpm install
pnpm dev               # arranca Vite en modo PWA
```

### 3.5 Conexión con Supabase
- Configurar el archivo `src/lib/supabase.ts` con las variables VITE.
- Verificar que `supabase/migrations` contiene las tablas descritas (ver sección 5).
- Para Realtime y RLS, ejecutar `supabase db diff` tras los cambios y versionar los archivos SQL.

### 3.6 Notificaciones Push
1. Generar claves VAPID (`npx web-push generate-vapid-keys`).
2. Registrar el service worker en React (ej. `src/sw.ts`).
3. Implementar una Edge Function (`supabase/functions/send-reminders`) que use el servicio `web-push` y la tabla `Notification`.
4. Programar recordatorios con cron jobs (`supabase functions deploy send-reminders --no-verify-jwt`).

### 3.7 Almacenamiento de archivos
- Crear buckets privados en Supabase: `kine-studies` y `pilates-progress`.
- Activar RLS y definir políticas basadas en rol (propietario, profesional asignado, alumno).
- Usar `createSignedUrl` para compartir enlaces temporales.

---

## 4. Flujo de despliegue a producción

1. **Infraestructura**
   - Supabase en plan Pro o superior para funciones programadas y storage.
   - Dominio personalizado para la PWA (ej. `app.moviu.com`).

2. **Build frontend**
   ```bash
   pnpm build           # genera dist/
   pnpm preview         # verificación local
   ```

3. **Proveedor de hosting**
   - **Vercel** (recomendado) o **Netlify**.
   - Configurar variables de entorno en el panel (las mismas que en `.env`).
   - Activar _PWA caching_ y HTTPS obligatorio.

4. **Despliegue de Supabase**
   ```bash
   supabase db push
   supabase functions deploy send-reminders
   supabase storage policies set --from policies/storage.sql
   ```

5. **Automatización CI/CD** (ejemplo GitHub Actions)
   - Workflow que ejecute `pnpm install`, `pnpm test`, `pnpm build`.
   - Enviar migraciones con `supabase db push --non-interactive`.

6. **Post-despliegue**
   - Registrar `service worker` con `skipWaiting` + `clientsClaim` para actualizaciones.
   - Probar notificaciones, subida de archivos y reglas RLS usando usuarios reales.

---

## 5. Esquema de datos recomendado

| Tabla | Campos principales |
|-------|--------------------|
| `User` | `id`, `rol`, `email`, `metadata` |
| `Professional` | `id_user`, `especialidad`, `bio`, `disponibilidad` |
| `Student` | `id_user`, datos personales, `emergency_contact` |
| `Service` | `tipo`, `duracion`, `cupo`, `recurrencia`, `politicas` |
| `Plan` | `id_service`, `nombre`, `precio`, `veces_por_semana`, `reglas_recupero` |
| `Subscription` | `id_student`, `id_plan`, `estado`, `inicio`, `vencimiento`, `saldo_clases` |
| `ScheduleBlock` | `id_professional`, `dia_semana`, `hora_inicio`, `hora_fin`, `capacidad` |
| `Reservation` | `id_student`, `id_service`, `fecha`, `estado`, `tipo`, `id_recurrencia` |
| `Attendance` | `id_reservation`, `presente`, `motivo` |
| `KineRecord` | `id_patient`, `ficha_clinica` (JSON), `adjuntos` |
| `KineSession` | `id_record`, `fecha`, `tecnicas`, `EVA_pre/post` |
| `PilatesProgress` | `id_student`, `fecha`, `fotos`, `notas`, `metricas` |
| `Notification` | `id_user`, `tipo`, `payload`, `leido` |
| `Expense` | `id_professional/null`, `categoria`, `monto`, `compartido`, `prorrateo` |
| `Income` | `id_professional`, `origen`, `monto`, `fecha` |

> Utiliza tipos JSONB para campos flexibles (ficha clínica, métricas) y **RLS** basado en `auth.uid()` para asegurar el acceso por rol.

---

## 6. Seguridad y RLS

1. **Propiedad por registro**: cada fila en `Service`, `Plan`, `ScheduleBlock` y `Expense` incluye `owner_id`. Las políticas permiten `select/update/delete` únicamente al propietario.
2. **Clases grupales**: se otorga acceso a los alumnos inscritos mediante una tabla `ServiceMember` o utilizando `Reservation` con política `exists`.
3. **Storage**: buckets privados con políticas `auth.uid() = resource_owner` o pertenencia a la clase/sesión.
4. **Ingresos**: solo visibles por el profesional y administradores.
5. **Edge Functions**: validar `JWT` (cuando aplica) y utilizar `service_role` únicamente en backend seguro.

---

## 7. Métricas y reportes
- Asistencia % por clase/plan.
- Evolución por alumno (hitos, comparativas fotográficas, métricas físicas).
- Ingresos/egresos por mes y profesional con ratio.
- No-shows, cancelaciones tardías y recuperos utilizados.

---

## 8. Próximos pasos sugeridos
1. Scaffold del proyecto con Vite + React + TypeScript (`pnpm create vite`).
2. Integrar HeroUI y actualizar Tailwind a la versión 4 (peer dependency de HeroUI v2).
3. Implementar autenticación Supabase y layout básico (Dashboard profesional + Portal alumno).
4. Construir componentes clave: agenda (semana/día), asistente de horarios, ficha clínica editable y comparador de fotos.
5. Añadir pruebas E2E (Playwright) para flujos críticos: reserva, cancelación y carga de sesión.

---

## 9. Soporte
- Documentar nuevas migraciones en `supabase/migrations`.
- Usar issues/PRs para coordinar features.
- Consultas: soporte@moviu.app.


---

## 10. Aplicación de referencia (`web/`)

Para facilitar la exploración rápida del MVP se añadió un **frontend funcional** en `web/` construido con **Vite + React + TypeScript**. Esta app no sustituye la integración real con Supabase, pero maqueta todos los módulos descritos en la visión:

- Dashboard profesional con KPIs (asistencia, notificaciones, suscripciones) y lista de próximas clases.
- Gestión de servicios/planes y asistente para duplicar horarios recurrentes.
- Agenda semanal + vista puntual de disponibilidad por día con validación de cupos.
- Tabla de suscripciones con acciones de pausa/reactivación y control de recuperos.
- Portal del alumno con tarjeta de plan, notificaciones PWA simuladas y línea de tiempo de evolución (Pilates).
- Ficha clínica de Kinesiología con antecedentes, dolor, sesiones y adjuntos mockeados.
- Panel financiero con ratio ingreso/egreso por profesional.
- PWA lista para instalar (manifest, íconos, `service worker` básico con caché).

### 10.1 Ejecutar en desarrollo
```bash
cd web
npm install            # primera vez
npm run dev            # abre http://localhost:5173 (usa --host para LAN/PWA)
```
La app utiliza datos mock en `src/data/mockData.ts` y un `MoviuProvider` que emula altas/bajas de reservas, asistencias y notificaciones.

### 10.2 Build de producción
```bash
npm run build          # genera dist/
npm run preview        # sirve el build localmente
```
El `service worker` se registra desde `src/pwa.ts` y cachea `index.html` + `manifest`. Ajusta la estrategia antes de pasar a producción.

### 10.3 Integración con Supabase
1. Define las variables `VITE_SUPABASE_URL` y `VITE_SUPABASE_ANON_KEY` en `web/.env`.
2. Implementa un cliente en `src/lib/supabase.ts` y reemplaza `mockData` por llamadas reales.
3. Las acciones del `MoviuProvider` (`bookReservation`, `toggleAttendance`, `logFinance`, etc.) son el lugar ideal para conectar `RPC`, `Edge Functions` o `Supabase Realtime`.
4. Reutiliza los tipos de `src/types.ts` para mapear tus respuestas y minimizar discrepancias.

### 10.4 Buenas prácticas PWA
- Mantén el `manifest` sincronizado con la identidad visual de la marca (íconos en `public/icons/`).
- Habilita HTTPS y `service-worker` en el hosting (Vercel/Netlify requieren configuración mínima).
- Para Web Push necesitarás exponer la clave pública (`VITE_WEB_PUSH_PUBLIC_KEY`) y manejar la suscripción en el `service worker`.

Con este andamiaje puedes iterar sobre UX/UI sin bloquearte por el backend y, al mismo tiempo, validar los flujos descritos en la visión original.
