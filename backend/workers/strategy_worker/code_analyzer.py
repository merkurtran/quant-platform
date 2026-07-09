import ast
from typing import Optional


class CodeSecurityError(Exception):
    """代码安全检查未通过"""
    pass


# 允许导入的白名单模块（只允许数据分析相关的）
ALLOWED_IMPORTS = {
    # backtrader 生态
    'backtrader', 'bt',
    # 数值计算
    'math', 'numpy', 'pandas',
    # 标准库（安全子集）
    'datetime', 'time', 'collections', 'itertools', 'functools',
    'typing', 'dataclasses', 'enum',
}

# 禁止调用的简单函数名（用于 ast.Name 节点，如 eval()、compile()）
FORBIDDEN_SIMPLE_CALLS = frozenset({
    '__import__', 'eval', 'exec', 'compile',
    'open', 'input',
})

# 禁止的属性链调用（如 os.system、subprocess.Popen）
FORBIDDEN_ATTR_CALLS = frozenset({
    'os.system', 'os.popen', 'os.remove', 'os.unlink',
    'subprocess.call', 'subprocess.Popen', 'subprocess.run',
})

# 禁止访问的危险属性/双下划线属性
FORBIDDEN_DUNDER_ATTRS = frozenset({
    '__class__', '__mro__', '__subclasses__', '__bases__',
    '__init_subclass__', '__getattribute__', '__setattr__',
    '__delattr__', '__dict__', '__globals__', '__locals__',
    '__builtins__', '__import__', '__loader__', '__spec__',
    '__file__', '__path__', '__call__', '__new__', '__reduce__',
    '__reduce_ex__', '__getstate__', '__setstate__',
})


class SecurityVisitor(ast.NodeVisitor):
    """遍历AST节点，检测潜在的安全违规"""

    def __init__(self):
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import):
        """检查 import xxx"""
        for alias in node.names:
            module_name = alias.name.split('.')[0]
            if module_name not in ALLOWED_IMPORTS:
                self.violations.append(
                    f"Line {node.lineno}: 禁止导入 '{alias.name}' (不在白名单中)"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """检查 from xxx import yyy"""
        if node.module:
            module_name = node.module.split('.')[0]
            if module_name not in ALLOWED_IMPORTS:
                self.violations.append(
                    f"Line {node.lineno}: 禁止从 '{node.module}' 导入"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """检查危险的函数调用"""

        # 情况1: 直接调用危险函数名 (如 eval(), compile(), input())
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_SIMPLE_CALLS:
                self.violations.append(
                    f"Line {node.lineno}: 禁止调用 '{node.func.id}()' (高危操作)"
                )

        # 情况2: 属性链调用 (如 os.system(), subprocess.Popen())
        elif isinstance(node.func, ast.Attribute):
            attr_chain = self._get_attr_chain(node.func)
            if attr_chain in FORBIDDEN_ATTR_CALLS:
                self.violations.append(
                    f"Line {node.lineno}: 禁止调用 '{attr_chain}()' (高危操作)"
                )
            # 额外检测：xxx.__class__() 或 xxx.__subclasses__()
            if node.func.attr in {'__class__', '__subclasses__', '__mro__'}:
                self.violations.append(
                    f"Line {node.lineno}: 禁止调用反射方法 '{node.func.attr}()'"
                )

        self.generic_visit(node)

    def visit_Attribute(self, node):
        """
        检查属性访问中的危险模式

        核心修复：不再要求必须是多层属性访问，
        只要 attr 是危险 dunder 属性就拦截。
        """
        # 检测所有形式的危险属性访问（无论 node.value 类型）
        if node.attr in FORBIDDEN_DUNDER_ATTRS:
            context = self._get_attr_context(node)
            self.violations.append(
                f"Line {node.lineno}: 检测到危险属性访问 '{node.attr}' "
                f"(上下文: {context})"
            )
        
        # 特殊检测：__builtins__.__import__
        if isinstance(node.value, ast.Name):
            if node.value.id == "__builtins__" and node.attr == "__import__":
                self.violations.append(
                    f"Line {node.lineno}: 试图访问 __builtins__.__import__"
                )

        self.generic_visit(node)

    def visit_Subscript(self, node):
        """检查：__mro__[1].__subclasses__() 等"""
        # 检测调用链中的 __subclasses__
        if isinstance(node.value, ast.Attribute):
            if node.value.attr == "__subclasses__":
                self.violations.append(
                    f"Line {node.lineno}: 禁止调用 __subclasses__()"
                )
        self.generic_visit(node)

    def _get_attr_chain(self, node) -> str:
        """
        提取完整的属性调用链（类的私有方法）

        例: os.system -> "os.system"
            a.b.c -> "a.b.c"
        """
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))

    def _get_attr_context(self, node, max_depth=3) -> str:
        """
        获取属性访问的上下文信息（用于错误报告）

        这是类的私有方法，不是模块级函数。
        """
        parts = []
        current = node
        depth = 0
        while depth < max_depth:
            if isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            elif isinstance(current, ast.Name):
                parts.append(current.id)
                break
            elif isinstance(current, ast.Constant):
                repr_val = repr(current.value)[:20]
                parts.append(f'Constant({repr_val})')
                break
            else:
                parts.append(type(current).__name__)
                break
            depth += 1
        return '.'.join(reversed(parts))


def analyze_code_security(code: str) -> None:
    """
    分析用户代码的安全性

    Raises:
        CodeSecurityError: 如果发现安全违规
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise CodeSecurityError(f"语法错误: {e.msg} (行 {e.lineno})")

    visitor = SecurityVisitor()
    visitor.visit(tree)

    if visitor.violations:
        error_msg = "代码安全检查失败:\n" + "\n".join(f"  • {v}" for v in visitor.violations)
        raise CodeSecurityError(error_msg)
