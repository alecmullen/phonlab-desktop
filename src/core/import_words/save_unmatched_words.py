import csv

from core.base.use_case_sync import UseCaseSync


class SaveUnmatchedWords(UseCaseSync[int]):
    """Writes the words of the project that a table lacks to a CSV file, with how often
    each occurs, the most frequent first. Returns how many words were written."""

    def __call__(self, path: str, unmatched: dict[str, int]) -> int:
        words = sorted(unmatched.items(), key=lambda item: (-item[1], item[0]))
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["word", "count"])
            writer.writerows(words)
        return len(words)
