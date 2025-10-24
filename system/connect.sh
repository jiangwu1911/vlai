nohup autossh -i id_rsa.jwu -M 0 -N -L 7862:127.0.0.1:8000 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 wj@dolphin-sound.weidows.tech &
