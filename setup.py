from setuptools import setup, find_packages

setup(
    name="onlyadguardhererules",
    version="0.1.0",
    packages=find_packages(where="src"),  # 指定包在src目录下
    package_dir={"": "src"},              # 声明源码在src目录
    install_requires=[
        # 这里列出你的依赖，会从requirements.txt读取
        'requests>=2.28.2',
        'setuptools',
    ],
    entry_points={
        # 如果有命令行工具可以在这里配置
    },
)