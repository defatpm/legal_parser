#GITHUB ERROR 1

Your job failed due to outdated type annotations flagged by your linter, specifically related to the use of Union for type hints. The linter recommends using the Python 3.10+ syntax X | Y instead of Union[X, Y]. This affects several places in your src/utils/error_handler.py file.

Solution

Update all function signatures where you use Union[...] for type annotations to use the vertical bar (|) syntax.

Examples of fixes:

Change:
Python
def handle_error(self, error: Exception, context: Union[dict[str, Any], None] = None) -> dict[str, Any]:
to:

Python
def handle_error(self, error: Exception, context: dict[str, Any] | None = None) -> dict[str, Any]:
Change:
Python
def retry_on_error(
    ...
    retryable_check: Union[Callable[[Exception], bool], None] = None
) -> Callable:
to:

Python
def retry_on_error(
    ...
    retryable_check: Callable[[Exception], bool] | None = None
) -> Callable:
Change:
Python
def handle_exceptions(
    default_return: Union[Any, None] = None,
    ...
) -> Callable:
to:

Python
def handle_exceptions(
    default_return: Any | None = None,
    ...
) -> Callable:
Change:
Python
def safe_execute(
    ...
    default_return: Union[Any, None] = None,
    ...
) -> Union[T, Any]:
to:

Python
def safe_execute(
    ...
    default_return: Any | None = None,
    ...
) -> T | Any:
Change:
Python
def validate_input(
    ...
    field_name: Union[str, None] = None
) -> None:
to:

Python
def validate_input(
    ...
    field_name: str | None = None
) -> None:
Change:
Python
def check_resource_limits(
    memory_mb: Union[float, None] = None,
    disk_space_mb: Union[float, None] = None,
    timeout_seconds: Union[float, None] = None
) -> None:
to:

Python
def check_resource_limits(
    memory_mb: float | None = None,
    disk_space_mb: float | None = None,
    timeout_seconds: float | None = None
) -> None:
Tip:
Many of these can be auto-fixed using your linter/formatter by running with the --fix option. For example:

sh
ruff check src/utils/error_handler.py --fix
After making these changes, commit and push your code. This should resolve the linter errors and allow your CI job to pass. If you need the exact lines, let me know!