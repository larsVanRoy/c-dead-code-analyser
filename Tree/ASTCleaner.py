from Tree.AbstractSyntaxTree import AbstractSyntaxTree

from SymbolTable.SymbolTable import SymbolTable


class ASTCleaner:
    def __init__(self, root):
        self.__root = root
        self.__symbol_table = SymbolTable()

        self.__scope_counter = 0  # this value is used to give scopes unique names

        self.__declarations = dict()  # this dict keeps track of the node that declared a variable

        self.__changes_occurred = True  # this value tracks whether or not something changes in a cycle

    def print_symbol_table(self):
        self.__symbol_table.print()

    def get_ast(self):
        return self.__root

    def clean_children(self, node):
        for child in node.get_children():
            self.clean(child)

    @staticmethod
    def perform_optimal_cast(value):
        if value[0] == "\"":  # string
            return value
        elif value[0] == "'":  # character
            return ord(value[1])
        else:  # numeric type
            try:
                if int(value) == float(value):
                    return int(value)
            except ValueError:
                return float(value)

    def perform_full_clean(self, trace=False):
        while self.__changes_occurred:
            if trace:
                print("Optimization cycle started")
            self.__changes_occurred = False
            self.clean(self.__root)
            if trace:
                print("Optimization cycle finished")

    # this is used when folding occurs, this will change the node name to the new node name,
    # and will pop all of its children
    @staticmethod
    def clean_node(node, new_label):
        node.set_label(new_label)
        for i in reversed(range(len(node.get_children()))):
            node.pop_child(i)

    # this is used when a node is no longer needed/of value to the further execution
    def remove_node(self, node_name):
        node = self.__declarations[node_name]

        parent = node.get_parent()
        index = parent.find_child(node)

        parent.pop_child(index)

    # this is used when an assignment occurs, on a variable that did not get used in the meantime
    def update_assigned_value(self, variable_name, assignment_node, value):
        # set the assignment node equal to the desired value, and move the declaration to be the next statement
        # in the current scope
        self.clean_node(assignment_node, value)
        self.remove_node(variable_name)

        child = assignment_node
        parent = assignment_node.get_parent()
        while parent.get_label() != "Compound Statement":
            child = parent
            parent = parent.get_parent()

        ctx = assignment_node.get_ctx()
        variable_type = self.__symbol_table.get_type(variable_name)
        index = parent.find_child(child) + 1

        declaration_node = AbstractSyntaxTree("Declaration", ctx)
        parent.add_child_at_index(declaration_node, index)
        declaration_node.set_parent(parent)

        type_specifier_node = AbstractSyntaxTree("Type Specifier", ctx)
        declaration_node.add_child(type_specifier_node)
        type_specifier_node.set_parent(declaration_node)

        type_node = AbstractSyntaxTree(variable_type, ctx)
        type_specifier_node.add_child(type_node)
        type_node.set_parent(type_specifier_node)

        init_declarator_node = AbstractSyntaxTree("Init Declarator", ctx)
        declaration_node.add_child(init_declarator_node)
        init_declarator_node.set_parent(declaration_node)

        declarator_node = AbstractSyntaxTree("Declarator", ctx)
        init_declarator_node.add_child(declarator_node)
        declarator_node.set_parent(init_declarator_node)

        variable_node = AbstractSyntaxTree(variable_name, ctx)
        declarator_node.add_child(variable_node)
        variable_node.set_parent(declarator_node)

        initializer_node = AbstractSyntaxTree("Initializer", ctx)
        init_declarator_node.add_child(initializer_node)
        initializer_node.set_parent(init_declarator_node)

        value_node = AbstractSyntaxTree(value, ctx)
        initializer_node.add_child(value_node)
        value_node.set_parent(initializer_node)

        self.__declarations[variable_name] = declaration_node

    def clean(self, node: AbstractSyntaxTree):
        result = ""

        # these are values passed to an existing identifier, needed for folding
        # these are always of the format operand operation operand
        # this node will return a computed value, in case this is possible
        # if not, it will just return an empty string
        if node.get_label() == "Additive Expression":
            operand_1 = self.clean(node.get_children()[0])
            operator = node.get_children()[1].get_label()
            operand_2 = self.clean(node.get_children()[2])

            if operand_1 != "" and operand_1[:5] == "ID = " and self.__symbol_table.is_initialized(operand_1[5:]):
                operand_1 = "Val = {}".format(self.__symbol_table.get_value(operand_1[5:]))

            if operand_2 != "" and operand_2[:5] == "ID = " and self.__symbol_table.is_initialized(operand_2[5:]):
                operand_2 = "Val = {}".format(self.__symbol_table.get_value(operand_2[5:]))

            if operand_1 != "" and operand_2 != "" and operand_1[:6] == "Val = " and operand_2[:6] == "Val = ":
                casted_operand_1 = self.perform_optimal_cast(operand_1[6:])
                casted_operand_2 = self.perform_optimal_cast(operand_2[6:])
                if operator == "+":
                    value = "Val = {}".format(casted_operand_1 + casted_operand_2)
                    self.clean_node(node, value)
                    return value
                else:
                    value = "Val = {}".format(casted_operand_1 - casted_operand_2)
                    self.clean_node(node, value)
                    return value
            else:
                return ""

        # this gives an alignment restriction equal to a value/expression to an identifier, not needed
        # given the goal
        elif node.get_label() == "Alignment Specifier":
            return result

        # these are the values passed in a function call, needed for folding
        elif node.get_label() == "Arguments":
            pass

        # new values assigned to a variable, this is needed for folding
        elif node.get_label() == "Assignment Expression":
            operand_1 = self.clean(node.get_children()[0])
            operator = node.get_children()[1].get_label()
            operand_2 = self.clean(node.get_children()[2])

            operand_1_val = None

            if operand_1 != "" and operand_1[:5] == "ID = " and self.__symbol_table.is_initialized(operand_1[5:]):
                operand_1_val = "Val = {}".format(self.__symbol_table.get_value(operand_1[5:]))

            if operand_2 != "" and operand_2[:5] == "ID = " and self.__symbol_table.is_initialized(operand_2[5:]):
                operand_2 = "Val = {}".format(self.__symbol_table.get_value(operand_2[5:]))

            if operand_1 != "" and operand_2 != "" and operand_1[:5] == "ID = " and operand_2[:6] == "Val = ":
                if operator == "=":
                    value = self.perform_optimal_cast(operand_2[6:])
                    self.clean_node(node, "Val = {}".format(value))
                    self.update_assigned_value(operand_1[5:], node, "Val = {}".format(value))
                    self.__symbol_table.set_value(operand_1[5:], value)
                    return "Val = {}".format(value)
                elif operand_1_val is not None:
                    if operator == "*=":
                        value = self.perform_optimal_cast(operand_1_val[6:]) * self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value
                    elif operator == "/=":
                        value = self.perform_optimal_cast(operand_1_val[6:]) / self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value
                    elif operator == "%=":
                        value = self.perform_optimal_cast(operand_1_val[6:]) % self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value
                    elif operator == "+:":
                        value = self.perform_optimal_cast(operand_1_val[6:]) + self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value
                    elif operator == "-=":
                        value = self.perform_optimal_cast(operand_1_val[6:]) + self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value
                    elif operator == "<<=":
                        value = self.perform_optimal_cast(operand_1_val[6:]) << self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value
                    elif operator == ">>=":
                        value = self.perform_optimal_cast(operand_1_val[6:]) >> self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value
                    elif operator == "$=":
                        value = self.perform_optimal_cast(operand_1_val[6:]) & self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value
                    elif operator == "^=":
                        value = self.perform_optimal_cast(operand_1_val[6:]) ^ self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value
                    elif operator == "|=":
                        value = self.perform_optimal_cast(operand_1_val[6:]) | self.perform_optimal_cast(operand_2[6:])
                        self.__symbol_table.set_value(operand_1[5:], value)
                        return value

        # this defines an atomic type, not really needed given the goal but returned as type to ensure
        # declarations don't break
        elif node.get_label() == "Atomic Type Specifier":
            return node.get_children()[0].get_label()

        # this defines a bitwise and comparison, this is needed for condition evaluation
        elif node.get_label() == "Bitwise And Expression":
            pass

        # this defines a bitwise or comparison, this is needed for condition evaluation
        elif node.get_label() == "Bitwise Or Expression":
            pass

        # this defines a bitwise xor comparison, this is needed for condition evaluation
        elif node.get_label() == "Bitwise Xor Expression":
            pass

        # this defines a cast expression
        # its parameters are the type, and the value to cast
        # this is needed for folding
        elif node.get_label() == "Cast Expression":
            pass

        # this is the root of the ast
        elif node.get_label() == "CompilationUnit":
            self.clean_children(node)
            return ""

        # this defines a bracket enclosed scope
        # in case of a function the scope will be opened as soon as the definition occurs, so that the parameters
        # are enclosed within the functions scope
        elif node.get_label() == "Compound Statement":
            if not node.is_parent("Function Definition"):
                self.__symbol_table.open_scope("scope_{}".format(self.__scope_counter))
                self.__scope_counter += 1
                self.clean_children(node)
                self.__symbol_table.close_scope()
            else:
                self.clean_children(node)

        # this defines an expression of the form: condition ? expression : condition
        # this is needed for folding
        elif node.get_label() == "Conditional Expression":
            condition = self.clean(node.get_children()[0])

            if condition != "" and condition[:6] == "Val = ":
                if condition[6:] == "true":
                    value_1 = self.clean(node.get_children()[2])
                    self.clean_node(node, value_1)
                    return value_1
                elif condition[6:] == "false":
                    value_2 = self.clean(node.get_children()[4])
                    self.clean_node(node, value_2)
                    return value_2
            return ""

        # this defines a new identifier, this is needed for the symbol table
        elif node.get_label() == "Declaration":
            children = node.get_children()

            declaration_type = ""

            i = 0
            for i in range(len(children)):
                child = children[i]
                if child.get_label() == "Type Specifier":
                    declaration_type += self.clean(child)
                elif child.get_label() == "Type Def Name":
                    declaration_type += self.clean(child)
                elif child.get_label() == "Type Name":
                    declaration_type += self.clean(child)
                elif child.get_label() == "Struct or Union Specifier":
                    declaration_type += node.get_children()[1].get_label()
                elif child.get_label() == "auto":
                    declaration_type += "auto"
                elif child.get_label() == "Init Declarator":
                    break

            for i in range(i, len(children)):
                declarator_child = children[i].get_children()[0]
                declarator = self.clean(declarator_child)

                self.__declarations[declarator] = node

                if len(children[i].get_children()) > 1:
                    initializer_child = children[i].get_children()[1]
                    initializer = self.clean(initializer_child)
                    if initializer[:6] == "Val = ":
                        self.__symbol_table.add_symbol(declaration_type, declarator, initializer[6:])
                    else:
                        self.__symbol_table.add_symbol(declaration_type, declarator)

                else:
                    self.__symbol_table.add_symbol(declaration_type, declarator)

            return ""

        # this node occurs when declaring a variable with another variable or an expression
        elif node.get_label() == "Declarator":
            children = node.get_children()

            if children[0].get_label() == "Direct Declarator":
                return self.clean(children[0])
            else:
                return children[0].get_label()

        # used to specify the default option in switch statements, possibly needed for advanced folding
        elif node.get_label() == "Default":
            pass

        # specifies the expression used to declare a different variable
        elif node.get_label() == "Direct Declarator":
            result = node.get_children()[0].get_label()
            return result

        # specifies variable part of an enumerator
        elif node.get_label() == "Enumerator":
            pass

        # head node for an enumerator, this has the name of the enumerator plus the values part of the enumeration
        elif node.get_label() == "Enum Specifier":
            pass

        # defines a conditional expression with '==' or '!=' comparison, needed for condition evaluation
        elif node.get_label() == "Equality Expression":
            operand_1 = self.clean(node.get_children()[0])
            operator = node.get_children()[1].get_label()
            operand_2 = self.clean(node.get_children()[2])

            if operand_1 != "" and operand_1[:5] == "ID = " and self.__symbol_table.is_initialized(operand_1[5:]):
                operand_1 = "Val = {}".format(self.__symbol_table.get_value(operand_1[5:]))

            if operand_2 != "" and operand_2[:5] == "ID = " and self.__symbol_table.is_initialized(operand_2[5:]):
                operand_2 = "Val = {}".format(self.__symbol_table.get_value(operand_2[5:]))

            if operand_1 != "" and operand_2 != "" and operand_1[:6] == "Val = " and operand_2[:6] == "Val = ":
                if operator == "==":
                    if operand_1[6:] == operand_2[6:]:
                        self.clean_node(node, "Val = true")
                        return "Val = true"
                    if operand_1[6:] != operand_2[6:]:
                        self.clean_node(node, "Val = false")
                        return "Val = false"
                if operator == "!=":
                    if operand_1[6:] != operand_2[6:]:
                        self.clean_node(node, "Val = true")
                        return "Val = true"
                    if operand_1[6:] == operand_2[6:]:
                        self.clean_node(node, "Val = false")
                        return "Val = false"

        # head node when multiple expression occur on the same line, needed for folding
        elif node.get_label() == "Expression":
            pass

        # defines a variable inside the first clause of a for specifier, needed for condition evaluation
        elif node.get_label() == "For Declaration":
            pass

        # defines an expression part of one of the clauses of a for specifier, needed for condition evaluation
        elif node.get_label() == "For Expression":
            pass

        # head node for the for clauses
        elif node.get_label() == "For Condition":
            pass

        # defines a function, will open its associated scope too
        elif node.get_label() == "Function Definition":
            children = node.get_children()
            function_type = ""

            i = None

            # iterate over specifiers
            for i in range(len(children)):
                child = children[i]

                if child.get_label() == "Declarator":
                    break

                function_type += self.clean(child)

            # get the function name
            function_name = self.clean(children[i])

            # register function scope
            self.__symbol_table.open_scope(function_name)

            # check if parameters were given
            if len(children[i].get_children()) > 1:
                self.clean(children[i].get_children()[1])

            # get the declarations that might have occurred
            for i in range(i+1, len(children)):
                child = children[i]

                if child.get_label() == "Compound Statement":
                    break

                self.clean(child)

            # analyze the block items part of the function
            self.clean_children(children[i])

            # close the function scope
            self.__symbol_table.close_scope()

            return ""

        # adds specifier to functions, not needed considering goal
        elif node.get_label() == "Function Specifier":
            return ""

        # head node for generic specification
        elif node.get_label() == "Generic":
            pass

        # specifies one possible generic association
        elif node.get_label() == "Generic Association":
            pass

        # specifies an identifier name, this is needed for symbol table/folding
        elif node.get_label()[:4] == "ID =":
            return node.get_label()

        # specifies initial non constant value of an identifier for declaration
        elif node.get_label() == "Init Declarator":
            pass

        # specifies initial constant value of an identifier for declaration
        elif node.get_label() == "Initializer":
            label = node.get_children()[0].get_label()
            if label[:6] == "Val = ":
                return node.get_children()[0].get_label()
            elif label == "Assignment Expression":
                return self.clean(node.get_children()[0])
            elif label == "Conditional Expression":
                return self.clean(node.get_children()[0])
            elif label == "Additive Expression":
                value = self.clean(node.get_children()[0])
                return value
            elif label == "Multiplication Expression":
                return self.clean(node.get_children()[0])

        # head node for loops
        elif node.get_label() == "Iteration Statement":
            pass

        # head node for a jump statement
        elif node.get_label() == "Jump Statement":
            pass

        # head node for a labeled statement
        elif node.get_label() == "Labeled Statement":
            pass

        # head node for a logical and comparison, needed for condition evaluation
        elif node.get_label() == "Logical And Expression":
            pass

        # head node for a logical or comparison, needed for condition evaluation
        elif node.get_label() == "Logical Or Expression":
            pass

        # head node for a multiplication expression, needed for folding
        elif node.get_label() == "Multiplication Expression":
            operand_1 = self.clean(node.get_children()[0])
            operator = node.get_children()[1].get_label()
            operand_2 = self.clean(node.get_children()[2])

            if operand_1 != "" and operand_1[:5] == "ID = " and self.__symbol_table.is_initialized(operand_1[5:]):
                operand_1 = "Val = {}".format(self.__symbol_table.get_value(operand_1[5:]))

            if operand_2 != "" and operand_2[:5] == "ID = " and self.__symbol_table.is_initialized(operand_2[5:]):
                operand_2 = "Val = {}".format(self.__symbol_table.get_value(operand_2[5:]))

            if operand_1 != "" and operand_2 != "" and operand_1[:6] == "Val = " and operand_2[:6] == "Val = ":
                casted_operand_1 = self.perform_optimal_cast(operand_1[6:])
                casted_operand_2 = self.perform_optimal_cast(operand_2[6:])
                if operator == "*":
                    value = "Val = {}".format(casted_operand_1 * casted_operand_2)
                    self.clean_node(node, value)
                    return value
                elif operator == "/":
                    value = "Val = {}".format(casted_operand_1 / casted_operand_2)
                    self.clean_node(node, value)
                    return value
                else:
                    value = "Val = {}".format(casted_operand_1 % casted_operand_2)
                    self.clean_node(node, value)
                    return value
            else:
                return ""

        # specifies types and names of parameters of a function, needed for symbol table
        elif node.get_label() == "Parameter Type List":
            self.clean_children(node)

        # head node for a specification of a specific parameter
        elif node.get_label() == "Parameter Declaration":
            if len(node.get_children()) > 1:
                parameter_type = self.clean(node.get_children()[0])
                parameter_name = self.clean(node.get_children()[1])

                self.__symbol_table.add_symbol(parameter_type, parameter_name)

        # head node for a postfix expression
        elif node.get_label() == "Postfix Expression":
            pass

        # head node for a primary expression
        elif node.get_label() == "Primary Expression":
            pass

        # head node for a relation expression
        elif node.get_label() == "Relational Expression":
            pass

        # head node for a selection statement
        elif node.get_label() == "Selection Statement":
            pass

        # head node for a shift expression
        elif node.get_label() == "Shift Expression":
            pass

        # head node for a struct declaration, specifying the variables and (possibly) their values
        elif node.get_label() == "Struct Declaration":
            pass

        # head for a struct variable declaration
        elif node.get_label() == "Struct Declarator":
            pass

        # head node for a struct declaration plus its name
        elif node.get_label() == "Struct or Union Specifier":
            pass

        # defines a static assertion, this is possible dead code so this will be checked in dead code elimination
        elif node.get_label() == "Static Assert Declaration":
            pass

        # defines the name of a type
        elif node.get_label() == "Type Def Name":
            pass

        # head node for a type specification
        elif node.get_label() == "Type Name":
            result = ""
            children = node.get_children()
            for i in range(len(children)):
                child = children[i]

                if child.get_label() == "Type Specifier":
                    result += self.clean(child)
                elif child.get_label() == "Type Qualifier":
                    result += self.clean(child)
                elif child.get_label() == "pointer":
                    result += self.clean(child)
                else:  # array, ...
                    break

            return result

        # node that specifies (part of) an existing type
        elif node.get_label() == "Type Specifier":
            children = node.get_children()
            result = ""
            for child in children:
                if child.get_label() == "Type Specifier":
                    result += self.clean(child)
                elif child.get_label() == "pointer":
                    result += "*"
                else:
                    result += child.get_label()
            return result

        # qualification for a type, not needed considering the goal
        elif node.get_label() == "Type Qualifier":
            return ""

        # head node for a unary expression
        elif node.get_label() == "Unary Expression":
            pass

        # node specifying a constant value
        elif node.get_label()[:5] == "Val =":
            return node.get_label()

        # node that specifies the type of an iteration statement
        elif node.get_label() == "While":
            pass

        print("exited without specific return for node, {}, with children:".format(node.get_label()))
        for child in node.get_children():
            print("\t{}".format(child.get_label()))
        return result