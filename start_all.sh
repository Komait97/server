#!/bin/bash

# الانتقال للمجلد
cd ~/server

# إيقاف أي عمليات قديمة
killall python3
killall cloudflared

# 1. تشغيل السيرفر
echo "Starting Telegram Server..."
screen -d -m -S server python3 server_bot.py

# 2. تشغيل التونل وحفظ المخرجات في ملف مؤقت
echo "Starting Tunnel..."
./cloudflared tunnel --url http://localhost:5001 > /tmp/tunnel_output.txt 2>&1 &

# 3. انتظر 8 ثواني ليتصل التونل ويستخرج الرابط
sleep 8

# 4. استخراج الرابط وحفظه في ذاكرة الهاتف الداخلية (SD Card)
grep -o 'https://[-a-zA-Z0-9]*\.trycloudflare\.com' /tmp/tunnel_output.txt > /sdcard/bot_url.txt

echo "-------------------------------------------------"
echo "تم التشغيل بنجاح!"
echo "الرابط تم حفظه في: /sdcard/bot_url.txt"
echo "-------------------------------------------------"