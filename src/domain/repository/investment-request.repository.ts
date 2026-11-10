export type InvestmentRequestViewerRole = "ADMIN" | "OWNER" | "USER";

export interface InvestmentRequestListQuery {
  skip: number;
  take: number;
  viewer: { id: string; role: InvestmentRequestViewerRole };
}

export interface InvestmentRequestDetail {
  id: string;
  investorId: string;
  projectOwnerId: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "WITHDRAWN" | "DELETED";
  data: unknown;
}

export interface InvestmentRequestRepository {
  list(query: InvestmentRequestListQuery): Promise<{ data: unknown[]; total: number }>;
  findById(id: string): Promise<InvestmentRequestDetail | null>;
}