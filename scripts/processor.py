import os
import sys

# 获取项目根目录路径（即包含 src 的目录）
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)  # 将根目录加入模块搜索路径

from src import (
    config,
    file_utils,
    rules_processor,
    readme_generator
)

def main():
    has_changes = False
    
    try:
        # 读取源文件
        urls = file_utils.read_source_file()
        
        # 处理规则
        results = rules_processor.process_urls(urls)
        
        # 创建输出目录
        output_dir = os.path.join(config.BASE_DIR, 'dist')
        os.makedirs(output_dir, exist_ok=True)

        # 写入基础规则文件
        has_changes |= file_utils.safe_write_file(
            os.path.join(output_dir, 'all.txt'),
            "\n".join(results['normal'])
        )
        has_changes |= file_utils.safe_write_file(
            os.path.join(output_dir, 'OAdH_ALL.txt'),
            "\n".join(results['strict'])
        )

        # 生成 OAdH_NCR 规则
        with open(os.path.join(output_dir, 'OAdH_ALL.txt'), 'r', encoding='utf-8') as f:
            oadh_all_rules = f.read().splitlines()
        
        oadh_ncr_rules, oadh_ncr_duplicates = rules_processor.process_lite_rules(oadh_all_rules)
        has_changes |= file_utils.safe_write_file(
            os.path.join(output_dir, 'OAdH_NCR.txt'),
            "\n".join(oadh_ncr_rules)
        )

        # 生成README内容
        readme_content = readme_generator.generate_readme_content(
            results['stats'],
            results['sources'],
            (oadh_ncr_rules, oadh_ncr_duplicates)
        )
        
        # 更新README
        has_changes |= readme_generator.update_readme(readme_content)

        # 设置输出变量
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            print(f'has_changes={str(has_changes).lower()}', file=fh)
        
        print(f"处理完成{'，检测到变更' if has_changes else '，无新变更'}")
        return 0
        
    except Exception as e:
        print(f"发生严重错误: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())