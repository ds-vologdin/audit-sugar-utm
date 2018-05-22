import os
import sys
from datetime import datetime, timedelta, timezone, date
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
    if 'ASTERISK_DB' in config:
        asterisk_db = {
            key.upper(): config['ASTERISK_DB'][key]
            for key in config['ASTERISK_DB']
        }
    django_db = None
    if 'DJANGO_DB' in config:
        django_db = {
            key.upper(): config['DJANGO_DB'][key]
            for key in config['DJANGO_DB']
        }

    return {
        'ASTERISK_DB': asterisk_db,
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
        sql = '''SELECT date_event FROM audit_queuelog
ORDER BY date_event DESC
LIMIT 1'''
        cur_django.execute(sql)
        last_date_db = cur_django.fetchone()
        if last_date_db:
            args.dateb = last_date_db[0]

    # Проверяем корректность заданных дат
    if args.dateb > args.datee:
        print("Заданы не корректные даты")
        return None

    # Конектимся к БД asterisk
    asterisk_db_config = config.get('ASTERISK_DB')

    ast_db = pymysql.connect(
        host=asterisk_db_config.get('HOST'),
        user=asterisk_db_config.get('USER'),
        passwd=asterisk_db_config.get('PASSWD'),
        db=asterisk_db_config.get('DB'),
        use_unicode=True, charset="utf8"
    )

    # Если включена опция last, то с dateb мы должны брать невключительно
    comparison = '>='
    if args.last:
        comparison = '>'
    sql = '''SELECT id, time, callid, queuename, agent, event,
data1, data2, data3, data4, data5
FROM asterisk.queue_log
WHERE queuename = 'q-support'
AND STR_TO_DATE(time, '%Y-%m-%d') {0} '{1}'
AND STR_TO_DATE(time, '%Y-%m-%d') < '{2}';
    '''.format(comparison, args.dateb, args.datee)

    cur_asterisk = ast_db.cursor()
    cur_asterisk.execute(sql)
    events = cur_asterisk.fetchall()

    ast_db.close()

    # Пишем полученные данные в БД django
    for event in events:
        sql = '''INSERT INTO  audit_queuelog(
id_asterisk, date_event, callid, queuename, agent, event,
data1, data2, data3, data4, data5)
VALUES (%s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');
''' % (event)
        cur_django.execute(sql)

    django_db.commit()
    print('Количество записей: %i' % len(events))

    cur_django.close()
    django_db.close()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
