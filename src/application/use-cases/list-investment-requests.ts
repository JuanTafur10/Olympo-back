import type {
  InvestmentRequestRepository,
  InvestmentRequestViewerRole,
} from "../../domain/repository/investment-request.repository.js";

interface ListInvestmentRequestsInput {
  pagination: { currentPage: number; limit: number };
  viewer: { id: string; role: InvestmentRequestViewerRole };
}

export class ListInvestmentRequests {
  constructor(private readonly requests: InvestmentRequestRepository) {}

  async execute(input: ListInvestmentRequestsInput) {
    const { pagination, viewer } = input;
    const { data, total } = await this.requests.list({
      viewer,
      skip: (pagination.currentPage - 1) * pagination.limit,
      take: pagination.limit,
    });

    return {
      data,
      pagination: {
        ...pagination,
        total,
        totalPages: Math.ceil(total / pagination.limit),
      },
    };
  }
}