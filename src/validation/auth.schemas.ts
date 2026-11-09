import { z } from "zod";

export const registerSchema = z.object({
  name: z.string().trim().min(2).max(120),
  email: z.email().trim().toLowerCase(),
  password: z.string().min(8).max(128),
  role: z.enum(["USER", "OWNER"]).default("USER"),
});

export const loginSchema = z.object({
  email: z.email().trim().toLowerCase(),
  password: z.string().min(1).max(128),
});

export const updateUserSchema = z.object({
  name: z.string().trim().min(2).max(120).optional(),
  email: z.email().trim().toLowerCase().optional(),
  role: z.enum(["USER", "OWNER", "ADMIN"]).optional(),
}).refine((value) => Object.keys(value).length > 0, "Indica al menos un dato para actualizar.");
