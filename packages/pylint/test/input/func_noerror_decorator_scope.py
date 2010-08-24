# -*- pylint: disable-msg=W0232,R0903
"""Test that decorators sees the class namespace - just like
function default values does but function body doesn't.

https://www.logilab.net/elo/ticket/3711 - bug finding decorator arguments 
https://www.logilab.net/elo/ticket/5626 - name resolution bug inside classes
"""

__revision__ = 0
 
class Test:
    """test class"""
    ident = lambda x: x

    @ident(ident)
    def method(self, val=ident(7), func=ident):
        """hop"""
        print self
        return func(val)
