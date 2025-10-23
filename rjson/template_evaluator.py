# template_evaluator.py
import random

class TemplateEvaluator:
    def __init__(self, context=None, functions=None):
        # context: dict chứa biến runtime
        self.context = context or {}
        # functions: dict tên -> callable
        self.functions = functions or {}

    def evaluate(self, node):
        # Nếu node là literal Python type (parser có thể trả int/float/str/list...)
        if isinstance(node, (int, float, bool)) or node is None:
            return node
        if isinstance(node, str):
            # NOTE: đây là trường hợp parser/array literal có thể trả string literal
            return node

        nodename = type(node).__name__

        if nodename == "TemplateNode":
            # nếu chỉ có 1 phần: trả về giá trị nguyên bản của phần đó (không ép thành str)
            if len(node.parts) == 1:
                single = node.parts[0]
                val = self.evaluate(single)
                # nếu giá trị là chuỗi và phần template thực sự là mảng text+expr,
                # caller muốn chuỗi; nhưng ở đây len(parts)==1 -> trả nguyên bản
                return val
            # nhiều phần -> concat thành string
            return "".join(str(self.evaluate(p)) for p in node.parts)

        if nodename == "TextNode":
            return node.value

        if nodename == "ExpressionNode":
            return self.evaluate(node.expr)

        if nodename == "BinaryOpNode":
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            # helper: coerce to numeric when needed
            def coerce_numeric(x):
                if x is None:
                    return 0
                if isinstance(x, (int, float)):
                    return x
                if isinstance(x, str):
                    try:
                        if '.' in x or 'e' in x or 'E' in x:
                            return float(x)
                        return int(x)
                    except Exception:
                        return 0
                try:
                    return float(x)
                except Exception:
                    return 0

            if node.op == "+":
                # if either is string, perform concatenation (keep original semantics)
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                return coerce_numeric(left) + coerce_numeric(right)
            elif node.op == "-":
                return coerce_numeric(left) - coerce_numeric(right)
            elif node.op == "*":
                return coerce_numeric(left) * coerce_numeric(right)
            elif node.op == "/":
                denom = coerce_numeric(right)
                if denom == 0:
                    raise ZeroDivisionError("Division by zero in template expression")
                return coerce_numeric(left) / denom
            else:
                raise ValueError(f"Unknown operator: {node.op}")

        if nodename == "VariableNode":
            return self.eval_var(node)

        if nodename == "FunctionCallNode":
            return self.eval_func(node)

        if nodename == "ArrayLiteralNode":
            # elements có thể là literals hoặc nodes
            return [self.evaluate(e) for e in node.elements]

        # fallback
        raise ValueError(f"Unknown node type: {nodename}")

    # ---------- biến ----------
    def eval_var(self, node):
        # node.name là tên base, node.accessors là list of ('dot', name) or ('index', expr)
        value = None
        # special-case: accessing the _set namespace: '$_set.total_members'
        if node.name == "_set":
            value = self.context.get("_set", {})
        else:
            # prefer direct context key (e.g. $name), then fallback to _set namespace (e.g. $total_members)
            if node.name in self.context:
                value = self.context[node.name]
            elif "_set" in self.context and node.name in self.context["_set"]:
                value = self.context["_set"][node.name]
            else:
                value = None
        for acc_type, acc_val in node.accessors:
            if acc_type == "dot":
                if isinstance(value, dict):
                    value = value.get(acc_val)
                else:
                    value = getattr(value, acc_val, None)
            elif acc_type == "index":
                idx = int(self.evaluate(acc_val))
                try:
                    value = value[idx]
                except Exception:
                    value = None
            else:
                raise ValueError(f"Unknown accessor type: {acc_type}")
        return value

    # ---------- function ----------
    def eval_func(self, node):
        fn = self.functions.get(node.name)
        if fn is None:
            raise NameError(f"Function '{node.name}' is not defined")

        # args có thể là nodes hoặc literals
        args = [self.evaluate(a) for a in node.args]

        # gọi hàm, bọc try để hiện thông báo rõ ràng
        try:
            result = fn(*args)
        except Exception as e:
            raise RuntimeError(f"Error calling function {node.name} with args {args}: {e}")

        # áp dụng accessors nếu có (ví dụ $f(...).prop or $f(...)[0])
        for acc_type, acc_val in node.accessors:
            if acc_type == "dot":
                if isinstance(result, dict):
                    result = result.get(acc_val)
                else:
                    result = getattr(result, acc_val, None)
            elif acc_type == "index":
                idx = self.evaluate(acc_val)
                try:
                    result = result[idx]
                except Exception:
                    result = None

        return result
