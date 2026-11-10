export interface NewInvestmentRequestNotice {
  ownerId: string;
  projectTitle: string;
  projectId: string;
  requestId: string;
}

export interface InvestmentRequestNotifier {
  notifyNewRequest(notice: NewInvestmentRequestNotice): Promise<void>;
}