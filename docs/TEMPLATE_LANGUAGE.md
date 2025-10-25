# RJSON Template Language — Tài liệu (Tiếng Việt)

Tài liệu này mô tả toàn bộ hệ thống template hiện có trong dự án `rjson`:
- Cách lexer (`TemplateLexer`) tách chuỗi template thành token.
- Cấu trúc ngữ pháp và các nút AST do `TemplateParser` tạo ra.
- Ngữ nghĩa khi chạy/evaluate AST trong `TemplateEvaluator`.
- Hành vi runtime trong `TemplateRuntime` (bao gồm `_repeat`, `_set`, và rendering của dict/list/str).

Tài liệu viết bằng tiếng Việt và có ví dụ sử dụng.

## 1. Tổng quan

Một template là một chuỗi văn bản có thể chứa các biểu thức bắt đầu bằng ký tự `$`. Mỗi biểu thức được token hóa, phân tích cú pháp thành AST và được đánh giá với một `context` và một bảng `functions` (helper functions) do người dùng cung cấp.

Luồng xử lý chung (ở `TemplateRuntime`):
1. Tokenize: `TemplateLexer.tokenize()`
2. Parse: `TemplateParser(tokens).parse_template()`
3. Evaluate: `TemplateEvaluator(context, functions).evaluate(ast)`

`TemplateRuntime.render()` chấp nhận:
- dict: sẽ xử lý _repeat và _set, trả về dict mới.
- list: render từng phần tử.
- str: nếu chứa `$` thì được tokenized/parsed/evaluated.


## 2. Lexer (`rjson/template_lexer.py`)

Mục đích: tách chuỗi template thành các token để parser tiêu thụ.

Hai chế độ hoạt động (ý tưởng):
- Plain text (chữ thường, không bắt đầu bằng `$`) — được trả về dưới dạng token `STRING`.
- Expression (bắt đầu bằng `$`) — tokenizer sẽ tạo token `DOLLAR` sau đó các token biểu thức như `IDENTIFIER`, `LPAREN`, `RPAREN`, `LBRACKET`, `RBRACKET`, `COMMA`, các toán tử `+ - * /`, các so sánh `==, !=, >, <, >=, <=` và token `NUMBER`, `STRING` (chuỗi có dấu nháy) cùng `QUESTION` (`?`) và `COLON` (`:`) cho toán tử ternary.

Các token chính (tên token trong mã):
- STRING: mảnh văn bản (plain text) không phải biểu thức.
- DOLLAR: ký tự `$` bắt đầu biểu thức.
- IDENTIFIER: tên biến hoặc tên hàm, cho phép chữ/ số/ `_` và `$` (trong các tên phụ trợ như `$_set`).
- DOT, LBRACKET, RBRACKET, LPAREN, RPAREN, COMMA: dấu câu/accessor.
- PLUS, MINUS, STAR, SLASH: toán tử số học.
- EQ, NE, GT, LT, GE, LE: toán tử so sánh.
- NUMBER: số nguyên/float.
- STRING: literal chuỗi (các nội dung trong `"` hoặc `'`), hỗ trợ escape `\"`, `\'`, `\\`, `\n`.
- QUESTION (`?`) và COLON (`:`): dành cho toán tử ternary.
- EOF: kết thúc input.

Lưu ý quan trọng:
- Lexer hiện lưu cả mảng `STRING` cho các phần text giữa các biểu thức.
- Khi gặp `$`, lexer thu nhận phần biểu thức tiếp theo và sau đó tiếp tục gộp phần text ngay phía sau biểu thức dưới dạng `STRING`.
- Quoted strings ("..." hay '...') bên trong biểu thức được đọc đầy đủ và trả lại dưới dạng token `STRING` (giá trị đã được unescape).


## 3. Parser (`rjson/template_parser.py`)

Parser chuyển danh sách token thành AST. Các node chính:

- TemplateNode(parts): danh sách các phần — các phần có thể là TextNode hoặc ExpressionNode.
- TextNode(value): mảnh văn bản bất kỳ.
- ExpressionNode(expr): wrapper cho phép biểu thức trả về giá trị.
- VariableNode(name, accessors): tham chiếu biến (ví dụ `$user.name` -> name='user', accessors=[('dot','name')]). Accessors có thể là dot hoặc index (mảng `[...]`).
- FunctionCallNode(name, args, accessors): gọi hàm `$random(1,10)`.
- ArrayLiteralNode(elements): biểu diễn literal mảng `[1, 2, $x]`.
- BinaryOpNode(left, op, right): biểu thức nhị phân (phép +, -, *, /, so sánh).
- TernaryOpNode(condition, true_expr, false_expr): biểu thức điều kiện `cond ? true_expr : false_expr`.

Ngữ pháp chính (tóm tắt):

- template := (STRING | DOLLAR expr_body)* EOF
- expr := DOLLAR expr_body
- expr_body := expression
- expression := ternary
- ternary := comparison ('?' expression ':' ternary)?
  - Ghi chú: thiết kế hiện cho `ternary` phải là right-associative; parser phân tích nhánh true bằng `expression` và nhánh false bằng `ternary` để bảo đảm thứ tự phải phải là A ? B : (C ? D : E).
- comparison := additive ((==|!=|>|<|>=|<=) additive)*
- additive := term ((+|-) term)*
- term := factor ((*|/) factor)*
- factor := DOLLAR expr_body | IDENTIFIER expr_tail | NUMBER | STRING | '(' expression ')' | '[' array_literal ']'
- expr_tail := '(' arg_list? ')' accessors* | accessors*
- accessors := ('.' IDENTIFIER | '[' index_or_expr ']' )*
- arg_list := arg (',' arg)*
- arg := NUMBER | STRING | DOLLAR expr_body | '[' array_literal ']' | IDENTIFIER (bare identifier treated like string/variable depending on context)
- array_literal := '[' (arg (',' arg)*)? ']'
- index_or_expr := NUMBER | IDENTIFIER | DOLLAR expr_body

Các điểm cần lưu ý:
- Bare IDENTIFIER trong `arg` hoặc `index` có thể được coi là `VariableNode` khi ở trong ngữ cảnh index (parser hiện trả `VariableNode` cho identifier trong index).
- Parser hiện cho phép biểu thức ternary ở bất cứ chỗ nào mà `expression` được phép xuất hiện — vì vậy nó hoạt động trong args, mảng, index, `_set`, v.v.

Ví dụ:
- Input: `Hello $user.name, score $random(1,100)!`
  - TemplateNode với các phần: TextNode("Hello "), ExpressionNode(VariableNode('user', accessors=[('dot','name')])), TextNode(', score '), ExpressionNode(FunctionCallNode('random', args=[1, 100])), TextNode('!')

- Ternary: `$score >= 50 ? "pass" : "fail"` => ExpressionNode(TernaryOpNode(BinaryOpNode(VariableNode('score'), '>=', 50), 'pass', 'fail'))


## 4. Evaluator (`rjson/template_evaluator.py`)

`TemplateEvaluator.evaluate(node)` trả về giá trị Python của node. Các điểm chính:

1. Kiểu literal cơ bản (int/float/bool/None và str) được trả nguyên bản.
2. TemplateNode:
   - Nếu node.parts có 1 phần, trả đúng giá trị của phần đó (không ép thành string).
   - Nếu có nhiều phần, nối kết tất cả giá trị các phần thành một chuỗi (string) theo thứ tự.
3. TextNode: trả `node.value`.
4. ExpressionNode: evaluate node.expr.
5. BinaryOpNode:
   - Toán học (+ - * /): cố gắng ép về số (int/float) với helper `coerce_numeric`. Nếu một trong hai là string, toán tử `+` sẽ thực hiện nối chuỗi (concatenation) thay vì phép cộng số.
   - Chia cho 0 sẽ ném `ZeroDivisionError`.
   - So sánh (==, !=, >, <, >=, <=):
     - `==`/`!=` dùng so sánh Python trực tiếp.
     - Toán tử so sánh thứ tự (`>`, `<`, `>=`, `<=`) sẽ thử chuyển hai bên về số (float) nếu có thể; nếu không được, sẽ thử so sánh Python (nếu khả dụng), nếu không so sánh được thì trả `False` (an toàn).
6. TernaryOpNode:
   - `condition` được evaluate theo truthiness kiểu Python (ví dụ: `0`, `''`, `None`, `False` là falsey).
   - Ngắn mạch (short-circuit): chỉ evaluate branch được chọn (true_expr hoặc false_expr).
7. VariableNode:
   - Tên biến base: nếu tên là `_set` thì truy xuất namespace `_set` trong context.
   - Nếu tên có tồn tại trực tiếp trong `context`, dùng giá trị đó.
   - Nếu không, nhưng tồn tại trong `context['_set']`, lấy từ đó — hành vi này giúp `_set` và việc mirror vào context hoạt động như mong muốn.
   - Accessors: với dot (.) truy cập key của dict hoặc attribute của object; với index thì evaluate biểu thức index rồi lấy phần tử.
8. FunctionCallNode:
   - Tìm hàm trong `self.functions` (bảng các helper function đã đăng ký). Nếu không tồn tại sẽ ném `NameError`.
   - Tính toán các args (mỗi arg có thể là node/literal) rồi gọi hàm.
   - Sau khi gọi, tiếp tục áp dụng accessors nếu có (dot/index) lên kết quả hàm.
9. ArrayLiteralNode: trả list mà mỗi phần đã được evaluate.

Lỗi và exception:
- Gọi hàm gây lỗi: bọc vào `RuntimeError` với thông tin args để dễ debug.
- Khi không thể parse/expect token: `SyntaxError` được ném.


## 5. Runtime (`rjson/template_runtime.py`)

`TemplateRuntime` là lớp cao cấp dùng để render toàn bộ template (file/dict/list/str). Các phương thức chính:

- `render(template)`:
  - Nếu `template` là dict: gọi `_render_dict` (xử lý _repeat, _set, etc.).
  - Nếu `template` là list: render từng phần.
  - Nếu `template` là str: nếu chứa `$` thì gọi `_render_string`.
  - Với kiểu khác: trả nguyên bản.
  - Bao bọc toàn bộ bằng try/except để ném `RuntimeError` có kèm template khi có lỗi runtime.

- `_render_string(template_str)`:
  - Nếu không chứa `$`, trả về chuỗi nguyên gốc.
  - Tokenize với `TemplateLexer`, parse với `TemplateParser`, evaluate với `TemplateEvaluator`.

- `_render_dict(d)`:
  - Hỗ trợ `_repeat` để lặp (xuất ra list kết quả của sub-dict), và `_set` namespace để lưu biến tạm (ẩn) xuyên các vòng lặp.
  - Khi gặp key bắt đầu bằng `_set.`: không đưa vào kết quả, mà ghi vào context `_set` (có thể chứa list khi `_repeat` trong value được dùng để xây dựng list ẩn).
  - Khi render sub-dictionaries, `TemplateRuntime` dùng sub-runtime với `local_ctx` copy để tránh rò rỉ side-effects không mong muốn, rồi hợp nhất `_set` từ sub-runtime vào context hiện tại.
  - Kết thúc, `self.context` được cập nhật với `local_ctx` (propagate các biến side-effect như `_set`).

- `_eval_value(value)`:
  - Nếu `value` là chuỗi bắt đầu băng `$` thì render như expression string, nếu không giữ nguyên.


## 6. Ví dụ ngắn

1) Ternary với biến:

```py
from rjson.template_runtime import TemplateRuntime

rt = TemplateRuntime(context={'a': True, 'b': 'X', 'c': 'Y'})
print(rt._render_string('$a ? $b : $c'))  # => 'X'

rt2 = TemplateRuntime(context={'score': 60})
print(rt2._render_string('$score >= 50 ? "pass" : "fail"'))  # => 'pass'
```

2) Dùng trong dict với `_set` và `_repeat` (ví dụ tóm tắt):

```py
template = {
  "_set.items": {
    "_repeat": 3,
    "name": "$random_name()",
    "score": "$random(0,100)"
  },
  "summary": "$len($_set.items)"
}

rt = TemplateRuntime(functions={
  'random': lambda a,b: 42,
  'random_name': lambda: 'Alice',
  'len': lambda x: len(x)
})
print(rt.render(template))
```

Ghi chú: ví dụ ở trên mô phỏng cách `_set` và `_repeat` có thể được dùng để nhặt dữ liệu tạm và dùng lại ở phần khác của template.


## 7. Thêm hàm (functions / addons)

- `TemplateEvaluator` không có helper builtin (nếu dự án của bạn đã di chuyển vào addon pattern). Bảng `functions` được truyền vào runtime/evaluator là nơi chứa các helper.
- Mỗi helper có signature Python bình thường; evaluator truyền các tham số đã evaluate (Python values) vào hàm.
- Nếu bạn muốn tạo addon, export một dict tên->callable và nạp nó vào `TemplateRuntime(..., functions=your_funcs)` hoặc dùng cơ chế addon loader nếu dự án có module `rjson.helpers` để load addon từ file.


## 8. Lưu ý, edge-cases và khuyến cáo

- Ternary: hiện sử dụng `condition ? true_expr : false_expr` (C-style) và chịu truthiness giống Python (`bool(condition)` quyết định). Nếu muốn thay đổi cú pháp (ví dụ Python-style `x if cond else y`) hoặc truthiness, cần cập nhật parser/evaluator.
- Short-circuit: evaluator hiện chỉ thực thi branch được chọn.
- Ép kiểu: arithmetic sẽ cố gắng ép về số nếu có thể; `+` ưu tiên nối chuỗi nếu một nhánh là string.
- Accessor index: khi dùng biểu thức như `$arr[$i]` thì phần trong `[]` phải trả về số nguyên (parser/evaluator sẽ cố cast), nếu không hợp lệ thì trả `None`.
- Errors: parse error sẽ ném `SyntaxError`; lỗi trong hàm người dùng ném `RuntimeError` với thông tin args.


## 9. Muốn mở rộng ngữ pháp/semantics?

Nếu bạn muốn thay đổi/ mở rộng ngữ pháp (ví dụ thêm toán tử logic `&&`/`||`, phép gán trong biểu thức, toán tử null-coalescing `??`, hoặc hỗ trợ Python-style ternary), hãy cho biết chính xác cú pháp và ngữ nghĩa mong muốn:
- Cú pháp mong muốn (ví dụ `a && b` hoặc `a and b`)?
- Precedence so với `+`, `*`, so sánh như thế nào?
- Truthiness rules (Python-like hay strict boolean)?
- Short-circuiting / evaluate-order mong muốn?

Khi bạn xác nhận các lựa chọn đó, tôi sẽ thực hiện thay đổi ở:
- `rjson/template_lexer.py` — thêm token mới
- `rjson/template_parser.py` — thêm rule và tương ứng đảm bảo precedence/associativity
- `rjson/template_evaluator.py` — thực thi semantic mới
- Thêm unit tests để bảo đảm không phá vỡ behavior hiện tại


---

Tôi đã tạo file này ở `docs/TEMPLATE_LANGUAGE.md`. Nếu muốn tôi dịch sang tiếng Anh, tách thành nhiều trang nhỏ (lexer/parser/evaluator/runtime), hoặc thêm bảng token/AST tự động từ mã nguồn — nói cho tôi biết hướng bạn muốn.
