"""
Qwen3 大模型 API 服务
基于 FastAPI 提供模型推理接口
"""
import os
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from transformers import AutoModelForCausalLM, AutoTokenizer
import uvicorn
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 FastAPI 应用
app = FastAPI(
    title="Qwen3 大模型 API 服务",
    description="基于 Qwen3-4B-Instruct 的推理服务",
    version="1.0.0"
)

# 全局变量存储模型和 tokenizer
model = None
tokenizer = None
device = None

# 请求模型
class ChatRequest(BaseModel):
    messages: List[dict]  # [{"role": "user", "content": "你好"}]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.8
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False

# 响应模型
class ChatResponse(BaseModel):
    response: str
    usage: dict

@app.on_event("startup")
async def load_model():
    """启动时加载模型"""
    global model, tokenizer, device
    
    try:
        # 检测设备
        if torch.cuda.is_available():
            device = "cuda"
            logger.info(f"使用 GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU 内存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        else:
            device = "cpu"
            logger.warning("CUDA 不可用，使用 CPU")
        
        # 模型路径（支持环境变量配置）
        model_path = os.getenv("MODEL_PATH", "./Qwen3-4B-Instruct-2507")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型路径不存在: {model_path}")
        
        logger.info(f"正在加载模型: {model_path}")
        logger.info(f"设备: {device}")
        
        # 加载 tokenizer
        logger.info("加载 tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        
        # 加载模型
        logger.info("加载模型（这可能需要几分钟）...")
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,  # 使用 bfloat16 以节省显存
            device_map="auto",  # 自动分配设备
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        # 设置为评估模式
        model.eval()
        
        logger.info("模型加载完成！")
        logger.info(f"模型参数量: {sum(p.numel() for p in model.parameters()) / 1e9:.2f}B")
        
        if device == "cuda":
            logger.info(f"当前 GPU 内存使用: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
            logger.info(f"GPU 内存缓存: {torch.cuda.memory_reserved(0) / 1024**3:.2f} GB")
        
    except Exception as e:
        logger.error(f"模型加载失败: {str(e)}")
        raise

@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "running",
        "model": "Qwen3-4B-Instruct-2507",
        "device": device,
        "cuda_available": torch.cuda.is_available()
    }

@app.get("/health")
async def health():
    """健康检查端点"""
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    return {"status": "healthy", "model_loaded": True}

@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    """聊天完成接口（兼容 OpenAI API 格式）"""
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    
    try:
        # 构建输入消息
        if not request.messages:
            raise HTTPException(status_code=400, detail="messages 不能为空")
        
        # 将消息列表转换为模型输入格式
        # Qwen3 使用 chat template
        text = tokenizer.apply_chat_template(
            request.messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize
        inputs = tokenizer(text, return_tensors="pt").to(device)
        
        # 生成参数
        generation_config = {
            "max_new_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "do_sample": request.temperature > 0,
        }
        
        # 推理
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                **generation_config,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # 解码输出（只取新生成的部分）
        input_length = inputs.input_ids.shape[1]
        generated_tokens = outputs[0][input_length:]
        response_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        # 计算 token 使用量
        input_tokens = inputs.input_ids.shape[1]
        output_tokens = len(generated_tokens)
        
        return ChatResponse(
            response=response_text,
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        )
    
    except Exception as e:
        logger.error(f"推理错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

@app.post("/chat")
async def chat(request: ChatRequest):
    """简化的聊天接口"""
    return await chat_completions(request)

if __name__ == "__main__":
    # 启动服务
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )