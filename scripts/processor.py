import requests
from datetime import datetime
import os
import sys

def get_base_dir():
    if 'GITHUB_WORKSPACE' in os.environ:
        return os.environ['GITHUB_WORKSPACE']
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

BASE_DIR = get_base_dir()

def process_urls(urls):
    results = {
        'normal': [],
        'strict': [],
        'sources': [],
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
            
            normal_count = 0
            strict_count = 0
            normal_lines = []
            strict_lines = []
            
            for line in response.text.splitlines():
                stripped = line.strip()
                results['stats']['total_lines'] += 1
                
                if not stripped or stripped.startswith('!'):
                    continue
                
                # 普通模式计数
                normal_count += 1
                normal_lines.append(line)
                
                # 严格模式计数
                if stripped.startswith(('||', '@@')):
                    strict_count += 1
                    strict_lines.append(line)
            
            # 记录来源数据
            results['sources'].append({
                'url': url,
                'normal': normal_count,
                'strict': strict_count
            })
            
            results['normal'].extend(normal_lines)
            results['strict'].extend(strict_lines)
            
        except Exception as e:
            print(f"处理失败：{str(e)}")
            results['sources'].append({
                'url': url,
                'normal': 0,
                'strict': 0
            })
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

def update_readme(stats, sources):
    # 生成来源表格
    sources_table = "\n".join(
        f"| [{s['url']}]({s['url']}) | {s['normal']} | {s['strict']} |"
        for s in sources
    )

    template = f"""## 自动更新规则列表

### 上游规则列表
| 来源地址 | 普通模式规则数 | 严格模式规则数 |
|----------|----------------|----------------|
{sources_table}

### 统计信息
| 类别        | 普通模式       | 严格模式       |
|-------------|---------------|---------------|
| 数据源数量  | {stats['total_urls']:>6}       | {stats['total_urls']:>6}       |
| 有效规则数  | {stats['normal']['valid']:>6}       | {stats['strict']['valid']:>6}       |
| 重复过滤数  | {stats['normal']['duplicates']:>6}       | {stats['strict']['duplicates']:>6}       |

最后更新时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

### 下载链接
- [普通模式列表](dist/all.txt)
- [严格模式列表](dist/strict.txt)
"""

    readme_path = os.path.join(BASE_DIR, 'README.md')
    
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
    source_path = os.path.join(BASE_DIR, 'source.txt')
    
    if not os.path.exists(source_path):
        print(f"错误：未找到 source.txt")
        sys.exit(1)

    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"文件读取失败：{str(e)}")
        sys.exit(1)

    results = process_urls(urls)
    
    output_dir = os.path.join(BASE_DIR, 'dist')
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        with open(os.path.join(output_dir, 'all.txt'), 'w', encoding='utf-8') as f:
            f.write("\n".join(results['normal']))
        with open(os.path.join(output_dir, 'strict.txt'), 'w', encoding='utf-8') as f:
            f.write("\n".join(results['strict']))
    except Exception as e:
        print(f"文件写入失败：{str(e)}")
        sys.exit(1)
    
    update_readme(results['stats'], results['sources'])
    print("处理完成！")
