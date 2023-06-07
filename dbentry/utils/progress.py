def print_progress(iteration: int, total: int, prefix: str = '', suffix: str = '', decimals: int = 1, length: int = 100,
                   fill: str = '█', end: str = "\r") -> None:
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

    Usage:
        for i in range(100):
            print_progress(i + 1, 100)

    Credit: https://stackoverflow.com/a/34325723/9313033
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled = int(length * iteration // total)
    bar = fill * filled + '-' * (length - filled)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=end)
    # Print New Line on Complete
    if iteration == total:
        print()
