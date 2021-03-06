
def typeErrors(obj, value, skipAttrs=[]):
    """Provoke type errors.

    Attempts to set every attribute of object to the given value,
    expecting that TypeError will be raised. skipAttrs can be used to
    give a list of attribute names to by pass.
    """
    for attr in obj.klass().allAttrs():
        if attr.name() not in skipAttrs:
            try:
                obj.setValueForAttr(attr, value)
            except TypeError:
                pass
            except Exception as e:
                raise Exception('no type error for %s. instead got: %r, %s'
                    % (attr.name(), e, e))
            else:
                raise Exception('no type error for %s' % attr.name())


def test(store):
    import sys
    from MiscUtils.DataTable import DataTable
    from Foo import Foo
    from Bar import Bar

    class Blarg(object):
        pass
    blarg = Blarg()  # a dummy object, incompatible with everything

    f = Foo()
    typeErrors(f, blarg)
    typeErrors(f, sys.stdout)
    typeErrors(f, 1.0, ['f'])
    typeErrors(f, 1, 'b i l f'.split())

    # ValueErrors and others
    try:
        f.setB(5)
    except ValueError:
        pass
    else:
        raise Exception('expecting ValueError for bad bool argument')

    try:
        f.setI(2L**32)
    except OverflowError:
        pass
    else:
        raise Exception('expecting OverflowError for large int argument')

    try:
        f.setE('c')
    except ValueError:
        pass
    else:
        raise Exception('expecting ValueError for invalid enum')

    # Numerics that pass
    f.setI(1L)  # ints can take longs that fit in the int range
    f.setL(1)  # longs can take ints
    f.setF(1)  # floats can take ints
    f.setF(1L)  # floats can take longs
