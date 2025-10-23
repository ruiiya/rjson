# Example of a stateful addon using register/teardown

def register(funcs):
    cache = {}
    def cached_calc(key, n=1):
        if key in cache:
            return cache[key]
        # expensive calculation simulated
        val = sum(range(int(n)))
        cache[key] = val
        return val
    def teardown():
        cache.clear()
    funcs['cached_calc'] = cached_calc
    # expose teardown so the runtime can call it
    global _teardown
    _teardown = teardown
    return ['cached_calc']

def teardown():
    # if runtime calls module.teardown(), clear any module-level resources
    try:
        _teardown()
    except Exception:
        pass
