"""Small dimensional algebra over explicit scalar Python expressions; never eval."""
import ast


def _normalized(dimensions):
    return {key: value for key, value in dimensions.items() if value}


def expression_dimensions(expression: str, symbols: dict) -> dict:
    def visit(node):
        if isinstance(node, ast.Name):
            if node.id not in symbols:
                raise ValueError(f"Unknown dimensional symbol: {node.id}")
            return _normalized(symbols[node.id])
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            return {}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return visit(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                if left != right:
                    raise ValueError("Dimensional mismatch between additive terms")
                return left
            if isinstance(node.op, (ast.Mult, ast.Div)):
                sign = 1 if isinstance(node.op, ast.Mult) else -1
                return _normalized({key: left.get(key, 0) + sign * right.get(key, 0) for key in left.keys() | right.keys()})
            if isinstance(node.op, ast.Pow):
                if not isinstance(node.right, ast.Constant) or type(node.right.value) is not int:
                    raise ValueError("Dimensional exponents must be explicit integers")
                return _normalized({key: value * node.right.value for key, value in left.items()})
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1 and not node.keywords:
            dimensions = visit(node.args[0])
            if node.func.id in {"abs", "mean", "sum"}:
                return dimensions
            if node.func.id in {"exp", "log", "sin", "cos", "tan"}:
                if dimensions:
                    raise ValueError("Transcendental function requires dimensionless input")
                return {}
            if node.func.id == "sqrt":
                if any(value % 2 for value in dimensions.values()):
                    raise ValueError("Fractional dimensions need an explicit supported reformulation")
                return _normalized({key: value // 2 for key, value in dimensions.items()})
        raise ValueError("Unsupported dimensional expression; supply a reviewed scalar reformulation")
    try:
        return visit(ast.parse(expression, mode="eval").body)
    except SyntaxError as exc:
        raise ValueError("Dimension checks require scalar Python expressions") from exc


def verify_formula_units(spec: dict, symbols: dict):
    if set(spec["variables"]) - symbols.keys():
        raise ValueError("Pinned dimensional registry does not cover model variables")
    for formula in spec["formulae"]:
        parts = formula["expression"].split("=")
        if len(parts) != 2:
            raise ValueError("Dimensional formula must contain one explicit equality")
        left = expression_dimensions(parts[0].strip(), symbols)
        right = expression_dimensions(parts[1].strip(), symbols)
        if left != right or left != _normalized(symbols[formula["output_symbol"]]):
            raise ValueError(f"Formula unit mismatch: {formula['formula_id']}")
