import { z } from "zod";

const pageFields = {
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(10),
};

export const categoryListSchema = z.object(pageFields);
export const categoryCreateSchema = z.object({
  name: z.string().trim().min(2).max(100),
  description: z.string().trim().max(500).optional(),
});
export const categoryUpdateSchema = categoryCreateSchema.partial()
  .refine((value) => Object.keys(value).length > 0, "Indica un dato para actualizar.");

export const projectListSchema = z.object({
  ...pageFields,
  q: z.string().trim().max(120).optional(),
  categoryId: z.uuid().optional(),
  status: z.enum(["DRAFT", "PUBLISHED", "CLOSED"]).optional(),
});
export const projectCreateSchema = z.object({
  title: z.string().trim().min(5).max(160),
  description: z.string().trim().min(30).max(10000),
  categoryId: z.uuid(),
  targetAmount: z.coerce.number().positive().max(999999999999),
  status: z.enum(["DRAFT", "PUBLISHED"]).default("DRAFT"),
});
export const projectUpdateSchema = projectCreateSchema.partial()
  .refine((value) => Object.keys(value).length > 0, "Indica un dato para actualizar.");

export const investmentRequestListSchema = z.object(pageFields);
export const investmentRequestCreateSchema = z.object({
  projectId: z.uuid(),
  amount: z.coerce.number().positive().max(999999999999),
  message: z.string().trim().max(2000).optional(),
});
export const investmentRequestUpdateSchema = z.object({
  amount: z.coerce.number().positive().max(999999999999).optional(),
  message: z.string().trim().max(2000).optional(),
  status: z.enum(["APPROVED", "REJECTED", "WITHDRAWN"]).optional(),
}).refine((value) => Object.keys(value).length > 0, "Indica un dato para actualizar.");
