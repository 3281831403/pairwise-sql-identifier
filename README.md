# pairwise-sql-identifier

默认配置和生产配置不一致时，报表查询开始被改写：表名列名直接拼进 SQL，分号和注释都能过；ORDER BY 的字段与方向不校验，塞子查询也行；LIKE 里的 % 和 _ 不转义，一次输入就变成全表越权匹配；LIMIT 直接格式化，负数与分号能绕过上限；白名单用前缀包含判断，users_old 和 USERS 混进了不该给的列。reportdb/query.py 是核心，tests/test_query.py 15个红。要修的是：标识符白名单加双引号转义；排序字段与方向都走枚举；LIKE 通配符与转义符全部转义；LIMIT 参数化并限制范围；白名单按完整名精确匹配。

## 运行方式与初始状态

在仓库根目录执行：

```powershell
python -m pytest tests -q
```

初始桩实现下的预期输出恰好是：

```text
15 failed
```

要求无 collection error、无 import error、无 syntax error。15 个测试全部调用 `reportdb/query.py` 中的桩并因 `NotImplementedError` 失败；完成实现后应达到 `15 passed`。

## 字段表

| 字段 | 取值 |
| --- | --- |
| 所属领域 | 安全 |
| 子方向 | 漏洞检测与攻防 |
| 任务类型 | Bugfix |
| 语言/框架 | Python 3, pytest |
| 环境可复现等级 | 无外部依赖 |

## tests 不可修改

`tests/test_query.py` 是评测契约，不可修改；修复只能发生在 `reportdb/query.py`。测试数量固定为 15。
