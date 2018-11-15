
import re
import sys

import ParseError

import EndToken
import DoToken
import ElseToken
import BreakToken
import ContinueToken
import ReturnToken
import IfToken
import ElifToken
import WhileToken
import MethodToken
import IncludeToken
import InherintToken
import ForToken
import FunctionToken
import TextToken
import PlaceholderToken
import StatementToken
import FlowControlToken

import Template
import IfNode
import ForNode
import DoWhileNode

STATEMENT_PARSERS = {
    "end": EndToken.EndToken,
    "do": DoToken.DoToken,
    "else": ElseToken.ElseToken,
    "break": BreakToken.BreakToken,
    "continue": ContinueToken.ContinueToken,
    "return": ReturnToken.ReturnToken,
    "if": IfToken.IfToken,
    "elif": ElifToken.ElifToken,
    "while": WhileToken.WhileToken,
    "method": MethodToken.MethodToken,
    "include": IncludeToken.IncludeToken,
    "inherint": InherintToken.InherintToken,
    "for": ForToken.ForToken,
    "function": FunctionToken.FunctionToken,
}
def parseToken(source):
    if source.startswith("${"):
        return PlaceholderToken.PlaceholderToken(source)

    elif source.startswith("##"):
        return StatementToken.StatementToken(source)

    elif source.startswith("#"):
        token_string = str((source + 1).getSimpleToken())
        try:
            statement_parse_function = STATEMENT_PARSERS[token_string]
        except KeyError:
            return Text(source[:source.start + 1])

        return statement_parse_function(source)

    else:
        return TextToken.TextToken(source[:source.start + 1])

START_TOKEN_RE = re.compile("[$#]")
def tokenize(source):
    """
    >>> from SourceFile import SourceFile

    >>> list(tokenize(SourceFile("", "foo ${bar} baz")))
    ['foo ', ${bar}, ' baz']

    >>> list(tokenize(SourceFile("", "foo\\n#if zap == 3\\nzip\\n#end\\nbaz")))
    ['foo\\n', <if zap == 3>, '\\nzip\\n', <end>, '\\nbaz']

    >>> list(tokenize(SourceFile("", "foo\\n#while zap == 3\\nzip\\n#end\\nbaz")))
    ['foo\\n', <while zap == 3>, '\\nzip\\n', <end>, '\\nbaz']

    >>> list(tokenize(SourceFile("", "foo\\n#for zap in 3 + 5\\nzip\\n#end\\nbaz")))
    ['foo\\n', <for zap in 3 + 5>, '\\nzip\\n', <end>, '\\nbaz']

    >>> list(tokenize(SourceFile("", "\\tfoo\\r\\n## a = 5\\r\\nzip\\r\\n#end\\r\\nbaz")))
    ['\\tfoo\\r\\n', <statement a = 5>, '\\r\\nzip\\r\\n', <end>, '\\r\\nbaz']

    """
    while True:
        match = START_TOKEN_RE.search(source.text, source.start)
        if match:
            token = TextToken.TextToken(source[:match.start(0)])
            yield token
            source = token.getRest()

            token = parseToken(source)
            yield token
            source = token.getRest()

        else:
            yield TextToken.TextToken(source[:])
            break

def parse(source):
    """
    >>> from SourceFile import SourceFile
    >>> from RenderContext import RenderContext

    >>> parse(SourceFile("", "foo ${bar} baz"))
    ['foo ', ${bar}, ' baz']

    >>> parse(SourceFile("", "foo\\n#if zap == 3\\nzip\\n#end\\nbaz"))
    ['foo\\n', <if zap == 3: ['\\nzip\\n']>, '\\nbaz']

    >>> parse(SourceFile("", "foo\\n#if zap == 3\\nzip\\n#else\\nbar\\n#end\\nbaz"))
    ['foo\\n', <if zap == 3: ['\\nzip\\n'] else ['\\nbar\\n']>, '\\nbaz']

    >>> parse(SourceFile("", "foo\\n#if zap == 3\\nzip\\n#elif zap > 4\\ntip\\n#else\\nbar\\n#end\\nbaz"))
    ['foo\\n', <if zap == 3: ['\\nzip\\n'] elif zap > 4: ['\\ntip\\n'] else ['\\nbar\\n']>, '\\nbaz']

    >>> parse(SourceFile("", "foo\\n#while zap == 3\\nzip\\n#end\\nbaz"))
    ['foo\\n', <while zap == 3: ['\\nzip\\n']>, '\\nbaz']

    >>> parse(SourceFile("", "foo\\n#do\\nzip\\n#while zap == 3\\nbaz"))
    ['foo\\n', <dowhile zap == 3: ['\\nzip\\n']>, '\\nbaz']

    >>> parse(SourceFile("", "foo\\n#for zap in 3 + 5\\nzip\\n#end\\nbaz"))
    ['foo\\n', <for zap in 3 + 5: ['\\nzip\\n']>, '\\nbaz']

    >>> parse(SourceFile("", "foo\\n#for zap in 3 + 5\\nzip\\n#else\\nbar\\n#end\\nbaz"))
    ['foo\\n', <for zap in 3 + 5: ['\\nzip\\n'] else ['\\nbar\\n']>, '\\nbaz']

    >>> parse(SourceFile("", "foo\\n#function zap(a, b)\\nzip\\n#end\\nbaz"))
    ['foo\\n', <function zap(a, b): ['\\nzip\\n']>, '\\nbaz']

    >>> parse(SourceFile("", "foo\\n#method zap\\nzip\\n#end\\nbaz"))
    ['foo\\n', <method zap: ['\\nzip\\n']>, '\\nbaz']

    >>> parse(SourceFile("", "foo\\n## a = 5\\nbar\\n"))
    ['foo\\n', <statement a = 5>, '\\nbar\\n']

    >>> template = parse(SourceFile("test.vc"))
    >>> context = template.makeRenderContext()
    >>> template.render(context)
    >>> str(context)

    """
    token_stack = [Template.Template()]
    for token in tokenize(source):
        if not token_stack:
            raise ParseError.ParseError(token.source, "Unbalanced, too many, #end statement.")

        top = token_stack[-1]

        if isinstance(token, EndToken.EndToken):
            if len(token_stack) < 2:
                raise ParseError.ParseError(token.source, "Unbalanced, too many, #end statement.")

            token_stack.pop()

        elif isinstance(token, WhileToken.WhileToken):
            if isinstance(top, DoWhileNode.DoWhileNode):
                top.appendWhile(token.expression)
                token_stack.pop()

            else:
                ast_node = token.getNode()
                top.append(ast_node)
                token_stack.append(ast_node)

        elif isinstance(token, FunctionToken.FunctionToken) or isinstance(token, MethodToken.MethodToken):
            if not isinstance(top, Template.Template):
                raise ParseError.ParseError(token.source, "#function and #method may only be instantiated at top level of a file.")

            ast_node = token.getNode()
            top.append(ast_node)
            token_stack.append(ast_node)

        elif isinstance(token, FlowControlToken.FlowControlToken):
            ast_node = token.getNode()
            top.append(ast_node)
            token_stack.append(ast_node)

        elif isinstance(token, ElifToken.ElifToken):
            if not isinstance(top, IfNode.IfNode):
                raise ParseError.ParseError(token.source, "Unexpected #elif statement.")

            top.appendElif(token.expression)

        elif isinstance(token, ElseToken.ElseToken):
            if not isinstance(top, IfNode.IfNode) and not isinstance(top, ForNode.ForNode):
                raise ParseError.ParseError(token.source, "Unexpected #else statement.")

            top.appendElse()

        elif isinstance(token, IncludeToken.IncludeToken) or isinstance(token, InherintToken.InherintToken):
            if not isinstance(top, Template.Template):
                raise ParseError.ParseError(token.source, "#include and #inherint may only be instantiated at top level of a file.")

            top.append(token.getNode())

        else:
            top.append(token.getNode())

    if not token_stack:
        raise ParseError.ParseError(token.source, "Unbalanced, too many, #end statement.")
    elif len(token_stack) > 1:
        raise ParseError.ParseError(token.source, "Unbalanced, too few, #end statement.")

    template = token_stack[-1]
    template.postProcess()
    return template




if __name__ == "__main__":
    import doctest
    doctest.testmod()
