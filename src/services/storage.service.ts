import { randomUUID } from "node:crypto";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { env } from "../config/env.js";
import { HttpError } from "../errors/http-error.js";

let storageClient: SupabaseClient | undefined;

const getStorageClient = () => {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    throw new HttpError(503, "La carga de imágenes todavía no está configurada.");
  }
  storageClient ??= createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
  return storageClient;
};

const extensionByType: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

export const uploadProjectImageFile = async (projectId: string, file: Express.Multer.File) => {
  const extension = extensionByType[file.mimetype];
  if (!extension) throw new HttpError(400, "Usa una imagen JPG, PNG o WEBP.");

  const objectPath = "projects/" + projectId + "/" + randomUUID() + "." + extension;
  const storage = getStorageClient().storage.from(env.SUPABASE_STORAGE_BUCKET);
  const { error } = await storage.upload(objectPath, file.buffer, {
    contentType: file.mimetype,
    cacheControl: "3600",
    upsert: false,
  });
  if (error) throw new HttpError(502, "No se pudo guardar la imagen en Supabase Storage.");

  return storage.getPublicUrl(objectPath).data.publicUrl;
};
