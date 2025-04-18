import requests
import re
import os
import sys
from datetime import datetime

def get_base_dir():
    """获取仓库根目录"""
    if 'GITHUB_WORKSPACE' in os.environ:
        return os.environ['GITHUB_WORKSPACE']
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def extract_rule_domain(rule):
    """从规则中提取域名部分"""
    match = re.match(r'^(@@\|\||\|\|)([^\^$]+)', rule)
    return match.group(2).rstrip('/') if match else None

def process_lite_rules(strict_rules):
    """生成 Lite 模式规则"""
    whitelist = []
    whitelist_domains = set()
    blacklist = []
    
    for rule in strict_rules:
        rule = rule.strip()
        if not rule:
            continue
        
        if rule.startswith('@@||'):
            domain = extract_rule_domain(rule)
            if domain:
                whitelist_domains.add(domain)
                whitelist.append(rule)
        elif rule.startswith('||'):
            blacklist.append(rule)

    filtered_blacklist = [
        rule for rule in blacklist
        if extract_rule_domain(rule) not in whitelist_domains
    ]
    
    return filtered_blacklist + whitelist

def process_urls(urls):
    """处理 URL 源数据"""
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
                
                normal_count += 1
                normal_lines.append(line)
                
                if stripped.startswith(('||', '@@')):
                    strict_count += 1
                    strict_lines.append(line)
            
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

def update_readme(stats, sources, lite_count):
    """更新 README 文档"""
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
| 类别        | 普通模式       | 严格模式       | 精简模式       |
|-------------|---------------|---------------|---------------|
| 数据源数量  | {stats['total_urls']:>6}       | {stats['total_urls']:>6}       | {"-"*11}       |
| 有效规则数  | {stats['normal']['valid']:>6}       | {stats['strict']['valid']:>6}       | {lite_count:>6}       |
| 重复过滤数  | {stats['normal']['duplicates']:>6}       | {stats['strict']['duplicates']:>6}       | {"-"*11}       |

最后更新时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

### 下载链接
- [普通模式列表](dist/all.txt)（{stats['normal']['valid']} 条）
- [严格模式列表](dist/strict.txt)（{stats['strict']['valid']} 条）
- [精简模式列表](dist/Lite.txt)（{lite_count} 条）
"""

    readme_path = os.path.join(get_base_dir(), 'README.md')
    
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
    BASE_DIR = get_base_dir()
    
    # 读取源文件
    source_path = os.path.join(BASE_DIR, 'source.txt')
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"文件读取失败：{str(e)}")
        sys.exit(1)

    # 处理规则
    results = process_urls(urls)
    
    # 创建输出目录
    output_dir = os.path.join(BASE_DIR, 'dist')
    os.makedirs(output_dir, exist_ok=True)

    # 写入基础规则文件
    try:
        with open(os.path.join(output_dir, 'all.txt'), 'w', encoding='utf-8') as f:
            f.write("\n".join(results['normal']))
        with open(os.path.join(output_dir, 'strict.txt'), 'w', encoding='utf-8') as f:
            f.write("\n".join(results['strict']))
    except Exception as e:
        print(f"文件写入失败：{str(e)}")
        sys.exit(1)
    
    # 生成 Lite 模式
    with open(os.path.join(output_dir, 'strict.txt'), 'r', encoding='utf-8') as f:
        strict_rules = f.read().splitlines()
    
    lite_rules = process_lite_rules(strict_rules)
    lite_count = len(lite_rules)
    
    try:
        with open(os.path.join(output_dir, 'Lite.txt'), 'w', encoding='utf-8') as f:
            f.write("\n".join(lite_rules))
    except Exception as e:
        print(f"Lite 模式写入失败：{str(e)}")
        sys.exit(1)
    
    # 更新文档
    update_readme(results['stats'], results['sources'], lite_count)
    print("所有规则处理完成！")
