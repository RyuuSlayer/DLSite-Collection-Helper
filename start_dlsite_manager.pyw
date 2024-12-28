#!/usr/bin/env python3
import os
import sys

# Get the absolute path of the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Add the src directory to Python path
src_dir = os.path.join(script_dir, 'src')
sys.path.insert(0, src_dir)

# Import and run the main function
from gui import main

if __name__ == '__main__':
    main()
