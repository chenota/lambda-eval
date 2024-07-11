# lambda-calculus-eval
Step-by-step lambda calculus expression reducer.

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
Atom         -> \[a-z][A-Z]+\
```