-- Extensiones requeridas
create extension if not exists pgcrypto;
create extension if not exists "uuid-ossp";

-- Enums
DO $$ BEGIN
  CREATE TYPE service_type AS ENUM ('pilates_group','pilates_individual','kinesio_individual');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE sub_status AS ENUM ('active','suspended','cancelled','expired');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE occurrence_status AS ENUM ('scheduled','cancelled','completed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Tenants y perfiles
CREATE TABLE IF NOT EXISTS tenants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  timezone text NOT NULL DEFAULT 'America/Asuncion',
  locale text NOT NULL DEFAULT 'es-PY',
  billing_email text,
  settings jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL UNIQUE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('tenant_admin','staff','pro','member','platform_admin')),
  linked_professional_id uuid,
  linked_member_id uuid,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Profesionales y miembros
CREATE TABLE IF NOT EXISTS professionals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  full_name text NOT NULL,
  email text,
  phone text,
  specialties text[],
  color text,
  bio text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_prof_tenant ON professionals(tenant_id);

CREATE TABLE IF NOT EXISTS members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  full_name text NOT NULL,
  email text,
  phone text,
  doc_type text,
  doc_number text,
  birth_date date,
  sex text,
  address text,
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_members_tenant ON members(tenant_id);

-- Servicios, planes, políticas
CREATE TABLE IF NOT EXISTS cancellation_policies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name text NOT NULL,
  min_notice_hours int NOT NULL DEFAULT 6,
  refund_type text NOT NULL DEFAULT 'makeup',
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS services (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name text NOT NULL,
  type service_type NOT NULL,
  duration_min int NOT NULL,
  capacity int,
  buffer_before int NOT NULL DEFAULT 0,
  buffer_after int NOT NULL DEFAULT 0,
  cancellation_policy_id uuid REFERENCES cancellation_policies(id) ON DELETE SET NULL,
  makeup_policy_id uuid,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_services_tenant ON services(tenant_id);

CREATE TABLE IF NOT EXISTS plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  service_id uuid NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  name text NOT NULL,
  price_cents int NOT NULL,
  currency text NOT NULL DEFAULT 'PYG',
  times_per_week int NOT NULL CHECK (times_per_week BETWEEN 1 AND 7),
  validity_days int NOT NULL DEFAULT 30,
  max_makeups_per_month int NOT NULL DEFAULT 1,
  autopause boolean NOT NULL DEFAULT false,
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_plans_tenant ON plans(tenant_id);

-- Disponibilidad y clases
CREATE TABLE IF NOT EXISTS professional_availability (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  professional_id uuid NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
  weekday int NOT NULL CHECK (weekday BETWEEN 0 AND 6),
  start_time time NOT NULL,
  end_time time NOT NULL,
  location_id uuid,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_avail_prof ON professional_availability(tenant_id, professional_id, weekday);

CREATE TABLE IF NOT EXISTS class_templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  service_id uuid NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  professional_id uuid NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
  weekday int NOT NULL CHECK (weekday BETWEEN 0 AND 6),
  start_time time NOT NULL,
  duration_min int NOT NULL,
  capacity_override int,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_templates_prof ON class_templates(tenant_id, professional_id, weekday);

CREATE TABLE IF NOT EXISTS class_occurrences (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  service_id uuid NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  professional_id uuid NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
  start_ts timestamptz NOT NULL,
  end_ts timestamptz NOT NULL,
  capacity int NOT NULL,
  booked_count int NOT NULL DEFAULT 0,
  status occurrence_status NOT NULL DEFAULT 'scheduled',
  origin text NOT NULL DEFAULT 'template',
  cancel_reason text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT uniq_occ UNIQUE (tenant_id, professional_id, start_ts)
);
CREATE INDEX IF NOT EXISTS idx_occ_prof_start ON class_occurrences(tenant_id, professional_id, start_ts);

-- Suscripciones y reservas
CREATE TABLE IF NOT EXISTS subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  member_id uuid NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  plan_id uuid NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  start_date date NOT NULL,
  end_date date NOT NULL,
  status sub_status NOT NULL DEFAULT 'active',
  preferred_weekdays int[] NOT NULL DEFAULT '{}',
  preferred_time time,
  assigned_professional_id uuid REFERENCES professionals(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_subs_member ON subscriptions(tenant_id, member_id, status);

CREATE TABLE IF NOT EXISTS subscription_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  subscription_id uuid NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  class_occurrence_id uuid NOT NULL REFERENCES class_occurrences(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'scheduled',
  source text NOT NULL DEFAULT 'initial',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT uniq_entry UNIQUE (subscription_id, class_occurrence_id)
);
CREATE INDEX IF NOT EXISTS idx_entries_sub ON subscription_entries(tenant_id, subscription_id);

CREATE TABLE IF NOT EXISTS bookings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  member_id uuid NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  service_id uuid NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  class_occurrence_id uuid NOT NULL REFERENCES class_occurrences(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'booked',
  source text NOT NULL DEFAULT 'portal',
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT uniq_booking UNIQUE (member_id, class_occurrence_id)
);
CREATE INDEX IF NOT EXISTS idx_bookings_member ON bookings(tenant_id, member_id);

CREATE TABLE IF NOT EXISTS makeups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  subscription_id uuid NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  month date NOT NULL,
  allowed int NOT NULL,
  used int NOT NULL DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT uniq_makeup_month UNIQUE (subscription_id, month)
);

-- Notificaciones / Push
CREATE TABLE IF NOT EXISTS notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  type text NOT NULL CHECK (type IN ('push','email','sms')),
  template_key text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  status text NOT NULL DEFAULT 'queued',
  error text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notify_user ON notifications(tenant_id, user_id, status);

CREATE TABLE IF NOT EXISTS push_subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  endpoint text NOT NULL,
  p256dh text NOT NULL,
  auth text NOT NULL,
  user_agent text,
  last_seen_at timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_push_endpoint ON push_subscriptions(endpoint);

-- Finanzas
CREATE TABLE IF NOT EXISTS expenses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  date date NOT NULL,
  concept text NOT NULL,
  amount_cents int NOT NULL,
  shared boolean NOT NULL DEFAULT false,
  professional_id uuid REFERENCES professionals(id) ON DELETE SET NULL,
  split_rule jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS expense_shares (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  expense_id uuid NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
  professional_id uuid NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
  share_amount_cents int NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_share_expense ON expense_shares(expense_id);

CREATE TABLE IF NOT EXISTS incomes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  professional_id uuid NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
  date date NOT NULL,
  concept text NOT NULL,
  amount_cents int NOT NULL,
  source text NOT NULL DEFAULT 'class',
  ref_id uuid,
  private boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_incomes_prof ON incomes(tenant_id, professional_id, date);

-- Adjuntos y evolución
CREATE TABLE IF NOT EXISTS attachments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  owner_type text NOT NULL CHECK (owner_type IN ('member','case','session','evolution')),
  owner_id uuid NOT NULL,
  bucket text NOT NULL,
  path text NOT NULL,
  mime text,
  size int,
  sha256 text,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evolution_photos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  member_id uuid NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  date date NOT NULL,
  tags text[],
  left_path text,
  right_path text,
  derived_overlay_path text,
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Kinesiología
CREATE TABLE IF NOT EXISTS kine_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  member_id uuid NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  professional_id uuid NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
  diagnosis_text text,
  cie10 text[],
  start_date date NOT NULL DEFAULT current_date,
  status text NOT NULL DEFAULT 'open',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kine_assessments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  case_id uuid NOT NULL REFERENCES kine_cases(id) ON DELETE CASCADE,
  date date NOT NULL,
  hee text,
  antecedentes jsonb,
  habitos jsonb,
  postura jsonb,
  marcha jsonb,
  palpacion jsonb,
  rom jsonb,
  fuerza_mmt jsonb,
  sensibilidad jsonb,
  reflejos jsonb,
  pruebas_especiales jsonb,
  dolor_vas int,
  escalas jsonb,
  objetivos jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kine_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  case_id uuid NOT NULL REFERENCES kine_cases(id) ON DELETE CASCADE,
  date date NOT NULL,
  techniques jsonb,
  duration_min int,
  response text,
  recommendations text,
  next_plan text,
  signed_by uuid,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Auditoría
CREATE TABLE IF NOT EXISTS audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  actor_id uuid,
  action text NOT NULL,
  entity text NOT NULL,
  entity_id uuid NOT NULL,
  diff jsonb,
  at timestamptz DEFAULT now()
);
