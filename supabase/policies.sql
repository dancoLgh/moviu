ALTER TABLE professionals ENABLE ROW LEVEL SECURITY;
ALTER TABLE members ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE class_occurrences ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE expense_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE incomes ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.current_tenant() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT (auth.jwt() ->> 'tenant_id')::uuid;
$$;

CREATE OR REPLACE FUNCTION public.current_role() RETURNS text LANGUAGE sql STABLE AS $$
  SELECT auth.jwt() ->> 'role';
$$;

CREATE OR REPLACE FUNCTION public.current_user_id() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT auth.uid();
$$;

CREATE POLICY tenant_read_professionals ON professionals FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY tenant_write_professionals ON professionals FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (tenant_id = current_tenant());

CREATE POLICY tenant_read_members ON members FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY tenant_write_members ON members FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (tenant_id = current_tenant());

CREATE POLICY tenant_read_services ON services FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY tenant_write_services ON services FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (tenant_id = current_tenant());

CREATE POLICY tenant_read_plans ON plans FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY tenant_write_plans ON plans FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (tenant_id = current_tenant());

CREATE POLICY tenant_read_occ ON class_occurrences FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY pro_manage_occ ON class_occurrences FOR ALL
  USING (
    tenant_id = current_tenant() AND (
      current_role() IN ('tenant_admin','staff') OR
      (current_role() = 'pro' AND professional_id = (auth.jwt() ->> 'professional_id')::uuid)
    )
  )
  WITH CHECK (
    tenant_id = current_tenant() AND (
      current_role() IN ('tenant_admin','staff') OR
      (current_role() = 'pro' AND professional_id = (auth.jwt() ->> 'professional_id')::uuid)
    )
  );

CREATE POLICY tenant_read_subscriptions ON subscriptions FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY member_read_own_subscriptions ON subscriptions FOR SELECT USING (
  tenant_id = current_tenant() AND member_id = (auth.jwt() ->> 'member_id')::uuid
);

CREATE POLICY tenant_write_subscriptions ON subscriptions FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (tenant_id = current_tenant());

CREATE POLICY tenant_read_entries ON subscription_entries FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY member_read_entries ON subscription_entries FOR SELECT USING (
  tenant_id = current_tenant() AND EXISTS (
    SELECT 1 FROM subscriptions s
    WHERE s.id = subscription_id AND s.member_id = (auth.jwt() ->> 'member_id')::uuid
  )
);
CREATE POLICY member_makeup_entries ON subscription_entries FOR INSERT WITH CHECK (
  tenant_id = current_tenant() AND current_role() = 'member'
);

CREATE POLICY tenant_manage_entries ON subscription_entries FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (tenant_id = current_tenant());

CREATE POLICY tenant_read_bookings ON bookings FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY member_read_own_bookings ON bookings FOR SELECT USING (
  tenant_id = current_tenant() AND member_id = (auth.jwt() ->> 'member_id')::uuid
);
CREATE POLICY tenant_manage_bookings ON bookings FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (tenant_id = current_tenant());

CREATE POLICY tenant_read_expenses ON expenses FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY tenant_manage_expenses ON expenses FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (tenant_id = current_tenant());

CREATE POLICY tenant_read_expense_shares ON expense_shares FOR SELECT USING (tenant_id = current_tenant());
CREATE POLICY tenant_manage_expense_shares ON expense_shares FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (tenant_id = current_tenant());

CREATE POLICY tenant_read_incomes ON incomes FOR SELECT USING (
  tenant_id = current_tenant() AND (
    current_role() = 'tenant_admin' OR
    professional_id = (auth.jwt() ->> 'professional_id')::uuid
  )
);
CREATE POLICY tenant_manage_incomes ON incomes FOR ALL USING (tenant_id = current_tenant()) WITH CHECK (
  tenant_id = current_tenant() AND (
    current_role() IN ('tenant_admin','staff') OR
    professional_id = (auth.jwt() ->> 'professional_id')::uuid
  )
);
