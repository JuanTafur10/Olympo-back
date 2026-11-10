import { randomUUID } from "node:crypto";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { env } from "../config/env.js";
import { HttpError } from "../errors/http-error.js";
import type { ProjectImageFile } from "../domain/services/project-image-storage.js";

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

const matchesFileSignature = (file: ProjectImageFile) => {
  const bytes = file.buffer;
  if (file.mimetype === "image/jpeg") return bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  if (file.mimetype === "image/png") return bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
  if (file.mimetype === "image/webp") {
    return bytes.toString("ascii", 0, 4) === "RIFF" && bytes.toString("ascii", 8, 12) === "WEBP";
  }
  return false;
};

export const uploadProjectImageFile = async (projectId: string, file: ProjectImageFile) => {
  const extension = extensionByType[file.mimetype];
  if (!extension || !matchesFileSignature(file)) throw new HttpError(400, "El archivo debe ser una imagen JPG, PNG o WEBP válida.");

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
