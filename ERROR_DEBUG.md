#GITHUB ERROR 1

The failure is due to a type annotation issue in your code, specifically at this line:

Python
def some_function(
    ...,
) -> T | Any:
The error (UP047) suggests that the type annotation T | Any is not valid syntax in this context. Instead, you should use type parameters with typing.TypeVar for generics.

To fix this, declare T as a TypeVar and use only T or Any where appropriate. For example:

Python
from typing import TypeVar, Any

T = TypeVar('T')

def some_function(
    ...,
) -> T:
Or if you want to allow both T and Any, just use Any:

Python
def some_function(
    ...,
) -> Any:
Adjust your function signature in the file referenced by the error to resolve the CI job failure.