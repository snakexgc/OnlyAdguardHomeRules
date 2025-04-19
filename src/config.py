import os

def get_base_dir():
    """获取仓库根目录"""
    if 'GITHUB_WORKSPACE' in os.environ:
        return os.environ['GITHUB_WORKSPACE']
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

BASE_DIR = get_base_dir()