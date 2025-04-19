import os
import hashlib
from .config import BASE_DIR

def safe_write_file(path, content):
    """安全写入文件，仅在内容变化时更新，返回是否发生变更"""
    # 统一换行符为LF
    normalized_content = '\n'.join(content.splitlines()) + '\n'
    
    # 检测是否需要写入
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        if existing_content == normalized_content:
            return False
    
    # 写入文件
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(normalized_content)
    return True

def read_source_file():
    """读取源文件"""
    source_path = os.path.join(BASE_DIR, 'source.txt')
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"文件读取失败：{str(e)}")
        raise