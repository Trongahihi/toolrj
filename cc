#!/bin/bash
if [ -e "/data/data/com.termux/files/home/storage" ]; then
	rm -rf /data/data/com.termux/files/home/storage
fi
termux-setup-storage
yes | pkg update
. <(curl https://raw.githubusercontent.com/u400822/setup-termux/refs/heads/main/termux-change-repo.sh)
yes | pkg upgrade
yes | pkg i python
yes | pkg i python-pip
pip install requests psutil prettytable pycryptodome
curl -o /sdcard/Download/main.py https://raw.githubusercontent.com/Trongahihi/toolrj/refs/heads/main/main.py
