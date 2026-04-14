export type UUID = string;

export type ISODateString = string;

export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

export type ProcessingStatus = 'uploaded' | 'processing' | 'completed' | 'failed';

export type PricingStatus = 'pending' | 'partial' | 'completed' | 'confirmed';
