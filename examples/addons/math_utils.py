def register(funcs):
    def sum_list(lst):
        return sum(float(x) for x in lst)
    funcs['sum_list'] = sum_list
    return ['sum_list']
