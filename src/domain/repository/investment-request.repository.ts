export type InvestmentRequestViewerRole = "ADMIN" | "OWNER" | "USER";

export interface InvestmentRequestListQuery {
  skip: number;
  take: number;
  viewer: { id: string; role: InvestmentRequestViewerRole };
}

export interface InvestmentRequestRepository {
  list(query: InvestmentRequestListQuery): Promise<{ data: unknown[]; total: number }>;
}