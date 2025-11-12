export type SessionClaims = {
  tenant_id: string;
  role: 'tenant_admin' | 'staff' | 'pro' | 'member' | 'platform_admin';
  professional_id?: string;
  member_id?: string;
};

export function guardByTenant<T extends { tenant_id: string }>(rows: T[], tenantId: string) {
  return rows.filter((row) => row.tenant_id === tenantId);
}

export function canManageIncome(claims: SessionClaims, professionalId: string) {
  return claims.role === 'tenant_admin' || claims.professional_id === professionalId;
}
