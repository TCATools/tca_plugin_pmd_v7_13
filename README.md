# tca_plugin_pmd_v7_13
A TCA plugin for [pmd](https://github.com/pmd/pmd/releases/tag/pmd_releases%2F7.13.0).

## 依赖

[pmd v7.13.0](https://github.com/pmd/pmd/releases/download/pmd_releases%2F7.13.0/pmd-dist-7.13.0-bin.zip)

## 使用
- 部署好TCA
- 下载本插件
- 在TCA上加载本插件的[工具JSON](config/pmd.json)
- 在TCA上的节点管理页面上，给节点添加本插件的工具进程
- 在待分析的TCA项目的分析方案中，添加本插件的规则，然后启动任务即可

## 更新 config 文件
1. 下载并指定 PMD 对应版本源代码目录位置
2. 执行以下命令
```bash
python src/update.py -i <pmd源代码目录>
```
