import { z } from "zod";

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  PORT: z.coerce.number().int().min(1).max(65535).default(4000),
  DATABASE_URL: z.string().min(1, "DATABASE_URL es obligatoria"),
  JWT_SECRET: z.string().min(32, "JWT_SECRET debe tener al menos 32 caracteres"),
  JWT_EXPIRES_IN: z.string().default("1d"),
  CORS_ORIGIN: z.string().default("http://localhost:3000"),
  SUPABASE_URL: z.union([z.url(), z.literal("")]).default(""),
  SUPABASE_SERVICE_ROLE_KEY: z.string().default(""),
  SUPABASE_STORAGE_BUCKET: z.string().min(1).default("projects"),
});

const result = envSchema.safeParse(process.env);

if (!result.success) {
  const details = result.error.issues
    .map((issue) => issue.path.join(".") + ": " + issue.message)
    .join("; ");
  throw new Error("Configuración inválida: " + details);
}

export const env = result.data;
