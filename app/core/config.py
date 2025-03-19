"""
Configuration settings for ReplyRocket.io.

This module handles environment-specific configuration values and ensures
secrets are properly loaded from environment variables.
"""

import os
import secrets
import logging
import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal

from pydantic import AnyHttpUrl, PostgresDsn, validator, Field, SecretStr
from pydantic_settings import BaseSettings


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BaseAppSettings(BaseSettings):
    """Base application settings shared across all environments."""
    
    # Environment settings
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ReplyRocket.io API"
    VERSION: str = "0.1.0"
    
    # Derived values
    IS_DEVELOPMENT: bool = False
    IS_STAGING: bool = False
    IS_PRODUCTION: bool = False
    IS_TEST: bool = False
    
    # Logging settings
    LOG_LEVEL: LogLevel = LogLevel.INFO
    LOG_FORMAT: LogFormat = LogFormat.TEXT
    
    # Security
    SECURE_COOKIES: bool = False
    
    @validator("ENVIRONMENT", pre=True)
    def validate_environment(cls, v: Any) -> EnvironmentType:
        if isinstance(v, str):
            # Strip comments and whitespace
            v = v.split("#")[0].strip().lower()
            try:
                return EnvironmentType(v)
            except ValueError:
                logging.warning(f"Invalid environment value: '{v}'. Falling back to development.")
                return EnvironmentType.DEVELOPMENT
        return v
    
    @validator("IS_DEVELOPMENT", "IS_STAGING", "IS_PRODUCTION", "IS_TEST", pre=True, always=True)
    def set_environment_flags(cls, v: bool, values: Dict[str, Any]) -> bool:
        if "ENVIRONMENT" not in values:
            return False
        env = values["ENVIRONMENT"]
        if v:  # If manually set to True, respect that
            return True
        return cls._check_environment_match(env, v)
    
    @validator("LOG_LEVEL", pre=True)
    def validate_log_level(cls, v: Any) -> LogLevel:
        if isinstance(v, str):
            # Strip comments and whitespace
            v = v.split("#")[0].strip().upper()
            try:
                return LogLevel(v)
            except ValueError:
                logging.warning(f"Invalid log level value: '{v}'. Falling back to INFO.")
                return LogLevel.INFO
        return v
    
    @validator("LOG_FORMAT", pre=True)
    def validate_log_format(cls, v: Any) -> LogFormat:
        if isinstance(v, str):
            # Strip comments and whitespace
            v = v.split("#")[0].strip().lower()
            try:
                return LogFormat(v)
            except ValueError:
                logging.warning(f"Invalid log format value: '{v}'. Falling back to TEXT.")
                return LogFormat.TEXT
        return v
    
    @validator("SECURE_COOKIES", pre=True)
    def validate_secure_cookies(cls, v: Any) -> bool:
        if isinstance(v, str):
            # Strip comments and whitespace
            v = v.split("#")[0].strip().lower()
            if v in ("true", "yes", "1", "t", "y"):
                return True
            if v in ("false", "no", "0", "f", "n"):
                return False
            logging.warning(f"Invalid secure cookies value: '{v}'. Falling back to False.")
        return False
    
    @classmethod
    def _check_environment_match(cls, env: EnvironmentType, flag_value: bool) -> bool:
        field_name = f"IS_{env.upper()}"
        return flag_value or field_name == f"IS_{env.upper()}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


class DevelopmentSettings(BaseAppSettings):
    """Settings for the development environment."""
    
    # Debug settings
    DEBUG: bool = True
    
    # Security settings - less strict for development
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days for easier development
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days for easier development
    SECURE_COOKIES: bool = False
    
    # CORS - more permissive for development
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Database settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432  # Default PostgreSQL port
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "replyrocket_dev"
    
    # AI Service settings
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    AI_MODEL: str = "gpt-3.5-turbo"
    
    # Database pool settings for development (smaller pool)
    DB_POOL_SIZE: int = 2
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    # Logging
    LOG_LEVEL: LogLevel = LogLevel.DEBUG
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Build database URI from component parts."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


class StagingSettings(BaseAppSettings):
    """Settings for the staging environment."""
    
    # Debug settings
    DEBUG: bool = False
    
    # Security settings - more strict for staging
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # Required from environment
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECURE_COOKIES: bool = True
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Database settings
    POSTGRES_SERVER: str = Field(..., env="POSTGRES_SERVER")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    
    # Database pool settings 
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Build database URI from component parts."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


class ProductionSettings(BaseAppSettings):
    """Settings for the production environment."""
    
    # Debug settings
    DEBUG: bool = False
    
    # Security settings - very strict for production
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # Required from environment
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Shorter token lifetime for security
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECURE_COOKIES: bool = True
    
    # CORS - restrict to specific domains in production
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Database settings
    POSTGRES_SERVER: str = Field(..., env="POSTGRES_SERVER")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    
    # Database pool settings - larger pool for production
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    # AI Service settings - required for production
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    AI_MODEL: str = Field(..., env="AI_MODEL")
    
    # Superuser - optional in production
    FIRST_SUPERUSER_EMAIL: Optional[str] = None
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None
    
    # Email settings - required for production
    EMAIL_TEMPLATES_DIR: str = "app/email-templates/"
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Build database URI from component parts."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


class TestSettings(BaseAppSettings):
    """Settings for the test environment."""
    
    # Debug settings
    DEBUG: bool = False
    
    # Security settings
    SECRET_KEY: str = "test-secret-key-not-used-in-real-environments"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1
    SECURE_COOKIES: bool = False
    
    # Database settings - use SQLite for tests
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./test.db"
    
    # Testing flag
    TESTING: bool = True


# Common validation for all settings classes
@validator("BACKEND_CORS_ORIGINS", pre=True)
def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
    """Parse CORS origins from string to list."""
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)


# Load settings based on the environment
def get_settings() -> BaseAppSettings:
    """
    Get the appropriate settings based on the ENVIRONMENT variable.
    Falls back to development settings if not specified.
    """
    # Get and clean the environment variable
    env_raw = os.getenv("ENVIRONMENT", "development")
    # Strip any comments and whitespace
    env_str = env_raw.split("#")[0].strip().lower() if env_raw else "development"
    
    # Map environment string to enum value
    env_map = {
        "development": EnvironmentType.DEVELOPMENT,
        "staging": EnvironmentType.STAGING,
        "production": EnvironmentType.PRODUCTION,
        "test": EnvironmentType.TEST
    }
    
    env = env_map.get(env_str, EnvironmentType.DEVELOPMENT)
    
    settings_class = {
        EnvironmentType.DEVELOPMENT: DevelopmentSettings,
        EnvironmentType.STAGING: StagingSettings, 
        EnvironmentType.PRODUCTION: ProductionSettings,
        EnvironmentType.TEST: TestSettings,
    }.get(env, DevelopmentSettings)
    
    try:
        settings = settings_class()
        
        # Check for critical settings
        required_vars = ["SECRET_KEY"]
        if env == EnvironmentType.PRODUCTION:
            required_vars.extend(["POSTGRES_PASSWORD", "OPENAI_API_KEY"])
        
        missing_vars = [var for var in required_vars if not getattr(settings, var, None)]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            if env == EnvironmentType.PRODUCTION:
                logging.error(error_msg)
                logging.error("Production deployment requires all security-critical variables to be set!")
                sys.exit(1)
            else:
                logging.warning(error_msg)
        
        # Log a warning if OPENAI_API_KEY is missing
        if not settings.OPENAI_API_KEY:
            logging.warning("OPENAI_API_KEY is not set. Please check your environment variables.")
        
        # Print SQLALCHEMY_DATABASE_URI for debugging
        logging.info(f"SQLALCHEMY_DATABASE_URI: {settings.SQLALCHEMY_DATABASE_URI}")
        
        return settings
    except Exception as e:
        logging.error(f"Failed to load settings: {str(e)}")
        if env == EnvironmentType.PRODUCTION:
            logging.error("Aborting startup due to missing critical configuration!")
            sys.exit(1)
        logging.warning(f"Falling back to development settings")
        return DevelopmentSettings()


# Instantiate the settings
settings = get_settings()

# Debug output for development environment
if settings.IS_DEVELOPMENT:
    print("\n" + "="*50)
    print("ENVIRONMENT VARIABLE DEBUGGING")
    print("="*50)
    print(f"ENVIRONMENT: '{settings.ENVIRONMENT}'")
    print(f"VERSION: '{settings.VERSION}'")
    print(f"SQLALCHEMY_DATABASE_URI: '{settings.SQLALCHEMY_DATABASE_URI}'")
    print(f"DEBUG: DB URL = {settings.SQLALCHEMY_DATABASE_URI}")  # Additional debugging
    print(f".env file location: {os.path.abspath('.env') if os.path.exists('.env') else '.env NOT FOUND!'}")
    print("="*50 + "\n")

# Add logging to warn if SQLALCHEMY_DATABASE_URI is missing
if not settings.SQLALCHEMY_DATABASE_URI:
    logging.warning("SQLALCHEMY_DATABASE_URI is not set. Please check your environment variables.")

# Function to manually test the database connection
def test_database_connection():
    from sqlalchemy import create_engine, text
    try:
        db_uri = settings.SQLALCHEMY_DATABASE_URI
        
        if not db_uri:
            logging.error("Database URI is None or empty")
            return False
            
        logging.info(f"Testing database connection with URI: {db_uri}")
        engine = create_engine(db_uri)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logging.info("Database connection test successful.")
            return result.scalar() == 1
    except Exception as e:
        logging.error(f"Database connection test failed: {str(e)}")
        return False

# Run the database connection test
if settings.IS_DEVELOPMENT or settings.IS_TEST:
    test_database_connection() 