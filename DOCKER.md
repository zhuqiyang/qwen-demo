# Docker 部署指南

## 前置要求

1. **Docker** 已安装（版本 20.10+）
2. **NVIDIA Docker** 支持（用于 GPU 加速）
   - 安装指南: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
3. **模型文件** 已下载到 `./Qwen3-4B-Instruct-2507` 目录

## 快速开始

### 方式一：使用 Docker Compose（推荐）

```bash
# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式二：使用 Docker 命令

#### 1. 构建镜像

```bash
docker build -t qwen-api:latest .
```

#### 2. 运行容器

```bash
docker run -d \
  --name qwen-api \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/Qwen3-4B-Instruct-2507:/app/Qwen3-4B-Instruct-2507:ro \
  qwen-api:latest
```

#### 3. 查看日志

```bash
docker logs -f qwen-api
```

#### 4. 停止容器

```bash
docker stop qwen-api
docker rm qwen-api
```

## 验证服务

### 健康检查

```bash
curl http://localhost:8000/health
```

### 测试 API

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"你好"}]}'
```

## 配置说明

### 端口配置

默认端口是 `8000`，如需修改：

**docker-compose.yml:**
```yaml
ports:
  - "8080:8000"  # 宿主机:容器
```

**Docker 命令:**
```bash
-p 8080:8000
```

### GPU 配置

#### 指定 GPU

**docker-compose.yml:**
```yaml
environment:
  - CUDA_VISIBLE_DEVICES=0  # 使用第一块 GPU
```

**Docker 命令:**
```bash
-e CUDA_VISIBLE_DEVICES=0
```

#### 多 GPU 支持

修改 `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all  # 使用所有 GPU
          capabilities: [gpu]
```

### 模型路径

模型文件通过卷挂载，确保路径正确：

```yaml
volumes:
  - ./Qwen3-4B-Instruct-2507:/app/Qwen3-4B-Instruct-2507:ro
```

`:ro` 表示只读挂载，保护模型文件。

## 性能优化

### 1. 使用更小的基础镜像

如果需要更小的镜像，可以使用 `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel` 并手动优化。

### 2. 多阶段构建（可选）

对于生产环境，可以使用多阶段构建减小镜像大小。

### 3. 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 16G
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## 故障排查

### 1. GPU 不可用

检查 NVIDIA Docker 是否正确安装：

```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

### 2. 模型加载失败

检查模型路径是否正确挂载：

```bash
docker exec qwen-api ls -la /app/Qwen3-4B-Instruct-2507
```

### 3. 端口被占用

修改端口映射或停止占用端口的服务。

### 4. 查看详细日志

```bash
docker-compose logs -f qwen-api
# 或
docker logs -f qwen-api
```

## 生产环境建议

1. **使用 HTTPS**: 配置反向代理（如 Nginx）并启用 SSL
2. **资源监控**: 使用 Prometheus + Grafana 监控服务
3. **日志管理**: 配置日志收集（如 ELK Stack）
4. **自动重启**: 已在 docker-compose.yml 中配置 `restart: unless-stopped`
5. **健康检查**: 已配置健康检查，可配合监控系统使用

## 更新服务

```bash
# 停止旧容器
docker-compose down

# 重新构建（如果代码有更新）
docker-compose build

# 启动新容器
docker-compose up -d
```

## 清理

```bash
# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi qwen-api:latest

# 清理未使用的资源
docker system prune -a
```
