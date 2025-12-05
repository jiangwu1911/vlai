from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import sherpa_onnx
import numpy as np
import io
import wave
import tempfile
import os
import uuid
import logging
from typing import Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局识别器实例
recognizer = None

def init_recognizer():
    """初始化语音识别器"""
    global recognizer
    
    try:
        model_dir = "./sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
        
        # 使用在线识别器，与 voice_recognizer.py 保持一致
        recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=f"{model_dir}/tokens.txt",
            encoder=f"{model_dir}/encoder-epoch-99-avg-1.onnx",
            decoder=f"{model_dir}/decoder-epoch-99-avg-1.onnx",
            joiner=f"{model_dir}/joiner-epoch-99-avg-1.onnx",
            num_threads=4,
            sample_rate=16000,
            feature_dim=80,
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=1.2,
            rule3_min_utterance_length=300,
        )
        logger.info("使用在线 transducer 模式初始化成功")
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    init_recognizer()
    yield
    # 关闭时清理
    global recognizer
    recognizer = None

app = FastAPI(title="Sherpa语音识别服务", version="1.0.0", lifespan=lifespan)

def read_wav_file(file_content: bytes) -> np.ndarray:
    """读取WAV文件内容为numpy数组"""
    try:
        with wave.open(io.BytesIO(file_content), 'rb') as wav_file:
            # 检查音频参数
            sample_width = wav_file.getsampwidth()
            n_channels = wav_file.getnchannels()
            framerate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            
            # 读取音频数据
            frames = wav_file.readframes(n_frames)
            
            # 转换为numpy数组
            if sample_width == 2:
                audio_data = np.frombuffer(frames, dtype=np.int16)
            elif sample_width == 4:
                audio_data = np.frombuffer(frames, dtype=np.int32)
            else:
                audio_data = np.frombuffer(frames, dtype=np.int8)
            
            # 转换为float32并归一化到[-1, 1]
            audio_data = audio_data.astype(np.float32)
            if sample_width == 2:
                audio_data = audio_data / 32768.0
            elif sample_width == 4:
                audio_data = audio_data / 2147483648.0
            else:
                audio_data = audio_data / 128.0
            
            # 如果是多声道，取第一个声道
            if n_channels > 1:
                audio_data = audio_data[::n_channels]
            
            # 重采样到16kHz（如果需要）
            if framerate != 16000:
                from scipy import signal
                audio_data = signal.resample(audio_data, int(len(audio_data) * 16000 / framerate))
                framerate = 16000
            
            logger.info(f"音频信息: 采样率={framerate}Hz, 声道数={n_channels}, 样本数={len(audio_data)}")
            return audio_data, framerate
            
    except Exception as e:
        logger.error(f"读取WAV文件失败: {e}")
        raise HTTPException(status_code=400, detail=f"无效的WAV文件: {e}")

def recognize_audio(audio_data: np.ndarray, sample_rate: int = 16000) -> str:
    """使用Sherpa进行语音识别 - 模拟实时处理"""
    global recognizer
    
    if recognizer is None:
        raise HTTPException(status_code=500, detail="语音识别器未初始化")
    
    try:
        # 创建音频流
        stream = recognizer.create_stream()
        
        # 模拟实时处理：将音频分成小块输入
        chunk_size = int(0.1 * sample_rate)  # 100ms 的块
        total_chunks = len(audio_data) // chunk_size
        
        all_results = []  # 存储所有完整的识别结果
        
        for i in range(total_chunks + 1):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(audio_data))
            
            if start_idx >= len(audio_data):
                break
                
            chunk = audio_data[start_idx:end_idx]
            
            # 输入音频数据
            stream.accept_waveform(sample_rate, chunk)
            
            # 解码
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)
            
            # 检查端点
            is_endpoint = recognizer.is_endpoint(stream)
            result = recognizer.get_result(stream)
            
            # 如果检测到端点，保存结果并重置流
            if is_endpoint and result.strip():
                all_results.append(result.strip())
                logger.info(f"检测到端点，识别结果: {result.strip()}")
                recognizer.reset(stream)
        
        # 处理音频结束时的最后结果
        result = recognizer.get_result(stream)
        if result.strip():
            all_results.append(result.strip())
            logger.info(f"最终识别结果: {result.strip()}")
        
        # 合并所有结果
        if all_results:
            final_result = "".join(all_results)
            logger.info(f"合并后的最终结果: {final_result}")
            return final_result
        else:
            return ""
        
    except Exception as e:
        logger.error(f"语音识别失败: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"语音识别失败: {e}")

@app.post("/recognize", summary="语音识别")
async def recognize_speech(file: UploadFile = File(...)):
    """
    上传WAV文件进行语音识别
    
    - **file**: WAV格式的音频文件
    """
    # 检查文件类型
    if not file.filename.lower().endswith('.wav'):
        raise HTTPException(status_code=400, detail="只支持WAV格式文件")
    
    request_id = str(uuid.uuid4())
    logger.info(f"开始处理请求 {request_id}, 文件: {file.filename}")
    
    try:
        # 读取上传的文件
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        # 读取音频数据
        audio_data, sample_rate = read_wav_file(file_content)
        
        # 进行语音识别
        recognized_text = recognize_audio(audio_data, sample_rate)
        
        # 返回结果
        return JSONResponse({
            "success": True,
            "request_id": request_id,
            "text": recognized_text,
            "filename": file.filename
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理请求 {request_id} 时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {e}")

@app.get("/health", summary="健康检查")
async def health_check():
    """服务健康状态检查"""
    return {
        "status": "healthy",
        "recognizer_initialized": recognizer is not None
    }

@app.post("/reload", summary="重新加载模型")
async def reload_models():
    """重新加载语音识别模型"""
    try:
        init_recognizer()
        return {"success": True, "message": "模型重新加载成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新加载失败: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8134)
