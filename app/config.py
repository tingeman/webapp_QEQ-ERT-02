from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

class RunServerSettings(BaseSettings):
    DEBUG: bool = Field(..., env="DEBUG")

    class Config:
        env_file = ".env"


class ConfigSettings(BaseSettings):
    GRADIENT_INVERSION_PATH: Path = Field(..., env="GRADIENT_INVERSION_PATH")
    GRADIENT_INVERSION_URL: Path = Field(..., env="GRADIENT_INVERSION_URL")
    TASK_INFO_FILE: Path = Field(..., env="TASK_INFO_FILE")
    BAT_STATS_FILE: Path = Field(..., env="BAT_STATS_FILE")
    LS_LOG_FILE: Path = Field(..., env="LS_LOG_FILE")
    SUPPLY_DAT_FTR_FILE: Path = Field(..., env="SUPPLY_DAT_FTR_FILE")
    COMPLETED_PCT: float = Field(..., env="COMPLETED_PCT")

    class Config:
        env_file = ".env"


def load_environment():
    env = os.getenv('APP_ENV', 'production')
    env_file = f".env.{env}"
    
    if not os.path.exists(env_file):
        if os.path.exists(".env.example"):
            print(f"No {env_file} file found. Creating one from .env.example...")
            with open(".env.example") as f:
                example_content = f.read()
            with open(env_file, 'w') as f:
                f.write(example_content)
            print(f"Please update the {env_file} file with your configuration.")
        else:
            raise FileNotFoundError(f"No {env_file} or .env.example file found. Please create one.")

    load_dotenv(env_file)

load_environment()
run_server_settings = RunServerSettings()
settings = ConfigSettings()

