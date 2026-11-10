export interface ProjectImageFile {
  buffer: Buffer;
  mimetype: string;
}

export interface ProjectImageStorage {
  upload(projectId: string, file: ProjectImageFile): Promise<string>;
}