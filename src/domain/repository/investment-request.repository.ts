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

export interface PublishedProject {
  id: string;
  title: string;
  ownerId: string;
}

export interface InvestmentRequestCreateData {
  projectId: string;
  amount: number;
  message?: string;
}

export interface InvestmentRequestRepository {
  list(query: InvestmentRequestListQuery): Promise<{ data: unknown[]; total: number }>;
  findById(id: string): Promise<InvestmentRequestDetail | null>;
  findPublishedProject(projectId: string): Promise<PublishedProject | null>;
  create(input: InvestmentRequestCreateData, investorId: string): Promise<{ id: string; data: unknown }>;
}