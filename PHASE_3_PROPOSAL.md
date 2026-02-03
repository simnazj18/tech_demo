# Phase 3: Multi-Tenancy, Authentication & Dynamic Azure Management

## Goal
Transform the "Secrets Drift Dashboard" from a static, single-tenant viewer into a **secure, multi-user management portal**. Users can login, manage multiple Azure Service Principals (for different subscriptions/clients), and switch between them dynamically.

## 1. Infrastructure Upgrades
- [ ] **SQL Server Service**: Create a K8s Service (`sql-service.yaml`) to expose the running `sql-server` pod to the dashboard via a stable DNS name (`sql-server`).
- [ ] **Database Setup**: Auto-initialize the SQL Database (`TechDemoDB`) and tables on app startup.

## 2. Dependencies & Build
- [ ] **Python Packages**: Add `sqlalchemy`, `pyodbc`, `passlib[bcrypt]`, `python-jose`, `python-multipart`.
- [ ] **Dockerfile**: Update to install system-level ODBC drivers (`msodbcsql17`) required for Python to talk to SQL Server.

## 3. Backend Architecture
### Database Schema (`app/models.py`)
- **User**: `id`, `username`, `password_hash`
- **AzureAccount**: `id`, `name` (alias), `client_id`, `client_secret` (encrypted?), `tenant_id`, `keyvault_url`, `user_id` (FK)

### Authentication (`app/auth.py`)
- Implement **JWT (JSON Web Token)** based authentication.
- Login Endpoint: `/auth/token` (verify user, return JWT).
- Dependency: `get_current_user` to protect routes.

### Dynamic Scanning (`app/services.py`)
- Refactor `SecretScanner` to **NO LONGER** rely on environment variables (`AZURE_CLIENT_ID`, etc.).
- Instead, it will accept an `AzureAccount` object at runtime to instantiate the `SecretClient`.
- This allows scanning *any* Key Vault the user has added.

## 4. Frontend / UI Improvements
- [ ] **Login Page**: A clean, professional entry point.
- [ ] **Account Management**: A generic "Settings" modal to:
    - Lists added Azure Accounts.
    - "Add New Account" form (Client ID, Secret, Tenant, KV URL).
- [ ] **Context Selector**: A dropdown in the top-nav to switch the "Active View" (e.g., "Dev Env (Account A)" vs "Prod Env (Account B)").
- [ ] **Service Selection**: A sidebar or dropdown to choose "AKS Secrets" or "Azure Key Vault Inventories".

## 5. Security Note
- We will store Client Secrets in the DB. In a production app, these should be encrypted at rest (e.g., via Fernet encryption). For this demo, we will store them as plain text or base64, but **User Passwords** will be strictly hashed (Bcrypt).

## Execution Steps
1.  **Fix Infra**: Create SQL Service.
2.  **Update Build**: Fix Dockerfile & Requirements.
3.  **Code**: Implement DB models, Auth, and Refactor Scanner.
4.  **UI**: Build Login and Management screens.
5.  **Verify**: Log in, Add Account, Validate Scan.
