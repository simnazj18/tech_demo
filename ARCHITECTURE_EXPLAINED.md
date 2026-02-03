# Architecture & Workflow Explanation: Login & Multi-Tenancy

This document explains the technical implementation of the new **Login System**, **Multi-Account Support**, and **Service Selection** features added effectively in Phase 3.

## 1. High-Level Architecture
We transitioned the application from a "Stateless Viewer" (relying on hardcoded environment variables) to a **"Stateful Multi-Tenant Platform"**.

### key Components:
*   **Database (SQLite)**: Stores *Users* and *Azure Service Principal Credentials*.
*   **Backend (FastAPI + SQLAlchemy)**: Manages authentication, data persistence, and dynamic secret scanning.
*   **Frontend (Jinja2 + Bootstrap)**: Provides interactive Login, Registration, and Account Switching UIs.
*   **Security (JWT)**: JSON Web Token cookies maintain user sessions securely.

---

## 2. Authentication Flow (The "Login" Process)
The authentication system uses **OAuth2 with Password Flow**, implemented via JWT tokens stored in HTTP-only cookies.

### Step-by-Step Workflow:
1.  **Registration (`/register`)**:
    *   User submits Username/Password.
    *   Backend hashes the password using **Bcrypt** (secure hashing algorithm).
    *   User is saved to the `users` table in the database.
2.  **Login (`/token`)**:
    *   User submits credentials.
    *   Backend verifies the hash against the database.
    *   If valid, a **JWT Access Token** is generated (expiration: 30 mins).
    *   The token is sent back and stored in the browser's `access_token` cookie.
3.  **Protected Routes**:
    *   Every request to the Dashboard (`/`) runs a dependency check: `get_current_user_cookie`.
    *   This function decodes the JWT.
    *   If invalid or missing -> **Redirect to `/login`**.
    *   If valid -> **Allow Access**.

---

## 3. Multi-Account Dynamic Scanning
This is the core "Business Logic" update. Previously, the app could only scan *one* vault defined in env vars. Now, it can scan *any* vault the user owns.

### functionality:
1.  **Data Model (`models.py`)**:
    *   `AzureAccount` table stores: `client_id`, `client_secret`, `tenant_id`, `vault_url`.
    *   These are linked to the `User` via a Foreign Key (`owner_id`).
2.  **Adding an Account**:
    *   User fills the "Add Account" modal.
    *   Data is saved to the SQLite database.
3.  **Dynamic Scanner Initialization (`services.py`)**:
    *   When you select an account from the dropdown, the Backend retrieves that specific account's credentials.
    *   It initializes a **new** `SecretClient` instance on the fly using those exact credentials.
    *   It scans the target Key Vault immediately.

### Code Highlight (`main.py`):
```python
# Instead of global settings, we load from DB:
scanner = SecretScanner(
    vault_url=selected_account.keyvault_url,
    client_id=selected_account.client_id,  # <--- Dynamic
    client_secret=selected_account.client_secret, # <--- Dynamic
    tenant_id=selected_account.tenant_id
)
```

---

## 4. Frontend Integration
*   **Context Switching**: The Navbar request `/?account_id=X`. The backend detects this query parameter, loads Account X, and renders the dashboard with that account's data.
*   **Empty State**: If a user has no accounts, a special "Welcome" template is shown to guide them through the setup.

## Summary of Changes
| Feature | Old Way | New Way (Phase 3) |
| :--- | :--- | :--- |
| **Storage** | None (Env Vars) | **SQLite Database** (`techdemo.db`) |
| **Auth** | None (Open Access) | **JWT Login** (Username/Password) |
| **Tenancy** | Single Tenant | **Multi-Tenant** (User can have N accounts) |
| **Scanning** | Static Global Scanner | **Dynamic Per-Request Scanner** |
