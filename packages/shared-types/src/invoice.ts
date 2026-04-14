import { UUID, ISODateString, ProcessingStatus, PricingStatus } from './common';

export interface Invoice {
  id: UUID;
  tenantId: string;
  invoiceNumber: string;
  supplierName: string;
  totalAmount: number;
  status: ProcessingStatus;
  pricingStatus: PricingStatus;
  uploadedAt: ISODateString;
  processedAt?: ISODateString;
  s3Key?: string;
  textractJobId?: string;
  errorMessage?: string;
}

export interface InvoiceLineItem {
  id: UUID;
  invoiceId: UUID;
  productCode: string;
  description: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  salePrice?: number;
  markupPercentage?: number;
  isPriced: boolean;
  category?: string;
  confidence?: number;
}

// Note: File type is browser-specific, used only in client-side code
// For server-side, this interface is for type reference only
export interface InvoiceUploadRequest {
  tenantId: string;
  file?: any; // File object (browser) or form data
  metadata?: Record<string, any>;
}

export interface InvoiceUploadResponse {
  id: UUID;
  status: ProcessingStatus;
  message: string;
}

export interface InvoiceStatusResponse {
  id: UUID;
  status: ProcessingStatus;
  pricingStatus: PricingStatus;
  progress?: number;
  errorMessage?: string;
}

export interface InvoicePricingData {
  invoice: Invoice;
  lineItems: InvoiceLineItem[];
  pricingRecommendations: PricingRecommendation[];
}

export interface PricingRecommendation {
  lineItemId: UUID;
  recommendedPrice: number;
  confidence: number;
  reasoning: string;
  marginPercentage: number;
}

export interface SetPricingRequest {
  lineItems: {
    id: UUID;
    salePrice: number;
  }[];
}
