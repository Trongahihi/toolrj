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

# Cài các thư viện Python cần thiết (thêm rich và pytz)
pip install requests psutil prettytable pycryptodome rich pytz

# Tải file main.py về thư mục Download trên máy
curl -o /sdcard/Download/main.py https://raw.githubusercontent.com/Trongahihi/toolrj/refs/heads/main/main.py
