import type { RequestHandler } from "express";
import bcrypt from "bcryptjs";
import jwt, { type SignOptions } from "jsonwebtoken";
import { prisma } from "../config/database.js";
import { env } from "../config/env.js";
import { registerSchema, loginSchema } from "../validation/auth.schemas.js";
import { HttpError } from "../errors/http-error.js";

const createToken = (user: { id: string; role: string }) =>
  jwt.sign(
    { role: user.role },
    env.JWT_SECRET,
    {
      subject: user.id,
      expiresIn: env.JWT_EXPIRES_IN as SignOptions["expiresIn"],
    },
  );

const publicUser = (user: { id: string; name: string; email: string; role: string; createdAt: Date }) => ({
  id: user.id,
  name: user.name,
  email: user.email,
  role: user.role,
  createdAt: user.createdAt,
});

export const register: RequestHandler = async (request, response) => {
  const input = registerSchema.parse(request.body);
  const passwordHash = await bcrypt.hash(input.password, 12);
  const user = await prisma.user.create({
    data: {
      name: input.name,
      email: input.email,
      passwordHash,
      role: input.role,
    },
    select: { id: true, name: true, email: true, role: true, createdAt: true },
  });

  response.status(201).json({
    data: { user, token: createToken(user) },
  });
};

export const login: RequestHandler = async (request, response) => {
  const input = loginSchema.parse(request.body);
  const user = await prisma.user.findUnique({ where: { email: input.email } });
  if (!user || user.status !== "ACTIVE" || !(await bcrypt.compare(input.password, user.passwordHash))) {
    throw new HttpError(401, "El correo o la contraseña no son correctos.");
  }

  response.json({
    data: {
      user: publicUser(user),
      token: createToken(user),
    },
  });
};
