# -*- coding: utf8 -*-

import new
from SQLObjectStore import SQLObjectStore, LostDatabaseConnection
import MySQLdb
from MySQLdb import Warning


class MySQLObjectStore(SQLObjectStore):
    """MySQLObjectStore implements an object store backed by a MySQL database.

    MySQL notes:
      * MySQL home page: http://www.mysql.com.
      * MySQL version this was developed and tested with: 3.22.34 & 3.23.27
      * The platforms developed and tested with include Linux (Mandrake 7.1)
        and Windows ME.
      * The MySQL-Python DB API 2.0 module used under the hood is MySQLdb
        by Andy Dustman: http://dustman.net/andy/python/MySQLdb/.
      * Newer versions of MySQLdb have autocommit switched off by default.

    The connection arguments passed to __init__ are:
      - host
      - user
      - passwd
      - port
      - unix_socket
      - client_flag
      - autocommit

    You wouldn't use the 'db' argument, since that is determined by the model.

    See the MySQLdb docs or the DB API 2.0 docs for more information.
      http://www.python.org/topics/database/DatabaseAPI-2.0.html
    """

    def __init__(self, **kwargs):
        self._autocommit = kwargs.pop('autocommit', False)
        SQLObjectStore.__init__(self, **kwargs)

    def augmentDatabaseArgs(self, args, pool=False):
        if not args.get('db'):
            args['db'] = self._model.sqlDatabaseName()

    def newConnection(self):
        kwargs = self._dbArgs.copy()
        self.augmentDatabaseArgs(kwargs)
        conn = self.dbapiModule().connect(**kwargs)
        if self._autocommit:
            # MySQLdb 1.2.0 and later disables autocommit by default
            try:
                conn.autocommit(True)
            except AttributeError:
                pass
        return conn

    def connect(self):
        SQLObjectStore.connect(self)
        if self._autocommit:
            # Since our autocommit patch above does not get applied to pooled
            # connections, we have to monkey-patch the pool connection method
            try:
                pool = self._pool
                connection = pool.connection
            except AttributeError:
                pass
            else:
                def newConnection(self):
                    conn = self._normalConnection()
                    try:
                        conn.autocommit(True)
                    except AttributeError:
                        pass
                    return conn
                pool._normalConnection = connection
                pool._autocommit = self._autocommit
                pool.connection = new.instancemethod(
                    newConnection, pool, pool.__class__)

    def retrieveLastInsertId(self, conn, cur):
        try:
            # MySQLdb module 1.2.0 and later
            lastId = conn.insert_id()
        except AttributeError:
            # MySQLdb module 1.0.0 and earlier
            lastId = cur.insert_id()
        # The above is more efficient than this:
        # conn, cur = self.executeSQL('select last_insert_id();', conn)
        # id = cur.fetchone()[0]
        return lastId

    def dbapiModule(self):
        return MySQLdb

    def _executeSQL(self, cur, sql, clausesArgs=None):
        try:
            sql = sql.decode('utf8')
        except UnicodeEncodeError:
            print 'Query: ' + sql
            raise
        try:
            cur.execute(sql, clausesArgs)
        except MySQLdb.Warning:
            if not self.setting('IgnoreSQLWarnings', False):
                raise
        except UnicodeDecodeError:
            print 'Query: ' + sql
            raise
        except MySQLdb.OperationalError, e:
            if e[0] in (2006, 2013):   # OperationalError: (2006, 'MySQL server has gone away'), OperationalError: (2013, 'Lost connection to MySQL server during query')
                raise LostDatabaseConnection()
            raise

    def sqlNowCall(self):
        return 'NOW()'

    def sqlCaseInsensitiveLike(self, a, b):
        # mysql is case-insensitive by default
        return "%s like %s" % (a,b)


class Klass(object):

    def sqlTableName(self):
        return "`%s`" % self.name()


class Attr(object):

    def sqlColumnName(self):
        """ Returns the SQL column name corresponding to this attribute, consisting of self.name() + self.sqlTypeSuffix(). """
        if not self._sqlColumnName:
            self._sqlColumnName = "`%s`" % self.name()
        return self._sqlColumnName


# Mixins
import re
def escape_string(s):
    # Replacement for mysql's built-in escape_string (which doesn't support utf8),
    # and real_escape_string (which claims to support the connection's charset, 
    # but seems to be broken).
    # Characters encoded are NUL (ASCII 0), ‘\n’, ‘\r’, ‘\’, ‘'’, ‘"’, and Control-Z
    # (same as the 
    s = re.sub('\\\\', '\\\\\\\\', s)
    s = re.sub('\x00', '\\\\0', s)
    s = re.sub('\n', '\\\\n', s)
    s = re.sub('\r', '\\\\r', s)
    s = re.sub("\'", "\\\\'", s)
    s = re.sub('\"', '\\\\"', s)
    s = re.sub('\x1a', '\\\\Z', s)
    return s

def test_escape_string():
    def test(s):
        s1, s2 = repr(MySQLdb.escape_string(s)), repr(escape_string(s))
        assert s1 == s2, "%s != %s" % (s1, s2)

    test('''\0\\\n\\"\'''')
    test('\\')
    test('\n')
    test("Paul Zehr\'s carefully researched study on the tabernacle of the Old Testament draws from both Christian and Jewish sources. He not only probes the nature of the construction of the tabernacle, but also explores its theological meaning.\r\n1981. 216 pages. Paper.")
    assert escape_string(u'\xe4') == u'\xe4'


class StringAttr(object):

    def sqlForNonNone(self, value):
        """MySQL provides a quoting function for string -- this method uses it."""
        return "'%s'" % escape_string(value)
