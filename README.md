# Olympo Backend

API para una plataforma que conecta emprendedores con inversionistas. Está hecha con Node.js, Express, TypeScript, Prisma y PostgreSQL.

## Recursos

- Usuarios con los roles ADMIN, USER y OWNER.
- Categorías para organizar proyectos.
- Proyectos creados por propietarios y relacionados con una categoría.
- Solicitudes de inversión relacionadas con un proyecto y con el inversionista que la envía.

El administrador no se crea desde el formulario. Se crea una sola vez con el seed.

## Empezar en local

1. Copia .env.example como .env.
2. Define JWT_SECRET con una cadena aleatoria de al menos 32 caracteres.
3. Define ADMIN_PASSWORD y SEED_USER_PASSWORD con contraseñas distintas de al menos 12 caracteres.
4. Inicia PostgreSQL con docker compose up -d db.
5. Instala los paquetes con npm install.
6. Genera el cliente de Prisma con npm run db:generate.
7. Aplica las tablas con npm run db:deploy.
8. Crea el administrador, un usuario normal y las categorías iniciales con npm run db:seed.
9. Inicia la API con npm run dev.

En local, la API queda disponible en http://localhost:4000. Las rutas están bajo /api/v1 y también bajo /api para compatibilidad con los endpoints de autenticación de la rúbrica. El endpoint GET /api/v1/health permite revisar que el servidor responda.

## PostgreSQL alojado

El ejemplo de .env usa PostgreSQL local. Para usar Neon, Supabase o Railway, configura en las variables privadas del servicio la URL real de PostgreSQL. DATABASE_URL se usa para las consultas de la API y DIRECT_URL para ejecutar las migraciones. Si el proveedor ofrece un pooler, usa la conexión directa en DIRECT_URL y la conexión del pooler en DATABASE_URL.

## Rutas principales

| Recurso | Rutas |
| --- | --- |
| Registro e inicio de sesión | POST /auth/register, POST /auth/login |
| Usuarios | GET /users/me; administración: GET /users, GET /users/:id, PATCH /users/:id, DELETE /users/:id |
| Categorías | GET /categories, GET /categories/:id, POST /categories, PATCH /categories/:id, DELETE /categories/:id |
| Proyectos | GET /projects, GET /projects/:id, POST /projects, PATCH /projects/:id, DELETE /projects/:id |
| Imagen del proyecto | POST /projects/:id/image |
| Solicitudes de inversión | GET /investment-requests, GET /investment-requests/:id, POST /investment-requests, PATCH /investment-requests/:id, DELETE /investment-requests/:id |

Las listas reciben page y limit y devuelven data junto con pagination. Proyectos también admite q, categoryId y status.

Para crear un proyecto, envía JSON con title, description, categoryId y targetAmount. Para cargar su imagen, envía después multipart/form-data a /projects/:id/image, con el archivo en el campo image. Se aceptan JPG, PNG y WEBP de hasta 5 MB. La API guarda el archivo en Supabase Storage y conserva su URL en el proyecto.

## Permisos

- ADMIN: administra usuarios, categorías, proyectos y solicitudes.
- OWNER: crea y administra sus proyectos; revisa las solicitudes recibidas para esos proyectos.
- USER: explora proyectos y administra sus propias solicitudes de inversión.
- El registro permite escoger USER u OWNER; nunca permite crear ADMIN.
- Al eliminar, los registros cambian de estado y se conservan en la base de datos.

## Supabase Storage

Crea un bucket llamado projects o usa otro nombre en SUPABASE_STORAGE_BUCKET. El bucket debe ser público para servir la URL devuelta. Configura SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY solo en el backend y en las variables privadas del servicio de despliegue. No compartas la clave de servicio ni la subas a GitHub.

## Despliegue

El contenedor usa las variables de .env y ejecuta las migraciones antes de iniciar la API. En un proveedor como Render o Railway, configura el build como npm ci && npm run build y el inicio como npm run db:deploy && npm start. Añade allí DATABASE_URL, DIRECT_URL, JWT_SECRET, CORS_ORIGIN y las variables de Supabase. Ejecuta npm run db:seed una vez con ADMIN_EMAIL, ADMIN_PASSWORD, SEED_USER_EMAIL y SEED_USER_PASSWORD para crear el administrador y el usuario normal.

## Reparto del trabajo

Completar con los nombres y aportes reales del equipo antes de entregar:

| Integrante | Aporte en este repositorio |
| --- | --- |
| Pendiente de asignar | Pendiente |
| Pendiente de asignar | Pendiente |
| Pendiente de asignar | Pendiente |
