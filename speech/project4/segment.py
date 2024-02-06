"""Run as `python3 -m speech.project4.segment`."""

import numpy as np


def segment_text(text, dictionary):
    n = len(text)
    dp = np.full((n, n), 0)
    prev = np.full((n, n), -1)

    for i in range(n):
        word = text[: i + 1]
        if word not in dictionary:
            min_distance = float("inf")
            for w in dictionary:
                distance = levenshtein_distance(w, word)
                if distance < min_distance:
                    min_distance = distance
            dp[0][i] = min_distance
            prev[0][i] = 0

    for i in range(1, n):
        for j in range(i, n):
            word = text[i : j + 1]
            if word in dictionary:
                score = 0
                dp[i][j] = np.min(dp[:i, i - 1]) + score
                prev[i][j] = np.argmin(dp[:i, i - 1])
            else:
                min_distance = float("inf")
                closest_word = None
                for w in dictionary:
                    distance = levenshtein_distance(w, word)
                    if distance < min_distance:
                        min_distance = distance
                        closest_word = w
                dp[i][j] = np.min(dp[:i, i - 1]) + min_distance
                prev[i][j] = np.argmin(dp[:i, i - 1])

    # print(np.array(dp))
    # print(np.array(prev))

    last = np.argmin(dp[:, -1])
    result = [len(prev), last]

    for t in range(len(prev) - 1, 0, -1):
        if prev[result[-1], t] == 0:
            break
        result.append(prev[result[-1], t])

    result.reverse()
    result = [0] + result
    return result


def levenshtein_distance(word1, word2):
    m, n = len(word1), len(word2)
    dp = np.zeros((m + 1, n + 1))

    for i in range(m + 1):
        dp[i][0] = i

    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1

    return dp[m][n]


def main():

    dictionary = [
        "Genshin",
        "Impact",
        "is",
        "an",
        "action",
        "role-playing",
        "game",
        "developed",
        "by",
        "miHoYo",
        "takes",
        "place",
        "in",
        "the",
        "fantasy",
        "world",
        "of",
        "Teyvat",
        "home",
        "to",
        "seven",
        "nations",
    ]

    text = "GenshitImpartisanauctionrole-plugingamedeveloperbymiYoHo"
    segmented_result = segment_text(text, dictionary)
    print(segmented_result)
    segmented_text = [text[i:j] for i, j in zip(segmented_result, segmented_result[1:])]
    print(segmented_text)


main() if __name__ == "__main__" else None
