import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser, Node

class Interpreter:
    def __init__(self, source_file):
        # Check if file has .rx extension
        if not source_file.endswith('.rx'):
            raise Exception(f"Error: Only .rx files are supported. '{source_file}' is not a valid source file.")
        
        self.source_file = source_file
        self.variables = {}  # Global variable scope
        self.functions = {}  # User-defined functions
        self.call_stack = []  # For function call contexts
        
    def run(self):
        try:
            with open(self.source_file, 'r') as f:
                source_code = f.read()
        except FileNotFoundError:
            print(f"Error: Source file '{self.source_file}' not found.")
            return

        lexer = Lexer(source_code)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        # Execute the AST
        self.execute(ast)

    def execute(self, node):
        if node.type == 'Program':
            # First pass: collect all function definitions
            for child in node.children:
                if child.type == 'FunctionDeclaration':
                    self.functions[child.value] = child
                elif child.type == 'UseStatement':
                    # Ignore use statements in interpreter mode
                    pass
            
            # Second pass: execute main if it exists
            if 'main' in self.functions:
                self.execute_function('main', [])
            else:
                raise Exception("No main function found")
                
        elif node.type == 'Block':
            result = None
            for statement in node.children:
                result = self.execute(statement)
                # Check if we hit a return statement
                if isinstance(result, tuple) and result[0] == 'RETURN':
                    return result
            return result
            
        elif node.type == 'VariableDeclaration':
            var_name = node.value
            value = self.execute(node.children[0])
            
            # Store in current scope (top of call stack or global)
            if self.call_stack:
                self.call_stack[-1]['locals'][var_name] = value
            else:
                self.variables[var_name] = value
            return value
            
        elif node.type == 'IfStatement':
            condition = self.execute(node.children[0])
            if condition:
                return self.execute(node.children[1])
            elif len(node.children) > 2:
                return self.execute(node.children[2])
            return None
            
        elif node.type == 'MatchStatement':
            var_value = self.execute(node.children[0])
            
            # Compare against each case
            for case in node.children[1:]:
                if case.type == 'MatchCase':
                    if str(var_value) == str(case.value):
                        return self.execute(case.children[0])
            return None
            
        elif node.type == 'BinaryOp':
            left = self.execute(node.children[0])
            right = self.execute(node.children[1])
            
            if node.value == 'PLUS':
                return left + right
            elif node.value == 'MINUS':
                return left - right
            elif node.value == 'MULTIPLY':
                return left * right
            elif node.value == 'DIVIDE':
                return left // right  # Integer division
            elif node.value == 'EQUAL':
                return 1 if left == right else 0
            elif node.value == 'NOT_EQUAL':
                return 1 if left != right else 0
            elif node.value == 'GREATER':
                return 1 if left > right else 0
            elif node.value == 'GREATER_EQUAL':
                return 1 if left >= right else 0
            elif node.value == 'LESS':
                return 1 if left < right else 0
            elif node.value == 'LESS_EQUAL':
                return 1 if left <= right else 0
            elif node.value == 'AND':
                return 1 if left and right else 0
            elif node.value == 'OR':
                return 1 if left or right else 0
            return None
            
        elif node.type == 'UnaryOp':
            if node.value == 'NOT':
                value = self.execute(node.children[0])
                return 1 if not value else 0
            return None
            
        elif node.type == 'Number':
            return node.value
            
        elif node.type == 'StringLiteral':
            # Remove quotes and handle escape sequences
            value = node.value.strip('"')
            value = value.replace('\\n', '\n')
            value = value.replace('\\t', '\t')
            value = value.replace('\\\\', '\\')
            value = value.replace('\\"', '"')
            return value
            
        elif node.type == 'Variable':
            var_name = node.value
            
            # Check current scope first
            if self.call_stack and var_name in self.call_stack[-1]['locals']:
                return self.call_stack[-1]['locals'][var_name]
            
            # Check global scope
            if var_name in self.variables:
                return self.variables[var_name]
            
            raise Exception(f"Undefined variable: {var_name}")
            
        elif node.type == 'FunctionCall':
            func_name = node.value
            args = [self.execute(arg) for arg in node.children]
            
            # Check for built-in functions
            if func_name == 'print':
                return self.builtin_print(args)
            elif func_name == 'input':
                return self.builtin_input(args)
            elif func_name == 'pause':
                return self.builtin_pause(args)
            elif func_name == 'os':
                return self.builtin_os(args)
            
            # Check for user-defined functions
            if func_name in self.functions:
                return self.execute_function(func_name, args)
            
            raise Exception(f"Undefined function: {func_name}")
            
        elif node.type == 'ReturnStatement':
            value = self.execute(node.children[0]) if node.children else None
            return ('RETURN', value)
            
        return None

    def execute_function(self, func_name, args):
        func_node = self.functions[func_name]
        
        # Get parameter names (skip the first child which is the body)
        params = func_node.children[1:] if len(func_node.children) > 1 else []
        
        # Create new scope
        local_scope = {}
        
        # Bind arguments to parameters
        for i, param in enumerate(params):
            if i < len(args):
                local_scope[param.value] = args[i]
        
        # Push scope onto call stack
        self.call_stack.append({'locals': local_scope})
        
        # Execute function body
        result = self.execute(func_node.children[0])
        
        # Pop scope
        self.call_stack.pop()
        
        # Handle return value
        if isinstance(result, tuple) and result[0] == 'RETURN':
            return result[1]
        return None

    def builtin_print(self, args):
        """Built-in print function"""
        for arg in args:
            print(arg, end='',)
        print()
        return None

    def builtin_input(self, args):
        """Built-in input function"""
        prompt = args[0] if args else ""
        if prompt:
            print(prompt, end='')
        print()
        return input()

    def builtin_pause(self, args):
        """Built-in pause function (milliseconds)"""
        if args:
            ms = args[0]
            time.sleep(ms / 1000.0)
        return None

    def builtin_os(self, args):
        """Built-in os function - in interpreter mode, just exits"""
        if args and args[0] == "shutdown":
            sys.exit(0)
        return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python interpreter.py <source_file.rx>")
        sys.exit(1)
        
    source_file = sys.argv[1]
    try:
        interpreter = Interpreter(source_file)
        interpreter.run()
    except Exception as e:
        print(f"Interpretation error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)