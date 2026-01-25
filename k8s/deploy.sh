#!/bin/bash
# Kubernetes 快速部署脚本

set -e

echo "=========================================="
echo "Qwen3 API 服务 - Kubernetes 部署"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}错误: kubectl 未安装${NC}"
    exit 1
fi

# 检查集群连接
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}错误: 无法连接到 Kubernetes 集群${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Kubernetes 集群连接正常${NC}"
echo ""

# 检查 GPU 节点
echo "检查 GPU 节点..."
GPU_NODES=$(kubectl get nodes -l accelerator=nvidia-tesla-v100 --no-headers 2>/dev/null | wc -l)
if [ "$GPU_NODES" -eq 0 ]; then
    echo -e "${YELLOW}警告: 未找到 GPU 节点，请检查节点标签${NC}"
    echo "可用节点:"
    kubectl get nodes
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ 找到 $GPU_NODES 个 GPU 节点${NC}"
fi
echo ""

# 检查存储类
echo "检查存储类..."
STORAGE_CLASSES=$(kubectl get storageclass --no-headers 2>/dev/null | wc -l)
if [ "$STORAGE_CLASSES" -eq 0 ]; then
    echo -e "${YELLOW}警告: 未找到存储类，PVC 可能无法创建${NC}"
else
    echo -e "${GREEN}✓ 找到 $STORAGE_CLASSES 个存储类${NC}"
    kubectl get storageclass
fi
echo ""

# 询问部署选项
echo "部署选项:"
echo "1. 基础部署 (Deployment + Service)"
echo "2. 完整部署 (包含 HPA, Ingress)"
echo "3. 自定义部署"
read -p "请选择 (1-3): " choice

case $choice in
    1)
        FILES="namespace.yaml pvc.yaml configmap.yaml deployment.yaml service.yaml"
        ;;
    2)
        FILES="namespace.yaml pvc.yaml configmap.yaml deployment.yaml service.yaml hpa.yaml ingress.yaml"
        ;;
    3)
        read -p "请输入要部署的文件（空格分隔）: " FILES
        ;;
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac

echo ""
echo "开始部署..."
echo ""

# 部署资源
for file in $FILES; do
    if [ -f "$file" ]; then
        echo "部署 $file..."
        kubectl apply -f "$file"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ $file 部署成功${NC}"
        else
            echo -e "${RED}✗ $file 部署失败${NC}"
        fi
    else
        echo -e "${YELLOW}警告: $file 不存在，跳过${NC}"
    fi
done

echo ""
echo "等待 Pod 启动..."
kubectl wait --for=condition=ready pod -l app=qwen-api --timeout=600s || {
    echo -e "${YELLOW}Pod 启动超时，请检查日志:${NC}"
    echo "kubectl logs -l app=qwen-api"
    exit 1
}

echo ""
echo -e "${GREEN}=========================================="
echo "部署完成！"
echo "==========================================${NC}"
echo ""
echo "查看 Pod 状态:"
kubectl get pods -l app=qwen-api
echo ""
echo "查看服务:"
kubectl get svc qwen-api-service
echo ""
echo "查看日志:"
echo "kubectl logs -f deployment/qwen-api"
echo ""
echo "端口转发测试:"
echo "kubectl port-forward svc/qwen-api-service 8000:8000"
echo ""
