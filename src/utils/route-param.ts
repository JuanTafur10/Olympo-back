import type { Request } from "express";
import { z } from "zod";
import { HttpError } from "../errors/http-error.js";

const routeIdSchema = z.uuid();

export const getRouteParam = (request: Request, name: string): string => {
  const value = request.params[name];
  const parsed = routeIdSchema.safeParse(value);
  if (!parsed.success) throw new HttpError(400, `El parámetro ${name} debe ser un UUID válido.`);
  return parsed.data;
};
