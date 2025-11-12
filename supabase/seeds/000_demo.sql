INSERT INTO tenants (id, name)
VALUES ('00000000-0000-0000-0000-000000000001', 'Elementos Pilates & Kine')
ON CONFLICT DO NOTHING;

INSERT INTO professionals (tenant_id, id, full_name, email, color)
VALUES
  ('00000000-0000-0000-0000-000000000001','11111111-1111-1111-1111-111111111111','María Gómez','maria@elementos.test','#A3E635'),
  ('00000000-0000-0000-0000-000000000001','22222222-2222-2222-2222-222222222222','Juan López','juan@elementos.test','#60A5FA')
ON CONFLICT DO NOTHING;

INSERT INTO members (tenant_id, id, full_name, email, birth_date, sex)
VALUES
  ('00000000-0000-0000-0000-000000000001','33333333-3333-3333-3333-333333333333','Ana Torres','ana@demo.test','1995-08-12','F'),
  ('00000000-0000-0000-0000-000000000001','44444444-4444-4444-4444-444444444444','Pedro Díaz','pedro@demo.test','1990-02-03','M')
ON CONFLICT DO NOTHING;

INSERT INTO cancellation_policies (tenant_id, name, min_notice_hours)
VALUES ('00000000-0000-0000-0000-000000000001','Default 6h',6)
ON CONFLICT DO NOTHING;

INSERT INTO services (tenant_id, name, type, duration_min, capacity, buffer_before, buffer_after, cancellation_policy_id)
SELECT '00000000-0000-0000-0000-000000000001','Pilates Grupal','pilates_group',60,8,10,10, id
FROM cancellation_policies
WHERE tenant_id='00000000-0000-0000-0000-000000000001'
LIMIT 1;

INSERT INTO plans (tenant_id, service_id, name, price_cents, times_per_week, validity_days, max_makeups_per_month)
SELECT '00000000-0000-0000-0000-000000000001', s.id, 'Máximo 3×/sem', 35000000, 3, 30, 1
FROM services s
WHERE s.tenant_id='00000000-0000-0000-0000-000000000001' AND s.type='pilates_group'
LIMIT 1;

INSERT INTO professional_availability (tenant_id, professional_id, weekday, start_time, end_time, active)
VALUES
  ('00000000-0000-0000-0000-000000000001','11111111-1111-1111-1111-111111111111',1,'15:00','16:00',true),
  ('00000000-0000-0000-0000-000000000001','11111111-1111-1111-1111-111111111111',3,'15:00','16:00',true),
  ('00000000-0000-0000-0000-000000000001','11111111-1111-1111-1111-111111111111',5,'15:00','16:00',true)
ON CONFLICT DO NOTHING;
