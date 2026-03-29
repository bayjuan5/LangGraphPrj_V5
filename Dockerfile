# 1. 锁定基础环境：使用 Linux 版 Python 3.11，避开 Windows 3.12 的接口问题
FROM python:3.11-slim

# 2. 设定容器内的工作空间
WORKDIR /app

# 3. 先安装依赖（利用镜像缓存机制，这一步最关键）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 拷贝 App 代码和前端资源
COPY . .

# 5. 告诉 Docker 这个 App 跑在 5000 端口
EXPOSE 5000

# 6. 启动命令
CMD ["python", "app.py"]