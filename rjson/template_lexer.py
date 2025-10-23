import re
from enum import Enum, auto


class TokenType(Enum):
    STRING = auto()
    DOLLAR = auto()
    IDENTIFIER = auto()
    DOT = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    NUMBER = auto()
    EOF = auto()


class Token:
    def __init__(self, type_, value=None, pos=None):
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self):
        if self.value is None:
            return f"Token({self.type.name})"
        return f"Token({self.type.name}, {self.value!r})"


class TemplateLexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.len = len(text)

    def peek(self, offset=0):
        i = self.pos + offset
        if i >= self.len:
            return None
        return self.text[i]

    def next_char(self):
        if self.pos >= self.len:
            return None
        ch = self.text[self.pos]
        self.pos += 1
        return ch

    def eof(self):
        return self.pos >= self.len

    def read_identifier(self):
        start = self.pos
        while self.peek() and (self.peek().isalnum() or self.peek() in "_$"):
            self.pos += 1
        return self.text[start:self.pos]

    def read_number(self):
        start = self.pos
        while self.peek() and (self.peek().isdigit() or self.peek() in ".eE-+"):
            self.pos += 1
        return self.text[start:self.pos]

    def read_quoted_string(self):
        quote = self.next_char()
        result = []
        while not self.eof():
            ch = self.next_char()
            if ch == "\\":
                nxt = self.next_char()
                if nxt in ('"', "'", "\\"):
                    result.append(nxt)
                elif nxt == "n":
                    result.append("\n")
                else:
                    result.append("\\" + (nxt or ""))
            elif ch == quote:
                break
            else:
                result.append(ch)
        return "".join(result)

    def read_text_until_dollar(self):
        start = self.pos
        while not self.eof() and self.peek() != "$":
            self.pos += 1
        return self.text[start:self.pos]

    def tokenize(self):
        tokens = []

        while not self.eof():
            ch = self.peek()

            # ========== CASE 1: Expression ==========
            if ch == "$":
                self.next_char()
                tokens.append(Token(TokenType.DOLLAR, "$", self.pos - 1))

                ident = self.read_identifier()
                if ident:
                    tokens.append(Token(TokenType.IDENTIFIER, ident, self.pos - len(ident)))

                while not self.eof():
                    nxt = self.peek()
                    if nxt in ' \t\n\r':
                        self.next_char()
                        continue
                    if nxt == ".":
                        tokens.append(Token(TokenType.DOT, ".", self.pos))
                        self.next_char()
                        sub = self.read_identifier()
                        if sub:
                            tokens.append(Token(TokenType.IDENTIFIER, sub, self.pos - len(sub)))
                    elif nxt == "(":
                        tokens.append(Token(TokenType.LPAREN, "(", self.pos))
                        self.next_char()
                    elif nxt == ")":
                        tokens.append(Token(TokenType.RPAREN, ")", self.pos))
                        self.next_char()
                    elif nxt == "[":
                        tokens.append(Token(TokenType.LBRACKET, "[", self.pos))
                        self.next_char()
                    elif nxt == "]":
                        tokens.append(Token(TokenType.RBRACKET, "]", self.pos))
                        self.next_char()
                    elif nxt == ",":
                        tokens.append(Token(TokenType.COMMA, ",", self.pos))
                        self.next_char()
                    elif nxt == "+":
                        tokens.append(Token(TokenType.PLUS, "+", self.pos))
                        self.next_char()
                    elif nxt == "-":
                        tokens.append(Token(TokenType.MINUS, "-", self.pos))
                        self.next_char()
                    elif nxt == "*":
                        tokens.append(Token(TokenType.STAR, "*", self.pos))
                        self.next_char()
                    elif nxt == "/":
                        tokens.append(Token(TokenType.SLASH, "/", self.pos))
                        self.next_char()
                    elif nxt == "$":
                        tokens.append(Token(TokenType.DOLLAR, "$", self.pos))
                        self.next_char()
                        ident = self.read_identifier()
                        if ident:
                            tokens.append(Token(TokenType.IDENTIFIER, ident, self.pos - len(ident)))
                        continue
                    elif nxt.isdigit():
                        num = self.read_number()
                        tokens.append(Token(TokenType.NUMBER, num, self.pos))
                    elif nxt in ('"', "'"):
                        val = self.read_quoted_string()
                        tokens.append(Token(TokenType.STRING, val, self.pos))
                    elif nxt.isalnum() or nxt in "_":
                        ident = self.read_identifier()
                        tokens.append(Token(TokenType.IDENTIFIER, ident, self.pos - len(ident)))
                    else:
                        break

                # 👉 đọc text ngay sau biểu thức (vd: "Hello $user.name!")
                if not self.eof() and self.peek() == '$':
                    pass
                else:
                    text_after = self.read_text_until_dollar()
                    if text_after:
                        tokens.append(Token(TokenType.STRING, text_after, self.pos - len(text_after)))

            # ========== CASE 2: Plain text ==========
            else:
                text_segment = self.read_text_until_dollar()
                if text_segment:
                    tokens.append(Token(TokenType.STRING, text_segment, self.pos - len(text_segment)))

        tokens.append(Token(TokenType.EOF, None, self.pos))
        return tokens


# ------- quick test -------
if __name__ == "__main__":
    lexer = TemplateLexer("Hello $user.name, score $random(1,100)!")
    print(lexer.tokenize())
