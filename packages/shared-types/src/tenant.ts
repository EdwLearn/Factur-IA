import { UUID, ISODateString } from './common';

export interface Tenant {
  id: UUID;
  tenantId: string;
  businessName: string;
  email: string;
  phone?: string;
  address?: string;
  status: 'active' | 'inactive' | 'suspended';
  subscriptionTier: 'free' | 'basic' | 'premium' | 'enterprise';
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

export interface TenantSettings {
  tenantId: string;
  defaultMarginPercentage: number;
  autoProcessInvoices: boolean;
  enableMLRecommendations: boolean;
  duplicateThreshold: number;
}
