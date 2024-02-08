"""Run as `python3 -m speech.project4.segment_alt2`."""

from . import DATA_DIR, read_lines_stripped, write_split_lines
from .correct_story import correct_story_lines_stripped
from .dictionary import dictionary_trie
from .segment import compare_to_correct, segment
from .segment_and_spellcheck_alt2 import alter_dict_trie_losses


def main():
    dict_trie = dictionary_trie()
    alter_dict_trie_losses(dict_trie)

    lines = read_lines_stripped(f"{DATA_DIR}unsegmented0.txt")
    segmented_result = [segment(dict_trie, line, 0x20) for line in lines]
    write_split_lines("segment_unsegmented0.txt", segmented_result)

    correct_lines = correct_story_lines_stripped()
    compare_to_correct(correct_lines, segmented_result)


main() if __name__ == "__main__" else None
