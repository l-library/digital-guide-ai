# 测试markitdown功能
import os
import sys
from markitdown import MarkItDown

# 自动定位项目路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(backend_dir, "data")


test_file = os.path.join(data_dir, "灵山胜境：历史、文化、景点特色与个性化游览指南.docx")

def main():
    print(f"准备解析文件: {test_file}")
    if not os.path.exists(test_file):
        print("文件不存在")
        return

    print("正在准备转换...")
    
    # 初始化解析器
    md = MarkItDown()
    
    # 转换
    result = md.convert(test_file)
    
    print("\n" + "="*50)
    print("解析成功。以下是 Markdown 文本前 500 个字符：\n")
    print(result.text_content[:500])
    print("...")
    print("="*50)
    
    # 顺便统计一下字数，为后续的“文本切片”做个预估
    print(f"总字数: {len(result.text_content)} 字")

if __name__ == "__main__":
    main()