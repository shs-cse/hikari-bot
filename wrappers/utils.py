def is_number(x):
    return isinstance(x, (int, float, complex)) and not isinstance(x, bool)


class FormatText:
    """
    Use ANSI color codes/graphics mode to emphasize changes
    reference: https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797
    """

    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    DIM_BOLD_RESET = "\033[22m"
    ITALICS = "\033[3m"
    UNDERLINE = "\033[4m"

    # dim yellow
    @staticmethod
    def wait(text) -> str:
        return f"\n{FormatText.YELLOW}{FormatText.DIM} {text}{FormatText.RESET}"

    # cyan
    @staticmethod
    def status(text) -> str:
        return f"\n{FormatText.CYAN}\t• {text}{FormatText.RESET}"

    # green
    @staticmethod
    def success(text) -> str:
        return f"\n{FormatText.GREEN}✔ {text}{FormatText.RESET}"

    # yellow
    @staticmethod
    def warning(text) -> str:
        return f"\n{FormatText.YELLOW}{FormatText.BOLD}‼️ {text}{FormatText.RESET}"

    # red
    @staticmethod
    def error(text) -> str:
        return f"\n\n{FormatText.RED}{FormatText.BOLD}✘ {text}{FormatText.RESET}"

    # only dim text and reset
    @staticmethod
    def dim(text) -> str:
        return f"{FormatText.DIM}{text}{FormatText.DIM_BOLD_RESET}"

    # only bold text and reset
    @staticmethod
    def bold(text) -> str:
        return f"{FormatText.BOLD}{text}{FormatText.DIM_BOLD_RESET}"
