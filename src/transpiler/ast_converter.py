import ast

from pycparser import c_ast, parse_file


class CtoPythonVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.result = None

    def visit(self, node: c_ast.Node):
        method_name = "visit_" + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise NotImplementedError(
            f"Conversion not implemented for node type: {node.__class__.__name__}"
        )

    def visit_FileAST(self, node):
        body = [self.visit(child) for child in node.ext]
        self.result = ast.Module(body=body)

    def visit_FuncDef(self, node):
        name = node.decl.name
        args = self.visit(node.decl.type.args)
        body = [self.visit(child) for child in node.body.block_items]
        self.result = ast.FunctionDef(name=name, args=args, body=body)

    def visit_ParamList(self, node):
        args = [self.visit(param) for param in node.params]
        return ast.arguments(args=args, defaults=[])

    def visit_Decl(self, node):
        name = node.name
        type_node = self.visit(node.type)
        return ast.arg(arg=name, annotation=type_node)

    def visit_TypeDecl(self, node):
        return ast.Name(id=node.declname, ctx=ast.Param())

    def visit_Constant(self, node):
        value = node.value
        if isinstance(node.type, c_ast.Float):
            return ast.Constant(value=float(value), kind=None)
        elif isinstance(node.type, c_ast.Int):
            return ast.Constant(value=int(value), kind=None)
        else:
            return ast.Constant(value=value, kind=None)

    def visit_Assignment(self, node):
        target = self.visit(node.lvalue)
        value = self.visit(node.rvalue)
        return ast.Assign(targets=[target], value=value)

    def visit_If(self, node):
        test = self.visit(node.cond)
        body = [self.visit(child) for child in node.iftrue.block_items]
        orelse = (
            [self.visit(child) for child in node.iffalse.block_items]
            if node.iffalse
            else []
        )
        return ast.If(test=test, body=body, orelse=orelse)

    def visit_Typedef(self, node):
        name = node.name
        type_node = self.visit(node.type)
        return ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())], value=type_node)

    def visit_FuncDecl(self, node):
        args = self.visit(node.args)
        return ast.arguments(args=args, defaults=[])
