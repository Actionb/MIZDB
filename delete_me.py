def x(y):
    try:
        y = y + 1
    except AttributeError:
        pass
    else:
        print(y)
        
if __name__ == '__main__':
    x('1')
