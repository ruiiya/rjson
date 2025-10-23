functions = {
    'repeat': lambda s, n: str(s) * int(n),
    'upper_join': lambda sep, items: sep.join([str(x).upper() for x in items])
}
