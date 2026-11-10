import type { RequestHandler } from "express";
import { z } from "zod";
import { prisma } from "../config/database.js";

const historySchema = z.object({ limit: z.coerce.number().int().min(1).max(200).default(100) });
const messageSchema = z.object({ mensaje: z.string().trim().min(1).max(2000) });

const answerMessage = (message: string): string => {
  const text = message.toLocaleLowerCase("es");
  if (/hola|buenos días|buenas tardes|buenas noches/.test(text)) {
    return "¡Hola! Soy el asistente de Olympo. Puedo ayudarte con proyectos, inversiones, solicitudes y tu cuenta.";
  }
  if (/proyecto|publicar|emprend/.test(text)) {
    return "En Olympo, los emprendedores con rol propietario pueden crear proyectos, completar su información y publicarlos para que los inversionistas los exploren.";
  }
  if (/invert|solicitud|financ/.test(text)) {
    return "Explora los proyectos publicados y envía una solicitud desde su ficha. Puedes consultar el estado y el historial en la sección de solicitudes.";
  }
  if (/cuenta|perfil|contraseña|sesión|login|registr/.test(text)) {
    return "Puedes administrar tus datos desde Cuenta. Si tienes problemas para iniciar sesión, verifica tu correo y contraseña o vuelve a registrarte con un correo que no esté en uso.";
  }
  if (/notifica|ayuda|contact/.test(text)) {
    return "Las notificaciones aparecen en la sección Notificaciones. Para solicitar más ayuda, utiliza la opción de soporte de Olympo.";
  }
  return "Puedo orientarte sobre proyectos, solicitudes de inversión, notificaciones y tu cuenta. Cuéntame qué necesitas hacer en Olympo.";
};

export const getChatbotHistory: RequestHandler = async (request, response) => {
  const { limit } = historySchema.parse(request.query);
  const rows = await prisma.chatbotHistory.findMany({
    where: { userId: request.user!.id },
    orderBy: { createdAt: "desc" },
    take: limit,
  });
  response.json({ ok: true, historial: rows.reverse() });
};

export const postChatbotMessage: RequestHandler = async (request, response) => {
  const { mensaje } = messageSchema.parse(request.body);
  const respuesta = answerMessage(mensaje);
  await prisma.chatbotHistory.create({
    data: { userId: request.user!.id, userMessage: mensaje, botResponse: respuesta },
  });
  response.json({ ok: true, respuesta });
};
