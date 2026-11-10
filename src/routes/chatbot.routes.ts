import { Router } from "express";
import { getChatbotHistory, postChatbotMessage } from "../controllers/chatbot.controller.js";
import { authenticate } from "../middleware/authentication.js";

export const chatbotRoutes = Router();
chatbotRoutes.use(authenticate);
chatbotRoutes.get("/history", getChatbotHistory);
chatbotRoutes.post("/mensaje", postChatbotMessage);
