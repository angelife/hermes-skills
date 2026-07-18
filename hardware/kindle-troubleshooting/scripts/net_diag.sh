#!/bin/sh
# Kindle Network Diagnostic Script
# Usage: Place in /Volumes/Kindle/documents/ on USB mount
#        Eject, tap in Kindle Library to run
#        Plug back, read /Volumes/Kindle/documents/net_report.txt
LOG=/mnt/us/documents/net_report.txt

echo "=== Kindle Network Diagnostic ===" > $LOG
date >> $LOG
echo "" >> $LOG

echo "--- WiFi Status ---" >> $LOG
lipc-get-prop -s com.lab126.wifid cmState 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- IP Address ---" >> $LOG
ifconfig wlan0 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- Routing Table ---" >> $LOG
route -n 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- DNS ---" >> $LOG
cat /etc/resolv.conf 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- Ping 8.8.8.8 ---" >> $LOG
ping -c 2 -W 3 8.8.8.8 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- DNS Resolution ---" >> $LOG
nslookup example.com 2>/dev/null | grep -E "Name|Address" >> $LOG
nslookup baidu.com 2>/dev/null | grep -E "Name|Address" >> $LOG
echo "" >> $LOG

echo "--- HTTP Test (port 80, no encryption) ---" >> $LOG
curl -s --max-time 10 http://example.com 2>/dev/null | head -3 >> $LOG
echo "" >> $LOG

echo "--- HTTPS Test (port 443, encrypted) ---" >> $LOG
curl -s --max-time 10 https://example.com 2>/dev/null | head -3 >> $LOG
echo "" >> $LOG

echo "--- Proxy Settings ---" >> $LOG
echo "http_proxy=$http_proxy" >> $LOG
echo "https_proxy=$https_proxy" >> $LOG
echo "" >> $LOG

echo "=== Done ===" >> $LOG
date >> $LOG
echo "Report saved. Plug Kindle back to PC to read."
