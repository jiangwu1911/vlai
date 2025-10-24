# delphin_ai

**这些程序用来演示怎样连接海豚大模型**

```
   app_web.py   连接大模型的web程序

   app_qt.py    用pyqt写的应用程序

   runweb.sh    执行 app_web.py

   runqt.sh    执行 app_qt.py
```



**配置python环境**
   1. 安装需要的包 libxcb-cursor0, libportaudio2, espeak

   2. 用命令 `python3 -m venv env01` 来创建一个python虚拟环境
      如果报错需要先执行 `apt install python3-venv` 安装

   3. 执行命令: `. env01/bin/activate` 激活虚拟环境

   4. 执行命令: `pip install -r requirements.txt` 来安装需要的python库


**连接北航服务器**

   服务器没有对外开放端口，需要用ssh打tunnel过去, 

      `ssh -i id_rsa.jwu -L 7862:127.0.0.1:7860 wj@dolphin-sound.weidows.tech`

   这个命令，把大模型服务器上的7860端口映射到本地的7862端口

   key文件找jason.wu要 
   
**调试, 查看与大模型之间的通讯包**

   安装mitmproxy, 注意mitmproxy和streamlit冲突，要安装在另一个环境
      `pip install mitmproxy`

   运行mitmweb, 打开一个浏览器窗口
      `mitmweb &`

   在程序中添加
```
os.environ["HTTP_PROXY"] = "http://127.0.0.1:8080"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:8080"
```
