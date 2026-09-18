#!/bin/bash
set -e
sudo apt update
sudo apt install -y python3 python3-venv
sudo mkdir -p /home/minecraft/mcui
sudo cp app.py requirements.txt start.sh mcui.service /home/minecraft/mcui/
sudo chown -R minecraft:minecraft /home/minecraft/mcui
sudo -u minecraft python3 -m venv /home/minecraft/mcui/venv
sudo -u minecraft /home/minecraft/mcui/venv/bin/pip install -r /home/minecraft/mcui/requirements.txt
echo 'Set MCUI_PASSWORD and MCUI_SECRET in /home/minecraft/mcui/.env, then install the service.'
