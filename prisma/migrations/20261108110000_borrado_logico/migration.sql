CREATE TYPE "UserStatus" AS ENUM ('ACTIVE', 'INACTIVE');
CREATE TYPE "CategoryStatus" AS ENUM ('ACTIVE', 'INACTIVE');

CREATE TYPE "ProjectStatus_new" AS ENUM ('DRAFT', 'PUBLISHED', 'CLOSED', 'DELETED');
ALTER TABLE "projects" ALTER COLUMN "status" DROP DEFAULT;
ALTER TABLE "projects"
  ALTER COLUMN "status" TYPE "ProjectStatus_new"
  USING ("status"::text::"ProjectStatus_new");
ALTER TABLE "projects" ALTER COLUMN "status" SET DEFAULT 'DRAFT';
DROP TYPE "ProjectStatus";
ALTER TYPE "ProjectStatus_new" RENAME TO "ProjectStatus";

CREATE TYPE "InvestmentRequestStatus_new" AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'WITHDRAWN', 'DELETED');
ALTER TABLE "investment_requests" ALTER COLUMN "status" DROP DEFAULT;
ALTER TABLE "investment_requests"
  ALTER COLUMN "status" TYPE "InvestmentRequestStatus_new"
  USING ("status"::text::"InvestmentRequestStatus_new");
ALTER TABLE "investment_requests" ALTER COLUMN "status" SET DEFAULT 'PENDING';
DROP TYPE "InvestmentRequestStatus";
ALTER TYPE "InvestmentRequestStatus_new" RENAME TO "InvestmentRequestStatus";

ALTER TABLE "users"
  ADD COLUMN "status" "UserStatus" NOT NULL DEFAULT 'ACTIVE';
ALTER TABLE "categories"
  ADD COLUMN "status" "CategoryStatus" NOT NULL DEFAULT 'ACTIVE';

CREATE INDEX "users_status_idx" ON "users"("status");
CREATE INDEX "categories_status_idx" ON "categories"("status");
