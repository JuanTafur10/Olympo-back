import type { RequestHandler } from "express";
import jwt from "jsonwebtoken";
import type { Role } from "../generated/prisma/client.js";
import { prisma } from "../config/database.js";
import { env } from "../config/env.js";
import { HttpError } from "../errors/http-error.js";

const readToken = (authorization: string | undefined): string | null => {
  if (!authorization) return null;
  if (!authorization.startsWith("Bearer ")) {
    throw new HttpError(401, "Usa un token Bearer para acceder.");
  }
  return authorization.slice(7);
};

const findUserFromToken = async (token: string) => {
  let payload: string | jwt.JwtPayload;
  try {
    payload = jwt.verify(token, env.JWT_SECRET);
  } catch {
    throw new HttpError(401, "La sesión no es válida o ya venció.");
  }

  if (typeof payload === "string" || typeof payload.sub !== "string") {
    throw new HttpError(401, "La sesión no es válida.");
  }

  const user = await prisma.user.findUnique({
    where: { id: payload.sub },
    select: { id: true, role: true },
  });
  if (!user) throw new HttpError(401, "La sesión ya no está activa.");
  return user;
};

export const authenticate: RequestHandler = async (request, _response, next) => {
  const token = readToken(request.header("authorization"));
  if (!token) throw new HttpError(401, "Inicia sesión para continuar.");
  request.user = await findUserFromToken(token);
  next();
};

export const optionalAuthenticate: RequestHandler = async (request, _response, next) => {
  const token = readToken(request.header("authorization"));
  if (token) request.user = await findUserFromToken(token);
  next();
};

export const allowRoles = (...roles: Role[]): RequestHandler => (request, _response, next) => {
  if (!request.user) throw new HttpError(401, "Inicia sesión para continuar.");
  if (!roles.includes(request.user.role)) throw new HttpError(403, "No tienes permiso para realizar esta acción.");
  next();
};
