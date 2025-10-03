#!/bin/bash

# Create a virtual environment named 'venv' if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate the virtual environment
source venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt

echo "Requirements installed."
