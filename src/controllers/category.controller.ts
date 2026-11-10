import type { RequestHandler } from "express";
import { getRouteParam } from "../utils/route-param.js";
import { ListCategories } from "../application/use-cases/list-categories.js";
import { ManageCategories } from "../application/use-cases/manage-categories.js";
import { prismaCategoryRepository } from "../infrastructure/repository/prisma-category.repository.js";
import { paginationFromQuery } from "../utils/pagination.js";
import { categoryCreateSchema, categoryUpdateSchema } from "../validation/domain.schemas.js";

const listCategoriesUseCase = new ListCategories(prismaCategoryRepository);
const manageCategories = new ManageCategories(prismaCategoryRepository);

export const listCategories: RequestHandler = async (request, response) => {
  const pagination = paginationFromQuery(request.query);
  response.json(await listCategoriesUseCase.execute(pagination));
};

export const getCategory: RequestHandler = async (request, response) => {
  const category = await manageCategories.get(getRouteParam(request, "id"));
  response.json({ data: category });
};

export const createCategory: RequestHandler = async (request, response) => {
  const input = categoryCreateSchema.parse(request.body);
  const category = await manageCategories.create(input);
  response.status(201).json({ data: category });
};

export const updateCategory: RequestHandler = async (request, response) => {
  const input = categoryUpdateSchema.parse(request.body);
  const category = await manageCategories.update(getRouteParam(request, "id"), input);
  response.json({ data: category });
};

export const deleteCategory: RequestHandler = async (request, response) => {
  await manageCategories.deactivate(getRouteParam(request, "id"));
  response.status(204).send();
};