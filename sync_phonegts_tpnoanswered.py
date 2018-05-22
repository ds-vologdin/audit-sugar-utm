import os
import sys
from datetime import datetime, date, timedelta, timezone
import psycopg2
import pymysql
import argparse
import configparser


def valid_date(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d')
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def parse_argv():
    description_programm = '''Приложение для синхронизации БД asterisk с \
локальной БД'''
    parser = argparse.ArgumentParser(description=description_programm)
    parser.add_argument(
        "--dateb", type=valid_date,
        default=datetime.combine(
            (date.today() - timedelta(days=1)),
            datetime.min.time()
        ).replace(tzinfo=timezone.utc),
        help="Дата начала синхронизации. По-умолчанию вчера."
    )
    parser.add_argument(
        "--datee", type=valid_date,
        default=datetime.combine(
            date.today(), datetime.min.time()
        ).replace(tzinfo=timezone.utc),
        help="Дата окончания синхронизации. По-умолчанию текущий день в 00:00."
    )
    parser.add_argument(
        "--last", action='store_true',
        help="Смотрит последнюю дату в БД и присваивает её dateb"
    )
    parser.add_argument(
        "--config", type=str,
        default='/etc/django_reports.conf',
        help="Конфигурационный файл. По-умолчанию /etc/django_reports.conf."
    )
    return parser.parse_args()


def parse_config(file_config):
    if not os.path.isfile(file_config):
        # Если файл с конфигом отсутствует, то берём данные из примера
        file_config = 'reports/django_reports.conf'

    config = configparser.ConfigParser()
    config.read(file_config)

    asterisk_db = None
    if 'PHONEBASE_DB' in config:
        asterisk_db = {
            key.upper(): config['PHONEBASE_DB'][key]
            for key in config['PHONEBASE_DB']
        }
    django_db = None
    if 'DJANGO_DB' in config:
        django_db = {
            key.upper(): config['DJANGO_DB'][key]
            for key in config['DJANGO_DB']
        }

    return {
        'PHONEBASE_DB': asterisk_db,
        'DJANGO_DB': django_db,
    }


def main(args):
    args = parse_argv()
    config = parse_config(args.config)

    django_db_config = config.get('DJANGO_DB')

    django_db = psycopg2.connect(
        "host={} dbname={} user={} password={}".format(
            django_db_config.get('HOST'), django_db_config.get('NAME'),
            django_db_config.get('USER'), django_db_config.get('PASSWORD')
        ))

    cur_django = django_db.cursor()

    # Если задана опция last, то dateb мы должны узнать из базы django
    # В случае если в базе нет данных, то dateb = datee - timedelta(days=1)
    if args.last:
        sql = '''SELECT calldate FROM audit_tpnoanswered
ORDER BY calldate DESC
LIMIT 1'''
        cur_django.execute(sql)
        last_calldate = cur_django.fetchone()

        if last_calldate:
            args.dateb = last_calldate[0]

    # Проверяем корректность заданных дат
    if args.dateb > args.datee:
        print("Заданы не корректные даты")
        return None

    # Конектимся к БД phonebase
    asterisk_db_config = config.get('PHONEBASE_DB')

    phonebase_db = pymysql.connect(
        host=asterisk_db_config.get('HOST'),
        user=asterisk_db_config.get('USER'),
        passwd=asterisk_db_config.get('PASSWD'),
        db=asterisk_db_config.get('DB'),
        use_unicode=True, charset="utf8"
    )
    # host = "10.254.230.11"
    # db = "phonebase"
    # user = "bud_dev"
    # passwd = "ltcznrf"
    # phonebase_db = pymysql.connect(host=host, user=user, passwd=passwd,
    #                                db=db, use_unicode=True, charset="utf8")

    # Если включена опция last, то с dateb мы должны брать невключительно
    comparison = '>='
    if args.last:
        comparison = '>'

    sql = '''SELECT id, callerid, calldate, priority, retry,
last_calldate, done, dane_calldate
FROM phonebase.tp_noanswered
WHERE calldate {0} '{1}' AND calldate < '{2}'
'''.format(
        comparison, args.dateb.strftime('%Y-%m-%d %X'),
        args.datee.strftime('%Y-%m-%d %X')
    )

    cur_phonebase = phonebase_db.cursor()
    cur_phonebase.execute(sql)
    no_answers = cur_phonebase.fetchall()

    phonebase_db.close()

    # Пишем полученные данные в БД django
    for no_answer in no_answers:
        if no_answer[5]:
            last_calldate = "'%s'" % no_answer[5]
        else:
            last_calldate = 'NULL'
        if no_answer[7]:
            dane_calldate = "'%s'" % no_answer[7]
        else:
            dane_calldate = 'NULL'
        # Проверяем в БД django есть ли уже запись с таким id_phonebase
        # Если есть, то делаем UPDATE иначе INSERT
        sql = '''SELECT id FROM audit_tpnoanswered
WHERE id_phonebase = %d;
        ''' % no_answer[0]
        cur_django.execute(sql)
        id_phonebase = cur_django.fetchone()

        if not id_phonebase:
            sql = '''INSERT INTO audit_tpnoanswered(
id_phonebase, callerid, calldate, priority, retry, last_calldate,
done, dane_calldate)
VALUES (%d, '%s', '%s', %d, %d, %s, %d, %s);
        ''' % (no_answer[0], no_answer[1], no_answer[2], no_answer[3],
               no_answer[4], last_calldate, no_answer[6], dane_calldate)
        else:
            id_django = id_phonebase[0]
            sql = '''UPDATE audit_tpnoanswered SET calldate = '%s',
priority = %d, retry = %d, last_calldate = %s, done = %d, dane_calldate = %s
WHERE id = %d;
            ''' % (no_answer[2], no_answer[3], no_answer[4], last_calldate,
                   no_answer[6], dane_calldate, id_django)
        cur_django.execute(sql)

    django_db.commit()
    print('Количество записей: %i' % len(no_answers))

    cur_django.close()
    django_db.close()
    return None


if __name__ == '__main__':
    sys.exit(main(sys.argv))
