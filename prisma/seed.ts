import "dotenv/config";
import bcrypt from "bcryptjs";
import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "../src/generated/prisma/client.js";

const databaseUrl = process.env.DATABASE_URL;
const adminEmail = process.env.ADMIN_EMAIL?.trim().toLowerCase();
const adminPassword = process.env.ADMIN_PASSWORD;

if (!databaseUrl) throw new Error("Configura DATABASE_URL antes de crear los datos iniciales.");
if (!adminEmail || !adminPassword || adminPassword.length < 12) {
  throw new Error("Configura ADMIN_EMAIL y un ADMIN_PASSWORD de al menos 12 caracteres.");
}

const prisma = new PrismaClient({
  adapter: new PrismaPg({ connectionString: databaseUrl }),
});

const run = async () => {
  const passwordHash = await bcrypt.hash(adminPassword, 12);
  await prisma.user.upsert({
    where: { email: adminEmail },
    update: { name: process.env.ADMIN_NAME || "Administración Olympo", role: "ADMIN" },
    create: {
      name: process.env.ADMIN_NAME || "Administración Olympo",
      email: adminEmail,
      passwordHash,
      role: "ADMIN",
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
      update: { name: category.name, description: category.description },
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
