from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime, timezone

from app import models, schemas, auth
from app.database import engine, get_db, init_db
from app.services import SecretScanner
from app.config import settings
from sqlalchemy import desc

# Create Tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Secrets Drift Dashboard")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- Auth Routes ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Query for user directly
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Check existing
    if db.query(models.User).filter(models.User.username == username).first():
       return templates.TemplateResponse("login.html", {"request": {}, "error": "Username already exists"})
    
    hashed = auth.get_password_hash(password)
    user = models.User(username=username, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return RedirectResponse(url="/login", status_code=303)


# --- Dashboard & Account Routes ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    account_id: int = None,
    service_type: str = None, # Default to None (Force selection)
    current_user: models.User = Depends(auth.get_current_user_cookie),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    # Fetch User's Accounts
    accounts = current_user.accounts
    
    selected_account = None
    scan_data = {"akv_secrets": [], "k8s_usage": []}
    audit_logs = []
    
    if account_id:
        selected_account = db.query(models.AzureAccount).filter(models.AzureAccount.id == account_id).first()
    elif accounts:
        selected_account = accounts[0] # Default to first
    
    # Only scan if BOTH Account AND Service Type are selected
    if selected_account and service_type:
        # Initialize Scanner
        scanner = SecretScanner(
            vault_url=selected_account.keyvault_url,
            client_id=selected_account.client_id,
            client_secret=selected_account.client_secret,
            tenant_id=selected_account.tenant_id
        )
        data = scanner.get_dashboard_data()
        
        # Apply Filters
        # Apply Filters
        if service_type == "akv":
            scan_data["akv_secrets"] = data['akv_secrets']
        elif service_type == "aks":
             # AKS View now includes BOTH K8s Usage and AKV Inventory (Side-by-Side)
            scan_data["k8s_usage"] = data['k8s_usage']
            scan_data["akv_secrets"] = data['akv_secrets']
        elif service_type == "all":
            scan_data = data
            
    # Fetch Audit Logs
    if selected_account:
        audit_logs = db.query(models.AuditLog).filter(models.AuditLog.account_id == selected_account.id).order_by(desc(models.AuditLog.timestamp)).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": current_user,
        "accounts": accounts,
        "selected_account": selected_account,
        "service_type": service_type, 
        "akv_secrets": scan_data.get('akv_secrets', []),
        "k8s_usage": scan_data.get('k8s_usage', []),
        "audit_logs": audit_logs
    })

@app.post("/accounts/add")
async def add_account(
    name: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    tenant_id: str = Form(...),
    kv_url: str = Form(...), 
    current_user: models.User = Depends(auth.get_current_user_cookie),
    db: Session = Depends(get_db)
):
    new_account = models.AzureAccount(
        name=name,
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        keyvault_url=kv_url,
        owner_id=current_user.id
    )
    db.add(new_account)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/secrets/rotate")
async def rotate_secret(
    request: Request,
    account_id: int = Form(...),
    akv_secret_name: str = Form(...),
    k8s_secret_name: str = Form(None),
    deployment_name: str = Form(None),
    new_secret_value: str = Form(None),
    new_expiry_date: str = Form(None),
    current_user: models.User = Depends(auth.get_current_user_cookie),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    # Get Account
    account = db.query(models.AzureAccount).filter(models.AzureAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Initialize Scanner
    scanner = SecretScanner(
        vault_url=account.keyvault_url,
        client_id=account.client_id,
        client_secret=account.client_secret,
        tenant_id=account.tenant_id
    )

    # Parse Expiry Date if provided
    expiry_dt = None
    if new_expiry_date:
        try:
             # Expecting YYYY-MM-DD from HTML date input
             expiry_dt = datetime.fromisoformat(new_expiry_date)
             # Set to end of day or UTC
             expiry_dt = expiry_dt.replace(hour=23, minute=59, second=59)
        except Exception as e:
             print(f"Date Parsing Error: {e}")

    # Perform Rotation
    result = scanner.rotate_secret(
        akv_secret_name=akv_secret_name,
        k8s_secret_name=k8s_secret_name,
        deployment_name=deployment_name,
        new_secret_value=new_secret_value,
        new_expiry_date=expiry_dt
    )

    print(f"Rotation Result: {result}")
    
    # Create Audit Log
    log_status = "Success" if result["success"] else "Failed"
    log_action = "Rotated"
    log_entry = models.AuditLog(
        timestamp=datetime.now(timezone.utc),
        secret_name=akv_secret_name,
        action=log_action,
        status=log_status,
        details=result["message"],
        account_id=account.id
    )
    db.add(log_entry)
    db.commit()
    
    if result["success"]:
        return RedirectResponse(
            url=f"/?account_id={account_id}&service_type=aks&success={result['message']}", 
            status_code=303
        )
    else:
        return RedirectResponse(
            url=f"/?account_id={account_id}&service_type=aks&error={result['message']}", 
            status_code=303
        )
