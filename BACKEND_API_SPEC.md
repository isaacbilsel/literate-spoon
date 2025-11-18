# Backend API Specification for Literate Spoon

## 1. Project Overview

- **Project name:** Literate Spoon (frontend repository: `literate-spoon-fe`)
- **Brief description:**
  - A personal nutrition assistant and meal-planning front-end built with Next.js. Features include a multi-step biodata form, an LLM-backed interpreted-data step, a chatbot that accepts natural language profile updates/queries, browsing and favoriting recipes, meal plan viewing and grocery generation, and a dashboard summarizing user metrics.
- **Key features & functionality:**
  - User registration, login, and profile management (biodata).
  - Multi-step form to collect personal info, physical characteristics, and nutrition goals.
  - Chatbot that can parse natural language commands to update/query biodata.
  - Recipe browsing with favorites; integration to external recipe suggestion service (observed POST to `http://10.3.38.125:5001/api/recipes`).
  - Meal plans with days/meals and grocery list generation.
  - LocalStorage-backed client state (biodata, mealPlans, recipeFavorites) — needs backend equivalents for persistence and multi-device sync.
  - LLM and external recipe service integration.
- **Data entities identified:**
  - User (auth + profile)
  - Profile / BioData
  - Recipe
  - RecipeFavorite (or favorites as relationship)
  - MealPlan (with DayMeals and Meal)
  - GroceryList & GroceryItem
  - ChatMessage / ChatHistory
  - Health/Analytics (derived stats)

---

## 2. Database Schema Requirements

Recommendation: Use PostgreSQL for relational modeling and Prisma (or TypeORM/Sequelize) for ORM. Models below use Postgres data types.

- **User**
  - id: UUID (PK)
  - email: varchar(255) UNIQUE NOT NULL
  - password_hash: varchar(255) NOT NULL
  - created_at: timestamp with time zone DEFAULT now()
  - updated_at: timestamp with time zone
  - role: varchar(32) DEFAULT 'user'  -- enum('user','admin')
  - is_active: boolean DEFAULT true
  - last_login: timestamp with time zone NULL
  - indexes: unique on email; index on role

- **Profile (BioData)** — 1:1 with User
  - id: UUID (PK)
  - user_id: UUID (FK -> User.id) UNIQUE NOT NULL
  - first_name: varchar(100)
  - gender: varchar(32)  -- enum: 'male','female','non-binary','prefer not to say'
  - zip_code: varchar(16)
  - weight_kg: numeric(6,2)
  - height_cm: numeric(6,2)
  - age: integer
  - dietary_restrictions: text  -- possibly JSON array or text blob
  - budget_constraints: text
  - diet_health_goals: text
  - created_at: timestamp with time zone DEFAULT now()
  - updated_at: timestamp with time zone
  - indexes: index on user_id; index on zip_code (if location-based features later)

- **Recipe**
  - id: UUID (PK)
  - external_id: varchar(255) NULL  -- if from external API
  - name: varchar(255) NOT NULL
  - description: text NULL
  - image_url: varchar(1000) NULL
  - source_url: varchar(2000) NULL
  - source_name: varchar(255) NULL
  - prep_time_minutes: integer NULL
  - cook_time_minutes: integer NULL
  - servings: integer NULL
  - difficulty: varchar(16) NULL  -- 'Easy'|'Medium'|'Hard'
  - tags: text[] or jsonb  -- store array of tags
  - nutrients: jsonb NULL  -- calories/protein/carbs/fat
  - created_by: UUID NULL  -- user id if user-submitted
  - created_at, updated_at
  - indexes: index on name, GIN index on tags for search

- **RecipeFavorite**
  - id: UUID (PK)
  - user_id: UUID (FK -> User.id)
  - recipe_id: UUID (FK -> Recipe.id)
  - created_at: timestamp
  - unique constraint (user_id, recipe_id)
  - indexes: index on user_id

- **MealPlan**
  - id: UUID (PK)
  - user_id: UUID (FK -> User.id)
  - name: varchar(255)
  - start_date: date
  - end_date: date
  - is_current: boolean DEFAULT false
  - days: jsonb  -- array of DayMeals objects (see types)
  - total_calories: integer NULL
  - created_at, updated_at
  - indexes: index on user_id, index on is_current

  DayMeals (embedded as JSON):
  - day: string (e.g., "Monday" or date)
  - breakfast: Meal
  - lunch: Meal
  - dinner: Meal
  - snacks?: Meal[]

  Meal:
  - name
  - description
  - calories
  - protein
  - carbs
  - fat
  - recipe_id?: UUID (optional reference to Recipe)

- **GroceryList**
  - id: UUID (PK)
  - user_id: UUID (FK -> User.id)
  - meal_plan_id: UUID (FK -> MealPlan.id) NULL
  - items: jsonb  -- array of GroceryItem objects
  - total_cost: numeric(10,2)
  - created_at, updated_at
  - indexes: index on user_id

  GroceryItem:
  - name
  - quantity: numeric or string
  - unit (e.g., 'kg','each')
  - category
  - estimated_price

- **ChatMessage**
  - id: UUID
  - user_id: UUID
  - role: enum('user','assistant')
  - content: text
  - timestamp: timestamp
  - meta: jsonb (e.g., updatedFields, actionType)
  - indexes: index on user_id, timestamp

- **Audit / Logs (optional)** — track updates for compliance

Relationships:
- User 1:N MealPlan, 1:1 Profile, 1:N GroceryList, 1:N ChatMessage
- Recipe N:M User through RecipeFavorite
- MealPlan contains (in JSON) DayMeals which may reference Recipes

Indexes & Constraints:
- Unique email on User
- Unique (user_id, recipe_id) on RecipeFavorite
- FK constraints for user relations with cascading deletes on user deletion (configurable; maybe soft-delete users)
- GIN index on recipe.tags and search fields for efficient filtering

---

## 3. Authentication & Authorization

- **Authentication strategy:**
  - JWT (short-lived access token) + Refresh token (httpOnly secure cookie) OR session-based with server-side session store.
  - Passwords stored as salted hashes (bcrypt/argon2).
  - Optionally support OAuth2 (Google Apple) for third-party sign-in.
  - All endpoints that mutate user-specific data require authentication.
  - Use TLS for all traffic.

- **User roles & permissions:**
  - Roles: user (default), admin.
  - Permissions:
    - user: read/write own profile, create/read own meal plans, favorite/unfavorite recipes, chat with assistant, request recipe suggestions.
    - admin: manage recipes, view application metrics, moderate content.

- **Protected routes & resources:**
  - All `/api/profile*`, `/api/meal-plans*`, `/api/grocery*`, `/api/recipes/favorite*` require authentication.
  - Admin-only: `/api/admin/*` endpoints (managing recipe catalogue, metrics).

- **Token structure & expiration:**
  - Access token: JWT with 15 min expiry.
  - Refresh token: httpOnly cookie valid 7-30 days, rotate on use.
  - Revoke refresh tokens on logout.

- **CSRF:**
  - For cookie-based tokens, implement CSRF protection (double-submit cookie or SameSite cookies).

---

## 4. API Endpoints Specification

For each endpoint below: method, path, description, auth, validation, responses, business logic, related components.

Note: replace :id with UUID.

### User / Auth Endpoints

#### Register User
- **Method:** POST
- **Path:** `/api/auth/register`
- **Description:** Create a new user account and initial profile.
- **Authentication:** Optional
- **Authorization:** n/a
- **Request Body (JSON):**
  {
    "email": "user@example.com",
    "password": "securePassword123",
    "firstName": "Jane",            // optional
    "gender": "female",             // optional
    "zipCode": "12345"              // optional
  }
- **Response:**
  - Success 201:
    {
      "user": { "id": "uuid", "email": "user@example.com" },
      "accessToken": "jwt...",
      "refreshTokenSetCookie": true
    }
  - Errors:
    - 400: validation error (e.g., invalid email, password too short)
    - 409: email already exists
    - 500: server error
- **Business Logic:**
  - Validate inputs (email format, password strength).
  - Hash password (bcrypt/argon2).
  - Create User row and Profile (if provided).
  - Issue tokens.
- **Validation rules:**
  - email: required, valid format
  - password: min 6 (prefer 8+), recommended complexity
  - firstName: optional max 50
- **Related Components:**
  - `components/LoginForm.tsx`, registration page `app/register/page.tsx`

#### Login
- **Method:** POST
- **Path:** `/api/auth/login`
- **Description:** Authenticate user, return tokens.
- **Authentication:** Optional
- **Authorization:** n/a
- **Request Body:**
  {
    "email": "user@example.com",
    "password": "securePassword123",
    "remember": true  // optional
  }
- **Response:**
  - Success 200:
    {
      "user": { "id":"uuid","email":"..." },
      "accessToken": "jwt...",
      "refreshTokenSetCookie": true
    }
  - Errors:
    - 400: invalid payload
    - 401: incorrect credentials
    - 423: account disabled
- **Business Logic:**
  - Verify password hash.
  - Issue access token + refresh token (httpOnly cookie).
  - Update last_login timestamp.
- **Validation:**
  - email required, password required
- **Related Components:**
  - `components/LoginForm.tsx`, login page `app/login/page.tsx`

#### Logout
- **Method:** POST
- **Path:** `/api/auth/logout`
- **Description:** Revoke refresh token and clear cookie.
- **Authentication:** Required
- **Request Body:** none
- **Response:**
  - 204 No Content on success
  - 401 if token invalid
- **Business Logic:**
  - Invalidate refresh token server-side.
  - Clear httpOnly cookie.
- **Related Components:**
  - Any UI that logs out user (e.g., sidebar sign-out control)

#### Refresh Token
- **Method:** POST
- **Path:** `/api/auth/refresh`
- **Description:** Exchange refresh token cookie for new access token.
- **Authentication:** Cookie-based refresh token
- **Response:**
  - 200 with new access token
  - 401 if refresh token missing/invalid
- **Related components:** client-side token refresh logic

#### Get Current User
- **Method:** GET
- **Path:** `/api/auth/me`
- **Description:** Return user data and profile.
- **Authentication:** Required
- **Response:**
  - 200:
    {
      "user": { "id":"uuid","email":"...", "role":"user" },
      "profile": { ...BioData... }
    }
  - 401 if not authenticated
- **Related Components:**
  - Dashboard `app/(app)/dashboard/page.tsx` (loads biodata), Profile `app/(app)/profile/page.tsx`

---

### Profile & BioData Endpoints

#### Get Profile / BioData
- **Method:** GET
- **Path:** `/api/profile`  (returns current user's profile)
- **Description:** Retrieve current user's profile/biodata.
- **Authentication:** Required
- **Response:**
  - 200:
    {
      "profile": {
        "firstName": "John",
        "gender": "male",
        "zipCode": "12345",
        "weight_kg": 75.5,
        "height_cm": 180,
        "age": 30,
        "dietary_restrictions": ["peanuts"],
        "budget_constraints": "$60 per week",
        "diet_health_goals": "weight loss"
      }
    }
  - 404 if profile not found
- **Business Logic:**
  - Fetch profile by user_id
- **Validation:**
  - n/a (GET)
- **Related Components:**
  - Dashboard, ProfileDisplay, MultiStepForm, Chatbot

#### Create / Update Full Profile
- **Method:** PUT
- **Path:** `/api/profile`
- **Description:** Replace or create full profile for current user.
- **Authentication:** Required
- **Request Body (JSON):**
  See schema below (BioData). Example:
  {
    "firstName": "Jane",
    "gender": "female",
    "zipCode": "90210",
    "weight_kg": 68.0,
    "height_cm": 166.0,
    "age": 29,
    "dietary_restrictions": ["gluten"],
    "budget_constraints": "$80 per week",
    "diet_health_goals": "muscle gain"
  }
- **Response:**
  - 200 with updated profile
  - 400 validation errors
- **Business Logic:**
  - Validate full schema and upsert profile row
- **Validation rules:**
  - firstName: optional string <=50
  - gender: allowed enum
  - zipCode: length 5-10
  - weight_kg: >0 && <1000
  - height_cm: >0 && <300
  - age: >0 && <150
  - dietary_restrictions: array of strings or comma-separated text normalized
  - budget_constraints: text <=500
  - diet_health_goals: text <=1000
- **Related Components:**
  - `components/MultiStepForm.tsx`

#### Patch / Partial Update BioData
- **Method:** PATCH
- **Path:** `/api/profile`
- **Description:** Partial update of profile fields; used by chatbot updates and partial form saves.
- **Authentication:** Required
- **Request Body (JSON) — only fields to update:**
  { "weight_kg": 75, "dietary_restrictions": ["peanuts","dairy"] }
- **Response:**
  - 200 updated profile
  - 400 invalid fields
- **Business Logic:**
  - Merge partial fields; validate individual fields
  - Record audit of changed fields
- **Validation:**
  - Same as PUT but field-specific
- **Related Components:**
  - Chatbot `app/(app)/chatbot/page.tsx` (when user says "Update my weight"), MultiStepForm auto-save or step saves

---

### Recipes Endpoints

#### Search / List Recipes
- **Method:** GET
- **Path:** `/api/recipes`
- **Description:** Search and list recipes with pagination & filters.
- **Authentication:** Optional (authenticated returns favorites flags)
- **Query Params:**
  - q: string (search query)
  - tags: comma-separated tags
  - difficulty: Easy|Medium|Hard
  - minCalories, maxCalories: integer
  - page: integer (default 1)
  - limit: integer (default 20, max 100)
  - sort: 'relevance'|'popularity'|'newest'
- **Response 200:**
  {
    "meta": { "page":1,"limit":20,"total": 123 },
    "data": [{ recipe objects }]
  }
- **Errors:**
  - 400 invalid params
  - 500 server error
- **Business Logic:**
  - Combine local DB recipes + external API sources (if allowed).
  - If external recipe service (observed `http://10.3.38.125:5001/api/recipes`) is used, proxy or cache results.
  - Add `isFavorite` if user is authenticated.
- **Related Components:**
  - `components/recipes/RecipeGrid.tsx`, `RecipeCard.tsx`, `app/(app)/recipes/page.tsx`

#### Get Recipe by ID
- **Method:** GET
- **Path:** `/api/recipes/:id`
- **Description:** Fetch single recipe detail.
- **Authentication:** Optional
- **Path Params:**
  - id: recipe UUID
- **Response:**
  - 200 recipe object
  - 404 recipe not found
- **Related Components:**
  - Recipe detail (if exists), RecipeCard tooltips

#### Create Recipe (Admin/User-submitted)
- **Method:** POST
- **Path:** `/api/recipes`
- **Description:** Create a new recipe (admin or user-submitted).
- **Authentication:** Required
- **Authorization:** user (owner) or admin (global create)
- **Request Body:**
  {
    "name":"Chicken Salad",
    "description":"...",
    "ingredients":[{"name":"chicken","quantity":"200","unit":"g"}],
    "steps":["..."],
    "image_url":"https://...",
    "prep_time_minutes":10,
    "cook_time_minutes":15,
    "servings":2,
    "tags":["salad","quick"]
  }
- **Response:**
  - 201 created recipe
  - 400 validation errors
- **Business Logic:**
  - Validate content, optionally run content moderation
  - Save to DB, mark created_by = user_id
- **Related Components:**
  - Admin recipe creation UI (not present in frontend), future UX

#### Favorite / Unfavorite Recipe
- **Method:** POST / DELETE
- **Path:** `/api/recipes/:id/favorite`
- **Description:**
  - POST: add to favorites
  - DELETE: remove from favorites
- **Authentication:** Required
- **Response:**
  - 200 success with current favorite count and boolean
  - 404 if recipe not found
- **Business Logic:**
  - Upsert or delete row in RecipeFavorite
  - Return updated count
- **Related Components:**
  - RecipeCard, RecipeGrid, Dashboard favorite count

---

### Meal Plans Endpoints

#### List Meal Plans
- **Method:** GET
- **Path:** `/api/meal-plans`
- **Description:** List user's meal plans
- **Authentication:** Required
- **Query Params:**
  - is_current: boolean
  - page, limit
- **Response:**
  - 200 { meta, data: [meal plan objects] }
- **Related Components:**
  - `components/meal-plans/MealPlanList.tsx`, Dashboard MealPlanSummary

#### Create Meal Plan
- **Method:** POST
- **Path:** `/api/meal-plans`
- **Description:** Create a new meal plan for user
- **Authentication:** Required
- **Request Body:**
  {
    "name":"Weekly Plan",
    "start_date":"2025-11-17",
    "end_date":"2025-11-23",
    "days":[ { day: "Monday", breakfast: {...}, lunch: {...}, dinner: {...} }, ... ],
    "is_current": true
  }
- **Response:**
  - 201 created
  - 400 validation
- **Business Logic:**
  - Validate timeframe and days length; ensure only one is_current true (toggle others)
- **Related Components:**
  - MealPlan creation UI, MealPlanList, SelectedMealPlan

#### Get / Update / Delete Meal Plan
- **Method:** GET/PUT/PATCH/DELETE
- **Path:** `/api/meal-plans/:id`
- **Description:** fetch/update/delete a meal plan
- **Authentication:** Required (owner)
- **Response codes:**
  - GET 200
  - PUT 200 updated
  - PATCH 200 partial update
  - DELETE 204
- **Business Logic:**
  - Ensure ownership; cascade delete grocery lists if configured; allow linking recipes.

#### Activate Meal Plan
- **Method:** POST
- **Path:** `/api/meal-plans/:id/activate`
- **Description:** Mark a meal plan as current (is_current).
- **Authentication:** Required
- **Business Logic:**
  - Set all other user's meal plans is_current=false; set this to true.

#### Generate Grocery List From Meal Plan
- **Method:** POST
- **Path:** `/api/meal-plans/:id/grocery-list` or `/api/grocery/generate`
- **Description:** Generate grocery list for a meal plan, optionally call external service/logic to aggregate items & price estimates.
- **Authentication:** Required
- **Request Body:**
  {
    "include_snacks": true,
    "store": "Default",
    "budget": "user budget or override"
  }
- **Response:**
  - 201 GroceryList object
- **Business Logic:**
  - Aggregate ingredients across meals, normalize units, dedupe, estimate price (optional third-party price API)
- **Related Components:**
  - `components/meal-plans/GroceryListModal.tsx`

---

### Grocery Endpoints

#### Get Grocery List(s)
- **Method:** GET
- **Path:** `/api/grocery-lists`
- **Authentication:** Required
- **Query:** `meal_plan_id`
- **Response:** 200 list or specific

#### Create / Update / Delete Grocery List
- **Methods:** POST, PUT, DELETE
- **Path:** `/api/grocery-lists` or `/api/grocery-lists/:id`
- **Business Logic:**
  - CRUD for grocery lists; link to meal plans; recalc total_cost

---

### Chat & NLP Endpoints

Currently the frontend runs NLP parsing locally (`lib/nlpParser.ts`) but to support server-side persistence, LLM processing, or multi-device chat:

#### Parse & Process Chat Message (LLM-backed)
- **Method:** POST
- **Path:** `/api/chat/parse`
- **Description:** Accept user message, run parser + (optionally) send to LLM/external service to generate response; apply profile updates if commanded.
- **Authentication:** Required
- **Request Body:**
  {
    "message": "Update my weight to 75 kg"
  }
- **Response:**
  - 200:
    {
      "assistantMessage": "✅ Updated successfully! ...",
      "updatedFields": ["weight"],
      "profile": { ...updated profile... }
    }
  - 400 invalid
- **Business Logic:**
  - Run server-side command parser (same logic as lib/nlpParser), apply patch to profile, call LLM if more complex reasoning needed, return structured response.
  - Persist ChatMessage in DB if enabled.
- **Validation:**
  - message: non-empty string
- **Related Components:**
  - Chatbot page & components `app/(app)/chatbot/page.tsx`, ChatInput, ChatMessage

#### Chat History
- **Method:** GET
- **Path:** `/api/chat/history`
- **Params:** page, limit
- **Authentication:** Required
- **Response:** list of ChatMessage objects
- **Business Logic:** Retrieve user's chat history for UI

WebSocket endpoint for real-time chat:
- Path: `/ws/chat` (optional)
- Purpose: deliver immediate assistant responses and let server push updates (e.g., profile change notifications).

---

### Utility Endpoints

#### Health Check
- **Method:** GET
- **Path:** `/api/health`
- **Description:** Basic health/status of backend and key integrations.
- **Auth:** Optional (or restrict for internal)
- **Response:**
  - 200 { "status":"ok", "timestamp": "...", "dependencies": { "db":"ok", "llm":"ok" } }

#### Metrics / Status (Admin)
- **Method:** GET
- **Path:** `/api/admin/status`
- **Auth:** Admin
- **Response:** Usage metrics

---

## 5. Endpoint Categories

- User Management
  - /api/auth/* (register, login, logout, refresh)
  - /api/auth/me
- Profile / BioData
  - /api/profile (GET/PUT/PATCH)
- Recipes
  - /api/recipes (GET/POST)
  - /api/recipes/:id (GET/PUT/DELETE)
  - /api/recipes/:id/favorite (POST/DELETE)
- Meal Plans
  - /api/meal-plans (GET/POST)
  - /api/meal-plans/:id (GET/PUT/PATCH/DELETE)
  - /api/meal-plans/:id/activate (POST)
  - /api/meal-plans/:id/grocery-list (POST)
- Grocery
  - /api/grocery-lists (GET/POST/PUT/DELETE)
- Chat & NLP
  - /api/chat/parse (POST)
  - /api/chat/history (GET)
  - /ws/chat for real-time
- Utilities
  - /api/health
  - /api/admin/*

---

## 6. Data Validation Requirements

- Use a schema validation library both server-side and client-side: Zod (the project already uses Zod on client) or Joi.
- Shared validation rules should be kept in a shared repository or duplicated carefully.
- Important field validation (examples):
  - email: valid RFC email string
  - password: min length 8 (stronger recommended), disallow common passwords
  - firstName: max 50
  - gender: enum values
  - zipCode: pattern by country or min/max length 5-10
  - weight_kg: numeric, >0, <1000
  - height_cm: numeric, >0, <300
  - age: integer, >0, <150
  - recipe name: non-empty, max 255
  - image_url: must be valid URL if provided
  - mealPlan dates: start_date <= end_date
- Sanitization:
  - Strip dangerous HTML inputs for any free-text fields before storing or offer stored-safe representation (escape on render).
  - Use parameterized queries in DB access to avoid SQL injection.
- Error handling patterns:
  - Use consistent error response format:
    {
      "error": { "code": "VALIDATION_ERROR", "message": "Field x is required", "details": { "field":"x", "issue":"required" } }
    }
  - Use 4xx for client errors, 5xx for server errors, 401/403 for auth issues, 404 for not found.

---

## 7. External Integrations

- **Recipe Suggestion Service (observed):**
  - `http://10.3.38.125:5001/api/recipes` used in `MultiStepForm.tsx`.
  - Integrate via authenticated server-side proxy to avoid exposing internal addresses to clients. Implement caching and retries.
- **LLM / NLP:**
  - Optional: OpenAI, Anthropic, or local LLM endpoints to interpret `dietHealthGoals` and produce meal plans or extract structured info.
  - Chat parsing can be performed on server-side with the `nlpParser` logic or enhanced with an LLM for ambiguous inputs.
- **Price Estimation / Grocery pricing:**
  - Optional third-party APIs (store price APIs) for grocery cost estimation.
- **Storage:**
  - S3-compatible object storage for recipe images and user-uploaded images.
- **Analytics:**
  - Optional: Segment, Amplitude, or custom telemetry.

Webhooks / Events:
- On profile update: emit event to a queue (e.g., RabbitMQ or Redis Streams) if downstream LLM or personalization service needs real-time updates.
- On meal plan generation: event to background worker to precompute grocery pricing.

---

## 8. File Uploads & Media Handling

- **File upload endpoints (server-side):**
  - POST `/api/uploads` (multipart/form-data) to upload images (recipes/user avatars).
  - Use pre-signed uploads to S3 to avoid sending large files through app server.
- **Storage strategy:**
  - Store images in S3 (or equivalent) and save CDN-enabled URL in DB.
  - Thumbnails generated by background worker or on upload via Lambda.
- **Allowed types & sizes:**
  - image/jpeg, image/png, image/webp
  - Max file size: 5MB (adjustable)
  - Validate MIME type and perform virus scan if high-risk deployments.
- **Responses:**
  - 201 { "url":"https://cdn.example.com/..." }

---

## 9. Real-time Features

- **Requirements:**
  - Chat experience could be made real-time using WebSockets or SSE.
  - Real-time updates to meal plans or grocery list shared between devices (optional).
- **Proposed approach:**
  - Use WebSocket endpoint `/ws/chat` for real-time chat message streaming.
  - Alternatively use server-sent events (SSE) for one-way streaming from server to client (useful for LLM streaming).
  - Authentication via access token passed in connection handshake (query param or cookie).
  - Use scalable real-time infrastructure (Socket.io + Redis adapter, or Pusher/Ably).
- **Event flows:**
  - New assistant message -> broadcast to client(s)
  - Profile update -> broadcast to dashboard clients

---

## 10. Pagination, Filtering & Sorting

- **Endpoints needing pagination:**
  - /api/recipes (page & limit)
  - /api/meal-plans (page & limit)
  - /api/chat/history (page & limit)
- **Filtering parameters:**
  - recipes: tags, difficulty, calories range, query q, favorites-only
  - meal-plans: is_current, date range
  - grocery-lists: meal_plan_id
- **Sorting:**
  - recipes: relevance, popularity, newest, prep_time
  - meal-plans: start_date, created_at

**Pagination format:**
- Use standard metadata:
  {
    "meta": { "page":1, "limit":20, "total": 123, "totalPages":7 },
    "data": [...]
  }

---

## 11. Rate Limiting & Security

- **Rate limiting:**
  - Implement global rate limit per IP (e.g., 100 requests per minute).
  - Authenticated user limits: e.g., 1000 requests per day; stricter for endpoints that call external services (LLM).
  - API keys or billing tiers may adjust limits later.
- **CORS:**
  - Allow frontend origin(s) only (configured via env), reject open CORS.
  - For server-side calls from frontend, use secure cookie flags and CSRF protections.
- **Security headers:**
  - Use Helmet or equivalent to set:
    - Content-Security-Policy
    - X-Frame-Options: DENY
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: same-origin
- **Input sanitization:**
  - Escape or strip HTML from text inputs.
  - Validate and cast numeric inputs; normalize arrays.
- **Secrets:**
  - Store API keys, DB credentials, and service keys in secure environment variables / secret manager.
- **Logging & Monitoring:**
  - Structured logs for auth failures, 5xx errors.
  - Integrate Sentry or similar for error tracking.

---

## 12. Implementation Priority

- **Critical (MVP)**
  - Auth: register, login, refresh, logout
  - Profile endpoints (GET/PATCH) for saving and retrieving biodata
  - Recipes search/list (read-only)
  - Mark/unmark favorites
  - Meal plan list & basic create/update
  - Health endpoint
  - Chat parse endpoint (server-side) OR keep client-side parser with optional server persistence
- **Important**
  - Full CRUD for recipes (create/edit/delete) and admin management
  - Grocery list generation endpoint & storage
  - Real-time chat streaming (SSE or WebSocket)
  - External recipe service proxy & caching
  - File uploads (image uploads)
- **Nice-to-have**
  - LLM-backed advanced personalization and meal-plan generation
  - Price estimation integration for grocery items
  - Analytics dashboards and admin metrics
  - Webhooks and event-driven architecture for downstream services

---

## 13. Technology Recommendations

- **Backend framework:**
  - Node.js + NestJS (structured and modular), or
  - Express + TypeScript (lighter) OR Next.js API routes for small projects
- **ORM & DB:**
  - PostgreSQL with Prisma ORM (strong TypeScript experience)
- **Authentication:**
  - `jsonwebtoken` for JWTs + secure refresh token store
  - `argon2` or `bcrypt` for password hashing
- **Validation:**
  - Zod for TypeScript-compatible validation (already used in frontend)
- **Real-time:**
  - Socket.io + Redis adapter for scaling, or Pusher/Ably for managed service
- **File storage:**
  - AWS S3 + CloudFront (or DigitalOcean Spaces)
- **LLM Integration:**
  - OpenAI or provider with streaming capability; wrap requests in server to avoid exposing keys
- **Deployment:**
  - Containerized deployment (Docker) on AWS ECS, GCP Cloud Run, or Vercel (for Next.js API routes)
  - Use managed Postgres (RDS / Neon) with connection pooling
- **Observability:**
  - Sentry for errors, Prometheus/Grafana for metrics, or hosted solutions

---

## Appendices & Examples

- **BioData JSON Schema (Zod-like)**
```json
{
  "firstName": "string (max 50)",
  "gender": "male|female|non-binary|prefer not to say",
  "zipCode": "string (5-10)",
  "weight_kg": 75.5,
  "height_cm": 180,
  "age": 30,
  "dietary_restrictions": ["peanuts","gluten"],
  "budget_constraints": "$100 per week",
  "diet_health_goals": "lose weight, reduce sugar"
}
```

- **Example: POST /api/profile (update)**
Request:
```http
POST /api/profile
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "weight_kg": 82,
  "height_cm": 177,
  "dietary_restrictions": ["peanuts","dairy"]
}
```
Success 200:
```json
{
  "profile": {
    "user_id": "uuid",
    "weight_kg": 82,
    "height_cm": 177,
    "dietary_restrictions": ["peanuts","dairy"],
    "updated_at": "2025-11-17T12:34:56Z"
  }
}
```

- **Example error response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "weight_kg must be greater than 0",
    "details": { "weight_kg": "must be > 0" }
  }
}
```

- **Notes & Edge Cases:**
  - Client currently persists biodata, mealPlans, recipeFavorites to `localStorage`. To support multi-device sync, implement endpoints to read/write these entities server-side and migrate client data on first sync.
  - The MultiStepForm posts to an IP `http://10.3.38.125:5001/api/recipes` — this likely requires relocation behind a server-side proxy and proper auth; do not call internal IPs from the browser in production.
  - The current chatbot parsing logic lives in client `lib/nlpParser.ts`. If you want controlled updates and audit trails, move parsing to server-side and persist chat updates.
  - For any cascading deletes (e.g., user deletion), either use soft deletes or ensure cascade rules for meal plans, grocery lists, favorites, chat history.
  - Validation duplication: keep server-side rules authoritative (Zod schemas shared or duplicated with tests).

---

If you'd like, I can:
- Create `BACKEND_API_SPEC.md` at repository root (done).
- Scaffold a minimal Express + Prisma starter implementing the core MVP endpoints (auth, profile, recipes search).
- Move client-side NLP parsing into a server endpoint `/api/chat/parse` and wire the frontend to use it (I can implement this as a patch).

Which next step do you want me to take?
