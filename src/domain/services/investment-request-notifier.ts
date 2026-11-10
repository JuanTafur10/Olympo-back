export interface NewInvestmentRequestNotice {
  ownerId: string;
  projectTitle: string;
  projectId: string;
  requestId: string;
}

export interface InvestmentRequestStatusNotice {
  investorId: string;
  projectTitle: string;
  requestId: string;
  status: "APPROVED" | "REJECTED";
}

export interface InvestmentRequestNotifier {
  notifyNewRequest(notice: NewInvestmentRequestNotice): Promise<void>;
  notifyStatusUpdate(notice: InvestmentRequestStatusNotice): Promise<void>;
}