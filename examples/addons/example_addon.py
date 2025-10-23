# Example addon: exposes a functions dict

functions = {
    'shout': lambda s: str(s).upper() + '!',
}

# Optionally provide a register function
# def register(funcs):
#     funcs['shout'] = lambda s: str(s).upper() + '!'
#     return ['shout']
