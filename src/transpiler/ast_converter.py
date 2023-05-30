import ast
from typing import List

from pycparser import c_ast, parse_file


class CtoPythonVisitor(c_ast.NodeVisitor):
    def __init__(self, c_root: c_ast.Node):
        self.c_root = c_root
        self.imports: List[ast.Import] = []
        self.result = None

    def run(self):
        self.imports = []
        self.result = self.visit(self.c_root)
        if self.imports and hasattr(self.result, "body"):
            for i in reversed(self.imports):
                self.result.body.insert(0, i)
        return self.result

    def visit(self, node: c_ast.Node):
        method_name = "visit_" + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        result = visitor(node)
        return result

    def generic_visit(self, node):
        if node is None:
            return ""
        else:
            print(
                f"Warning: Conversion not implemented for node type: {node.__class__.__name__}"
            )
            return list(self.visit(c) for c_name, c in node.children())

        # raise NotImplementedError(
        #     f"Conversion not implemented for node type: {node.__class__.__name__}"
        # )

    def visit_FileAST(self, node: c_ast.FileAST):
        body = [self.visit(child) for child in node.ext]
        return ast.Module(body=body)

    def visit_FuncDef(self, node: c_ast.FuncDef):
        name = node.decl.name
        args = self.visit(node.decl.type.args)
        body = [self.visit(child) for child in node.body.block_items]
        return ast.FunctionDef(name=name, args=args, body=body)

    def visit_ParamList(self, node: c_ast.ParamList):
        args = [self.visit(param) for param in node.params]
        return ast.arguments(args=args, defaults=[])

    def visit_Decl(self, node: c_ast.Decl):
        if isinstance(node.type, c_ast.FuncDecl):
            return None

        name = node.name
        match node.type.__class__:
            case c_ast.TypeDecl:
                # Variable declaration
                var_type = self.visit(node.type)
                var_def = ast.AnnAssign(
                    target=ast.Name(id=name, ctx=ast.Store()),
                    annotation=var_type,
                    value=None,
                    simple=1,
                )
                return var_def
            case c_ast.Struct:
                # Struct declaration
                struct_def = self.visit(node.type)
                return struct_def
            case c_ast.Union:
                # Union declaration
                union_def = self.visit(node.type)
                union_def.name = name
                return union_def
            case _:
                raise NotImplementedError(
                    f"Conversion not implemented for declaration type: {node.type.__class__.__name__}"
                )

    def visit_Typedef(self, node):
        name = node.name
        typedef_type = self.visit(node.type)

        # Handle different types of typedefs
        if isinstance(typedef_type, ast.Name):
            # Basic C type
            typedef_def = ast.AnnAssign(
                target=ast.Name(id=name, ctx=ast.Store()),
                annotation=typedef_type,
                value=None,
                simple=1,
            )
        elif isinstance(typedef_type, ast.ClassDef):
            # Struct or Union typedef
            typedef_def = typedef_type
            typedef_def.name = name
        else:
            # Handle other types of typedefs as needed
            raise NotImplementedError(
                f"Conversion not implemented for typedef type: {typedef_type.__class__.__name__}"
            )

        return typedef_def

    def visit_TypeDecl(self, node: c_ast.TypeDecl):
        if isinstance(node.type, c_ast.Struct):
            struct = self.visit(node.type)
            struct.name = node.declname
            return struct
        return ast.Name(id=node.declname, ctx=ast.Param())

    def visit_Struct(self, node: c_ast.Struct):
        struct_name = node.name
        fields = []
        for decl in node.decls:
            field_name = decl.name
            field_type = self.visit(decl.type.type)
            field_def = ast.AnnAssign(
                target=ast.Name(id=field_name, ctx=ast.Store()),
                annotation=field_type,
                value=None,
                simple=1,
            )
            fields.append(field_def)

        class_def = ast.ClassDef(
            name=struct_name,
            bases=[],
            keywords=[],
            body=fields,
            decorator_list=[ast.Name(id="dataclasses.dataclass")],
        )
        self.imports.append(ast.Import(names=[ast.alias(name="dataclasses")]))
        # TODO: add dataclasses import to the self.imports list
        return class_def

    def visit_IdentifierType(self, node):
        type_name = node.names[0]
        type_mapping = {
            "void": ast.Name(id="None", ctx=ast.Load()),
            "char": ast.Name(id="str", ctx=ast.Load()),
            "short": ast.Name(id="int", ctx=ast.Load()),
            "int": ast.Name(id="int", ctx=ast.Load()),
            "long": ast.Name(id="int", ctx=ast.Load()),
            "long long": ast.Name(id="int", ctx=ast.Load()),
            "float": ast.Name(id="float", ctx=ast.Load()),
            "double": ast.Name(id="float", ctx=ast.Load()),
            "long double": ast.Name(id="float", ctx=ast.Load()),
            # Add more type mappings as needed
        }
        return type_mapping.get(type_name, ast.Name(id=type_name, ctx=ast.Load()))

    def visit_Constant(self, node: c_ast.Constant):
        value = node.value
        if isinstance(node.type, c_ast.TypeDecl) and isinstance(
            node.type.type, c_ast.IdentifierType
        ):
            type_names = node.type.type.names
            if "float" in type_names or "double" in type_names:
                return ast.Constant(value=float(value), kind=None)
        return ast.Constant(value=value, kind=None)

    def visit_Assignment(self, node: c_ast.Assignment):
        target = self.visit(node.lvalue)
        value = self.visit(node.rvalue)
        return ast.Assign(targets=[target], value=value)

    def visit_If(self, node: c_ast.If):
        test = self.visit(node.cond)
        body = [self.visit(child) for child in node.iftrue.block_items]
        orelse = (
            [self.visit(child) for child in node.iffalse.block_items]
            if node.iffalse
            else []
        )
        return ast.If(test=test, body=body, orelse=orelse)

    # def visit_FuncDecl(self, node: c_ast.FuncDecl):
    #     return ast.Expr(value=None)

    def visit_PtrDecl(self, node: c_ast.PtrDecl):
        type_node = self.visit(node.type)
        return ast.Subscript(value=type_node, slice=ast.Ellipsis())

    def visit_NoneType(self, node: None):
        return ast.Name(id="None", ctx=ast.Load())

    def visit_StructRef(self, node: c_ast.StructRef):
        field = node.field.name
        value = ast.Attribute(value=self.visit(node.name), attr=field, ctx=ast.Load())
        return value

    def visit_ID(self, node: c_ast.ID):
        return ast.Name(id=node.name, ctx=ast.Load())

    def visit_FuncCall(self, node: c_ast.FuncCall):
        func = self.visit(node.name)
        args = [self.visit(arg) for arg in node.args.exprs]
        return ast.Call(func=func, args=args, keywords=[])

    def visit_UnaryOp(self, node: c_ast.UnaryOp):
        print(f"UnaryOp: {node.op} {node.expr}")
        operand = self.visit(node.expr)
        return ast.Expr(value=None)
        # match node.op:
        #     case "sizeof":
        #         return ast.Call(
        #             func=ast.Name(id="sizeof", ctx=ast.Load()),
        #             args=[self.visit(node.expr)],
        #             keywords=[],
        #         )
        #     case "p++":
        #         return ast.Add()
        #         return ast.UnaryOp(target=self.visit(node.expr))
        #     case "p--":
        #         return ast.Decr(target=self.visit(node.expr))
        #     case _:
        #         operand = self.visit(node.expr)

        # if node.op == "sizeof":
        #     # Always parenthesize the argument of sizeof since it can be
        #     # a name.
        #     return "sizeof(%s)" % self.visit(n.expr)
        # else:
        #     operand = self._parenthesize_unless_simple(n.expr)
        #     if node.op == "p++":
        #         return "%s++" % operand
        #     elif node.op == "p--":
        #         return "%s--" % operand
        #     else:
        #         return "%s%s" % (node.op, operand)
        #
        # # op = self.visit(node.op)
        #
        # if isinstance(node.op, c_ast.UnaryOp) and node.op.op == "&":
        #     return operand  # Skip address-of (&) operator
        # return ast.UnaryOp(op=op, operand=operand)
