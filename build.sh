#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala o pip mais recente
pip install --upgrade pip

# Instala as dependências do requirements.txt
pip install -r requirements.txt
