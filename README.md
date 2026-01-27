## Qwen3 大模型 API 服务

基于 FastAPI + PyTorch 的 `Qwen3-4B-Instruct-2507` 本地推理服务，支持 GPU 加速、Docker 部署和 Kubernetes 部署。

---

## 系统与环境信息

- **操作系统**：建议 Linux / WSL2（示例基于 Ubuntu 24.04 + WSL2）
- **GPU**：NVIDIA GeForce RTX 4080（或其他支持 CUDA 的 GPU）
- **驱动**：NVIDIA Driver 591.59（CUDA 13.1）
- **CUDA 运行时**：通过 PyTorch 镜像自带（2.5.1 + CUDA 12.4）
- **Python**：3.11（Conda 虚拟环境中）
- **PyTorch**：2.5.1（CUDA 12.4）
- **模型**：`Qwen/Qwen3-4B-Instruct-2507`（4B Instruct）

> **说明**：README 以 WSL2 中的 Ubuntu 为示例环境，物理机为 Windows，浏览器或其他客户端可以通过 WSL IP 访问服务。

---

## 1. 准备基础环境

### 1.1 安装 Miniconda（在 WSL / Linux 中）

```bash
cd ~
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# 按提示完成安装后，重新打开终端或执行
source ~/.bashrc
```

### 1.2 创建并激活虚拟环境

```bash
# 创建环境
conda create -n pytorch-env python=3.11 -y

# 激活环境
conda activate pytorch-env
```

### 1.3 安装 Python 依赖

```bash
cd /mnt/e/code/qwen  # 根据实际路径调整

# 安装项目依赖
pip install -r requirements.txt

# 安装模型下载工具
pip install modelscope
```

---

## 2. 下载 Qwen3 模型

在已激活的 `pytorch-env` 环境中执行：

```bash
cd /mnt/e/code/qwen

modelscope download \
  --model Qwen/Qwen3-4B-Instruct-2507 \
  --local_dir ./Qwen3-4B-Instruct-2507
```

下载完成后，目录结构类似：

```text
Qwen3-4B-Instruct-2507/
  ├─ config.json
  ├─ generation_config.json
  ├─ model-00001-of-00003.safetensors
  ├─ model-00002-of-00003.safetensors
  ├─ model-00003-of-00003.safetensors
  ├─ model.safetensors.index.json
  ├─ tokenizer.json
  ├─ tokenizer_config.json
  ├─ merges.txt
  ├─ vocab.json
  └─ ...
```

---

## 3. 本地直接运行服务（不使用 Docker）

### 3.1 启动 API 服务

在 `pytorch-env` 环境中：

```bash
cd /mnt/e/code/qwen

# 启动 FastAPI 服务（使用内置 uvicorn）
python app.py
```

默认监听：
- **地址**：`http://0.0.0.0:8000`
- **API 文档**：`http://<WSL_IP>:8000/docs`
- **健康检查**：`http://<WSL_IP>:8000/health`

> WSL 中可通过 `ip a` 查看 `eth0` 的 IP，例如 `172.29.128.244`，Windows 浏览器可访问 `http://172.29.128.244:8000`。

### 3.2 使用命令行对话（持续聊天窗口）

在 Windows（或 WSL）中运行：

```bash
cd e:\code\qwen

# 确保 test_client.py 中的 API_URL 指向 WSL 的 IP，例如：
# API_URL = "http://172.29.128.244:8000"

python test_client.py
```

支持命令：
- 输入内容：发送一轮对话
- `history`：查看对话历史
- `clear`：清空历史
- `quit` / `exit` / `q`：退出

### 3.3 使用 curl 测试

```bash
curl -X POST "http://172.29.128.244:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "你好，介绍一下你自己"}
    ],
    "temperature": 0.7,
    "max_tokens": 1024
  }'
```

---

## 4. 构建 Docker 镜像

### 4.1 前置要求

- WSL2 中已安装 **Docker**（`docker.io`）
- 已配置 **NVIDIA 驱动**，`nvidia-smi` 在 WSL 中可用
- 已安装 **NVIDIA Container Toolkit**，支持 `--gpus all`
- 当前目录为 `/root/qwen` 或 `/home/<user>/qwen`，且包含：
  - `app.py`
  - `requirements.txt`
  - `Dockerfile`
  - `Qwen3-4B-Instruct-2507/`

### 4.2 构建镜像

```bash
cd ~/qwen   # 确保当前目录与 Dockerfile 同级

docker build -t qwen:0.1 .
```

> 构建镜像使用基础镜像：`pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime`，已自带 CUDA 与 PyTorch。

---

## 5. 使用 Docker 运行服务（GPU 加速）

### 5.1 启动容器

```bash
cd ~/qwen

docker run -d \
  --name qwen-api \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/Qwen3-4B-Instruct-2507:/app/Qwen3-4B-Instruct-2507:ro \
  qwen:0.1
```

说明：
- `--gpus all`：启用所有 GPU，需要 NVIDIA Container Toolkit
- `-p 8000:8000`：将容器端口 8000 映射到宿主机 8000
- `-v $(pwd)/Qwen3-4B-Instruct-2507:/app/Qwen3-4B-Instruct-2507:ro`：
  - 宿主机模型目录挂载到容器 `/app/Qwen3-4B-Instruct-2507`
  - `app.py` 默认使用相对路径 `./Qwen3-4B-Instruct-2507`，工作目录为 `/app`，因此能正确找到模型

> **注意**：不要挂载到 `/app/models/...`，否则会出现 `模型路径不存在: ./Qwen3-4B-Instruct-2507` 错误。

### 5.2 查看容器状态与日志

```bash
docker ps -a
docker logs -f qwen-api
```

如果启动正常，日志中会看到：
- 使用 GPU 信息
- 模型加载完成提示

### 5.3 宿主机访问 API

在 Windows 浏览器或命令行中：

- 健康检查：`http://127.0.0.1:8000/health`
- API 文档：`http://127.0.0.1:8000/docs`

curl 测试：

```bash
curl -X POST "http://127.0.0.1:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "用一句话介绍你自己"}
    ]
  }'
```

---

## 6. Kubernetes 部署（可选，生产环境）

项目提供了完整的 K8s 资源文件，位于 `k8s/` 目录，包括：

- `deployment.yaml`：部署（Deployment）
- `service.yaml`：Service（ClusterIP + NodePort 示例）
- `pvc.yaml`：模型存储 PVC / PV 示例
- `ingress.yaml`：Ingress 配置
- `hpa.yaml`：水平自动扩缩容（HPA）
- `configmap.yaml`：配置
- `namespace.yaml`、`kustomization.yaml` 等

**快速部署：**

```bash
cd /mnt/e/code/qwen/k8s

# 方式一：直接 apply
kubectl apply -f .

# 方式二：使用 kustomize
kubectl apply -k .
```

详细说明请查看：
- `k8s/README.md`

---

## 7. API 说明（与 OpenAI Chat API 类似）

### 7.1 请求格式

`POST /v1/chat/completions`

```json
{
  "messages": [
    {"role": "user", "content": "你好，介绍一下你自己"}
  ],
  "temperature": 0.7,
  "top_p": 0.8,
  "max_tokens": 1024,
  "stream": false
}
```

### 7.2 字段说明

- **messages**：对话消息数组
  - `role`：`"user"` / `"assistant"` / `"system"`
  - `content`：消息内容
- **temperature**：采样温度，0.0–2.0，越大越随机
- **top_p**：核采样参数，0.0–1.0
- **max_tokens**：最多生成多少个新 token
- **stream**：是否流式输出（当前未实现，保留字段）

### 7.3 响应示例

```json
{
  "response": "你好，我是 Qwen3-4B-Instruct 模型，可以帮助你完成各种自然语言任务……",
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 50,
    "total_tokens": 70
  }
}
```

---

## 8. 性能与注意事项

- **显存需求**：约 8–10 GB，建议 16 GB 显存的显卡（如 RTX 4080）
- **精度**：使用 `bfloat16`，在保证效果的同时节省显存
- **首次加载时间**：模型较大，首次启动需要数十秒到数分钟
- **并发**：单卡情况下建议适度控制并发请求数量

**常见问题：**

- **模型路径不存在**：
  - 确认本地 `Qwen3-4B-Instruct-2507` 目录存在
  - 容器中挂载路径必须为 `/app/Qwen3-4B-Instruct-2507`
- **CUDA 不可用**：
  - 确认宿主机 `nvidia-smi` 正常
  - 在 WSL 中 `nvidia-smi` 正常
  - Docker 中安装并配置好了 NVIDIA Container Toolkit

---

## 9. 项目结构概览

```text
qwen/
├─ app.py                     # FastAPI 服务主入口
├─ requirements.txt           # Python 依赖
├─ Dockerfile                 # Docker 构建文件
├─ README.md                  # 使用说明（本文件）
├─ test_client.py             # 交互式命令行聊天客户端
├─ Qwen3-4B-Instruct-2507/    # 本地模型目录（需手动下载）
└─ k8s/                       # Kubernetes 部署配置
   ├─ deployment.yaml
   ├─ service.yaml
   ├─ pvc.yaml
   ├─ ingress.yaml
   ├─ hpa.yaml
   └─ README.md
```

到这里，一个从 **环境准备 → 模型下载 → 本地运行 → Docker 部署 → K8s 部署 → API 调用** 的完整链路就打通了。