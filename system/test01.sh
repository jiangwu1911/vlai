curl http://127.0.0.1:7862/v1/chat/completions     -H "Content-Type: application/json"     -d '{
    "model": "/mnt/cfs/jssdqt/wengtaohan/model/modelscope/WTH1109/DolphonUltrasound72BV1___3",
    "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": "https://modelscope.oss-cn-beijing.aliyuncs.com/resource/qwen.png"}},
        {"type": "text", "text":"�~Y�| �~[��~C~O�~O��~C��~X��~@�~H"}
    ]}
    ]
    }'
