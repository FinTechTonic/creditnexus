"""Verification script to ensure environment is configured correctly."""

from app.core.config import settings

def main():
    """Verify that the environment is properly configured."""
    try:
        # Attempt to access the API key (this will raise if missing)
        api_key = settings.OPENAI_API_KEY.get_secret_value()
        
        # Check that the key is not empty
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY is not set or is using placeholder value")
        
        print("Environment Configured Successfully")
        return 0
    except Exception as e:
        print(f"Environment Configuration Error: {e}")
        print("\nPlease ensure:")
        print("1. A .env file exists in the project root")
        print("2. The .env file contains: OPENAI_API_KEY=your_actual_key")
        print("3. The API key is valid and not a placeholder")
        return 1

if __name__ == "__main__":
    exit(main())

