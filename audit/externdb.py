import psycopg2
import pymysql
import logging
from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, scoped_session

from django.conf import settings


engine_utm = create_engine(
    'postgresql+psycopg2://{}:{}@{}:{}/{}'.format(
        settings.DATABASES_UTM['user'],
        settings.DATABASES_UTM['passwd'],
        settings.DATABASES_UTM['host'],
        settings.DATABASES_UTM['port'],
        settings.DATABASES_UTM['db']
    ),
    echo=True,
    pool_recycle=3600
)
logging.debug('Создали engine_utm')
# session_factory_utm = sessionmaker(bind=engine_utm)
# Session_utm = scoped_session(session_factory_utm)
# session_utm = Session_utm()
# logging.debug('Создали session')

engine_crm = create_engine(
    'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8'.format(
        settings.DATABASES_CRM['user'],
        settings.DATABASES_CRM['passwd'],
        settings.DATABASES_CRM['host'],
        settings.DATABASES_CRM['port'],
        settings.DATABASES_CRM['db']
    ),
    echo=True,
    pool_recycle=3600
)
logging.debug('Создали engine_crm')


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
