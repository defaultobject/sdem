def str_to_bool(v: str) -> bool:
    #from https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def str_to_dict(s: str) -> dict:
    return json.loads(s)

def get_permission(question):
    ans = input(question)
    if ans == '1' or ans == 'y' or ans == 'yes':
        return True
    return False

def ask_permission(question, fn):
    #Ask permission before running fn
    ans = get_permission(question)
    if ans:
        fn()



