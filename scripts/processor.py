import requests
from datetime import datetime
import os

# 获取仓库根目录路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            normal_lines = []
            strict_lines = []
            
            for line in response.text.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith('!'):
                    normal_lines.append(line)
                    if stripped.startswith(('||', '@@')):
                        strict_lines.append(line)

            results['stats']['total_lines'] += len(response.text.splitlines())
            results['normal'].extend(normal_lines)
            results['strict'].extend(strict_lines)
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
    
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
    if os.path.exists(readme_path):
        with open(readme_path, 'r') as f:
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

    with open(readme_path, 'w') as f:
        f.write(new_content)

if __name__ == '__main__':
    # 读取source.txt
    source_path = os.path.join(BASE_DIR, 'source.txt')
    with open(source_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    # 处理数据
    results = process_urls(urls)
    
    # 创建输出目录
    output_dir = os.path.join(BASE_DIR, 'dist')
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存结果文件
    with open(os.path.join(output_dir, 'all.txt'), 'w') as f:
        f.write("\n".join(results['normal']))
    
    with open(os.path.join(output_dir, 'strict.txt'), 'w') as f:
        f.write("\n".join(results['strict']))
    
    # 更新README
    update_readme(results['stats'])
