__all__ = (
    "OCTAL_DIGIT_2_VALUE",
    "OCTAL_DIGITS",
    "DIGIT_2_VALUE",
    "DIGITS",
    "HEX_DIGIT_2_VALUE",
    "HEX_DIGITS",
    "SIMPLE_ESCAPE_SEQUENCE_2_ASCII",
    "SIMPLE_ESCAPE_SEQUENCES",
    "WHITE_SPACES",
    "LETTERS",
    "make_counter",
)


OCTAL_DIGIT_2_VALUE = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
}

OCTAL_DIGITS = OCTAL_DIGIT_2_VALUE.keys()

DIGIT_2_VALUE = {
    **OCTAL_DIGIT_2_VALUE,
    "8": 8,
    "9": 9,
}

DIGITS = DIGIT_2_VALUE.keys()

HEX_DIGIT_2_VALUE = {
    **DIGIT_2_VALUE,
    "a": 10, "A": 10,
    "b": 11, "B": 11,
    "c": 12, "C": 12,
    "d": 13, "D": 13,
    "e": 14, "E": 14,
    "f": 15, "F": 15,
}

HEX_DIGITS = HEX_DIGIT_2_VALUE.keys()

SIMPLE_ESCAPE_SEQUENCE_2_ASCII = {
    "\\a": ord("\a"),
    "\\b": ord("\b"),
    "\\f": ord("\f"),
    "\\n": ord("\n"),
    "\\r": ord("\r"),
    "\\t": ord("\t"),
    "\\v": ord("\v"),
    "\\\\": ord("\\"),
    "\\\'": ord("\'"),
    "\\\"": ord("\""),
    "\\?": ord("?"),
}

SIMPLE_ESCAPE_SEQUENCES = SIMPLE_ESCAPE_SEQUENCE_2_ASCII.keys()

WHITE_SPACES = set(" \t\n\v\f\r")
LETTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def make_counter(count):
    def counter(count_delta) -> int:
        nonlocal count
        count += count_delta
        return count

    return counter
