"""reportdb 的 SQL 构造契约（SQLite 方言）。

本模块只声明接口与契约，不包含实现。报表查询必须满足：

- 所有表名、列名与 ORDER BY 字段都经过标识符校验并以双引号包裹；
- 所有数据值、LIKE 模式与 LIMIT 都通过 ``?`` 占位符绑定；
- 任何非法输入统一抛出 :class:`InvalidQuery`。

实现时不得把用户输入拼进 SQL 文本。
"""

from __future__ import annotations


class InvalidQuery(Exception):
    """查询片段不符合语法或白名单契约。"""


def quote_ident(name: str) -> str:
    """校验并引用一个 SQLite 标识符。

    契约：

    - ``name`` 必须完整匹配 ``^[A-Za-z_][A-Za-z0-9_]{0,62}$``（ASCII）。
    - 合法时返回双引号包裹的标识符，并按 SQLite 规则把内部的 ``"``
      双写；虽然上述字符集本身不含 ``"``，双写仍是必须的防御性步骤。
    - 空串、含空格/分号/注释符、非 ASCII、超过 63 字符等不合法输入
      必须抛出 :class:`InvalidQuery`。
    - 本函数只处理标识符，不处理字符串字面量。
    """
    raise NotImplementedError


def check_identifier(name: str, allowed: set[str]) -> str:
    """按完整名称、大小写不敏感地检查白名单。

    用于表名、列名与 ORDER BY 字段。契约：

    - 只做完整名称匹配，禁止前缀、子串或包含判断；
    - 大小写不敏感：``"USERS"`` 可以命中 ``{"users"}``；
    - 命中时返回 ``allowed`` 中对应条目的规范拼写（保留白名单中的大小写）；
    - 未命中、``allowed`` 为空，或 ``name`` 不满足 :func:`quote_ident`
      的语法时，抛出 :class:`InvalidQuery`。
    """
    raise NotImplementedError


def build_select(
    table: str,
    columns: list[str],
    order_by: list[tuple[str, str]],
    limit: int,
    where: dict,
) -> tuple[str, list]:
    """构造参数化的 SELECT 查询（SQLite 方言）。

    生成的 SQL 使用单个空格分隔，形态固定为::

        SELECT <columns> FROM <table>
        [WHERE <col> = ? [AND <col> IN (?, ...)]]
        [ORDER BY <col> ASC|DESC]
        LIMIT ?

    具体契约：

    - ``table``、``columns`` 中的每一项、``order_by`` 中的字段都必须通过
      :func:`quote_ident` 并以双引号形式输出；``columns`` 不得为空。
    - ``where`` 只允许等值与 ``IN``：标量值生成 ``= ?``；非空 list/tuple
      生成 ``IN (?, ...)``。按 ``where`` 的插入顺序生成条件，值全部放入
      参数列表。``None``、空序列及其他不支持的值类型抛出
      :class:`InvalidQuery`。
    - ``order_by`` 的每一项是 ``(字段, 方向)``；方向必须是精确的 ``"ASC"``
      或 ``"DESC"``，否则抛出 :class:`InvalidQuery`。空列表省略 ORDER BY。
      有白名单时，调用方还必须先用 :func:`check_identifier` 校验排序字段。
    - ``limit`` 必须是真正的 ``int``（拒绝 ``bool``），范围为 1..1000，
      并且必须以 ``?`` 绑定，不得格式化进 SQL。
    - 返回 ``(sql, params)``，其中 ``params`` 依次是 where 的值与 limit；
      SQL 文本中不得出现任何数据值。
    """
    raise NotImplementedError


def escape_like(value: str, escape: str = "\\") -> str:
    """转义 LIKE 的通配符与转义符本身。

    - ``escape`` 必须是单个字符，且不能是 ``%`` 或 ``_``，否则抛出
      :class:`InvalidQuery`。
    - 先转义 ``escape`` 自身，再转义 ``%`` 与 ``_``，每个字符前加上
      ``escape``。
    - 返回可直接绑定到 ``LIKE ? ESCAPE '<escape>'`` 的值，不添加首尾
      ``%``，也不加引号。例如 ``escape_like("50%") == "50\\%"``。
    """
    raise NotImplementedError


def build_search(
    table: str,
    column: str,
    term: str,
    limit: int,
    allowed: dict,
) -> tuple[str, list]:
    """构造参数化的子串搜索（SQLite 方言）。

    ``allowed`` 必须是 ``{"tables": [...], "columns": [...]}``。先通过
    :func:`check_identifier` 校验表名与列名（大小写不敏感、完整名称匹配），
    再通过 :func:`escape_like` 转义 ``term``。生成的 SQL 形态固定为::

        SELECT "col" FROM "table" WHERE "col" LIKE ? ESCAPE '\\' LIMIT ?

    参数依次为 ``[f"%{escaped}%", limit]``。``term`` 可以为空串（匹配所有
    行）。``limit`` 与 :func:`build_select` 一样必须是 1..1000 的真正
    ``int`` 并以 ``?`` 绑定。``allowed`` 缺少键、列表为空或任一名称不在
    白名单中时，抛出 :class:`InvalidQuery`。
    """
    raise NotImplementedError
