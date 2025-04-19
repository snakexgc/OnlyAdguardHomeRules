import requests
import re
from .config import BASE_DIR

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