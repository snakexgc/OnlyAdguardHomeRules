import requests
import re
from .config import BASE_DIR
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 预编译正则表达式，提升匹配效率
RULE_DOMAIN_REGEX = re.compile(r'^(@@\|\||\|\|)([^\^$]+)')

def extract_rule_domain(rule):
    """从规则中提取域名部分"""
    match = RULE_DOMAIN_REGEX.match(rule)
    return match.group(2).rstrip('/') if match else None

def process_lite_rules(strict_rules):
    """生成 OAdH_NCR 规则并返回(规则列表, 重复数)"""
    logger.info("开始处理严格规则...")
    whitelist_domains = set()
    duplicates = 0
    processed_blacklist = []
    processed_whitelist = []

    for rule in strict_rules:
        rule = rule.strip()
        if not rule:
            continue
        
        if rule.startswith('@@||'):
            domain = extract_rule_domain(rule)
            if domain:
                if domain in whitelist_domains:
                    duplicates += 1
                    logger.debug(f"发现重复的白名单规则：{rule}")
                else:
                    whitelist_domains.add(domain)
                    processed_whitelist.append(rule)
                    logger.debug(f"添加白名单规则：{rule}")
        elif rule.startswith('||'):
            domain = extract_rule_domain(rule)
            if domain and domain not in whitelist_domains:
                processed_blacklist.append(rule)
                logger.debug(f"添加黑名单规则：{rule}")
            elif domain:
                duplicates += 1
                logger.debug(f"发现与白名单重复的黑名单规则：{rule}")

    logger.info(f"处理严格规则完成，共处理 {len(strict_rules)} 条规则，其中有效规则 {len(processed_blacklist) + len(processed_whitelist)} 条，重复规则 {duplicates} 条")
    return (processed_blacklist + processed_whitelist, duplicates)

def process_urls(urls):
    """处理 URL 源数据"""
    logger.info("开始处理 URL 源数据...")
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
        normal_count = 0
        strict_count = 0
        
        try:
            logger.info(f"开始处理 URL：{url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            logger.info(f"成功获取 URL：{url}，状态码：{response.status_code}")
            
            unique_normal = set()
            unique_strict = set()
            
            for line in response.text.splitlines():
                stripped = line.strip()
                results['stats']['total_lines'] += 1
                
                if not stripped or stripped.startswith('!'):
                    continue
                
                normal_count += 1
                unique_normal.add(line)
                logger.debug(f"处理普通规则：{line}")
                
                if stripped.startswith(('||', '@@')):
                    strict_count += 1
                    unique_strict.add(line)
                    logger.debug(f"处理严格规则：{line}")
            
            logger.info(f"处理 URL：{url} 完成，共处理 {normal_count} 条普通规则，其中有效规则 {len(unique_normal)} 条，重复规则 {normal_count - len(unique_normal)} 条")
            logger.info(f"处理 URL：{url} 完成，共处理 {strict_count} 条严格规则，其中有效规则 {len(unique_strict)} 条，重复规则 {strict_count - len(unique_strict)} 条")
            
            results['sources'].append({
                'url': url,
                'normal': normal_count,
                'strict': strict_count
            })
            
            results['normal'] = list(unique_normal)
            results['stats']['normal']['valid'] = len(results['normal'])
            results['stats']['normal']['duplicates'] = normal_count - len(results['normal'])
            
            results['strict'] = list(unique_strict)
            results['stats']['strict']['valid'] = len(results['strict'])
            results['stats']['strict']['duplicates'] = strict_count - len(results['strict'])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求 URL：{url} 失败，错误信息：{str(e)}")
            results['sources'].append({
                'url': url,
                'normal': 0,
                'strict': 0
            })
        except Exception as e:
            logger.error(f"处理 URL：{url} 时发生错误，错误信息：{str(e)}")
            results['sources'].append({
                'url': url,
                'normal': 0,
                'strict': 0
            })
            continue

    logger.info("处理 URL 源数据完成")
    return results