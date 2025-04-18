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
    # 分类收集规则
    whitelist = []
    whitelist_domains = set()
    blacklist = []
    
    # 预处理所有规则
    for rule in strict_rules:
        rule = rule.strip()
        if not rule:
            continue
        
        # 提取规则类型和域名
        if rule.startswith('@@||'):
            domain = extract_rule_domain(rule)
            if domain:
                whitelist_domains.add(domain)
                whitelist.append(rule)
        elif rule.startswith('||'):
            blacklist.append(rule)

    # 过滤黑名单规则
    filtered_blacklist = []
    for rule in blacklist:
        domain = extract_rule_domain(rule)
        if domain not in whitelist_domains:
            filtered_blacklist.append(rule)

    return filtered_blacklist + whitelist

def process_urls(urls):
    """处理 URL 源数据"""
    # ...保持原有 process_urls 函数不变...

def update_readme(stats, sources):
    """更新 README 文档"""
    # ...保持原有 update_readme 函数不变...

if __name__ == '__main__':
    BASE_DIR = get_base_dir()
    
    # 读取源文件
    source_path = os.path.join(BASE_DIR, 'source.txt')
    with open(source_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    # 处理规则
    results = process_urls(urls)
    
    # 创建输出目录
    output_dir = os.path.join(BASE_DIR, 'dist')
    os.makedirs(output_dir, exist_ok=True)

    # 写入基本规则文件
    with open(os.path.join(output_dir, 'all.txt'), 'w', encoding='utf-8') as f:
        f.write("\n".join(results['normal']))
    
    with open(os.path.join(output_dir, 'strict.txt'), 'w', encoding='utf-8') as f:
        f.write("\n".join(results['strict']))
    
    # 生成 Lite 模式规则
    with open(os.path.join(output_dir, 'strict.txt'), 'r', encoding='utf-8') as f:
        strict_rules = f.read().splitlines()
    
    lite_rules = process_lite_rules(strict_rules)
    
    with open(os.path.join(output_dir, 'Lite.txt'), 'w', encoding='utf-8') as f:
        f.write("\n".join(lite_rules))
    
    # 更新文档
    update_readme(results['stats'], results['sources'])
    print("规则处理完成！")
