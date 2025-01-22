#!/usr/bin/env python3
import pkg_resources
import re
from pathlib import Path

def get_installed_version(package_name):
    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        return None

def sync_requirements():
    req_file = Path(__file__).parent / 'requirements.txt'
    if not req_file.exists():
        print("requirements.txt not found!")
        return
    
    # Read current requirements
    with open(req_file) as f:
        requirements = f.read().splitlines()
    
    # Update versions
    new_requirements = []
    for req in requirements:
        if not req.strip():  # Skip empty lines
            continue
            
        # Extract package name
        package_name = re.split('[><=~]', req)[0].strip()
        
        # Get current version
        current_version = get_installed_version(package_name)
        if current_version:
            new_requirements.append(f"{package_name}>={current_version}")
        else:
            print(f"Warning: {package_name} is not installed")
            new_requirements.append(req)
    
    # Write back updated requirements
    with open(req_file, 'w') as f:
        f.write('\n'.join(new_requirements) + '\n')
    
    print("Requirements synced successfully!")

if __name__ == "__main__":
    sync_requirements() 