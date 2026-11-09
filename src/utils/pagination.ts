import { z } from "zod";

const paginationSchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(10),
});

export const paginationFromQuery = (query: Record<string, unknown>) => {
  const parsed = paginationSchema.parse(query);
  return { currentPage: parsed.page, limit: parsed.limit };
};
