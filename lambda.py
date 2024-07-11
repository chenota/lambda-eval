import re

# Custom exceptions
class LexingException(Exception):
    pass
class ParsingException(Exception):
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

if __name__ == "__main__":
    parser = Parser(r'(\x.x) a')
    print(parser.parse())