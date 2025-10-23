import copy
import json
from .template_parser import TemplateParser
from .template_evaluator import TemplateEvaluator
from .template_lexer import TemplateLexer

class TemplateRuntime:
    def __init__(self, context=None, functions=None):
        self.context = context or {}
        self.functions = functions or {}

    def render(self, template):
        try:
            if isinstance(template, dict):
                return self._render_dict(template)
            elif isinstance(template, list):
                return [self.render(item) for item in template]
            elif isinstance(template, str):
                return self._render_string(template)
            else:
                return template
        except Exception as e:
            raise RuntimeError(f"Error during rendering template: {json.dumps(template, indent=2)}\n{e}") from e

    def _render_string(self, template_str):
        # Nếu không chứa dấu $, coi như chuỗi thường
        if "$" not in template_str:
            return template_str

        # 1️⃣ Tokenize
        lexer = TemplateLexer(template_str)
        tokens = lexer.tokenize()

        # 2️⃣ Parse
        parser = TemplateParser(tokens)
        ast = parser.parse_template()

        # 3️⃣ Evaluate
        evaluator = TemplateEvaluator(self.context, self.functions)
        return evaluator.evaluate(ast)


    def _render_dict(self, d):
        result = {}
        # Tạo bản sao context cục bộ để không ảnh hưởng toàn cục trong vòng lặp
        local_ctx = copy.deepcopy(self.context)

        # Xử lý _repeat nếu có
        repeat_count = d.get("_repeat")
        if repeat_count is not None:
            # evaluate using local context copy so expressions can refer to previously-set keys
            repeat_count = int(TemplateRuntime(local_ctx, self.functions)._eval_value(repeat_count))
            items = []
            for i in range(repeat_count):
                # Tạo context tạm cho từng lần lặp
                loop_ctx = copy.deepcopy(local_ctx)
                loop_ctx["_index"] = i
                loop_ctx["_repeat"] = repeat_count

                sub_runtime = TemplateRuntime(loop_ctx, self.functions)
                # Loại bỏ key _repeat để render phần còn lại
                sub_dict = {k: v for k, v in d.items() if not k.startswith("_repeat")}
                item = sub_runtime._render_dict(sub_dict)
                # propagate _set context back to parent for next iterations
                if "_set" in sub_runtime.context:
                    local_ctx["_set"] = sub_runtime.context["_set"]
                    for k, v in sub_runtime.context["_set"].items():
                        local_ctx[k] = v
                items.append(item)
            return items

        # Xử lý từng key-value
        for key, value in d.items():
            # Bỏ qua _repeat
            if key.startswith("_repeat"):
                continue

            # Nếu là _set.<var>, chỉ lưu vào context, KHÔNG in ra kết quả
            if key.startswith("_set."):
                var_name = key.split(".", 1)[1]
                # Nếu value là dict có _repeat, xử lý như một danh sách ẩn
                if isinstance(value, dict) and value.get("_repeat") is not None:
                    # compute repeat count using current local_ctx
                    repeat_count = int(TemplateRuntime(local_ctx, self.functions)._eval_value(value.get("_repeat")))
                    items = []
                    for i in range(repeat_count):
                        loop_ctx = copy.deepcopy(local_ctx)
                        loop_ctx["_index"] = i
                        loop_ctx["_repeat"] = repeat_count
                        # expose previously built items under var_name so expressions can refer to them
                        loop_ctx[var_name] = list(items)

                        sub_rt = TemplateRuntime(loop_ctx, self.functions)
                        sub_dict = {k: v for k, v in value.items() if not k.startswith("_repeat")}
                        item = sub_rt._render_dict(sub_dict)

                        # merge any _set entries from sub-runtime
                        if "_set" in sub_rt.context:
                            if "_set" not in local_ctx:
                                local_ctx["_set"] = {}
                            for k, v in sub_rt.context["_set"].items():
                                local_ctx["_set"][k] = v
                                local_ctx[k] = v

                        items.append(item)
                        # update local context to include items built so far
                        local_ctx[var_name] = list(items)

                    # store result in _set namespace and in direct context but do not add to visible result
                    if "_set" not in local_ctx:
                        local_ctx["_set"] = {}
                    local_ctx["_set"][var_name] = items
                    local_ctx[var_name] = items
                    continue

                # Use a sub-runtime so nested _set assignments inside 'value' can run
                sub_rt = TemplateRuntime(local_ctx, self.functions)
                evaluated_value = sub_rt.render(value)

                # Merge any _set entries produced by the sub-runtime back into our local_ctx
                if "_set" in sub_rt.context:
                    if "_set" not in local_ctx:
                        local_ctx["_set"] = {}
                    for k, v in sub_rt.context["_set"].items():
                        local_ctx["_set"][k] = v
                        local_ctx[k] = v

                # Ghi vào context thường và namespace _set for this var_name
                local_ctx[var_name] = evaluated_value
                if "_set" not in local_ctx:
                    local_ctx["_set"] = {}
                local_ctx["_set"][var_name] = evaluated_value

                # Không đưa vào result (ẩn)
                continue

            # Nếu value là dict có _repeat, xử lý theo từng lần lặp và expose các phần tử đã dựng
            if isinstance(value, dict) and value.get("_repeat") is not None:
                # compute repeat count using current local_ctx
                repeat_count = int(TemplateRuntime(local_ctx, self.functions)._eval_value(value.get("_repeat")))
                items = []
                for i in range(repeat_count):
                    loop_ctx = copy.deepcopy(local_ctx)
                    loop_ctx["_index"] = i
                    loop_ctx["_repeat"] = repeat_count
                    # expose previously built items under the key so expressions can refer to them
                    loop_ctx[key] = list(items)

                    sub_rt = TemplateRuntime(loop_ctx, self.functions)
                    # render the body of the repeated dict (excluding _repeat)
                    sub_dict = {k: v for k, v in value.items() if not k.startswith("_repeat")}
                    item = sub_rt._render_dict(sub_dict)

                    # merge any _set entries from sub-runtime
                    if "_set" in sub_rt.context:
                        if "_set" not in local_ctx:
                            local_ctx["_set"] = {}
                        for k, v in sub_rt.context["_set"].items():
                            local_ctx["_set"][k] = v
                            local_ctx[k] = v

                    items.append(item)
                    # update local context to include items built so far
                    local_ctx[key] = list(items)

                result[key] = items
                local_ctx[key] = items
                # also mirror visible repeated list into _set so behavior matches `_set.<name>`
                if "_set" not in local_ctx:
                    local_ctx["_set"] = {}
                local_ctx["_set"][key] = list(items)
            else:
                # Các key bình thường: render using a sub-runtime so any _set side-effects are captured
                sub_rt = TemplateRuntime(local_ctx, self.functions)
                evaluated_value = sub_rt.render(value)

                # Merge any _set entries produced by the sub-runtime
                if "_set" in sub_rt.context:
                    if "_set" not in local_ctx:
                        local_ctx["_set"] = {}
                    for k, v in sub_rt.context["_set"].items():
                        local_ctx["_set"][k] = v
                        local_ctx[k] = v

                result[key] = evaluated_value
                local_ctx[key] = evaluated_value

        # propagate context back to self
        self.context = local_ctx
        return result

    def _eval_value(self, value):
        """Evaluate string expression if it starts with $, otherwise return as-is"""
        if isinstance(value, str) and value.startswith("$"):
            return self._render_string(value)
        return value
