'''
这是一个中文文本嵌入模型，能把一段文字转换为一个512维的数字向量
'''
import os

# 设置环境变量
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 再导入相关的下载库
from huggingface_hub import snapshot_download

model_id = "BAAI/bge-small-zh-v1.5"

# 获取项目根目录并拼接路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
local_model_path = os.path.join(project_root, "models", "bge-small-zh-v1.5")

print(f"正在从镜像站下载模型 {model_id} 到本地目录: {local_model_path}")

# 执行下载
snapshot_download(
    repo_id=model_id,
    local_dir=local_model_path,
    max_workers=4
)

print("\n模型下载完成！")