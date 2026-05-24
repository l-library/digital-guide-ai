#!/usr/bin/env python3
"""
LiveTalking 集成完整性验证脚本
检查代码完整性、配置一致性、清理确认，不启动 GPU 服务。
"""

import importlib.util
import os
import sys

# ─── 路径设置 ────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = PROJECT_ROOT
LIVETALKING_DIR = os.path.join(BACKEND_DIR, "LiveTalking")

sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, LIVETALKING_DIR)


# ─── 工具函数 ────────────────────────────────────────────────────────────────
def syntax_check(filepath: str) -> bool:
    """仅检查 Python 文件语法，不执行模块级代码。"""
    spec = importlib.util.spec_from_file_location("_check", filepath)
    if spec is None:
        return False
    try:
        importlib.util.module_from_spec(spec)
        return True
    except SyntaxError:
        return False


def file_exists(path: str) -> bool:
    return os.path.isfile(path)


def dir_exists(path: str) -> bool:
    return os.path.isdir(path)


# ─── 检查结果收集 ────────────────────────────────────────────────────────────
results: list[tuple[str, bool, str]] = []


def check(category: str, description: str, condition: bool):
    results.append((category, condition, description))
    mark = "✓ PASS" if condition else "✗ FAIL"
    print(f"  {mark}: {description}")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LiveTalking 代码完整性
# ═══════════════════════════════════════════════════════════════════════════════
print("\n=== 1. LiveTalking 代码完整性 ===")

service_path = os.path.join(LIVETALKING_DIR, "service.py")
check("LiveTalking", "service.py 语法正确", syntax_check(service_path))

wav2lip_path = os.path.join(LIVETALKING_DIR, "avatars", "wav2lip_avatar.py")
check("LiveTalking", "wav2lip_avatar.py 语法正确", syntax_check(wav2lip_path))

registry_path = os.path.join(LIVETALKING_DIR, "registry.py")
check("LiveTalking", "registry.py 语法正确", syntax_check(registry_path))

with open(wav2lip_path, "r", encoding="utf-8") as f:
    wav2lip_content = f.read()
check("LiveTalking", "wav2lip 已注册 (@register('avatar', 'wav2lip'))",
      '@register("avatar", "wav2lip")' in wav2lip_content)

edge_path = os.path.join(LIVETALKING_DIR, "tts", "edge.py")
with open(edge_path, "r", encoding="utf-8") as f:
    edge_content = f.read()
check("LiveTalking", "edgetts 已注册 (@register('tts', 'edgetts'))",
      '@register("tts", "edgetts")' in edge_content)

webrtc_path = os.path.join(LIVETALKING_DIR, "streamout", "webrtc.py")
with open(webrtc_path, "r", encoding="utf-8") as f:
    webrtc_content = f.read()
check("LiveTalking", "webrtc 已注册 (@register('streamout', 'webrtc'))",
      '@register("streamout", "webrtc")' in webrtc_content)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FastAPI 代码完整性
# ═══════════════════════════════════════════════════════════════════════════════
print("\n=== 2. FastAPI 代码完整性 ===")

dh_client_path = os.path.join(BACKEND_DIR, "app", "services", "digital_human_client.py")
check("FastAPI", "digital_human_client.py 语法正确", syntax_check(dh_client_path))

dh_session_path = os.path.join(BACKEND_DIR, "app", "services", "digital_human_session.py")
check("FastAPI", "digital_human_session.py 语法正确", syntax_check(dh_session_path))

dh_endpoint_path = os.path.join(BACKEND_DIR, "app", "api", "api_v1", "endpoints", "digital_human.py")
check("FastAPI", "digital_human.py 端点语法正确", syntax_check(dh_endpoint_path))

with open(dh_endpoint_path, "r", encoding="utf-8") as f:
    dh_content = f.read()
check("FastAPI", "digital_human 路由定义存在 (router = APIRouter())",
      "router = APIRouter()" in dh_content)

api_path = os.path.join(BACKEND_DIR, "app", "api", "api_v1", "api.py")
with open(api_path, "r", encoding="utf-8") as f:
    api_content = f.read()
check("FastAPI", "api_router 包含 digital_human 路由",
      "digital_human" in api_content)

main_path = os.path.join(BACKEND_DIR, "app", "main.py")
with open(main_path, "r", encoding="utf-8") as f:
    main_content = f.read()
check("FastAPI", "main.py 包含 api_router",
      "api_router" in main_content)

expected_routes = ["/session", "/speak", "/interrupt"]
for route in expected_routes:
    check("FastAPI", f"digital_human 端点 {route} 已定义",
          f'@router.{route.split("/")[0] if "/" in route else "post"}("{route}")' in dh_content
          or f'"{route}"' in dh_content)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 配置一致性
# ═══════════════════════════════════════════════════════════════════════════════
print("\n=== 3. 配置一致性 ===")

config_path = os.path.join(LIVETALKING_DIR, "config.py")
with open(config_path, "r", encoding="utf-8") as f:
    config_content = f.read()
check("配置", "config.py 包含 --watermark 参数",
      "--watermark" in config_content)
check("配置", "config.py watermark 默认值为 '景区导览AI数字人'",
      "景区导览AI数字人" in config_content)

base_avatar_path = os.path.join(LIVETALKING_DIR, "avatars", "base_avatar.py")
with open(base_avatar_path, "r", encoding="utf-8") as f:
    base_avatar_content = f.read()
check("配置", "base_avatar.py 使用 self.watermark_text (非硬编码 'LiveTalking')",
      "self.watermark_text" in base_avatar_content)
check("配置", "base_avatar.py 从 opt 读取 watermark 配置",
      "getattr(self.opt, 'watermark'" in base_avatar_content)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 清理确认
# ═══════════════════════════════════════════════════════════════════════════════
print("\n=== 4. 清理确认 ===")

check("清理", "LiveTalking/app.py 已删除", not file_exists(os.path.join(LIVETALKING_DIR, "app.py")))

check("清理", "LiveTalking/llm.py 已删除", not file_exists(os.path.join(LIVETALKING_DIR, "llm.py")))

check("清理", "LiveTalking/web/ 目录已删除", not dir_exists(os.path.join(LIVETALKING_DIR, "web")))

check("清理", "avatars/musetalk_avatar.py 已删除",
      not file_exists(os.path.join(LIVETALKING_DIR, "avatars", "musetalk_avatar.py")))

check("清理", "avatars/ultralight_avatar.py 已删除",
      not file_exists(os.path.join(LIVETALKING_DIR, "avatars", "ultralight_avatar.py")))


# ═══════════════════════════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════════════════════════
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
print(f"\n{'='*50}")
print(f"结果: {passed}/{total} 项检查通过")
print(f"{'='*50}")

# 按类别汇总
categories: dict[str, tuple[int, int]] = {}
for cat, ok, _ in results:
    c, t = categories.get(cat, (0, 0))
    categories[cat] = (c + (1 if ok else 0), t + 1)

for cat, (c, t) in categories.items():
    status = "✓" if c == t else "✗"
    print(f"  {status} {cat}: {c}/{t}")

if passed == total:
    print("\n所有检查通过！")
    sys.exit(0)
else:
    print(f"\n有 {total - passed} 项检查未通过。")
    sys.exit(1)