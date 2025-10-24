#!/bin/bash

# REST API测试脚本
# 用于测试PyQt RESTful服务器的各项功能

# 服务器地址和端口
SERVER="http://localhost:8133/v1"

# 颜色定义，用于美化输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # 无颜色

# 显示请求结果的函数
function show_result {
    local status=$1
    local response=$2
    
    echo -e "${YELLOW}状态码:${NC} $status"
    echo -e "${YELLOW}响应内容:${NC}"
    echo "$response" | jq . 2>/dev/null || echo "$response"
    echo
}

function show_window {
    echo -e "${GREEN}=== 测试1: 显示窗口 ===${NC}"
    response=$(curl -s -w "%{http_code}" "$SERVER/show" -o show_response.txt)
    show_result "$response" "$(cat show_response.txt)"
    rm show_response.txt
}

function hide_window {
    echo -e "${GREEN}=== 测试2: 隐藏窗口 ===${NC}"
    response=$(curl -s -w "%{http_code}" "$SERVER/hide" -o hide_response.txt)
    show_result "$response" "$(cat hide_response.txt)"
    rm hide_response.txt
}

function clear_history {
    echo -e "${GREEN}=== 测试3: 清除历史 ===${NC}"
    response=$(curl -s -w "%{http_code}" "$SERVER/clear" -o clear_response.txt)
    show_result "$response" "$(cat clear_response.txt)"
    rm clear_response.txt
}

function upload_image {
    echo -e "${GREEN}=== 测试4: 上传图片 ===${NC}"
    image_path="`pwd`/2025_05_13_155826_667.jpg"

    # 检查是否提供了图片路径参数
    if [ -z $image_path ]; then
        echo -e "${RED}错误: 请提供一个图片路径作为参数!${NC}"
        echo "用法: $0 /path/to/image.jpg"
        exit 1
    fi

    # 检查图片文件是否存在
    if [ ! -f "$image_path" ]; then
        echo -e "${RED}错误: 指定的图片文件不存在!${NC}"
        exit 1
    fi

    # 发送上传请求
    echo -e "${YELLOW}上传图片:${NC} $image_path"
    response=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "{\"image_path\": \"$image_path\"}" "$SERVER/upload" -o upload_response.txt)
    show_result "$response" "$(cat upload_response.txt)"
    rm upload_response.txt
}

title="Send request to AI assistant"
prompt="Pick a command:"
options=("Show window"
         "Hide window"
         "Clear history"
         "Upload image"
         )   

echo -e "$title\n"
PS3="$prompt "
select opt in "${options[@]}" "Quit"; do
    case "$REPLY" in
    1 ) show_window;;
    2 ) hide_window;;
    3 ) clear_history;;
    4 ) upload_image;;
    $(( ${#options[@]}+1 )) ) echo "Goodbye!"; break;;
    *) echo "Invalid option. Try another one.";continue;;
    esac
done

