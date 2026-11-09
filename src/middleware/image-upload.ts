import multer from "multer";
import { HttpError } from "../errors/http-error.js";

const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);

export const imageUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024, files: 1 },
  fileFilter: (_request, file, callback) => {
    if (!allowedTypes.has(file.mimetype)) {
      callback(new HttpError(400, "Usa una imagen JPG, PNG o WEBP."));
      return;
    }
    callback(null, true);
  },
}).single("image");
