"""Quick start script for the Multi-Agent Chatbot System."""

import os
import sys
import subprocess
from pathlib import Path


def check_requirements():
    """Check if requirements are installed."""
    try:
        import streamlit
        import langchain
        import langgraph
        print("✅ All requirements are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing requirements: {e}")
        print("Installing requirements...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Requirements installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install requirements")
            return False


def check_env_file():
    """Check if environment file exists."""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️ .env file not found")
        print("Creating .env from template...")
        
        template_file = Path("config.env.example")
        if template_file.exists():
            # Copy template to .env
            with open(template_file, 'r') as src, open(env_file, 'w') as dst:
                dst.write(src.read())
            print("✅ .env file created from template")
            print("🔧 Please edit .env file and add your API keys")
            return False
        else:
            print("❌ Template file not found")
            return False
    else:
        print("✅ .env file found")
        return True


def main():
    """Main function to start the application."""
    print("🚀 Multi-Agent Chatbot System - Quick Start")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        return
    
    # Check environment file
    env_ready = check_env_file()
    
    if not env_ready:
        print("\n⚠️ Please configure your .env file with API keys before running the app")
        print("Required: OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return
    
    print("\n🎯 Starting Streamlit application...")
    print("🌐 The app will open in your browser at: http://localhost:8501")
    print("🛑 Press Ctrl+C to stop the application")
    print("-" * 50)
    
    try:
        # Run Streamlit app
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running application: {e}")


if __name__ == "__main__":
    main() 