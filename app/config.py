import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_KEYVAULT_URL: str = ""
    
    # Database & Security
    SQL_DATABASE_URL: str = "mssql+pyodbc://adminUser:P@ssw0rd123!@sql-server:1433/TechDemoDB?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
    SECRET_KEY: str = "supersecretkey" # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    KUBERNETES_NAMESPACE: str = "default"  # Default to 'default' namespace or 'all'
    
    class Config:
        env_file = ".env"

settings = Settings()
