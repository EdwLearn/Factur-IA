import { UUID, ISODateString } from './common';

export interface Product {
  id: UUID;
  tenantId: string;
  code: string;
  name: string;
  description?: string;
  category?: string;
  costPrice: number;
  salePrice: number;
  stock: number;
  supplierId?: UUID;
  createdAt: ISODateString;
  updatedAt: ISODateString;
}

export interface ProductCategory {
  id: string;
  name: string;
  description?: string;
  defaultMargin: number;
}

export interface DuplicateProduct {
  product: Product;
  similarityScore: number;
  priceDifference: number;
  isDuplicate: boolean;
  recommendation: string;
}
