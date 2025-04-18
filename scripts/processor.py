import requests
import re
import os
import sys
from datetime import datetime
from urllib.parse import quote

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
    """生成 OAdH_NCR 规则并返回(规则列表, 重复数)"""
    whitelist = []
    whitelist_domains = set()
    blacklist = []
    duplicates = 0

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

    # 过滤黑名单并计数
    filtered_blacklist = []
    for rule in blacklist:
        domain = extract_rule_domain(rule)
        if domain in whitelist_domains:
            duplicates += 1
        else:
            filtered_blacklist.append(rule)

    return (filtered_blacklist + whitelist, duplicates)

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

def update_readme(stats, sources, lite_info):
    """更新 README 文档，返回是否有变更"""
    lite_rules, lite_duplicates = lite_info
    
    # 生成来源表格
    sources_table = [
        f"| 总数据源数量 | {stats['total_urls']} |",
        "|--------------|----------------|",
        "| 来源地址 | 全部规则数 | OAdH_ALL规则数 |"
    ] + [
        f"| [{s['url']}]({quote(s['url'], safe='/:')}) | {s['normal']} | {s['strict']} |"
        for s in sources
    ]

    template = f'''## 自动更新规则列表

### 上游规则列表
{"\n".join(sources_table)}

### 统计信息
| 类别        | 全部规则       | OAdH_ALL       | OAdH_NCR       |
|-------------|---------------|---------------|---------------|
| 有效规则数  | {stats['normal']['valid']:>6} | {stats['strict']['valid']:>6} | {len(lite_rules):>6} |
| 重复过滤数  | {stats['normal']['duplicates']:>6} | {stats['strict']['duplicates']:>6} | {lite_duplicates:>6} |

最后更新时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

### 下载链接
- [全部规则列表](dist/all.txt)
- [OAdH_ALL 列表](dist/OAdH_ALL.txt)
- [OAdH_NCR 列表](dist/OAdH_NCR.txt)'''

    readme_path = os.path.join(get_base_dir(), 'README.md')
    new_content = ""
    has_changes = False
    
    start_marker = '<!-- AUTO_UPDATE_START -->'
    end_marker = '<!-- AUTO_UPDATE_END -->'
    
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            exists_content = f.read()
        
        # 生成新内容
        if start_marker in exists_content and end_marker in exists_content:
            new_content = exists_content.split(start_marker)[0] + \
                        f"{start_marker}\n{template}\n{end_marker}" + \
                        exists_content.split(end_marker)[-1]
        else:
            new_content = f"{exists_content}\n{start_marker}\n{template}\n{end_marker}"
        
        # 比较内容差异
        if new_content.strip() != exists_content.strip():
            has_changes = True
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
    else:
        has_changes = True
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(f"{start_marker}\n{template}\n{end_marker}")
    
    return has_changes

def safe_write_file(path, content):
    """安全写入文件，返回是否有变更"""
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            if f.read() == content:
                return False
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

if __name__ == '__main__':
    BASE_DIR = get_base_dir()
    has_changes = False
    
    # 读取源文件
    source_path = os.path.join(BASE_DIR, 'source.txt')
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"文件读取失败：{str(e)}")
        sys.exit(1)

    results = process_urls(urls)
    
    # 创建输出目录
    output_dir = os.path.join(BASE_DIR, 'dist')
    os.makedirs(output_dir, exist_ok=True)

    # 写入基础规则文件
    has_changes |= safe_write_file(
        os.path.join(output_dir, 'all.txt'),
        "\n".join(results['normal'])
    )
    has_changes |= safe_write_file(
        os.path.join(output_dir, 'OAdH_ALL.txt'),
        "\n".join(results['strict'])
    )

    # 生成 OAdH_NCR 规则
    with open(os.path.join(output_dir, 'OAdH_ALL.txt'), 'r', encoding='utf-8') as f:
        oadh_all_rules = f.read().splitlines()
    
    oadh_ncr_rules, oadh_ncr_duplicates = process_lite_rules(oadh_all_rules)
    has_changes |= safe_write_file(
        os.path.join(output_dir, 'OAdH_NCR.txt'),
        "\n".join(oadh_ncr_rules)
    )

    # 更新README
    readme_changed = update_readme(results['stats'], results['sources'], (oadh_ncr_rules, oadh_ncr_duplicates))
    has_changes |= readme_changed

    # 设置输出变量
    print(f"::set-output name=has_changes::{str(has_changes).lower()}")
    print(f"处理完成{'，检测到变更' if has_changes else '，无新变更'}")
