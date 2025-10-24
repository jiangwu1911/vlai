#!/bin/sh

# 安装需要的包
apt install python3-dev portaudio19-dev espeak-ng libxcb-cursor-dev

chmod 600 id_rsa.jwu

cp autossh.service /etc/systemd/system/
systemctl daemon-reload
systemctl start autossh
systemctl enable autossh
