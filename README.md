# Lambda Evaluator
Lambda evaluator is a lambda calculus expression reducer with an optional step-by-step interactive mode.

## How to Use

To get started, you may run the lambda.py file with a lambda calculus expression like so:

```
python3 lambda.py '(\x.\y.y x) a (\x.x)'
```

You may include the --interactive flag to run the program in interactive mode, which makes use of a curses TUI:

```
Expression
  (\x.\y.y x) a (\x.x)

Action
  Start
```

In interactive mode, you can press the right arrow key to advance and the left arrow key to backtrack.

Here are some helpful tips:

- The backslash character (\\) represents lambda.
- You may represent multi-parameters functions as curried (e.g., \\x.\\y.\\z...) or non-curried (e.g., \\x y z...). Lambda Evaluator will throw a runtime error if non-curried functions aren't applied to enough arguments.
- Lambda Evaluator uses Python exceptions to communicate synatx and runtime errors, so if you encounter a Python exception, pay attention to the message!

## Compatibility

Lambda Evaluator uses the curses library for its TUI, which means it should work out of the box on Mac and Linux machines, however Windows users will need to install windows-curses in order for the program to work.

## Church Numerals

Church numerals are a way of encoding numbers in the lambda calculus. In simple terms, the number a church numeral represents is equivalent to the amount of times a function f is applied to its argument x. Here's a table of church numerals:

| Number | Church Numeral    |
|--------|-------------------|
| 0      | \f.\x.x           |
| 1      | \f.\x.f x         |
| 2      | \f.\x.f (f x)     |
| 3      | \f.\x.f (f (f x)) |

You can do simple math operations on church numerals using lambda calculus functions:

| Name      | Equation | Lambda Calculus         |
|-----------|----------|-------------------------|
| Successor | $n+1$    | \n.\f.\x.f (n f x)      |
| Plus      | $m+n$    | \m.\n.\f.\x.m f (n f x) |
| Times     | $m*n$    | \m.\n.\f.\x.m (n f) x   |
| Power     | $m^n$    | \m.\n.\f.\x.(n m) f x   |

Numbers aren't the only thing you can encode using the lambda calculus. In the lambda calculus, you can encode booleans, lists, tuples, predicates, and even recursion using the y-combinator. The lambda calculus may seem obtuse at first, but it may suprise you that it is a turing-complete model of computation!

## Implementation Details

### The Grammar

The Lambda Evaluator is based on the following CFG:

```
Program      -> Statement $
Statement    -> "\" <Binding> "." <Statement>
              | <Application>
Application  -> <Expression> <Application'>
Application' -> <Expression> <Application'>
              | Empty
Expression   -> <Atom>
              | "(" <Statement> ")"
Binding      -> <Atom> Binding'
Binding'     -> <Atom> Binding'
              | Empty
Atom         -> \[a-zA-Z]+\
```

You might notice that applications are right-recursive which should be initially concerning because the lambda calculus is typically evaluated with left associativity, however no conern is needed! The parser (to be further discussed later) uses SDT to flatten application chains, which are then evaluated in a left-associative manner.

### The Lexer

The lambda calculus language is incredibly simple, which means the lexer is also incredibly simple. The lexer only looks generates five tokens:

| Token | Regex |
|-|-|
| LAMBDA | \\ |
| DOT    | .  |
| ATOM   | [a-zA-Z]+ |
| LPAREN | ( |
| RPAREN | ) |

Given that tokens don't overlap at all, the lexer doesn't need a scheme for token hierarchy and can immediately terminate upon the first match it finds. Furthemore, the lexer doesn't tokenize the entire input at once, rather it only generates a single token upon a request from the parser.

### The Parser

The parser is an LL(1) recursive descent parser, which is to say it's a recursive descent parser with a single token lookahead that doesn't backtrack and determines which alternation to use in constant time based on that single token. The syntax of the lambda calculus is incredibly simple so I didn't need to use a complex parser.

### The Evaluator

The evaluator uses small-step operational semantics. In contrast to big-step semantics, small-step semantics are more difficult to implement but offer significantly reduced memory consumption and greater support for features like GOTO's, debugging, and in our case, step-by-step operation visualizations.

## Sources
- Church Encodings: https://en.wikipedia.org/wiki/Church_encoding