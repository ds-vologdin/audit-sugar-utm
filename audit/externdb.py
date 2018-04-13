import psycopg2
import pymysql
from django.conf import settings


class SqlDB:
    '''работа с БД'''
    def sqlQuery(self, query):
        c = self.dbс.cursor()
        c.execute(query)
        out = c.fetchall()
        c.close()
        return out


class PgSqlDB(SqlDB):
    '''работа с БД postgres (utm)'''
    typeDB = 'postgres'

    def __init__(self):
        host = settings.DATABASES_UTM['host']
        db = settings.DATABASES_UTM['db']
        user = settings.DATABASES_UTM['user']
        passwd = settings.DATABASES_UTM['passwd']

        self.dbс = psycopg2.connect(
            "host=%s dbname=%s user=%s password=%s" % (host, db, user, passwd))


class MySqlDB(SqlDB):
    '''работа с БД mysql (sugar)'''
    typeDB = 'mysql'

    def __init__(self):
        host = settings.DATABASES_CRM['host']
        db = settings.DATABASES_CRM['db']
        user = settings.DATABASES_CRM['user']
        passwd = settings.DATABASES_CRM['passwd']

        self.dbс = pymysql.connect(
            host=host, user=user, passwd=passwd, db=db,
            use_unicode=True, charset="utf8"
        )
