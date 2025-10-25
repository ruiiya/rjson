from .template_lexer import TemplateLexer, TokenType

# ===== AST Nodes =====
class Node: pass

class TextNode(Node):
    def __init__(self, value): self.value = value
    def __repr__(self): return f"TextNode({self.value!r})"

class VariableNode(Node):
    def __init__(self, name, accessors=None):
        self.name = name
        self.accessors = accessors or []  # list of ('dot', name) or ('index', expr)
    def __repr__(self): return f"VariableNode({self.name!r}, accessors={self.accessors})"

class FunctionCallNode(Node):
    def __init__(self, name, args=None, accessors=None):
        self.name = name
        self.args = args or []
        self.accessors = accessors or []
    def __repr__(self): return f"FunctionCallNode({self.name!r}, args={self.args}, accessors={self.accessors})"

class ArrayLiteralNode(Node):
    def __init__(self, elements): self.elements = elements
    def __repr__(self): return f"ArrayLiteralNode({self.elements})"

class ExpressionNode(Node):
    def __init__(self, expr): self.expr = expr
    def __repr__(self): return f"ExpressionNode({self.expr})"

class BinaryOpNode(Node):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
    def __repr__(self): return f"BinaryOpNode({self.left}, {self.op!r}, {self.right})"

class TernaryOpNode(Node):
    def __init__(self, condition, true_expr, false_expr):
        self.condition = condition
        self.true_expr = true_expr
        self.false_expr = false_expr
    def __repr__(self):
        return f"TernaryOpNode({self.condition}, {self.true_expr}, {self.false_expr})"

class TemplateNode(Node):
    def __init__(self, parts): self.parts = parts
    def __repr__(self): return f"TemplateNode({self.parts})"

class TemplateParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current = tokens[0]

        # --- tiện ích di chuyển ---
    def advance(self):
        """Di chuyển đến token kế tiếp"""
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
            self.current = self.tokens[self.pos]
        return self.current

    def expect(self, token_type):
        """Kiểm tra token hiện tại có đúng loại mong đợi không"""
        if self.current.type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {self.current.type}")
        value = self.current.value
        self.advance()
        return value

    # --- utility ---
    def peek(self): return self.current

    def next(self):
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
            self.current = self.tokens[self.pos]
        return self.current

    def match(self, *types):
        if self.current.type in types:
            tok = self.current
            self.next()
            return tok
        return None

    def expect(self, type_):
        if self.current.type != type_:
            raise SyntaxError(f"Expected {type_.name}, got {self.current.type.name}")
        val = self.current
        self.next()
        return val

    # --- entry ---
    def parse_template(self):
        parts = []
        while self.current.type != TokenType.EOF:
            if self.current.type == TokenType.STRING:
                parts.append(TextNode(self.current.value))
                self.next()
            elif self.current.type == TokenType.DOLLAR:
                parts.append(self.parse_expr())
            else:
                # bỏ qua ký tự lạ hoặc lỗi
                self.next()
        self.expect(TokenType.EOF)
        return TemplateNode(parts)

    # --- expr ::= '$' <expr_body>
    def parse_expr(self):
        self.expect(TokenType.DOLLAR)
        expr_body = self.parse_expr_body()
        return ExpressionNode(expr_body)

    # --- <expr_body> ::= <expression>
    def parse_expr_body(self):
        return self.parse_expression()

    # --- <expression> ::= <term> ((+|-) <term>)*
    # Top-level expression parser (includes comparisons)
    def parse_expression(self):
        return self.parse_ternary()
    
    # --- <ternary> ::= <comparison> ('?' <comparison> ':' <comparison>)?
    def parse_ternary(self):
        condition = self.parse_comparison()
        if self.match(TokenType.QUESTION):
            true_expr = self.parse_expression()
            self.expect(TokenType.COLON)
            false_expr = self.parse_expression()
            return TernaryOpNode(condition, true_expr, false_expr)
        return condition

    # --- <comparison> ::= <additive> ((==|!=|>|<|>=|<=) <additive>)*
    def parse_comparison(self):
        left = self.parse_additive()
        while self.current.type in (TokenType.EQ, TokenType.NE, TokenType.GT, TokenType.LT, TokenType.GE, TokenType.LE):
            op = self.current.value
            self.advance()
            right = self.parse_additive()
            left = BinaryOpNode(left, op, right)
        return left

    # --- <additive> ::= <term> ((+|-) <term>)*
    def parse_additive(self):
        left = self.parse_term()
        while self.current.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current.value
            self.advance()
            right = self.parse_term()
            left = BinaryOpNode(left, op, right)
        return left

    # --- <term> ::= <factor> ((*|/) <factor>)*
    def parse_term(self):
        left = self.parse_factor()
        while self.current.type in (TokenType.STAR, TokenType.SLASH):
            op = self.current.value
            self.advance()
            right = self.parse_factor()
            left = BinaryOpNode(left, op, right)
        return left

    # --- <factor> ::= <identifier> <expr_tail> | NUMBER | STRING | '(' <expression> ')' | '[' <array_literal> ']'
    def parse_factor(self):
        # allow nested expressions starting with $ (e.g. function args like $len($teams))
        if self.current.type == TokenType.DOLLAR:
            return self.parse_expr()
        # Read current token without double-consuming (use self.current and self.next())
        if self.current.type == TokenType.IDENTIFIER:
            ident = self.current.value
            self.next()
            return self.parse_expr_tail(ident)
        elif self.current.type == TokenType.NUMBER:
            val = self.current.value
            self.next()
            return float(val) if '.' in val else int(val)
        elif self.current.type == TokenType.STRING:
            val = self.current.value
            self.next()
            return val
        elif self.current.type == TokenType.LPAREN:
            self.next()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        elif self.current.type == TokenType.LBRACKET:
            return self.parse_array_literal()
        else:
            raise ValueError(f"Unexpected token: {self.current}")

    # --- <expr_tail> ::= '(' <arg_list>? ')' <accessors>* | <accessors>*
    def parse_expr_tail(self, ident):
        if self.current.type == TokenType.LPAREN:
            args = self.parse_arg_list()
            accessors = self.parse_accessors()
            return FunctionCallNode(ident, args, accessors)
        else:
            accessors = self.parse_accessors()
            return VariableNode(ident, accessors)

    # --- <accessors> ::= ( '.' <identifier> )* | ( '[' <index_or_expr> ']' )*
    def parse_accessors(self):
        accessors = []
        while True:
            if self.match(TokenType.DOT):
                name = self.expect(TokenType.IDENTIFIER).value
                accessors.append(('dot', name))
            elif self.match(TokenType.LBRACKET):
                index_expr = self.parse_index_or_expr()
                self.expect(TokenType.RBRACKET)
                accessors.append(('index', index_expr))
            else:
                break
        return accessors

    # --- <arg_list> ::= <arg> (',' <arg>)* )
    def parse_arg_list(self):
        args = []
        self.expect(TokenType.LPAREN)
        if self.current.type != TokenType.RPAREN:
            while True:
                args.append(self.parse_arg())
                if not self.match(TokenType.COMMA):
                    break
        self.expect(TokenType.RPAREN)
        return args

    # --- <arg> ::= NUMBER | STRING_LITERAL | <expr> | <array_literal> | IDENTIFIER
    def parse_arg(self):
        if self.current.type == TokenType.NUMBER:
            raw = self.current.value
            self.advance()
            # convert to number
            if '.' in raw or 'e' in raw or 'E' in raw:
                return float(raw)
            else:
                return int(raw)
        elif self.current.type == TokenType.STRING:
            val = self.current.value
            self.next()
            return val
        elif self.current.type == TokenType.DOLLAR:
            return self.parse_expr()
        elif self.current.type == TokenType.LBRACKET:
            return self.parse_array_literal()
        elif self.current.type == TokenType.IDENTIFIER:
            val = self.current.value
            self.next()
            return val
        else:
            raise SyntaxError(f"Unexpected token in arg: {self.current}")

    # --- <array_literal> ::= '[' ( <arg> (',' <arg>)* )? ']'
    def parse_array_literal(self):
        elements = []
        self.expect(TokenType.LBRACKET)
        if self.current.type != TokenType.RBRACKET:
            while True:
                elements.append(self.parse_arg())
                if not self.match(TokenType.COMMA):
                    break
        self.expect(TokenType.RBRACKET)
        return ArrayLiteralNode(elements)

    # --- <index_or_expr> ::= NUMBER | '$' | IDENTIFIER | <expr>
    def parse_index_or_expr(self):
        if self.current.type == TokenType.NUMBER:
            raw = self.current.value
            self.next()
            # convert to number
            if '.' in raw or 'e' in raw or 'E' in raw:
                return float(raw)
            else:
                return int(raw)
        elif self.current.type == TokenType.IDENTIFIER:
            name = self.current.value
            self.next()
            # treat bare identifier inside index as a variable reference
            return VariableNode(name)
        elif self.current.type == TokenType.DOLLAR:
            return self.parse_expr()
        else:
            raise SyntaxError(f"Unexpected token in index: {self.current}")

if __name__ == "__main__":
    text = "Hello $user.name! Your lucky numbers: $random([1,2,$x])"
    lexer = TemplateLexer(text)
    tokens = lexer.tokenize()

    from pprint import pprint
    pprint(tokens)

    parser = TemplateParser(tokens)
    ast = parser.parse_template()
    print("\nAST:")
    pprint(ast)
