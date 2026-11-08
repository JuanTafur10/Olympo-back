import { app } from "./app.js";
import { prisma } from "./config/database.js";
import { env } from "./config/env.js";

const server = app.listen(env.PORT, () => {
  console.log("Olympo API disponible en el puerto " + env.PORT);
});

const closeServer = async () => {
  server.close(async () => {
    await prisma.$disconnect();
    process.exit(0);
  });
};

process.on("SIGINT", closeServer);
process.on("SIGTERM", closeServer);
