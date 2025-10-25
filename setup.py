#!/usr/bin/env python3
"""
Setup script for Automated Insulin Dose Recommendation System
"""

import os
import sys
import subprocess

def install_requirements():
    """Install required packages in virtual environment"""
    print("Installing required packages in virtual environment...")
    
    # Check if virtual environment exists
    venv_path = "venv"
    if not os.path.exists(venv_path):
        print("Creating virtual environment...")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", venv_path])
            print("✓ Virtual environment created")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to create virtual environment: {e}")
            return False
    
    # Install requirements in virtual environment
    pip_path = os.path.join(venv_path, "bin", "pip")
    if os.name == 'nt':  # Windows
        pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
    
    try:
        subprocess.check_call([pip_path, "install", "-r", "requirements.txt"])
        print("✓ Requirements installed successfully in virtual environment")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False

def setup_environment():
    """Set up environment variables"""
    print("\nSetting up environment variables...")
    
    env_vars = {
        "GOOGLE_CLIENT_ID": "your-google-client-id-here",
        "GOOGLE_CLIENT_SECRET": "your-google-client-secret-here", 
        "SECRET_KEY": "your-secret-key-here"
    }
    
    env_file = ".env"
    with open(env_file, "w") as f:
        f.write("# Environment variables for Insulin Recommendation System\n")
        f.write("# Replace the values below with your actual credentials\n\n")
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"✓ Environment file created: {env_file}")
    print("Please update the .env file with your actual credentials")
    return True

def create_directories():
    """Create necessary directories"""
    print("\nCreating necessary directories...")
    directories = ["logs", "data"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")
        else:
            print(f"✓ Directory already exists: {directory}")
    
    return True

def main():
    """Main setup function"""
    print("Automated Insulin Dose Recommendation System - Setup")
    print("=" * 60)
    
    success = True
    
    # Install requirements
    if not install_requirements():
        success = False
    
    # Setup environment
    if not setup_environment():
        success = False
    
    # Create directories
    if not create_directories():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Update .env file with your Google OAuth credentials")
        print("2. Activate virtual environment: source venv/bin/activate")
        print("3. Run: python app.py")
        print("4. Run tests: python test_insulin_app.py")
        print("\nNote: Always activate the virtual environment before running the application!")
    else:
        print("✗ Setup failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
