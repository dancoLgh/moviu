'use client';

import { create } from 'zustand';

type TenantStore = {
  tenantId: string | null;
  setTenantId: (tenantId: string) => void;
};

export const useTenant = create<TenantStore>((set) => ({
  tenantId: null,
  setTenantId: (tenantId) => set({ tenantId })
}));
