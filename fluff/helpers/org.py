def chunkify(lst, n):
    return [lst[i::n] for i in range(n)]
