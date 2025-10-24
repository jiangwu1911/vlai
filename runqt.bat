@echo off
REM 开启批处理命令回显，便于调试
@echo on

set DELPHIN_API_KEY="eyJhbGciOiJSUzI1NiIsImtpZCI6ImNzbSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NTA0MTI2MDksImlzcyI6ImFpaGMiLCJzdWIiOiJzLXI0YmQ0ZDc5OTFkNy1leHRlcm5hbCJ9.gX-l-qCWSHQbiY5OT0JaHztcXedDCSc-uNLKBgF83l5s9HK3ma2H7y60aBvk-UJDjCLDyG-tVRSNvvofwPIce1CA0JY54fPuhrmUKcat8ZGnvJ1Ggx7xd5T2OnC74Al3PE4jLVwr5bDxgshRB_fprPld0BFN0sHo77_YEmszaRNtoGdjKYk53WuFCoi9NUdHpmQwfZy5tILSkxQs_06mGIEYSsNfPkCJSN2WUQCVzopKI1nP8Wl69kkhIFcaIwPRaNNdD5WPGJQyEg4U1L2ArXfeKM4Sa7rhjs5LwQSLs6a_K3hpueRERylGCn-6nLzPNBMS_BJ_1vzEpMi6lyoneg"

REM 检查虚拟环境激活脚本是否存在
if exist "..\env01\Scripts\activate.bat" (
    echo 找到虚拟环境激活脚本
    REM 使用CALL命令执行激活脚本，否则批处理会在此处终止
    call ..\env01\Scripts\activate.bat
) else (
    echo 错误：未找到虚拟环境激活脚本，请检查路径
    goto :END
)

REM 检查Python文件是否存在
if exist "app_qt.py" (
    echo 找到Python文件
    REM 执行Python脚本
    python app_qt.py -n
) else (
    echo 错误：未找到app_qt.py文件，请检查路径
)

:END
REM 暂停批处理，以便查看执行结果和错误信息
pause
