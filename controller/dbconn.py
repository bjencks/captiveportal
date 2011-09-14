import sqlite3
import config


def dbconn():
    return sqlite3.connect(config.DBPATH, isolation_level='EXCLUSIVE',
                           detect_types=sqlite3.PARSE_DECLTYPES)

def with_dbconn(method):
    def meth(*args, **kwargs):
        con = dbconn()
        try:
            with con:
                if not isinstance(args, list):
                    args = list(args)
                args.insert(0, con)
                return method(*args, **kwargs)
        finally:
            con.close()
    return meth
