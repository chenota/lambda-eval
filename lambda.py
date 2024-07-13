import re
import curses
import argparse

# Custom exceptions
class LexingException(Exception):
    pass
class ParsingException(Exception):
    pass
class EvaluationException(Exception):
    pass

# Lexer class, generates tokens one-by-one
class Lexer:
    def __init__(self, input_stream):
        # List of tokens (name, regular expression, save result)
        tokens = (
            ('LAMBDA', r'\\', False),
            ('DOT', r'\.', False),
            ('ATOM', r'[a-zA-Z]+', True),
            ('LPAREN', r'\(', False),
            ('RPAREN', r'\)', False),
            ('WHITESPACE', r'\s+', None)
        )
        # Compile tokens into dict with RE's
        self._tokens = {
            token_name: (re.compile(token_re), token_save) for token_name, token_re, token_save in tokens
        }
        # Current position in input stream
        self._position = 0
        # Input stream
        self._input_stream = input_stream
        # Advance one
        self.advance()
    def reset(self):
        self._position = 0
    def advance(self):
        # If at end of input, return EOF
        if self._position >= len(self._input_stream):
            return ('EOF', None, len(self._input_stream))
        # Initialize with None
        current_match = None
        current_token = None
        # Try each possible token
        for token_name, (token_re, _) in self._tokens.items():
            # Match starting at current position
            match = token_re.search(self._input_stream, self._position)
            # If match exists and is at start of search area...
            if match is not None and match.span()[0] == self._position: 
                # Save match
                current_match = match
                current_token = token_name
                # Exit loop (no possible token overlap so can do this!)
                break
        # If can't find match, raise an exception
        if current_match is None:
            raise LexingException(f'Lexer Error: unexpected character at position {self._position}')
        # Get save setting of found token
        _, token_save = self._tokens[current_token]
        # Save current position
        saved_position = self._position
        # Advance position
        self._position += current_match.span()[1] - current_match.span()[0]
        # Handle return
        if token_save is not None:
            return (current_token, None if token_save == False else current_match.group(), saved_position)
        # If skippable token like whitespace, advance again to get next real token
        else:
            return self.advance()

# Parser, generates AST from input
class Parser:
    # Constructor
    def __init__(self, input_stream):
        # Create lexer object
        self._lexer = Lexer(input_stream)
        # Store current token
        self._current_token = None
    # Raise an exception
    def _exception(self):
        raise ParsingException(f'Parsing Error: Unexpected token at position {self._current_token[2]}')
    # Advance to next token, return current token
    def _pop(self):
        saved_token = self._current_token
        self._current_token = self._lexer.advance()
        return saved_token
    # Return type of current token
    def _peek(self):
        return self._current_token[0]
    # Expect certain terminal, pop and return if is at start of stream, error if not 
    def _expect(self, token):
        if self._peek() != token:
            self._exception()
        return self._pop()
    # Parse given token stream
    def parse(self):
        # Reset lexer
        self._lexer.reset()
        # Get first token
        self._current_token = self._lexer.advance()
        # Parse program nonterminal
        return self._program()
    # Program nonterminal
    def _program(self):
        # Parse statement nonterminal
        statement = self._statement()
        # Expect EOF token
        self._expect('EOF')
        # If successful, return full tree
        return statement
    # Statement nonterminal
    def _statement(self):
        # If starts with lambda, use that production
        if self._peek() == 'LAMBDA':
            # Get rid of the lambda
            self._pop()
            # Parse binding nonterminal
            binding = self._binding()
            # Expect a dot
            self._expect('DOT')
            # Parse statement after binding
            statement = self._statement()
            # If has binding is function, so return function expression
            return ('FUNCTION', binding, statement)
        # Otherwise, should start with lparen or atom, parse application nonterminal if so
        elif self._peek() == 'LPAREN' or self._peek() == 'ATOM':
            return self._application()
        # Raise error if get to end
        self._exception()
    # Binding nonterminal
    def _binding(self):
        # Binding must start w/ atom
        _, atom_name, _ = self._expect('ATOM')
        # Get next binding
        b_prime = self._binding_prime()
        # Append current atom to list
        return [atom_name] + b_prime
    def _binding_prime(self):
        if self._peek() == 'ATOM':
            _, atom_name, _ = self._pop()
            # Get next binding
            b_prime = self._binding_prime()
            # Append current atom to list
            return [atom_name] + b_prime
        # If no more atoms, return empty list
        return []
    # Application nonterminal
    def _application(self):
        # Get current expression and following applications
        expression = self._expression()
        application = self._application_prime()
        # If no following applications, just return the expression
        if len(application) == 0:
            return expression
        # Otherwise, return application node
        return ('APPLICATION', [expression] + application) 
    # Application prime nonterminal
    def _application_prime(self):
        # If atom or lparen, move on to expression
        if self._peek() == 'ATOM' or self._peek() == 'LPAREN':
            expression = self._expression()
            application = self._application_prime()
            return [expression] + application
        # Empty list if no atom or lparen
        return []
    # Expression nonterminal
    def _expression(self):
        # If ATOM, ignore position
        if self._peek() == 'ATOM':
            token, value, _ = self._pop()
            return (token, value)
        # If not atom, should be parenthesized statement
        self._expect('LPAREN')
        statement = self._statement()
        self._expect('RPAREN')
        return statement

# Small-step evaluator
class Evaluator:
    # Associate a parser w/ evaluator
    def __init__(self, input_stream):
        self._parser = Parser(input_stream)
        self._ast = self._parser.parse()
        self._message = None
    # Reset ast to start
    def reset(self):
        self._ast = self._parser.parse()
    # Apply function to args
    def _apply(self, function, args):
        _, params, body = function
        # If just atom, replace 
        if body[0] == 'ATOM':
            if body[1] in params:
                return args[params.index(body[1])][::]
            return body
        # If function, do substitution in body for variables not remapped
        elif body[0] == 'FUNCTION':
            # Exclude params that exist in function
            new_params = []
            new_args = []
            for i in range(len(params)):
                if params[i] not in body[1]:
                    new_params.append(params[i])
                    new_args.append(args[i])
            # Do application
            return ('FUNCTION', body[1][::], self._apply(('FUNCTION', new_params, body[2][::]), new_args))
        # If application, do substitution for each item in application
        elif body[0] == 'APPLICATION':
            new_body = ('APPLICATION', body[1][::])
            for i in range(len(body[1])):
                new_body[1][i] = self._apply(('FUNCTION', params, new_body[1][i]), args)
            return new_body
    # Returns results of single step, doesn't update member variables
    def step(self, ast=None):
        # If didn't pass AST, assume its the root AST (make sure it's a copy!)
        if ast is None:
            ast = self._ast
        # Get type of node
        node_type = ast[0]
        # Application is reducable
        if node_type == 'APPLICATION':
            application_list = ast[1]
            if len(application_list) < 2:
                raise EvaluationException(f'Runtime exception: Application must be done on at least two items')
            # Need to reduce each application item to a value
            for i, item in enumerate(application_list):
                # Try to step the item
                step_result = self.step(ast=item)
                # If was able to step, return that result
                if step_result is not None:
                    # Update application list and return
                    new_application_list = application_list[::]
                    new_application_list[i] = step_result
                    return ('APPLICATION', new_application_list)
            # At this point, all items should be irreducable values
            # Need to make sure that first item in list is a function
            if application_list[0][0] != 'FUNCTION':
                # Cannot apply a non-function to anything
                return None
            # Expand function node
            _, function_args, function_body = application_list[0]
            # Sanity check: enough args given to satisfy function
            if len(application_list) - 1 < len(function_args):
                raise EvaluationException(f'Runtime error: Not enough arguments given to satisfy the function {self.pretty_print(node=application_list[0])}. Expected {len(function_args)}, got {len(application_list) - 1}.')
            # Apply function to args
            application_result = self._apply(application_list[0], application_list[1:1+len(function_args)])
            # Make message
            self._message = 'Applied ' + self.pretty_print(node=application_list[0]) + ' to ' + ' '.join([self.pretty_print(node=x) for x in application_list[1:1+len(function_args)]]) + ', generating ' + self.pretty_print(node=application_result)
            # Update application list
            new_application_list = [application_result] + application_list[1+len(function_args):]
            # If nothing else to apply, return singular item
            if len(new_application_list) == 1:
                return application_result
            # More to apply, return application
            return ('APPLICATION', new_application_list)
        # Function body is reducable
        elif node_type == 'FUNCTION':
            function_body = ast[2][::]
            step_result =  self.step(ast=function_body)
            if step_result is not None:
                return ('FUNCTION', ast[1][::], step_result)
            return None
        # Atom is already normal
        elif node_type == 'ATOM':
            return None
        raise EvaluationException(f'Runtime error: Unkown AST node {node_type}')
    # Reduce by one step, return reduction result and wether or not did any reduction
    def reduce_once(self):
        new_ast = self.step()
        if new_ast is not None:
            self._ast = new_ast
            return True
        return False
    # Reduce until cannot reduce any more
    def reduce_all(self):
        new_ast = self.step()
        while new_ast is not None:
            self._ast = new_ast
            new_ast = self.step()
        return self._ast
    # Pretty print current AST node as string
    def pretty_print(self, node=None, parent_fn=False, parent_app=False):
        if node is None:
            node = self._ast
        node_type = node[0]
        if node_type == 'ATOM':
            return node[1]
        elif node_type == 'APPLICATION':
            return (
                ('(' if parent_app else '') + 
                ' '.join([self.pretty_print(node=x,parent_app=True) for x in node[1]]) +
                (')' if parent_app else '')
            )
        elif node_type == 'FUNCTION':
            return (
                ('(' if not parent_fn else '') + 
                '\\' + 
                ' '.join(node[1]) + 
                '.' + 
                self.pretty_print(node=node[2],parent_fn=True) + 
                (')' if not parent_fn else '')
            )
    # Getter for AST
    def get_ast(self):
        return self._ast[::]
    # Setter for AST
    def set_ast(self, ast):
        self._ast = ast
    # Getter for message
    def get_message(self):
        return self._message
        
def main_interactive(stdscr, input_stream):
    # Clear screen
    stdscr.clear()
    # Setup evaluator
    eval = Evaluator(input_stream)
    # Print start screen
    stdscr.addstr(0, 0, 'Expression')
    stdscr.addstr(1, 2, eval.pretty_print())
    stdscr.addstr(3, 0, 'Action')
    stdscr.addstr(4, 2, 'Start')
    # Action index
    action_idx = 0
    history = [(eval._ast[::], 'Start')]
    final_idx = None
    while True:
        message = None
        exception_mode = False
        # Get key
        key = stdscr.getkey()
        # Clear screen
        stdscr.clear()
        # Go back if pressed left key
        if key == 'KEY_LEFT' and action_idx >= 0:
            # Go back one action if not already at 0
            if action_idx > 0: action_idx -= 1
            # Restore previous message and ast
            prev_ast, message = history[action_idx]
            eval.set_ast(prev_ast)
        # Perform next reduction if right key
        elif key == 'KEY_RIGHT':
            # Advance one action
            action_idx += 1
            # If went over end, stop main
            if final_idx is not None and action_idx > final_idx:
                return
            # If already calculated, restore that
            if action_idx < len(history):
                prev_ast, message = history[action_idx]
                eval.set_ast(prev_ast)
            # if not already calculated...
            else:
                try:
                    # Attempt to reduce once
                    did_reduce = eval.reduce_once()
                    # If reduction was successful, save message and new AST
                    if did_reduce is not None:
                        message = eval.get_message()
                        history.append((eval.get_ast(), message))
                    # If not successful, can't reduce any more so give option to quit
                    else:
                        final_idx = action_idx
                        message = 'Done! Press the right arrow to close...'
                # If encounter evaluation exception, put into exception mode
                except EvaluationException as e:
                    exception_mode = True
                    message = str(e)
        else:
            continue
        if not exception_mode:
            # Print screen
            stdscr.addstr(0, 0, 'Expression')
            stdscr.addstr(1, 2, eval.pretty_print())
            stdscr.addstr(3, 0, 'Action')
            stdscr.addstr(4, 2, message)
        else:
            # Print error screen
            stdscr.addstr(0, 0, 'An exception has occured! Press any key to continue...')
            stdscr.addstr(2, 0, message)
            stdscr.getkey()
            return

# Parses cli arguments
class ArgParser(argparse.ArgumentParser):
    def __init__(self):
        # Initialize parent class
        super(ArgParser, self).__init__(
            prog='lambda.py',
            description='Lambda calculus interpreter'
        )
        # Add arguments
        self.add_argument('expression', help='Lambda calculus expression to evaluate')
        self.add_argument('--interactive', help='Run the interpreter in interactive mode', action='store_true')

# Main entry point
if __name__ == "__main__":
    # Parse cli arguments
    args = ArgParser().parse_args()
    # Run in interactive mode
    if args.interactive:
        curses.wrapper(main_interactive, args.expression)
    # Just run interpreter
    else:
        eval = Evaluator(args.expression)
        eval.reduce_all()
        print(eval.pretty_print())