CREATE TABLE "notifications" (
    "id" UUID NOT NULL,
    "userId" UUID NOT NULL,
    "title" VARCHAR(160) NOT NULL,
    "message" VARCHAR(1000) NOT NULL,
    "type" VARCHAR(40) NOT NULL DEFAULT 'info',
    "routeDestination" VARCHAR(500),
    "metadata" JSONB,
    "readAt" TIMESTAMP(3),
    "deletedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "notifications_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "chatbot_histories" (
    "id" UUID NOT NULL,
    "userId" UUID NOT NULL,
    "userMessage" TEXT NOT NULL,
    "botResponse" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "chatbot_histories_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "notifications_userId_deletedAt_createdAt_idx" ON "notifications"("userId", "deletedAt", "createdAt");
CREATE INDEX "chatbot_histories_userId_createdAt_idx" ON "chatbot_histories"("userId", "createdAt");

ALTER TABLE "notifications" ADD CONSTRAINT "notifications_userId_fkey"
  FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "chatbot_histories" ADD CONSTRAINT "chatbot_histories_userId_fkey"
  FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
