from datetime import datetime
import os
from urllib.parse import quote
import hashlib
from .config import BASE_DIR

README_TEMPLATE = """# 🛡️ AdGuard Home 规则库
---
## 🤔 简介
融合多个Adguard规则，最终筛选出适用于Adguard Home使用的DNS规则  
- 全部规则：仅去重  
- OAdH规则(OAdH_ALL)：去重后仅DNS规则 **(推荐)**
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

def generate_readme_content(stats, sources, lite_info):
    """生成README内容"""
    version = f"v{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    
    # 数据源表格
    def format_source(source):
        encoded_url = quote(source['url'], safe='/:')
        return f"| 🔗 [{source['url']}]({encoded_url}) | `{source['normal']}` | `{source['strict']}` |"
    
    source_table = [
        "| 数据源地址 | 源规则数 | OAdH规则数 |",
        "|----------|-----------|-----------|",
        *map(format_source, sources)
    ]
    
    # 统计信息
    stats_cards = [
        "**全部规则**：",
        f"- 有效规则：`{stats['normal']['valid']}`  ",
        f"- 重复过滤：`{stats['normal']['duplicates']}`\n",
        
        "**OAdH规则 (OAdH_ALL)**：",
        f"- 有效规则：`{stats['strict']['valid']}`  ",
        f"- 重复过滤：`{stats['strict']['duplicates']}`\n",
        
        "**OAdH去冲突规则 (OAdH_NCR)**：",
        f"- 有效规则：`{len(lite_info[0])}`  ",
        f"- 冲突过滤：`{lite_info[1]}`"
    ]
    
    # 下载链接
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
    
    return README_TEMPLATE.format(
        version=version,
        timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        source_section="\n".join(source_table),
        stats_section="\n".join(stats_cards),
        download_links="\n".join(download_links),
        download_links_cn="\n".join(download_links_cn)
    )

def update_readme(content):
    """更新README文件"""
    readme_path = os.path.join(BASE_DIR, 'README.md')
    current_hash = hashlib.md5(content.encode()).hexdigest()
    
    if os.path.exists(readme_path):
        with open(readme_path, 'rb') as f:
            if hashlib.md5(f.read()).hexdigest() == current_hash:
                return False
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True