# Qwen3 大模型 API 服务

基于 FastAPI 的 Qwen3-4B-Instruct 模型推理服务。

## 系统信息

- **显卡**: NVIDIA GeForce RTX 4080
- **PyTorch**: 2.5.1
- **CUDA**: 12.4
- **模型**: Qwen3-4B-Instruct-2507

## 部署方式

### ☸️ Kubernetes 部署（生产环境推荐）

**快速开始：**
```bash
# 部署到 Kubernetes
kubectl apply -f k8s/

# 或使用 kustomize
kubectl apply -k k8s/
```

详细说明请查看 [k8s/README.md](k8s/README.md)

### 🐳 Docker 部署

**快速开始：**
```bash
# 使用 docker-compose
docker-compose up -d
```

详细说明请查看 [DOCKER.md](DOCKER.md)

### 💻 本地部署

## 本地部署

### 安装依赖

```bash
# 激活 conda 环境
conda activate pytorch-env

# 安装依赖
pip install -r requirements.txt
```

## 启动服务

```bash
# 方式1: 直接运行
python app.py

# 方式2: 使用 uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000
```

服务启动后，访问：
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## API 使用示例

### 1. 健康检查

```bash
curl http://localhost:8000/health
```

### 2. 聊天接口（兼容 OpenAI 格式）

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "你好，介绍一下你自己"}
    ],
    "temperature": 0.7,
    "max_tokens": 1024
  }'
```

### 3. Python 客户端示例

```python
import requests

url = "http://localhost:8000/v1/chat/completions"
data = {
    "messages": [
        {"role": "user", "content": "用 Python 写一个快速排序算法"}
    ],
    "temperature": 0.7,
    "max_tokens": 2048
}

response = requests.post(url, json=data)
result = response.json()
print(result["response"])
```

### 4. 使用 OpenAI SDK（兼容模式）

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="qwen3",
    messages=[
        {"role": "user", "content": "解释一下量子计算的基本原理"}
    ],
    temperature=0.7,
    max_tokens=1024
)

print(response.choices[0].message.content)
```

## API 参数说明

- `messages`: 对话消息列表，格式为 `[{"role": "user", "content": "..."}]`
- `temperature`: 采样温度 (0.0-2.0)，默认 0.7，值越大输出越随机
- `top_p`: 核采样参数 (0.0-1.0)，默认 0.8
- `max_tokens`: 最大生成 token 数，默认 2048
- `stream`: 是否流式输出（当前版本暂不支持）

## 性能优化建议

1. **显存优化**: 模型已使用 `bfloat16` 精度，可进一步使用量化
2. **批处理**: 当前版本支持单次请求，可扩展支持批处理
3. **流式输出**: 可添加流式输出支持以提升用户体验

## 注意事项

- 首次启动需要加载模型，可能需要几分钟时间
- 确保有足够的 GPU 显存（建议至少 8GB）
- 模型文件位于 `./Qwen3-4B-Instruct-2507` 目录
