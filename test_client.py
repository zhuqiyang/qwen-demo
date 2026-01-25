"""
交互式聊天客户端 - 持续对话窗口
支持多轮对话，维护对话历史
"""
import requests
import json
import time
import sys

API_URL = "http://localhost:8000"

class ChatClient:
    def __init__(self, api_url=API_URL):
        self.api_url = api_url
        self.conversation_history = []
        self.total_tokens = 0
        
    def check_health(self):
        """检查服务健康状态"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def wait_for_service(self, max_retries=30):
        """等待服务启动"""
        print("正在连接服务...")
        for i in range(max_retries):
            if self.check_health():
                print("✓ 服务已就绪！\n")
                return True
            if i < max_retries - 1:
                print(f"等待中... ({i+1}/{max_retries})", end='\r')
                time.sleep(2)
        print("\n✗ 服务未启动，请先运行: python app.py")
        return False
    
    def send_message(self, user_input: str, temperature=0.7, max_tokens=2048):
        """发送消息并获取回复"""
        # 添加用户消息到历史
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # 构建请求
        url = f"{self.api_url}/v1/chat/completions"
        data = {
            "messages": self.conversation_history,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            start_time = time.time()
            response = requests.post(url, json=data, timeout=300)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                assistant_reply = result['response']
                
                # 添加助手回复到历史
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_reply
                })
                
                # 更新 token 统计
                usage = result.get('usage', {})
                self.total_tokens += usage.get('total_tokens', 0)
                
                return {
                    "success": True,
                    "reply": assistant_reply,
                    "usage": usage,
                    "time": elapsed_time
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "请求超时，请稍后重试"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"请求失败: {str(e)}"
            }
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        self.total_tokens = 0
        print("✓ 对话历史已清空\n")
    
    def show_history(self):
        """显示对话历史"""
        if not self.conversation_history:
            print("对话历史为空\n")
            return
        
        print("\n" + "=" * 60)
        print("对话历史:")
        print("=" * 60)
        for i, msg in enumerate(self.conversation_history, 1):
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"]
            print(f"\n[{i}] {role}:")
            print(f"    {content}")
        print("=" * 60)
        print(f"总 Token 数: {self.total_tokens}\n")
    
    def run(self):
        """运行交互式对话"""
        print("=" * 60)
        print("Qwen3 交互式聊天客户端")
        print("=" * 60)
        print("提示:")
        print("  - 输入消息后按回车发送")
        print("  - 输入 'quit' 或 'exit' 退出")
        print("  - 输入 'clear' 清空对话历史")
        print("  - 输入 'history' 查看对话历史")
        print("  - 输入 'help' 查看帮助")
        print("=" * 60 + "\n")
        
        # 等待服务
        if not self.wait_for_service():
            return
        
        # 主循环
        while True:
            try:
                # 获取用户输入
                user_input = input("你: ").strip()
                
                # 处理特殊命令
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n再见！")
                    break
                
                if user_input.lower() == 'clear':
                    self.clear_history()
                    continue
                
                if user_input.lower() == 'history':
                    self.show_history()
                    continue
                
                if user_input.lower() == 'help':
                    print("\n可用命令:")
                    print("  quit/exit/q  - 退出程序")
                    print("  clear        - 清空对话历史")
                    print("  history      - 查看对话历史")
                    print("  help         - 显示帮助\n")
                    continue
                
                # 发送消息
                print("\n思考中...", end='', flush=True)
                result = self.send_message(user_input)
                
                if result["success"]:
                    # 清除"思考中"提示
                    print("\r" + " " * 20 + "\r", end='')
                    
                    # 显示回复
                    print("助手:", result["reply"])
                    
                    # 显示统计信息（可选）
                    usage = result.get("usage", {})
                    time_taken = result.get("time", 0)
                    print(f"\n[Token: {usage.get('total_tokens', 0)} | 时间: {time_taken:.2f}秒]")
                    print("-" * 60 + "\n")
                else:
                    print(f"\n✗ 错误: {result['error']}\n")
                    
            except KeyboardInterrupt:
                print("\n\n程序被中断，再见！")
                break
            except EOFError:
                print("\n\n再见！")
                break

if __name__ == "__main__":
    client = ChatClient()
    client.run()
