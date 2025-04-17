import requests
from datetime import datetime
import os

def process_urls(urls):
    # 初始化数据结构
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
                # 普通模式过滤
                if stripped and not stripped.startswith('!'):
                    normal_lines.append(line)
                # 严格模式过滤
                if stripped and not stripped.startswith('!') and (
                    stripped.startswith('||') or stripped.startswith('@@')):
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
    with open('README.md', 'r') as f:
        content = f.read()
    
    # 替换更新区块
    start_marker = '<!-- AUTO_UPDATE_START -->'
    end_marker = '<!-- AUTO_UPDATE_END -->'
    new_content = content.split(start_marker)[0] + \
        f"{start_marker}\n{template}\n{end_marker}" + \
        content.split(end_marker)[-1]
    
    with open('README.md', 'w') as f:
        f.write(new_content)

if __name__ == '__main__':
    # 读取URL列表
    with open('source.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    # 处理数据
    results = process_urls(urls)
    
    # 创建输出目录
    os.makedirs('dist', exist_ok=True)
    
    # 保存结果文件
    with open('dist/all.txt', 'w') as f:
        f.write("\n".join(results['normal']))
    
    with open('dist/strict.txt', 'w') as f:
        f.write("\n".join(results['strict']))
    
    # 更新README
    update_readme(results['stats'])