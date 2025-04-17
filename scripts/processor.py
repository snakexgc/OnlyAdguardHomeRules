import requests
from datetime import datetime
import os
import sys

# 获取仓库根目录
def get_base_dir():
    """ 直接使用GitHub Actions的默认工作目录 """
    return os.getcwd()  # 关键修正：直接使用当前工作目录

BASE_DIR = get_base_dir()
print(f"[DEBUG] 仓库根目录：{BASE_DIR}")
print(f"[DEBUG] 目录内容：{os.listdir(BASE_DIR)}")

def process_urls(urls):
    results = {
        'normal': [],
        'strict': [],
        'stats': {
            'total_urls': len(urls),
            'total_lines': 0,
            'normal': {'valid': 0, 'duplicates': 0},
            'strict': {'valid': 0, 'duplicates': 0}
        }
    }

    for url in urls:
        try:
            print(f"\n▷ 处理URL: {url[:50]}...")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            normal_lines = []
            strict_lines = []
            
            for line in response.text.splitlines():
                stripped = line.strip()
                results['stats']['total_lines'] += 1
                
                # 空行和注释过滤
                if not stripped or stripped.startswith('!'):
                    continue
                
                # 普通模式收集
                normal_lines.append(line)
                
                # 严格模式过滤
                if stripped.startswith(('||', '@@')):
                    strict_lines.append(line)

            results['normal'].extend(normal_lines)
            results['strict'].extend(strict_lines)
            print(f"  发现有效规则：普通模式 {len(normal_lines)} 条 | 严格模式 {len(strict_lines)} 条")
            
        except Exception as e:
            print(f"  × 处理失败：{str(e)}")
            continue

    # 去重处理
    for mode in ['normal', 'strict']:
        seen = set()
        unique = []
        duplicates = 0
        for line in results[mode]:
            if line not in seen:
                seen.add(line)
                unique.append(line)
            else:
                duplicates += 1
        results[mode] = unique
        results['stats'][mode]['valid'] = len(unique)
        results['stats'][mode]['duplicates'] = duplicates
    
    return results

def update_readme(stats):
    template = f"""## 自动更新规则列表

最后更新时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

### 统计信息
| 类别        | 普通模式       | 严格模式       |
|-------------|---------------|---------------|
| 有效规则数  | {stats['normal']['valid']:>6}       | {stats['strict']['valid']:>6}       |
| 重复过滤数  | {stats['normal']['duplicates']:>6}       | {stats['strict']['duplicates']:>6}       |
| 数据源数量  | {stats['total_urls']:>6}         | {"-"*11}       |

### 下载链接
- [普通模式列表](dist/all.txt)
- [严格模式列表](dist/strict.txt)
"""
    readme_path = os.path.join(BASE_DIR, 'README.md')
    
    # 处理README内容
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ""
    
    start_marker = '<!-- AUTO_UPDATE_START -->'
    end_marker = '<!-- AUTO_UPDATE_END -->'
    
    if start_marker in content and end_marker in content:
        new_content = content.split(start_marker)[0] + \
            f"{start_marker}\n{template}\n{end_marker}" + \
            content.split(end_marker)[-1]
    else:
        new_content = f"{content}\n{start_marker}\n{template}\n{end_marker}"

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == '__main__':
    # 获取source.txt路径
    source_path = os.path.join(BASE_DIR, 'source.txt')
    print(f"[DEBUG] 尝试读取源文件：{source_path}")
    
    if not os.path.exists(source_path):
        print(f"错误：未找到 source.txt 文件，请检查仓库根目录")
        sys.exit(1)

    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"文件读取失败：{str(e)}")
        sys.exit(1)

    # 处理数据
    results = process_urls(urls)
    
    # 创建输出目录
    output_dir = os.path.join(BASE_DIR, 'dist')
    os.makedirs(output_dir, exist_ok=True)
    
    # 写入结果文件
    try:
        with open(os.path.join(output_dir, 'all.txt'), 'w', encoding='utf-8') as f:
            f.write("\n".join(results['normal']))
        with open(os.path.join(output_dir, 'strict.txt'), 'w', encoding='utf-8') as f:
            f.write("\n".join(results['strict']))
    except Exception as e:
        print(f"文件写入失败：{str(e)}")
        sys.exit(1)
    
    # 更新README
    update_readme(results['stats'])
    print("\n处理完成！结果已更新")
