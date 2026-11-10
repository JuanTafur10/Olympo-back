import type { RequestHandler } from "express";
import { z } from "zod";
import { prisma } from "../config/database.js";
import { HttpError } from "../errors/http-error.js";
import { getRouteParam } from "../utils/route-param.js";

const listSchema = z.object({ limit: z.coerce.number().int().min(1).max(100).default(50) });
const present = (item: {
  id: string; title: string; message: string; type: string; readAt: Date | null;
  createdAt: Date; routeDestination: string | null; metadata: unknown;
}) => ({
  id: item.id,
  titulo: item.title,
  mensaje: item.message,
  tipo: item.type,
  leida: item.readAt !== null,
  creada_en: item.createdAt,
  ruta_destino: item.routeDestination,
  metadata: item.metadata,
});

export const listNotifications: RequestHandler = async (request, response) => {
  const { limit } = listSchema.parse(request.query);
  const items = await prisma.notification.findMany({
    where: { userId: request.user!.id, deletedAt: null },
    orderBy: { createdAt: "desc" },
    take: limit,
  });
  response.json({ ok: true, notificaciones: items.map(present) });
};

export const markNotificationRead: RequestHandler = async (request, response) => {
  const id = getRouteParam(request, "id");
  const result = await prisma.notification.updateMany({
    where: { id, userId: request.user!.id, deletedAt: null },
    data: { readAt: new Date() },
  });
  if (result.count === 0) throw new HttpError(404, "No se encontró la notificación.");
  response.json({ ok: true });
};

export const markAllNotificationsRead: RequestHandler = async (request, response) => {
  const result = await prisma.notification.updateMany({
    where: { userId: request.user!.id, deletedAt: null, readAt: null },
    data: { readAt: new Date() },
  });
  response.json({ ok: true, actualizadas: result.count });
};

export const deleteNotification: RequestHandler = async (request, response) => {
  const id = getRouteParam(request, "id");
  const result = await prisma.notification.updateMany({
    where: { id, userId: request.user!.id, deletedAt: null },
    data: { deletedAt: new Date() },
  });
  if (result.count === 0) throw new HttpError(404, "No se encontró la notificación.");
  response.json({ ok: true });
};
