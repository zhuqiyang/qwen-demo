# Kubernetes 部署指南

## 前置要求

1. **Kubernetes 集群** (版本 1.24+)
2. **NVIDIA GPU Operator** 或 **NVIDIA Device Plugin** 已安装
3. **存储类 (StorageClass)** 已配置
4. **Ingress Controller** (可选，用于外部访问)
5. **模型文件** 已准备好并可通过 PVC 访问

## 快速部署

### 1. 准备模型文件

模型文件需要存储在持久化存储中，有以下几种方式：

#### 方式 A: 使用 PVC (推荐)

```bash
# 创建 PVC
kubectl apply -f pvc.yaml

# 将模型文件复制到 PVC
# 方法1: 使用临时 Pod
kubectl run -it --rm model-copy --image=busybox --restart=Never -- \
  sh -c "wget -O- <模型下载链接> | tar -xz -C /mnt && ls -la /mnt"

# 方法2: 如果使用 NFS，直接挂载到节点复制
```

#### 方式 B: 使用 ConfigMap (仅适用于小模型，不推荐)

```bash
# 不推荐，因为模型文件太大
```

#### 方式 C: 使用 Init Container 下载

修改 deployment.yaml，添加 initContainers 从对象存储下载模型。

### 2. 构建并推送镜像

```bash
# 构建镜像
docker build -t qwen-api:latest .

# 标记镜像（替换为你的镜像仓库）
docker tag qwen-api:latest registry.example.com/qwen-api:latest

# 推送镜像
docker push registry.example.com/qwen-api:latest

# 更新 deployment.yaml 中的镜像地址
```

### 3. 部署服务

```bash
# 方式1: 使用 kubectl 逐个部署
kubectl apply -f namespace.yaml
kubectl apply -f pvc.yaml
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f hpa.yaml
kubectl apply -f ingress.yaml

# 方式2: 使用 kustomize
kubectl apply -k .

# 方式3: 使用 kubectl 一次性部署所有文件
kubectl apply -f .
```

### 4. 检查部署状态

```bash
# 查看 Pod 状态
kubectl get pods -l app=qwen-api

# 查看 Pod 日志
kubectl logs -f deployment/qwen-api

# 查看服务状态
kubectl get svc qwen-api-service

# 查看 HPA 状态
kubectl get hpa qwen-api-hpa
```

## 配置说明

### GPU 节点选择

根据你的集群 GPU 节点配置，修改 `deployment.yaml` 中的节点选择器：

```yaml
nodeSelector:
  # 选项1: 使用标签选择器
  accelerator: nvidia-tesla-v100
  
  # 选项2: 使用 NVIDIA GPU 标签
  nvidia.com/gpu.product: "RTX-4080"
  
  # 选项3: 使用节点名称
  kubernetes.io/hostname: "gpu-node-1"
```

### 资源限制

根据实际需求调整 `deployment.yaml` 中的资源限制：

```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "2"
    nvidia.com/gpu: 1
  limits:
    memory: "16Gi"
    cpu: "4"
    nvidia.com/gpu: 1
```

### 存储配置

根据你的存储后端修改 `pvc.yaml`：

- **NFS**: 使用 NFS StorageClass
- **Ceph**: 使用 RBD StorageClass
- **本地存储**: 使用 local-path-provisioner
- **云存储**: 使用云提供商 StorageClass (如 AWS EBS, GCE PD)

### 服务暴露

#### 方式1: ClusterIP (集群内部访问)

```bash
kubectl port-forward svc/qwen-api-service 8000:8000
# 然后访问 http://localhost:8000
```

#### 方式2: NodePort (节点端口访问)

```bash
# 使用 service.yaml 中的 qwen-api-nodeport
# 访问 http://<节点IP>:30080
```

#### 方式3: LoadBalancer (云环境)

修改 `service.yaml`，将 type 改为 LoadBalancer。

#### 方式4: Ingress (推荐生产环境)

1. 确保已安装 Ingress Controller
2. 修改 `ingress.yaml` 中的域名
3. 配置 DNS 解析

## 扩缩容

### 手动扩缩容

```bash
# 扩容到 3 个副本
kubectl scale deployment qwen-api --replicas=3

# 查看副本状态
kubectl get deployment qwen-api
```

### 自动扩缩容 (HPA)

HPA 已配置，会根据 CPU 和内存使用率自动扩缩容：

```bash
# 查看 HPA 状态
kubectl get hpa qwen-api-hpa

# 查看 HPA 详细信息
kubectl describe hpa qwen-api-hpa
```

**注意**: 由于 GPU 资源有限，HPA 的 maxReplicas 应该根据可用 GPU 节点数量设置。

## 监控和日志

### 查看日志

```bash
# 查看所有 Pod 日志
kubectl logs -l app=qwen-api --tail=100

# 查看特定 Pod 日志
kubectl logs <pod-name> -f

# 查看多个 Pod 日志
kubectl logs -l app=qwen-api --all-containers=true --prefix=true
```

### 监控指标

如果已安装 Prometheus，可以查看以下指标：

- Pod CPU/内存使用率
- GPU 使用率
- 请求延迟和吞吐量
- 错误率

## 故障排查

### Pod 无法启动

```bash
# 查看 Pod 状态
kubectl describe pod <pod-name>

# 查看事件
kubectl get events --sort-by=.metadata.creationTimestamp

# 常见问题:
# 1. GPU 不可用: 检查 NVIDIA Device Plugin 是否运行
# 2. 镜像拉取失败: 检查镜像地址和权限
# 3. 存储挂载失败: 检查 PVC 状态
```

### GPU 不可用

```bash
# 检查节点 GPU 资源
kubectl describe node <node-name> | grep nvidia.com/gpu

# 检查 Device Plugin
kubectl get daemonset -n kube-system | grep nvidia

# 检查节点标签
kubectl get nodes --show-labels | grep gpu
```

### 存储问题

```bash
# 检查 PVC 状态
kubectl get pvc qwen-model-pvc

# 查看 PVC 详情
kubectl describe pvc qwen-model-pvc

# 检查 PV 状态
kubectl get pv
```

### 服务无法访问

```bash
# 检查 Service
kubectl get svc qwen-api-service

# 检查 Endpoints
kubectl get endpoints qwen-api-service

# 测试服务连通性
kubectl run -it --rm test --image=curlimages/curl --restart=Never -- \
  curl http://qwen-api-service:8000/health
```

## 更新部署

### 更新镜像

```bash
# 方法1: 使用 kubectl set
kubectl set image deployment/qwen-api qwen-api=registry.example.com/qwen-api:v1.1.0

# 方法2: 编辑 deployment
kubectl edit deployment qwen-api

# 方法3: 使用 kustomize
# 修改 kustomization.yaml 中的镜像标签，然后
kubectl apply -k .
```

### 滚动更新

Deployment 默认使用滚动更新策略：

```bash
# 查看更新状态
kubectl rollout status deployment/qwen-api

# 回滚到上一版本
kubectl rollout undo deployment/qwen-api

# 查看更新历史
kubectl rollout history deployment/qwen-api
```

## 生产环境建议

1. **资源限制**: 根据实际负载调整资源请求和限制
2. **多副本**: 配置多个副本以提高可用性（需要多个 GPU 节点）
3. **持久化存储**: 使用可靠的存储后端（如云存储）
4. **监控告警**: 配置 Prometheus + Grafana 监控
5. **日志收集**: 使用 ELK 或 Loki 收集日志
6. **安全策略**: 配置 NetworkPolicy 和 PodSecurityPolicy
7. **备份**: 定期备份模型文件和配置
8. **TLS**: 配置 Ingress TLS 证书

## 清理资源

```bash
# 删除所有资源
kubectl delete -f .

# 或使用 kustomize
kubectl delete -k .

# 删除命名空间（如果使用独立命名空间）
kubectl delete namespace qwen
```

## 示例：完整部署流程

```bash
# 1. 创建命名空间
kubectl apply -f namespace.yaml

# 2. 创建 PVC
kubectl apply -f pvc.yaml

# 3. 等待 PVC 就绪
kubectl wait --for=condition=Bound pvc/qwen-model-pvc --timeout=60s

# 4. 复制模型文件到 PVC (使用临时 Pod)
# ... 根据你的存储类型选择方法

# 5. 创建 ConfigMap
kubectl apply -f configmap.yaml

# 6. 部署应用
kubectl apply -f deployment.yaml

# 7. 等待 Pod 就绪
kubectl wait --for=condition=ready pod -l app=qwen-api --timeout=600s

# 8. 创建服务
kubectl apply -f service.yaml

# 9. 创建 HPA
kubectl apply -f hpa.yaml

# 10. 创建 Ingress (可选)
kubectl apply -f ingress.yaml

# 11. 测试服务
kubectl port-forward svc/qwen-api-service 8000:8000
curl http://localhost:8000/health
```
