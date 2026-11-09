import "dotenv/config";
import bcrypt from "bcryptjs";
import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "../src/generated/prisma/client.js";

const databaseUrl = process.env.DATABASE_URL;
const adminEmail = process.env.ADMIN_EMAIL?.trim().toLowerCase();
const adminPassword = process.env.ADMIN_PASSWORD;
const testUserName = process.env.SEED_USER_NAME || "Usuario de prueba";
const testUserEmail = process.env.SEED_USER_EMAIL?.trim().toLowerCase();
const testUserPassword = process.env.SEED_USER_PASSWORD;

if (!databaseUrl) throw new Error("Configura DATABASE_URL antes de crear los datos iniciales.");
if (!adminEmail || !adminPassword || adminPassword.length < 12) {
  throw new Error("Configura ADMIN_EMAIL y un ADMIN_PASSWORD de al menos 12 caracteres.");
}
if (!testUserEmail || !testUserPassword || testUserPassword.length < 12) {
  throw new Error("Configura SEED_USER_EMAIL y un SEED_USER_PASSWORD de al menos 12 caracteres.");
}
if (adminEmail === testUserEmail) {
  throw new Error("ADMIN_EMAIL y SEED_USER_EMAIL deben ser diferentes.");
}

const prisma = new PrismaClient({
  adapter: new PrismaPg({ connectionString: databaseUrl }),
});

const run = async () => {
  const passwordHash = await bcrypt.hash(adminPassword, 12);
  await prisma.user.upsert({
    where: { email: adminEmail },
    update: {
      name: process.env.ADMIN_NAME || "Administración Olympo",
      passwordHash,
      role: "ADMIN",
      status: "ACTIVE",
    },
    create: {
      name: process.env.ADMIN_NAME || "Administración Olympo",
      email: adminEmail,
      passwordHash,
      role: "ADMIN",
    },
  });

  const testUserPasswordHash = await bcrypt.hash(testUserPassword, 12);
  await prisma.user.upsert({
    where: { email: testUserEmail },
    update: {
      name: testUserName,
      passwordHash: testUserPasswordHash,
      role: "USER",
      status: "ACTIVE",
    },
    create: {
      name: testUserName,
      email: testUserEmail,
      passwordHash: testUserPasswordHash,
      role: "USER",
    },
  });

  const categories = [
    { name: "Tecnología", slug: "tecnologia", description: "Soluciones de software y tecnología." },
    { name: "Alimentos", slug: "alimentos", description: "Proyectos de producción y servicios de alimentos." },
    { name: "Servicios", slug: "servicios", description: "Servicios para personas y empresas." },
  ];

  for (const category of categories) {
    await prisma.category.upsert({
      where: { slug: category.slug },
      update: { name: category.name, description: category.description, status: "ACTIVE" },
      create: category,
    });
  }

  console.log("Datos iniciales listos.");
};

run()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
