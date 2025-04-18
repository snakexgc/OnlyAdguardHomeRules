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
    """模块化构建README内容"""
    lite_rules, lite_duplicates = lite_info
    
    # 构建表格生成器
    def build_table(headers, rows):
        sep_line = "| " + " | ".join(["-"*len(h) for h in headers]) + " |"
        return "\n".join([
            "| " + " | ".join(headers) + " |",
            sep_line,
            *["| " + " | ".join(map(str, row)) + " |" for row in rows]
        ])
    
    # 数据源表格
    source_rows = [
        ["总数据源数量", stats['total_urls']],
        *[[f"[{s['url']}]({quote(s['url'], safe='/:')})", s['normal'], s['strict']] for s in sources]
    ]
    sources_table = build_table(["类别", "全部规则数", "OAdH_ALL规则数"], source_rows)
    
    # 统计表格
    stats_rows = [
        ["有效规则数", stats['normal']['valid'], stats['strict']['valid'], len(lite_rules)],
        ["重复过滤数", stats['normal']['duplicates'], stats['strict']['duplicates'], lite_duplicates]
    ]
    stats_table = build_table(["类别", "全部规则", "OAdH_ALL", "OAdH_NCR"], stats_rows)
    
    # 组装完整内容
    content = f"""## 自动更新规则列表

### 数据源信息
{sources_table}

### 规则统计
{stats_table}

**最后更新时间**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

### 文件下载
- [全部规则](dist/all.txt)
- [OAdH_ALL规则](dist/OAdH_ALL.txt)
- [OAdH_NCR规则](dist/OAdH_NCR.txt)"""
    
    # 变更检测
    readme_path = os.path.join(get_base_dir(), 'README.md')
    current_hash = hashlib.md5(content.encode()).hexdigest()
    
    if os.path.exists(readme_path):
        with open(readme_path, 'rb') as f:
            existing_hash = hashlib.md5(f.read()).hexdigest()
        if current_hash == existing_hash:
            return False
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

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
