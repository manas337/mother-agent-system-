#!/usr/bin/env python3
"""
Setup Script for Mother-Agent System
Handles installation, configuration, and verification
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Run setup"""
    print("\n" + "="*80)
    print("MOTHER-AGENT SYSTEM SETUP")
    print("="*80 + "\n")
    
    # Check Python version
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"   ❌ Python 3.9+ required, found {version.major}.{version.minor}")
        return 1
    print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("   ✅ Dependencies installed")
    except:
        print("   ❌ Failed to install dependencies")
        return 1
    
    # Setup environment
    print("\n⚙️  Setting up environment...")
    env_file = Path(".env")
    if not env_file.exists():
        with open(".env.example", 'r') as f:
            content = f.read()
        with open(".env", 'w') as f:
            f.write(content)
        print("   ✅ Created .env file")
        print("   ⚠️  Please edit .env and add your ANTHROPIC_API_KEY")
    else:
        print("   ℹ️  .env already exists")
    
    # Make CLI executable
    print("\n🔧 Setting up CLI...")
    os.chmod("cli.py", 0o755)
    print("   ✅ CLI is executable")
    
    print("\n" + "="*80)
    print("✅ SETUP COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Edit .env and add your ANTHROPIC_API_KEY")
    print("2. Run: python cli.py demo")
    print("3. Or: python cli.py create --inline 'your project spec'")
    print("\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
