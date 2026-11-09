import { Router } from "express";
import {
  createInvestmentRequest,
  deleteInvestmentRequest,
  getInvestmentRequest,
  listInvestmentRequests,
  updateInvestmentRequest,
} from "../controllers/investment-request.controller.js";
import { allowRoles, authenticate } from "../middleware/authentication.js";

export const investmentRequestRoutes = Router();

investmentRequestRoutes.use(authenticate, allowRoles("USER", "OWNER", "ADMIN"));
investmentRequestRoutes.get("/", listInvestmentRequests);
investmentRequestRoutes.get("/:id", getInvestmentRequest);
investmentRequestRoutes.post("/", allowRoles("USER"), createInvestmentRequest);
investmentRequestRoutes.patch("/:id", updateInvestmentRequest);
investmentRequestRoutes.delete("/:id", deleteInvestmentRequest);
