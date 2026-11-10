import { Router } from "express";
import {
  deleteNotification,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../controllers/notification.controller.js";
import { authenticate } from "../middleware/authentication.js";

export const notificationRoutes = Router();
notificationRoutes.use(authenticate);
notificationRoutes.get("/", listNotifications);
notificationRoutes.patch("/leidas", markAllNotificationsRead);
notificationRoutes.patch("/:id/leida", markNotificationRead);
notificationRoutes.delete("/:id", deleteNotification);
