FROM node:24-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY prisma ./prisma
COPY prisma.config.ts tsconfig.json ./
COPY src ./src
RUN npm run build

EXPOSE 4000

CMD ["sh", "-c", "npm run db:deploy && npm start"]
