import requests
import re
import os
import sys
from datetime import datetime
from urllib.parse import quote
import hashlib

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

README_TEMPLATE = """# 🛡️ AdGuard Home 规则库
---
## 🤔 简介
融合多个Adguard规则，最终筛选出适用于Adguard Home使用的DNS规则  
- 全部规则：仅去重  
- OAdH规则(OAdH_ALL)：仅DNS规则 **(推荐)**
- OAdH去冲突规则(OAdH_NCR)：去除黑白名单同时存在的情况 **(实验性)**
---

## 📦 当前版本
**版本标识**: {version}  
**更新时间**: {timestamp}  

---

## 📂 数据源列表
{source_section}

---

## 📊 规则统计
{stats_section}

---

## 📥 文件下载
### 🌐直连
{download_links}
### 🚀加速
{download_links_cn}
---
"""

def update_readme(stats, sources, lite_info):
    # 生成版本信息
    version = f"v{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    
    # 生成带样式的数据源表格
    def format_source(source):
        encoded_url = quote(source['url'], safe='/:')
        return f"| 🔗 [{source['url']}]({encoded_url}) | `{source['normal']}` | `{source['strict']}` |"
    
    source_table = [
        "| 数据源地址 | 源规则数 | OAdH规则数 |",
        "|----------|-----------|-----------|",
        *map(format_source, sources)
    ]
    
    # 生成统计信息卡片
    stats_cards = [
        "**全部规则**：",
        f"- 有效规则：`{stats['normal']['valid']}`  "  # 末尾双空格强制换行
        f"- 重复过滤：`{stats['normal']['duplicates']}`\n",
        
        "**OAdH规则 (OAdH_ALL)**：",
        f"- 有效规则：`{stats['strict']['valid']}`  "
        f"- 重复过滤：`{stats['strict']['duplicates']}`\n",
        
        "**OAdH去冲突规则 (OAdH_NCR)**：",
        f"- 有效规则：`{len(lite_info[0])}`  "
        f"- 冲突过滤：`{lite_info[1]}`"
    ]
    
    # 生成带图标的下载链接
    download_links = [
        "🔗 [全部规则 (all.txt)](dist/all.txt)  ",
        "🔒 [OAdH规则 (OAdH_ALL.txt)](dist/OAdH_ALL.txt)  ",
        "✂️ [OAdH去冲突规则 (OAdH_NCR.txt)](dist/OAdH_NCR.txt)"
    ]
    download_links_cn = [
        "🔗 [全部规则 (all.txt)](https://github.snakexgc.com/https://github.com/snakexgc/OnlyAdguardHomeRules/blob/main/dist/all.txt)  ",
        "🔒 [OAdH规则 (OAdH_ALL.txt)](https://github.snakexgc.com/https://github.com/snakexgc/OnlyAdguardHomeRules/blob/main/dist/OAdH_ALL.txt)  ",
        "✂️ [OAdH去冲突规则 (OAdH_NCR.txt)](https://github.snakexgc.com/https://github.com/snakexgc/OnlyAdguardHomeRules/blob/main/dist/OAdH_NCR.txt)"
    ]
    
    # 组装内容
    content = README_TEMPLATE.format(
        version=version,
        timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        source_section="\n".join(source_table),
        stats_section="\n".join(stats_cards),
        download_links="\n".join(download_links),
        download_links_cn="\n".join(download_links_cn)
    )
    
    # 变更检测（哈希校验）
    readme_path = os.path.join(get_base_dir(), 'README.md')
    current_hash = hashlib.md5(content.encode()).hexdigest()
    
    if os.path.exists(readme_path):
        with open(readme_path, 'rb') as f:
            if hashlib.md5(f.read()).hexdigest() == current_hash:
                return False
    
    with open(readme_path, 'w', encoding='utf-8') as f:
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
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(f'has_changes={str(has_changes).lower()}', file=fh)
    
    print(f"处理完成{'，检测到变更' if has_changes else '，无新变更'}")
