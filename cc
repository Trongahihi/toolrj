#!/bin/bash
if [ -e "/data/data/com.termux/files/home/storage" ]; then
	rm -rf /data/data/com.termux/files/home/storage
fi

termux-setup-storage
yes | pkg update
. <(curl -Ls https://raw.githubusercontent.com/u400822/setup-termux/refs/heads/main/termux-change-repo.sh)
yes | pkg upgrade
yes | pkg i python
yes | pkg i python-pip

# Cài đặt các công cụ biên dịch bắt buộc trên Termux (Sửa lỗi cài psutil bị fail)
yes | pkg install clang python-dev make ndk-sysroot

# Cài đặt các thư viện Python cần thiết
pip install requests psutil prettytable pycryptodome rich pytz

# Tải file main.py về thư mục Download trên máy
curl -o /sdcard/Download/main.py https://raw.githubusercontent.com/Trongahihi/toolrj/refs/heads/main/main.py
