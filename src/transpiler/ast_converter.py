import ast
from typing import List

from pycparser import c_ast


class CtoPythonVisitor(c_ast.NodeVisitor):
    def __init__(self, c_root: c_ast.Node):
        self.c_root = c_root
        self.imports: List[ast.Import] = []
        self.result = None
        self.parents = []
        self.parents_and_self = []

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
        self.parents = self.parents_and_self[:]
        self.parents_and_self.append(node)
        result = visitor(node)
        if self.parents:
            self.parents.pop()
        self.parents_and_self.pop()
        return result

    def generic_visit(self, node):
        if node is None:
            return ast.Expr(None)
        else:
            # print(
            #     f"Warning: Conversion not implemented for node type: {node.__class__.__name__}"
            # )
            # return list(self.visit(c) for c_name, c in node.children())

            raise NotImplementedError(
                f"Conversion not implemented for node type: {node.__class__.__name__}"
            )

    def visit_FileAST(self, node: c_ast.FileAST):
        body = [self.visit(child) for child in node.ext]
        return ast.Module(body=body)

    def visit_FuncDef(self, node: c_ast.FuncDef):
        name = node.decl.name
        args = []
        if node.decl.type.args:
            for param in node.decl.type.args.params:
                transpiled = ast.arg(
                    arg=param.name,
                    annotation=self.visit(param.type.type),
                )
                args.append(transpiled)
        body = [self.visit(child) for child in node.body.block_items]
        func_def = ast.FunctionDef(
            name=name,
            args=ast.arguments(args=args, vararg=None, kwarg=None, defaults=[]),
            body=body,
            decorator_list=[],
            returns=self.visit(node.decl.type.type.type),
        )
        return func_def

    def visit_For(self, node: c_ast.For):
        init = self.visit(node.init)
        cond = self.visit(node.cond)
        next_expr = self.visit(node.next)

        body = [self.visit(child) for child in node.stmt.block_items]

        for_node = ast.While(init=init, test=cond, orelse=[], body=body)
        for_node.body.append(next_expr)

        return for_node

    def visit_Return(self, node):
        if node.expr:
            return ast.Return(value=self.visit(node.expr))
        else:
            return ast.Return(value=None)

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
                # `Fibonacci fib;` -> `fib = Fibonacci()`
                var_type = self.visit(node.type.type)
                if not node.init:
                    return ast.AnnAssign(
                        target=ast.Name(id=name, ctx=ast.Store()),
                        annotation=var_type,
                        value=ast.Call(func=var_type, args=[], keywords=[]),
                        simple=1,
                    )
                else:
                    match node.init.__class__:
                        case c_ast.InitList:
                            # `Fibonacci fib = {1, 2};` -> `fib = Fibonacci(1, 2)`

                            return ast.AnnAssign(
                                target=ast.Name(id=name, ctx=ast.Store()),
                                annotation=var_type,
                                value=ast.Call(
                                    func=var_type,
                                    args=[self.visit(arg) for arg in node.init.exprs],
                                    keywords=[],
                                ),
                                simple=1,
                            )
                        case _:
                            # `int a = 5;` -> `a = 5`
                            return ast.AnnAssign(
                                target=ast.Name(id=name, ctx=ast.Store()),
                                annotation=var_type,
                                value=self.visit(node.init),
                                simple=1,
                            )

            case c_ast.PtrDecl:
                # Pointer declaration
                # `int *p;` -> `p = None`
                # `int *p = &x;` -> `p = x`
                var_type = self.visit(node.type.type)
                if not node.init:
                    var_def = ast.AnnAssign(
                        target=ast.Name(id=name, ctx=ast.Store()),
                        annotation=var_type,
                        value=None,
                        simple=1,
                    )
                else:
                    var_value = self.visit(node.init)
                    var_def = ast.AnnAssign(
                        target=ast.Name(id=name, ctx=ast.Store()),
                        annotation=var_type,
                        value=var_value,
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
        match node.type.__class__:
            case c_ast.IdentifierType:
                return ast.Name(id=node.type.names[0], ctx=ast.Load())
            case c_ast.Struct:
                # Struct type
                struct = self.visit(node.type)
                struct.name = node.declname
                return struct
            case _:
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
                # Since C data types have default values, we need to imitate that in Python
                value=ast.Call(func=field_type, args=[], keywords=[])
                if field_type
                else None,
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
        match node.type:
            case "char":
                return ast.Constant(value=str(value), kind=None)
            case "int":
                return ast.Constant(value=int(value), kind=None)
            case "float":
                return ast.Constant(value=float(value), kind=None)
            case "double":
                return ast.Constant(value=float(value), kind=None)
            case _:
                raise NotImplementedError(
                    f"Conversion not implemented for constant type: {node.type}"
                )

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
        if node.args:
            args = [self.visit(arg) for arg in node.args.exprs]
        else:
            args = []
        func_call = ast.Call(func=func, args=args, keywords=[])
        print([i.__class__ for i in self.parents])
        if self.parents[-1].__class__ in (
            c_ast.FuncDef,
            c_ast.For,
            c_ast.While,
            c_ast.DoWhile,
        ):
            func_call = ast.Expr(value=func_call)
        return func_call

    def visit_UnaryOp(self, node: c_ast.UnaryOp):
        print(f"UnaryOp: {node.op} {node.expr}")
        operand = self.visit(node.expr)
        match node.op:
            case "*":
                # skip dereference
                return operand
            case "&":
                # skip address-of
                return operand
            case "p++":
                # post-increment
                if isinstance(node.expr, c_ast.ID):
                    # Increment operator applied to a variable
                    return ast.AugAssign(
                        target=ast.Name(id=node.expr.name, ctx=ast.Store()),
                        op=ast.Add(),
                        value=ast.Constant(value=1),
                    )
                else:
                    raise NotImplementedError(
                        f"Conversion not implemented for {node.op} applied to expression"
                    )
            case _:
                raise NotImplementedError(f"{node.op} is not implemented yet")

    def visit_BinaryOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)

        # Mapping of C binary operators to Python binary operators
        operator_mapping = {
            "+": ast.Add(),
            "-": ast.Sub(),
            "*": ast.Mult(),
            "/": ast.Div(),
            "%": ast.Mod(),
            "<": ast.Lt(),
            "<=": ast.LtE(),
            ">": ast.Gt(),
            ">=": ast.GtE(),
            "==": ast.Eq(),
            "!=": ast.NotEq(),
            "&&": ast.And(),
            "||": ast.Or(),
            "&": ast.BitAnd(),
            "|": ast.BitOr(),
            "^": ast.BitXor(),
            "<<": ast.LShift(),
            ">>": ast.RShift(),
        }

        # Check if the operator is supported
        if node.op not in operator_mapping:
            raise NotImplementedError(
                f"Conversion not implemented for binary operator: {node.op}"
            )

        operator = operator_mapping[node.op]
        binary_op = ast.BinOp(left=left, op=operator, right=right)

        return binary_op
