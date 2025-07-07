"""
Main entry point for the MASS application
"""
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    """
    Run the MASS application using Uvicorn
    """
    # Define host and port
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    # Run application with uvicorn
    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=os.getenv("ENV", "production").lower() == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

if __name__ == "__main__":
    main()
