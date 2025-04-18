def update_readme(stats, sources, lite_info):
    """更新 README 文档"""
    lite_rules, lite_duplicates = lite_info
    
    # 生成来源表格内容（提前处理换行符）
    sources_content = "\n".join([
        f"| 总数据源数量 | {stats['total_urls']} |",
        "|--------------|----------------|",
        "| 来源地址 | 全部规则数 | OAdH_ALL规则数 |"
    ] + [
        f"| [{s['url']}]({quote(s['url'], safe='/:')}) | {s['normal']} | {s['strict']} |"
        for s in sources
    ])

    # 使用自然换行替代转义字符
    template = f'''## 自动更新规则列表

### 上游规则列表
{sources_content}

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
