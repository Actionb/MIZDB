import io
import sys
from typing import Optional


def print_progress(iteration: int, total: int, prefix: str = '', suffix: str = '', decimals: int = 1, length: int = 100,
                   fill: str = '█', end: str = "\r", file: Optional[io.TextIOBase] = None) -> None:  # pragma: no cover
    """
    Print an increment of a progress bar.

    Args:
        iteration (int): current iteration
        total (int): total iterations
        prefix (str): string inserted before the progress bar
        suffix (str): string appended after the progress percentage
        decimals (int): floating point precision for the percentage
        length (int): character length of the progress bar
        fill (str): the 'fill' character for the progress bar
        end (str): value for print(end=)
        file (stream): file-like output stream

    Usage:
        for i in range(100):
            print_progress(i + 1, 100)

    Credit: https://stackoverflow.com/a/34325723/9313033
    """
    if file is None:
        file = sys.stdout
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled = int(length * iteration // total)
    bar = fill * filled + '-' * (length - filled)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=end, file=file)
    # Print New Line on Complete
    if iteration == total:
        print(file=file)
