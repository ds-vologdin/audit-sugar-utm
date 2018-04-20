from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
# from django.core.urlresolvers import reverse

# Опять же, спасибо django за готовую форму аутентификации.
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic.edit import FormView
from django.views.generic.base import View

from django.contrib import messages

# Функция для установки сессионного ключа.
# По нему django будет определять, выполнил ли вход пользователь.
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required

from datetime import date, timedelta

# Классы работы с базами CRM и UTM
from audit.externdb import PgSqlDB, MySqlDB

import logging


logger = logging.getLogger(__name__)


class LoginFormView(FormView):
    form_class = AuthenticationForm

    # Аналогично регистрации, только используем шаблон аутентификации.
    template_name = "audit/login.html"

    # В случае успеха перенаправим на главную.
    success_url = "/audit/"

    def form_valid(self, form):
        # Получаем объект пользователя на основе введённых в форму данных.
        self.user = form.get_user()

        # Выполняем аутентификацию пользователя.
        login(self.request, self.user)
        return super(LoginFormView, self).form_valid(form)


class LogoutView(View):
    def get(self, request):
        # Выполняем выход для пользователя, запросившего данное представление.
        logout(request)

        # После чего, перенаправляем пользователя на главную страницу.
        return HttpResponseRedirect("/audit/login/")


# Базовые функции
def gen_report_begin_end_date(year='', month='', last='month'):
    '''Функция формирования даты начала и конца отчётного периода'''
    if year == '':
        # не задан год
        date_end = date.today()
        # Год не задан, берём период - последние 30 дней
        if last == 'week':
            date_begin = date_end - timedelta(days=6)
        elif last == 'month':
            date_begin = date_end - timedelta(days=30)
        elif last == 'quarter':
            date_begin = date_end - timedelta(days=90)
        elif last == 'year':
            date_begin = date_end.replace(year=(date_end.year-1), day=1)
        elif last == '2years':
            date_begin = date_end.replace(year=(date_end.year-2), day=1)
        elif last == '3years':
            date_begin = date_end.replace(year=(date_end.year-3), day=1)

        return date_begin, date_end

    if month == '':
        # Не задан месяц
        # Берём период - весь год
        date_begin = date(int(year), 1, 1)
        date_end = date(int(year), 12, 31)

        return date_begin, date_end

    # Задан месяц и год
    date_begin = date(int(year), int(month), 1)
    if int(month) < 12:
        date_end = date(int(year), int(month)+1, 1) - timedelta(days=1)
    else:
        date_end = date(int(year), 12, 31)

    return date_begin, date_end


def gen_type_report(year, month):
    '''Частая конструкция для определения типа отчёта: last, year, month
    '''
    if year == '' and month == '':
        return 'last'
    if not year == '' and month == '':
        return 'year'
    if not year == '' and not month == '':
        return 'month'
    return ''


def gen_last_months(last=12):
    ''' Функция генерации списка последних месяцев для выпадающего списка меню
    >>> len(gen_last_months(12))
    12
    >>> len(gen_last_months(2))
    2
    '''
    date_iter = date.today().replace(day=1)

    # Расчитываем дату последнего месяца
    if date_iter.month > last % 12:
        year_end = date_iter.year - last//12
        month_end = date_iter.month - last % 12
    else:
        year_end = date_iter.year - last//12 - 1
        month_end = date_iter.month - last % 12 + 12
    date_end = date(year=year_end, month=month_end, day=1)

    # Формируем список месяцев
    months_report = []
    while date_iter > date_end:
        months_report.append(date_iter)
        if date_iter.month == 1:
            date_iter = date_iter.replace(year=date_iter.year - 1, month=12)
        else:
            date_iter = date_iter.replace(month=date_iter.month - 1)
    return months_report


def gen_last_years(last=5):
    ''' Функция генерации списка последних лет для выпадающего списка меню
    '''
    date_cur = date.today().replace(month=1, day=1)

    years_report = [
        date_cur.replace(year=date_cur.year - i)
        for i in range(last)
    ]
    return years_report


def next_month(date_val):
    if date_val.month < 12:
        return date_val.replace(month=date_val.month+1, day=1)
    else:
        return date(year=date_val.year+1, month=1, day=1)


def gen_period(date_begin, date_end):
    '''
    TODO: УСТАРЕЛА! Надо везде заменить на gen_report_periods !!!!!!!!!!!!!!!!
    Формируем список дат: помесячный, если период более 120 дней
    понедельный, если от 31 до 120 дней
    подневной, если до 31 дня
    Возвращаем period, последнее значение используем как закрывающую дату
    period = [d1, d2, ..., d(n-1), dn]
    используем date >= d1 and date < d2, ... date >= d(n-1) and date < dn
    '''
    delta = date_end - date_begin
    period = []
    if delta < timedelta(days=31):
        period = [date_begin + timedelta(days=i) for i in range(delta.days+1)]
    elif delta < timedelta(days=120):
        period = gen_week_period(date_begin, date_end)
    else:
        # Помесячная статистика
        if date_begin.day > 1:
            begin_period = next_month(date_begin)
        else:
            begin_period = date_begin
        while begin_period <= date_end:
            period.append(begin_period)
            begin_period = next_month(begin_period)
        # Надо добавить ещё и следующий месяц
        period.append(begin_period)
    return period


def gen_report_periods(date_begin, date_end):
    '''
    Формируем список дат: помесячный, если период более 120 дней
    понедельный, если от 31 до 120 дней
    подневной, если до 31 дня
    Возвращаем period
    period = [(d1, d2), (d2, d3), ..., (d(n-1), dn)]
    используем date >= d1 and date < d2, ... date >= d(n-1) and date < dn
    '''
    delta = date_end - date_begin

    # Подневная разбивка
    if delta < timedelta(days=31):
        return [
            (date_begin + timedelta(days=i), date_begin + timedelta(days=i+1))
            for i in range(delta.days + 1)
        ]
    # Понедельная разбивка
    if delta < timedelta(days=120):
        # Нас интересуют только полные недели
        days_to_new_week = (7 - date_begin.weekday()) % 7
        data_cur = date_begin + timedelta(days=days_to_new_week)
        delta = date_end - data_cur

        return [
            (data_cur + timedelta(days=i), data_cur + timedelta(days=i+7))
            for i in range(0, delta.days, 7)
        ]

    # Помесячная разбивка
    period = []

    # Нас интересуют только полные месяцы
    date_cur = next_month(date_begin) if date_begin.day > 1 else date_begin

    while date_cur <= date_end:
        period.append((date_cur, next_month(date_cur)))
        date_cur = next_month(date_cur)

    return period
# Конец базовых функций


@login_required
def index(request):
    '''Главная пустая страница :)
    '''
    if request.user.is_authenticated():
        context = {'user': request.user.username,
                   }
        return render(request, 'audit/base.html', context)
    else:
        return HttpResponseRedirect('/audit/login/')


def fetch_pays_from_utm(db, date_begin, date_end):
    '''Получить данные из БД UTM
    '''
# Запрос в базу
    sql = '''SELECT (to_timestamp(payment_enter_date))::date as datep,
sum(payment_absolute), count(payment_absolute)
FROM payment_transactions
WHERE to_timestamp(payment_enter_date)>='%s'
AND to_timestamp(payment_enter_date)<'%s' AND method = 5
GROUP BY datep
ORDER BY datep''' % (date_begin, date_end + timedelta(days=1))
    pays_lists = db.sqlQuery(sql)

    pays_dicts = [
        {'date': pay[0], 'summ': pay[1], 'count': pay[2]}
        for pay in pays_lists
    ]

    return pays_dicts


def calc_pays_stat_periods(pays, report_periods):
    '''Функция рассчитывает статистику по платежам за каждый период
       в report_periods
    '''
    pays_periods_dicts = []
    # sum_tmp и count_tmp используется для расчёта смещения относительно
    # предыдущего отчётного периода
    sum_tmp = 0
    count_tmp = 0
    for date_begin, date_end in report_periods:
        pays_period = [
            pay for pay in pays
            if (pay.get('date') >= date_begin and pay.get('date') < date_end)
        ]
        # Расчитываем среднее значение и количество
        summ = 0
        count = 0
        for pay in pays_period:
            summ += pay.get('summ', 0)
            count += pay.get('count', 0)

        # Считаем среднее значение платежа (ARPU)
        avg_pay = summ/count if count > 0 else 0

        # Расчитываем изменение относительно предыдущего отчетного периода
        sum_dif = 0
        sum_dif_p = 0
        count_dif = 0
        count_dif_p = 0

        if sum_tmp > 0 and count_tmp > 0:
            sum_dif = summ - sum_tmp
            sum_dif_p = sum_dif*100/sum_tmp
            count_dif = count - count_tmp
            count_dif_p = count_dif*100/count_tmp

        sum_tmp = summ
        count_tmp = count

        pays_periods_dicts.append(
            {'date': date_begin,
             'summ': summ,
             'count': count,
             'avg': round(avg_pay, 2),
             'sum_dif': sum_dif,
             'sum_dif_p': round(sum_dif_p, 2),
             'count_dif': count_dif,
             'count_dif_p': round(count_dif_p, 2),
             }
        )
    return pays_periods_dicts


def fetch_balances_periods(db, report_periods):
    '''Функция расчёта баланса по заданным периодам
    '''
    # Расчитываем только в случае если отчёт помесячный
    date_begin, date_end = report_periods[0]
    if (date_end - date_begin) < timedelta(days=28):
        return None

    balances_dicts = []
    for date_begin, date_end in report_periods:
        # считаем сколько людей с положительным балансом перешло
        # на текущий месяц, какой у них средний баланс
        sql = '''SELECT  count(t1.out_balance), avg(t1.out_balance),
sum(t1.out_balance)
FROM balance_history t1 LEFT JOIN users t2 ON t1.account_id = t2.basic_account
WHERE to_timestamp(t1.date) = '%s' AND t2.login ~ '^\d\d\d\d\d$'
AND t1.out_balance >= 0 and t1.out_balance < 15000
        ''' % date_begin
        active_balance = db.sqlQuery(sql)

        # Смотрим средний баланс среди всех абонентов
        sql = '''SELECT  avg(t1.out_balance)
FROM balance_history t1 LEFT JOIN users t2 ON t1.account_id = t2.basic_account
WHERE to_timestamp(t1.date) = '%s' AND t2.login ~ '^\d\d\d\d\d$'
AND t1.out_balance > -15000 and t1.out_balance < 15000
        ''' % date_begin
        all_balance = db.sqlQuery(sql)

        count, avg, summ = active_balance[0] if len(active_balance) == 1 \
            else (0, 0, 0)

        avg_all = all_balance[0][0] if len(all_balance) == 1 else 0

        balances_dicts.append(
            {'date': date_begin,
             'count': count,
             'avg': avg,
             'summ': summ,
             'avg_all': avg_all,
             }
        )
    return balances_dicts


@login_required
def utmpays_statistic(request, year='', month='', csv_flag=False, last='year'):
    '''Функция формирует отчёт по платежам физ. лиц
    '''
    if not request.user.groups.filter(name__exact='utmpays').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, utmpays_statistic.__name__, last, year, month)
    )

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    # Получаем данные из БД UTM
    db = PgSqlDB()
    pays = fetch_pays_from_utm(db, date_begin, date_end)

    # Формируем отчётные периоды (разбиваем date_begin - date_end на отрезки)
    report_periods = gen_report_periods(date_begin, date_end)

    # Расчитываем помесячную статистику
    pays_stat_periods = calc_pays_stat_periods(pays, report_periods)

    # Считаем статистику по всем платежам
    summ_pay, count_pay = 0, 0
    for pay in pays_stat_periods:
        summ_pay += pay['summ']
        count_pay += pay['count']

    if last == '':
        count_period = len(report_periods)
        avg_summ = summ_pay/count_period if count_period > 0 else 0
        avg_count = count_pay/count_period if count_period > 0 else 0
    else:
        # Не учитываем последний месяц (он чаще всего не полный)
        count_period = len(report_periods) - 1
        avg_summ = (summ_pay - pays_stat_periods[-1]['summ'])/count_period \
            if count_period > 0 else 0
        avg_count = (count_pay - pays_stat_periods[-1]['count'])/count_period \
            if count_period > 0 else 0

    avg_pays = summ_pay/count_pay if count_pay > 0 else 0

    pays_stat_summary = {
        'summ': summ_pay,
        'count': count_pay,
        'avg_summ': avg_summ,
        'avg_count': avg_count,
        'avg_pay': avg_pays,
    }

    # Запрашиваем помесячную статистику по исходящему остатку на начало месяца
    # и по количеству активных абонентов на начало месяца
    # Если статистика не помесячная, то balances_periods = None
    balances_periods = fetch_balances_periods(db, report_periods)

    # Объединяем pays_stat_periods и balances_periods
    if balances_periods:
        for i in range(len(pays_stat_periods)):
            pays_stat_periods[i]['count_active'] = \
                balances_periods[i].get('count', 0)

            pays_stat_periods[i]['avg_balance'] = \
                balances_periods[i].get('avg', 0)

            pays_stat_periods[i]['avg_balance_all'] = \
                balances_periods[i].get('avg_all', 0)

            pays_stat_periods[i]['sum_balance'] = \
                balances_periods[i].get('summ', 0)

    # Формируем переменные для меню шаблона
    months_report = gen_last_months(last=12)
    years_report = gen_last_years(last=5)
    type_report = gen_type_report(year, month)

    context = {
        'pays_stat': pays_stat_periods,
        'pays_stat_summary': pays_stat_summary,
        'months': months_report,
        'years': years_report,
        'type': type_report,
        'date_begin': date_begin,
        'menu_url': '/audit/utmpays/',
    }
    if balances_periods:
        return render(request, 'audit/pays_year.html', context)
    return render(request, 'audit/index.html', context)


def fetch_users_block_month(date_start, date_stop):
    ''' Функция для получения данных по блокировке пользователей UTM
    в промежутке между date_start, date_stop
    '''
    db = PgSqlDB()

    # Запрашиваем в БД список заблокированных пользователей
    q = '''SELECT DISTINCT t1.id, t1.login, t1.full_name, t1.actual_address,
t1.mobile_telephone, to_timestamp(t3.start_date) dateblock
FROM users t1
LEFT JOIN users_accounts t2 ON t1.id = t2.uid
LEFT JOIN blocks_info t3 ON t3.account_id=t2.account_id
WHERE (to_timestamp(t3.start_date)>='%s' AND to_timestamp(t3.start_date)<'%s'
AND to_timestamp(t3.expire_date)>'2030-01-01')
AND t1.login ~ '^\d\d\d\d\d$'
ORDER BY dateblock''' % (date_start, date_stop + timedelta(days=1))
    blocks = db.sqlQuery(q)

    users_block = []
    # Получаем тарифы пользователя и формируем список словарей с информацией
    # об ушёдшим в блок пользователям
    for block in blocks:
        # Запрашиваем активную сервисную связку (хотим узнать тарифный план)
        q = '''SELECT DISTINCT t3.service_name, t3.comment, t3.id
FROM users t1
LEFT JOIN service_links t2 ON t1.basic_account=t2.account_id
LEFT JOIN services_data t3 ON t2.service_id=t3.id
WHERE t1.id = '%i' AND t3.is_deleted = 0 AND t2.is_deleted = 0
AND t1.is_deleted='0' AND not t3.id = 614''' % (block[0])
        services = db.sqlQuery(q)

        service = ''

        if len(services) == 0:
            # Активных сервисных связок нет, запрашиваем историю тарифов.
            q = '''SELECT t1.tariff_name, to_timestamp(t1.unlink_date)\
unlink_date
FROM tariffs_history t1
LEFT JOIN users_accounts t2 ON t1.account_id = t2.account_id
WHERE  t2.uid = %i
ORDER BY unlink_date desc''' % block[0]
            tarif_history = db.sqlQuery(q)
            service = tarif_history[0][0] if len(tarif_history) > 0 else ''
        else:
            # Есть активные сервисные связки
            service_names = [ser[0] for ser in services]
            service = '; '.join(service_names)

        users_block.append(
            {
                'login': block[1],
                'user': block[2],
                'address': block[3],
                'phone': block[4],
                'date': block[5],
                'tarif': service,
            }
        )
    return users_block


def gen_ods_user_block_month(users_blok, date_start, date_stop):
    # Библиотеки для формирования ods файлов
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.style import Style, TextProperties, TableColumnProperties, \
        TableCellProperties, TableRowProperties, ParagraphProperties
    from odf.text import P
    from odf.table import Table, TableColumn, TableRow, TableCell

    report_ods = OpenDocumentSpreadsheet()
    # Create a style for the table content. One we can modify
    # later in the spreadsheet.
    tablecontents = Style(name="Large number", family="table-cell")
    tablecontents.addElement(
        TextProperties(fontfamily="Arial", fontsize="10pt")
    )
    report_ods.styles.addElement(tablecontents)

    # Create automatic styles for the column widths.
    wideco1 = Style(name="co1", family="table-column")
    wideco1.addElement(
        TableColumnProperties(columnwidth="1.3cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco1)

    wideco2 = Style(name="co2", family="table-column")
    wideco2.addElement(
        TableColumnProperties(columnwidth="9.3cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco2)

    wideco3 = Style(name="co3", family="table-column")
    wideco3.addElement(
        TableColumnProperties(columnwidth="7.5cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco3)

    wideco4 = Style(name="co4", family="table-column")
    wideco4.addElement(
        TableColumnProperties(columnwidth="4.5cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco4)

    wideco5 = Style(name="co5", family="table-column")
    wideco5.addElement(
        TableColumnProperties(columnwidth="4.5cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco5)

    wideco6 = Style(name="co6", family="table-column")
    wideco6.addElement(
        TableColumnProperties(columnwidth="2.6cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco6)

    # Create automatic styles for the row widths.
    roheighthead = Style(name="ro1", family="table-row")
    roheighthead.addElement(TableRowProperties(rowheight="0.90cm"))
    report_ods.automaticstyles.addElement(roheighthead)

    roheight = Style(name="ro2", family="table-row")
    roheight.addElement(TableRowProperties(rowheight="2.00cm"))
    report_ods.automaticstyles.addElement(roheight)

    textcontent = Style(name="ce2", family="table-cell",
                        parentstylename=tablecontents)
    textcontent.addElement(
        TableCellProperties(border="0.74pt solid #000000",
                            wrapoption="wrap",
                            verticalalign="middle")
    )
    report_ods.automaticstyles.addElement(textcontent)

    titlecontent = Style(name="ce0", family="table-cell",
                         parentstylename=tablecontents)
    titlecontent.addElement(TextProperties(fontweight="bold"))
    titlecontent.addElement(ParagraphProperties(textalign="center"))
    titlecontent.addElement(
        TextProperties(fontfamily="Arial", fontsize="12pt")
    )

    report_ods.automaticstyles.addElement(titlecontent)

    headtable = Style(name="ce3", family="table-cell",
                      parentstylename=tablecontents)
    headtable.addElement(TextProperties(fontweight="bold"))
    headtable.addElement(ParagraphProperties(textalign="center"))
    headtable.addElement(
        TextProperties(fontfamily="Arial", fontsize="10pt")
    )
    headtable.addElement(
        TableCellProperties(border="0.74pt solid #000000",
                            wrapoption="wrap",
                            verticalalign="middle")
    )
    report_ods.automaticstyles.addElement(headtable)

    textcenter = Style(name="ce4", family="table-cell",
                       parentstylename=tablecontents)
    textcenter.addElement(ParagraphProperties(textalign="center"))
    textcenter.addElement(
        TableCellProperties(border="0.74pt solid #000000",
                            wrapoption="wrap",
                            verticalalign="middle")
    )
    report_ods.automaticstyles.addElement(textcenter)

    # Start the table, and describe the columns
    table = Table(name="Снятие оборудования")

    # Create a column (same as <col> in HTML)
    # Make all cells in column default to currency
    table.addElement(
        TableColumn(stylename=wideco1, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco2, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco3, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco4, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco5, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco6, defaultcellstylename="ce1")
    )

    tr = TableRow()
    table.addElement(tr)

    textCell = "Заблокированные абоненты за период с %s по %s" % \
        (date_start, date_stop)
    cell = TableCell(stylename="ce0", valuetype="string",
                     value=textCell, numbercolumnsspanned="6",
                     numberrowsspanned="1")
    cell.addElement(P(text=textCell))
    tr.addElement(cell)
    table.addElement(tr)

    tr = TableRow(stylename=roheighthead)
    table.addElement(tr)

    # Отображаем названия полей
    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Логин"))
    tr.addElement(cell)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Абонент"))
    tr.addElement(cell)
    table.addElement(tr)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Адрес"))
    tr.addElement(cell)
    table.addElement(tr)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Тариф"))
    tr.addElement(cell)
    table.addElement(tr)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Телефон"))
    tr.addElement(cell)
    table.addElement(tr)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Дата блокировки"))
    tr.addElement(cell)
    table.addElement(tr)

    # i - Итератор. Используется при формировании стиля
    i = 2
    for line in users_blok:
        count_line = 1
        if (len(line['tarif']) > 20 or len(line['phone']) > 20 or
           len(line['address']) > 35):
            count_line += max(len(line['tarif']), len(line['phone'])) // 20
            count_line = max(count_line, len(line['address'])/35 + 1)

        # Создаём стиль строки с "правильной" высотой
        roheightcstm = Style(name="ro%i" % i, family="table-row")
        roheightcstm.addElement(
            TableRowProperties(rowheight="%fcm" % (count_line * 0.5))
        )
        report_ods.automaticstyles.addElement(roheightcstm)
        # Итератор больше не исполльзуется, потому его увеличиваем
        i += 1

        # Create a row (same as <tr> in HTML)
        tr = TableRow(stylename=roheightcstm)
        table.addElement(tr)

        # Login
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line['login']))
        tr.addElement(cell)
        table.addElement(tr)

        # Абонент
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line['user']))
        tr.addElement(cell)
        table.addElement(tr)

        # Адрес
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line['address']))
        tr.addElement(cell)
        table.addElement(tr)

        # Тариф
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line['tarif']))
        tr.addElement(cell)
        table.addElement(tr)

        # Телефон
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line['phone']))
        tr.addElement(cell)
        table.addElement(tr)

        # Дата блокировки
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line['date'].date()))
        tr.addElement(cell)
        table.addElement(tr)
    report_ods.spreadsheet.addElement(table)

    return report_ods


@login_required
def block_users_month(request, year='2017', month='01', ods_flag=False):
    '''Функция формирования отчёта по заблокированным пользователям
    за заданный месяц
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments year="%s" month="%s"' %
        (request.user, block_users_month.__name__, year, month)
    )

    # Формируем даты начала и конца периода
    date_start, date_stop = gen_report_begin_end_date(year, month)

    # Получаем список пользователей с блокировкой
    users_blok = fetch_users_block_month(date_start, date_stop)

    # Для выпадающего списка меню
    months_report = gen_last_months(last=12)

    if ods_flag:
        # Запрошен отчёт в ods файле
        response = HttpResponse(content_type='application/ods')
        response['Content-Disposition'] = 'attachment; filename=\
"block_users_%s%s.ods"' % (year, month)
        # Формируем ods файл
        report_ods = gen_ods_user_block_month(
            users_blok, date_start, date_stop
        )
        report_ods.write(response)
        return response

    # ods файл не запрошен
    context = {'blocks': users_blok,
               'date_begin': date_start,
               'months': months_report,
               }
    return render(request, 'audit/block_month.html', context)


def fetch_hardwares_remove(date_stat):
    '''Получить из БД список оборудования на снятие
    '''
    from audit.crmdict import hardware_type_list, status_device
    dbUTM = PgSqlDB()
    # Выбираем из базы билинга всех заблокированных пользователей
    sql = '''SELECT DISTINCT ON (t1.id) t1.login, t1.full_name,
t1.actual_address, t3.service_name, t1.mobile_telephone,
to_timestamp(t4.start_date) dateblock
FROM users t1 LEFT JOIN service_links t2 ON t1.basic_account=t2.account_id
LEFT JOIN services_data t3 ON t2.service_id=t3.id
LEFT JOIN blocks_info t4 ON t1.basic_account=t4.account_id
WHERE t1.login ~ '^\d\d\d\d\d$'
AND t1.is_deleted='0' AND t3.id<>614
AND to_timestamp(t4.start_date)<'%s'
AND to_timestamp(t4.expire_date)>'2030-01-01'
ORDER BY t1.id''' % date_stat

    users_block_lists = dbUTM.sqlQuery(sql)

    dbCrm = MySqlDB()

    # Нужно отсортировать по дате блокировки
    # Средствами postgres сортировать сложно из-за ограничений DISTINCT ON
    def l(x): return x[5]

    users_block = [
        {'login': user[0],
         'name': user[1],
         'address': user[2],
         'tarif': user[3],
         'phone': user[4],
         'date': user[5]}
        for user in sorted(users_block_lists, key=l, reverse=False)
    ]

    # У каждого заблокированного пользователя проверяем есть ли
    # не снятое оборудование
    # TODO: возможно эффективнее будет запросить все устройства и искать уже
    # в полученном списке. Надо проверить, что будет быстрее.
    for user in users_block:
        # Смотрим, есть ли у заблокированного пользователя железо
        sql = '''SELECT t1.name, t1.description, t2.status_c,
t2.hardware_types_c, t2.invnum_c
FROM po_po as t1 LEFT JOIN po_po_cstm t2 ON t1.id = t2.id_c
LEFT JOIN accounts t3 ON t2.account_id_c = t3.id
LEFT JOIN accounts_cstm t4 ON t3.id = t4.id_c
WHERE t4.login_ph_c = '%s'
''' % user['login']
        devices = dbCrm.sqlQuery(sql)
        if len(devices) == 0:
            continue
        # Отсекаем клиентов, у которых стоит только WiFi
        if len(devices) == 1 and (devices[0][3] == '101'or
                                  devices[0][3] == '116'):
            continue

        devices_humanly = [
            {'type': hardware_type_list.get(device[3], device[3]),
             'inventory': device[4],
             'name': device[0].replace('_', '').replace('-', ''),
             'desc': device[1],
             'status': status_device.get(device[2], device[2]),
             } for device in devices
        ]

        # devices используется в hw_remove (в шаблоне)
        # dev используется в gen_ods_hw_remove
        # надо бы вспомнить почему так (лучше переделать...)
        user['devices'] = devices_humanly
        user['dev'] = devices

    # Формируем список словарей пользователей, у которых есть что снять
    user_remove_hardware = [
        user for user in users_block if 'devices' in user
    ]

    return user_remove_hardware


def gen_ods_hardware_remove(hardwares, date_stat):
    # Библиотеки для формирования ods файлов
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.style import Style, TextProperties, TableColumnProperties, \
        TableCellProperties, TableRowProperties, ParagraphProperties
    from odf.text import P
    from odf.table import Table, TableColumn, TableRow, TableCell

    report_ods = OpenDocumentSpreadsheet()
    # Create a style for the table content. One we can modify
    # later in the spreadsheet.
    tablecontents = Style(name="Large number", family="table-cell")
    tablecontents.addElement(
        TextProperties(fontfamily="Arial", fontsize="10pt")
    )
    report_ods.styles.addElement(tablecontents)

    # Create automatic styles for the column widths.
    wideco1 = Style(name="co1", family="table-column")
    wideco1.addElement(
        TableColumnProperties(columnwidth="1.3cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco1)

    wideco2 = Style(name="co2", family="table-column")
    wideco2.addElement(
        TableColumnProperties(columnwidth="9.3cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco2)

    wideco3 = Style(name="co3", family="table-column")
    wideco3.addElement(
        TableColumnProperties(columnwidth="7.5cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco3)

    wideco4 = Style(name="co4", family="table-column")
    wideco4.addElement(
        TableColumnProperties(columnwidth="4.5cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco4)

    wideco5 = Style(name="co5", family="table-column")
    wideco5.addElement(
        TableColumnProperties(columnwidth="4.5cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco5)

    wideco6 = Style(name="co6", family="table-column")
    wideco6.addElement(
        TableColumnProperties(columnwidth="2.6cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco6)

    wideco7 = Style(name="co7", family="table-column")
    wideco7.addElement(
        TableColumnProperties(columnwidth="12.3cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco7)

    # Create automatic styles for the row widths.
    roheighthead = Style(name="ro1", family="table-row")
    roheighthead.addElement(TableRowProperties(rowheight="0.70cm"))
    report_ods.automaticstyles.addElement(roheighthead)

    roheight = Style(name="ro2", family="table-row")
    roheight.addElement(TableRowProperties(rowheight="3.00cm"))
    report_ods.automaticstyles.addElement(roheight)

    textcontent = Style(name="ce2", family="table-cell",
                        parentstylename=tablecontents)
    textcontent.addElement(
        TableCellProperties(border="0.74pt solid #000000",
                            wrapoption="wrap", verticalalign="middle")
    )
    report_ods.automaticstyles.addElement(textcontent)

    titlecontent = Style(name="ce0", family="table-cell",
                         parentstylename=tablecontents)
    titlecontent.addElement(TextProperties(fontweight="bold"))
    titlecontent.addElement(ParagraphProperties(textalign="center"))
    titlecontent.addElement(
        TextProperties(fontfamily="Arial", fontsize="12pt")
    )

    report_ods.automaticstyles.addElement(titlecontent)

    headtable = Style(name="ce3", family="table-cell",
                      parentstylename=tablecontents)
    headtable.addElement(TextProperties(fontweight="bold"))
    headtable.addElement(ParagraphProperties(textalign="center"))
    headtable.addElement(
        TextProperties(fontfamily="Arial", fontsize="10pt")
    )
    headtable.addElement(
        TableCellProperties(border="0.74pt solid #000000",
                            wrapoption="wrap", verticalalign="middle")
    )
    report_ods.automaticstyles.addElement(headtable)

    textcenter = Style(name="ce4", family="table-cell",
                       parentstylename=tablecontents)
    textcenter.addElement(ParagraphProperties(textalign="center"))
    textcenter.addElement(
        TableCellProperties(border="0.74pt solid #000000",
                            wrapoption="wrap", verticalalign="middle")
    )
    report_ods.automaticstyles.addElement(textcenter)

    # Start the table, and describe the columns
    table = Table(name="Снятие оборудования")

    # Create a column (same as <col> in HTML)
    # Make all cells in column default to currency
    table.addElement(
        TableColumn(stylename=wideco1, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco2, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco3, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco4, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco5, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco6, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco7, defaultcellstylename="ce1")
    )

    # Create a row (same as <tr> in HTML)
    tr = TableRow()
    table.addElement(tr)

    textCell = "Оборудование на снятие. Отчёт на %s" % (date_stat)
    cell = TableCell(stylename="ce0", valuetype="string",
                     value=textCell, numbercolumnsspanned="7",
                     numberrowsspanned="1")
    cell.addElement(P(text=textCell))
    tr.addElement(cell)
    table.addElement(tr)

    tr = TableRow(stylename=roheighthead)
    table.addElement(tr)

    # Отображаем названия полей
    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Логин"))
    tr.addElement(cell)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Абонент"))
    tr.addElement(cell)
    table.addElement(tr)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Адрес"))
    tr.addElement(cell)
    table.addElement(tr)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Тариф"))
    tr.addElement(cell)
    table.addElement(tr)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Телефон"))
    tr.addElement(cell)
    table.addElement(tr)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Дата блокировки"))
    tr.addElement(cell)
    table.addElement(tr)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Оборудование"))
    tr.addElement(cell)
    table.addElement(tr)

    # i - Итератор. Используется при формировании стиля
    i = 2
    for line in hardwares:
        count_line = len(line['devices'])
        for dev in line['devices']:
            dev_str = '%s (%s) - %s: %s %s' % (dev.get('type'),
                                               dev.get('inventory'),
                                               dev.get('status'),
                                               dev.get('name'),
                                               dev.get('desc'))
            if len(dev_str) > 50:
                count_line += 1

        # Создаём стиль строки с "правильной" высотой
        roheightcstm = Style(name="ro%i" % i, family="table-row")
        roheightcstm.addElement(
            TableRowProperties(rowheight="%fcm" % (count_line * 0.5))
        )
        report_ods.automaticstyles.addElement(roheightcstm)
        # Дальше итератор не используется, потому инкрементируем
        # (что бы не забыть это сделать потом)
        i += 1

        # Create a row (same as <tr> in HTML)
        tr = TableRow(stylename=roheightcstm)
        table.addElement(tr)

        # Login
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line.get('login')))
        tr.addElement(cell)
        table.addElement(tr)

        # Абонент
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line.get('name')))
        tr.addElement(cell)
        table.addElement(tr)

        # Адрес
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line.get('address')))
        tr.addElement(cell)
        table.addElement(tr)

        # Тариф
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line.get('tarif')))
        tr.addElement(cell)
        table.addElement(tr)

        # Телефон
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line.get('phone')))
        tr.addElement(cell)
        table.addElement(tr)

        # Дата блокировки
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text=line.get('date').strftime("%Y-%m-%d")))
        tr.addElement(cell)
        table.addElement(tr)

        # Оборудование
        cell = TableCell(stylename="ce2", valuetype="string")
        for dev in line['devices']:
            cell.addElement(
                P(text='%s (%s) - %s: %s %s' % (dev.get('type'),
                                                dev.get('inventory'),
                                                dev.get('status'),
                                                dev.get('name'),
                                                dev.get('desc')))
            )
        tr.addElement(cell)
        table.addElement(tr)
    report_ods.spreadsheet.addElement(table)

    return report_ods


@login_required
def hardware_remove(request, year='2017', month='01', day='01',
                    ods_flag=False):
    '''Функция формирования отчёта по списку оборудования на снятие
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments year="%s" month="%s"' %
        (request.user, hardware_remove.__name__, year, month)
    )

    date_stat = date(int(year), int(month), int(day))

    # Запрашиваем у БД список оборудования на снятие
    hardwares = fetch_hardwares_remove(date_stat)

    if ods_flag:
        # Запрошен отчёт в ods файле
        response = HttpResponse(content_type='application/ods')
        response['Content-Disposition'] = 'attachment; filename=\
"hw_remove_%s%s%s.ods"' % (year, month, day)

        # Формируем ods файл
        report_ods = gen_ods_hardware_remove(hardwares, date_stat)
        report_ods.write(response)

        return response

    # ods файл не запрошен
    months_report = gen_last_months(last=6)

    context = {'hw_removes': hardwares,
               'date_stat': date_stat,
               'months': months_report,
               }
    return render(request, 'audit/hw_remove.html', context)


def fetch_ticket_type_stat(db, date_begin, date_end):
    '''Функция генерации статистики по тикетам за заданный период.
    Определяет распределение тикетов по локализаци, по типам проведения работ,
    по ремени отсуствия сервиса у абонентов
    '''
    from audit.crmdict import bug_perform_list, bug_localisation_list

    sql = '''SELECT t1.bug_number, CONVERT_TZ(t1.date_entered,\
'+00:00','+03:00') AS date_entered, t2.status_bugs_c, t2.perform_c,
t2.localisation_c, t2.duration_bug_c, t1.id, t2.duration_min_c
FROM sugar.bugs t1 LEFT JOIN sugar.bugs_cstm t2 on t1.id=t2.id_c
WHERE t1.date_entered >='%s'  AND t1.date_entered <='%s' AND t1.deleted = '0'
ORDER BY t1.bug_number
    ''' % (date_begin, date_end)

    tickets = db.sqlQuery(sql)

    ticket_local_stat = {}  # Словарь со статистикой по локализации тикетов
    # no_loc = 0  # Количество тикетов, у которых нет локализации
    ticket_perf_stat = {}  # Словарь со статистикой по проведённым работам
    # no_perf = 0  # Количество тикетов, у которых нет типа работ

    for ticket in tickets:
        # Собираем статистику по локализации проблемы
        if ticket[4]:
            # Локализаций может быть несколько, разделяются запятыми
            for loc in ticket[4].split(','):
                localization = bug_localisation_list.get(loc, loc)
                ticket_local_stat.setdefault(localization, 0)
                ticket_local_stat[localization] += 1
        else:
            ticket_local_stat.setdefault('Не задано', 0)
            ticket_local_stat['Не задано'] += 1
            # no_loc += 1
        # Собираем статистику проведённых работ
        if ticket[3]:
            # Типов работ может быть несколько, разделяются запятыми
            for perf in ticket[3].split(','):
                perform = bug_perform_list.get(perf, perf)
                ticket_perf_stat.setdefault(perform, 0)
                ticket_perf_stat[perform] += 1
        else:
            ticket_perf_stat.setdefault('Не задано', 0)
            ticket_perf_stat['Не задано'] += 1
            # no_perf += 1

    # Формируем сортированный список из словаря
    def l(x): return x[1]
    ticket_local_list = sorted(ticket_local_stat.items(), key=l, reverse=True)
    ticket_perf_list = sorted(ticket_perf_stat.items(), key=l, reverse=True)

    # Cловарь, который мы возвращаем в return
    tickets_stat = {'all': len(tickets),  # Всего тикетов
                    # Тикетов без локализации
                    'no_loc': ticket_local_stat.get('Не задано', 0),
                    # Тикетов без типов работ
                    'no_perf': ticket_perf_stat.get('Не задано', 0),
                    # Статистика по локализации тикетов
                    'ticket_local_stat': ticket_local_list,
                    # Статистика по проведённым работам
                    'ticket_perf_stat': ticket_perf_list,
                    }
    return tickets_stat


def fetch_tickets_open_stat_day(db, date_report):
    '''Функция формирования статистики за заданный день
    db - экземпляр класса SqlDB
    date_report - дата, на начало которой формируется отчёт
    Возвращаемые значения:
    tickets - перечень открытых тикетов
    group_stats - статистика по группам
    create_ticket - количество созданых тикетов в предыдущий день
    '''
    sql = '''SELECT t1.bug_number, CONVERT_TZ(t1.date_entered,'+00:00',\
'+03:00'),
CONVERT_TZ(t2.date_close_c, '+00:00','+03:00'),
t2.status_bugs_c, t2.department_bugs_c
FROM bugs t1 LEFT JOIN bugs_cstm t2 ON t1.id = t2.id_c
WHERE CONVERT_TZ(t1.date_entered,'+00:00','+03:00') < '%s 00:00:00'
AND (CONVERT_TZ(t2.date_close_c, '+00:00','+03:00') > '%s 00:00:00'
OR (t2.date_close_c IS NULL AND t2.status_bugs_c = 'open'))
AND t1.deleted = 0
    ''' % (date_report.strftime('%Y-%m-%d'), date_report.strftime('%Y-%m-%d'))

    tickets = db.sqlQuery(sql)

    # group_stats используется для формирования статистики открытых тикетов
    # по каждой группе
    group_stats = {}
    # считаем количество тикетов в каждой группе
    for ticket in tickets:
        group_stats.setdefault(ticket[4], 0)
        group_stats[ticket[4]] += 1

    # Cмотрим, сколько тикетов было открыто за предыдущий день
    sql = '''SELECT COUNT(t1.bug_number)
FROM bugs t1 LEFT JOIN bugs_cstm t2 ON t1.id = t2.id_c
WHERE t1.date_entered BETWEEN '%s 00:00:00' AND '%s 00:00:00'
AND t1.deleted = 0
    ''' % ((date_report - timedelta(days=1)).strftime('%Y-%m-%d'),
           date_report.strftime('%Y-%m-%d'))

    count_ticket_yesterday_list = db.sqlQuery(sql)
    count_ticket_yesterday = \
        count_ticket_yesterday_list[0][0] \
        if len(count_ticket_yesterday_list) == 1 else 0

    tickets_dict = {
        'count_open': len(tickets),
        'count_create_yesterday': count_ticket_yesterday,
        'count_tp': group_stats.get('tp', 0),
        'count_rs': group_stats.get('rs', 0),
        'count_tf': group_stats.get('tf', 0),
        'count_pd': group_stats.get('pd', 0),
        'date': date_report,
    }
    return tickets_dict


def fetch_tickets_open_stat(dbCrm, date_begin, date_end):
    '''Вывод статистики по открытым тикетам за интересующий период
    date_begin - дата начала (datetime.date)
    date_end - дата окончания (datetime.date)
    Возвращает:
    tickets_open - словарь с отчётом
    '''

    dates = [
        date_begin + timedelta(days=offset)
        for offset in range((date_end - date_begin).days)
    ]

    tickets_open_stat = [
        fetch_tickets_open_stat_day(dbCrm, date_current)
        for date_current in dates
    ]

    return tickets_open_stat


def tickets_open(request, year='', month='', csv_flag=False, last='month'):
    '''Вывод статистики по открытым тикетам
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, tickets_open.__name__, last, year, month)
    )

    # Коннектимся к БД CRM
    db = MySqlDB()

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    # Получаем статистику по открытым тикетам
    tickets_open_stat = fetch_tickets_open_stat(db, date_begin, date_end)

    # Получаем статистику по типам тикетов
    tickets_type_stat = fetch_ticket_type_stat(db, date_begin, date_end)

    if csv_flag:
        import csv
    # Формриуем csv файл, статистику на каждый день, интересующего нас периода
    # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=\
"ticket_open_%s_%s.csv"' % (date_begin.strftime('%Y%m%d'),
                            date_end.strftime('%Y%m%d'))

        writer = csv.DictWriter(
            response,
            fieldnames=['date', 'count_open', 'count_create_yesterday',
                        'count_tp', 'count_rs', 'count_tf', 'count_pd']
        )
        writer.writeheader()
        for ticket in tickets_open_stat:
            writer.writerow(ticket)

        return response

    # Формируем HTML
    months_report = gen_last_months(last=12)
    years_report = gen_last_years(3)
    type_report = gen_type_report(year=year, month=month)

    context = {'tickets': tickets_open_stat,
               'tickets_stat': tickets_type_stat,
               'type': 'month',
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'years': years_report,
               'type': type_report,
               'menu_url': '/audit/tickets/',
               }
    return render(request, 'audit/tickets_open.html', context)


def fetch_tickets_bad_fill(date_begin, date_end):
    '''Функция генерации статистики по тикетам за заданный период.
    Определяет распределение тикетов по локализаци, по типам проведения работ,
    по ремени отсуствия сервиса у абонентов
    '''
    from audit.crmdict import bug_perform_list, bug_localisation_list

    db = MySqlDB()

    sql = '''SELECT t1.id, t1.bug_number, CONVERT_TZ(t1.date_entered,'+00:00',\
'+03:00'),
CONVERT_TZ(t2.date_close_c, '+00:00','+03:00'), t2.department_bugs_c,
t2.status_bugs_c, t2.perform_c, t2.localisation_c, t2.duration_bug_c,
t2.duration_min_c
FROM bugs t1 LEFT JOIN bugs_cstm t2 ON t1.id = t2.id_c
WHERE t1.date_entered >= '%s' AND t1.date_entered <= '%s'
AND (t2.perform_c is Null OR t2.perform_c = ''
OR t2.perform_c = 'none'
OR t2.localisation_c is Null OR t2.localisation_c = ''
OR t2.localisation_c = 'none')
AND NOT t2.status_bugs_c = 'open' AND t1.deleted = 0
    ''' % (date_begin, date_end + timedelta(days=1))

    tickets = db.sqlQuery(sql)

    tickets_dicts = []
    for ticket in tickets:
        # Переводим локализации из терминов CRM в человеческий язык
        # Формируем список
        localization = [
            bug_localisation_list.get(loc, loc)
            for loc in ticket[7].split(',')
            if (ticket[7] is not None or ticket[7] == '')
        ]

        # Переводим выполненые работы из терминов CRM  в человеческий язык
        # Формируем список
        perform = [
            bug_perform_list.get(perf, perf)
            for perf in ticket[6].split(',')
            if (ticket[6] is not None or ticket[6] == '')
        ]

        # Расчитываем время отсутствия сервиса
        duration = ticket[8] if ticket[8] is not None else 0.0

        if ticket[9] is not None:
            duration += round(ticket[9]/60, 2)

        tickets_dicts.append(
            {'id': ticket[0],               # id тикета
             'number': ticket[1],           # номер тикета
             'date_entered': ticket[2],     # дата создания
             'date_close': ticket[3],       # дата закрытия тикета
             'group': ticket[4],            # ответственная группа
             'status': ticket[5],           # статус тикета
             'perform': perform,            # список выполненных работ
             'loc': localization,           # локализация
             'dur': duration, }             # остановка сервиса
        )
    return tickets_dicts


@login_required
def tickets_bad_fill(request, year='', month='', csv_flag=False, last='month'):
    '''Вывод списка неверно оформленных тикетов
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, tickets_bad_fill.__name__, last, year, month)
    )

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    tickets = fetch_tickets_bad_fill(date_begin, date_end)

    if csv_flag:
        import csv

    # Формируем csv файл, статистику на каждый день, интересующего нас периода
    # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=\
"ticket_bad_month_%s_%s.csv"' % (date_begin.strftime('%Y%m%d'),
                                 date_end.strftime('%Y%m%d'))

        writer = csv.writer(response)
        writer.writerow(['number', 'date_entered', 'date_close', 'group',
                         'status', 'perform', 'localization', 'duration'])
        for ticket in tickets:
            writer.writerow(
                [ticket.get('number'), ticket.get('date_entered'),
                 ticket.get('date_close'), ticket.get('group'),
                 ticket.get('status'),
                 ', '.join(ticket.get('perform')),
                 ', '.join(ticket.get('loc')), ticket.get('dur')]
            )
        return response

    # Флаг csv_flag не задан
    months_report = gen_last_months(last=12)
    type_report = gen_type_report(year, month)

    context = {'tickets': tickets,
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'type': type_report,
               'menu_url': '/audit/tickets/bad_fill/',
               }
    return render(request, 'audit/bad_fill.html', context)


def gen_ods_repairs_dublicate(repairs_dub):
    # Библиотеки для формирования ods файлов
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.style import Style, TextProperties, TableColumnProperties, \
        TableCellProperties, TableRowProperties, ParagraphProperties
    from odf.text import P
    from odf.table import Table, TableColumn, TableRow, TableCell

    report_ods = OpenDocumentSpreadsheet()
    tablecontents = Style(name="Large number", family="table-cell")
    tablecontents.addElement(
        TextProperties(fontfamily="Arial", fontsize="10pt")
    )
    report_ods.styles.addElement(tablecontents)

    # Create automatic styles for the column widths.
    wideco1 = Style(name="co1", family="table-column")
    wideco1.addElement(
        TableColumnProperties(columnwidth="3.5cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco1)

    wideco2 = Style(name="co2", family="table-column")
    wideco2.addElement(
        TableColumnProperties(columnwidth="13.0cm", breakbefore="auto")
    )
    report_ods.automaticstyles.addElement(wideco2)

    # Create automatic styles for the row widths.
    roheighthead = Style(name="ro1", family="table-row")
    roheighthead.addElement(TableRowProperties(rowheight="0.50cm"))
    report_ods.automaticstyles.addElement(roheighthead)

    roheight = Style(name="ro2", family="table-row")
    roheight.addElement(TableRowProperties(rowheight="2.00cm"))
    report_ods.automaticstyles.addElement(roheight)

    titlecontent = Style(name="ce0", family="table-cell",
                         parentstylename=tablecontents)
    titlecontent.addElement(TextProperties(fontweight="bold"))
    titlecontent.addElement(ParagraphProperties(textalign="center"))
    titlecontent.addElement(
        TextProperties(fontfamily="Arial", fontsize="12pt")
    )
    report_ods.automaticstyles.addElement(titlecontent)

    headtable = Style(
        name="ce3", family="table-cell", parentstylename=tablecontents
    )
    headtable.addElement(TextProperties(fontweight="bold"))
    headtable.addElement(ParagraphProperties(textalign="center"))
    headtable.addElement(TextProperties(
        fontfamily="Arial", fontsize="10pt"))
    headtable.addElement(
        TableCellProperties(border="0.74pt solid #000000",
                            wrapoption="wrap",
                            verticalalign="middle")
    )
    report_ods.automaticstyles.addElement(headtable)

    textcenter = Style(name="ce4", family="table-cell",
                       parentstylename=tablecontents)
    textcenter.addElement(ParagraphProperties(textalign="center"))
    textcenter.addElement(
        TableCellProperties(border="0.74pt solid #000000",
                            wrapoption="wrap",
                            verticalalign="middle")
    )
    report_ods.automaticstyles.addElement(textcenter)

    text_cell = Style(
        name="ce5", family="table-cell", parentstylename=tablecontents
    )
    text_cell.addElement(
        TableCellProperties(border="0.74pt solid #000000",
                            wrapoption="wrap",
                            verticalalign="middle")
    )
    report_ods.automaticstyles.addElement(text_cell)

    # Start the table, and describe the columns
    table = Table(name="Повторные ремонты")

    # Create a column (same as <col> in HTML)
    # Make all cells in column default to currency
    table.addElement(
        TableColumn(stylename=wideco1, defaultcellstylename="ce1")
    )
    table.addElement(
        TableColumn(stylename=wideco2, defaultcellstylename="ce1")
    )
    tr = TableRow()
    table.addElement(tr)

    textCell = "Повторные ремонты"
    cell = TableCell(stylename="ce0", valuetype="string",
                     value=textCell, numbercolumnsspanned="2",
                     numberrowsspanned="1")
    cell.addElement(P(text=textCell))
    tr.addElement(cell)
    table.addElement(tr)

    # Создаём новую строку
    tr = TableRow(stylename=roheighthead)
    table.addElement(tr)

    # Отображаем названия полей
    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Дата"))
    tr.addElement(cell)

    cell = TableCell(stylename="ce3", valuetype="string")
    cell.addElement(P(text="Описание"))
    tr.addElement(cell)
    table.addElement(tr)

    # Формируем тело таблицы
    # i - Итератор. Используется при формировании стиля
    i = 2
    for repair in repairs_dub:
        repair_new = repair.get('new')
        repairs_old = repair.get('old')

        # Создаём строку с названием контрагента
        tr = TableRow(stylename=roheighthead)
        table.addElement(tr)
        cell_acc = TableCell(stylename="ce3", valuetype="string",
                             value=textCell, numbercolumnsspanned="2",
                             numberrowsspanned="1")
        text_cell = '%s - %s' % (repair_new.get('account'),
                                 repair_new.get('address'))
        cell_acc.addElement(P(text=text_cell))
        tr.addElement(cell_acc)
        table.addElement(tr)

        # Создаём строку с новым ремонтом
        count_line = 5
        if repair_new.get('description'):
            count_line += len(repair_new.get('description'))//60
        if repair_new.get('name'):
            count_line += len(repair_new.get('name'))//60
        if repair_new.get('comment'):
            count_line += len(repair_new.get('comment'))//60

        # Создаём стиль строки с "правильной" высотой
        roheightcstm = Style(name="ro%i" % i, family="table-row")
        roheightcstm.addElement(
            TableRowProperties(rowheight="%fcm" % (count_line * 0.5))
        )
        report_ods.automaticstyles.addElement(roheightcstm)
        # Итератор больше не используется, потому его увеличиваем
        i += 1

        tr = TableRow(stylename=roheightcstm)
        cell = TableCell(stylename="ce4", valuetype="string")
        cell.addElement(P(text='%s' % repair_new.get('date')))
        cell.addElement(P(text=repair_new.get('user')))
        tr.addElement(cell)

        cell = TableCell(stylename="ce5", valuetype="string")
        text_cell = 'Статус: %s' % (repair_new.get('status'))
        cell.addElement(P(text=text_cell))
        text_cell = 'Задание: %s' % (repair_new.get('name'))
        cell.addElement(P(text=text_cell))
        text_cell = 'Описание: %s' % (repair_new.get('description'))
        cell.addElement(P(text=text_cell))
        if not repair_new.get('comment') == '':
            text_cell = 'Комментарий: %s' % (repair_new.get('comment'))
            cell.addElement(P(text=text_cell))
        tr.addElement(cell)

        table.addElement(tr)

        # Создаём строки с повторными ремонтами
        for repair in repairs_old:
            count_line = 5
            if repair.get('description'):
                count_line += len(repair.get('description'))//60
            if repair.get('name'):
                count_line += len(repair.get('name'))//60
            if repair.get('comment'):
                count_line += len(repair.get('comment'))//60

            # Создаём стиль строки с "правильной" высотой
            roheightcstm = Style(name="ro%i" % i, family="table-row")
            roheightcstm.addElement(
                TableRowProperties(rowheight="%fcm" % (count_line * 0.5))
            )
            report_ods.automaticstyles.addElement(roheightcstm)
            # Итератор больше не исполльзуется, потому его увеличиваем
            i += 1

            tr = TableRow(stylename=roheightcstm)
            cell = TableCell(stylename="ce4", valuetype="string")
            cell.addElement(P(text='%s' % repair.get('date')))
            cell.addElement(P(text=repair.get('user')))
            tr.addElement(cell)

            cell = TableCell(stylename="ce5", valuetype="string")
            text_cell = 'Статус: %s' % (repair.get('status'))
            cell.addElement(P(text=text_cell))
            text_cell = 'Задание: %s' % (repair.get('name'))
            cell.addElement(P(text=text_cell))
            text_cell = 'Описание: %s (%s)' % (repair.get('description'),
                                               repair.get('address'))
            cell.addElement(P(text=text_cell))
            if not repair.get('comment') == '':
                text_cell = 'Комментарий: %s' % (repair.get('comment'))
                cell.addElement(P(text=text_cell))
            tr.addElement(cell)
            table.addElement(tr)
    report_ods.spreadsheet.addElement(table)
    return report_ods


@login_required
def repairs_dublicate(request, year='', month='', last='month',
                      ods_flag=False):
    '''Функция формирования статистики по повторным ремонтам
    year - стастика за конкретный год
    month - статистика за конкретный месяц
    last - статистика за последнее время
        last = 'month' - за последние 30 дней
        last = 'year' - за последний год
    '''
    from audit.crmdict import repair_status

    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, repairs_dublicate.__name__, last, year, month)
    )

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    # Ищем в базе ремонты
    db = MySqlDB()

    sql = '''SELECT t1.name, t1.description, t2.comment_c, t3.last_name,
t2.address_c, t4.name, t2.account_id_c, t2.status_c, t2.date_of_completion_c,
t1.id
FROM sugar.rep_repairs t1 LEFT JOIN sugar.rep_repairs_cstm t2 on t1.id=t2.id_c
LEFT JOIN sugar.users t3 on t2.user_id_c=t3.id
LEFT JOIN sugar.accounts t4 on t4.id=t2.account_id_c
WHERE t2.date_of_completion_c BETWEEN '%s' AND '%s' AND NOT t4.id =''
AND t1.deleted = 0
ORDER BY t2.date_of_completion_c DESC
    ''' % (date_begin, date_end + timedelta(days=1))

    repairs = db.sqlQuery(sql)

    repairs_dub_dicts = []

    for repair in repairs:
        # Словарь используем для наглядности
        repair_dict = {'name': repair[0],
                       'description': repair[1],
                       'comment': repair[2],
                       'user': repair[3],
                       'address': repair[4],
                       'account': repair[5],
                       'account_id': repair[6],
                       'status': repair_status.get(repair[7], repair[7]),
                       'date': repair[8],
                       'id': repair[9],
                       }

        # Ищем повторяющиеся ремонты за предыдущие 30*6 дней
        sql = '''SELECT t1.name, t1.description, t2.comment_c, t3.last_name,
t2.address_c, t4.name, t2.account_id_c, t2.status_c, t2.date_of_completion_c,
t1.id
FROM sugar.rep_repairs t1 LEFT JOIN sugar.rep_repairs_cstm t2 ON t1.id=t2.id_c
LEFT JOIN sugar.users t3 ON t2.user_id_c=t3.id
LEFT JOIN sugar.accounts t4 ON t4.id=t2.account_id_c
WHERE t2.date_of_completion_c BETWEEN '%s' AND '%s'
AND NOT t1.id = '%s' AND t4.id ='%s'
AND t1.deleted = 0
ORDER BY t2.date_of_completion_c DESC
        ''' % (repair_dict['date'] - timedelta(days=30*6), repair_dict['date'],
               repair_dict['id'], repair_dict['account_id'])

        repairs_old = db.sqlQuery(sql)

        if len(repairs_old) == 0:
            # повторный ремонтов нет - переходим к следующей записи
            continue
        # У контрагента ранее выполняли ремонты
        repairs_old_dicts = [
            {'name': repair_old[0],
             'description': repair_old[1],
             'comment': repair_old[2],
             'user': repair_old[3],
             'address': repair_old[4],
             'account': repair_old[5],
             'account_id': repair_old[6],
             'status': repair_status.get(repair_old[7]),
             'date': repair_old[8],
             'id': repair_old[9],
             } for repair_old in repairs_old
        ]

        # Запрашиваем тикеты по данному контрагенту за последние 365 дней
        sql = '''SELECT t1.bug_number, t1.date_entered, t1.id
FROM bugs t1 LEFT JOIN bugs_cstm t2 ON t1.id = t2.id_c
LEFT JOIN accounts_bugs t3 ON t3.bug_id = t1.id
WHERE t3.account_id = '%s' AND t1.date_entered >= '%s'
ORDER BY t1.bug_number DESC
        ''' % (repair_dict['account_id'],
               repair_dict['date'] - timedelta(days=365))

        bugs = db.sqlQuery(sql)
        bugs_dicts = [
            {'number': bug[0],
             'date': bug[1],
             'id': bug[2],
             } for bug in bugs
        ]

        repairs_dub_dicts.append(
            {'new': repair_dict,
             'old': repairs_old_dicts,
             'bugs': bugs_dicts}
        )

    if ods_flag:
        response = HttpResponse(content_type='application/ods')
        response['Content-Disposition'] = 'attachment; filename=\
"repair_dublicat_%s_%s.ods"' % (date_begin, date_end)
        report_ods = gen_ods_repairs_dublicate(repairs_dub_dicts)
        report_ods.write(response)
        return response

    # формируем html
    months_report = gen_last_months(last=12)
    years_report = gen_last_years(last=5)
    type_report = gen_type_report(year=year, month=month)

    context = {'repairs': repairs_dub_dicts,
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'years': years_report,
               'type': type_report,
               'menu_url': '/audit/repairs/dublicate/',
               }
    return render(request, 'audit/repairs_dublicate.html', context)


def gen_repairs_stat_periods(repairs_list, periods):
    '''Формируем статистику ремонтов
    '''
    from audit.crmdict import repair_status

    statistic = []
    for date_begin, date_end in periods:
        # Формируем список ремонтов за текущий период
        repeirs_cur = [
            repair
            for repair in repairs_list
            if (repair.get('date') >= date_begin and
                repair.get('date') < date_end)
        ]

        # Считаем количество ремонтов за период
        count_repairs = len(repeirs_cur)

        # Считаем количество выполненных ремонтов
        count_repeirs_done = 0
        for repair in repeirs_cur:
            if repair.get('status') == repair_status.get('four'):
                count_repeirs_done += 1
        # Сохраняем данные по периоду в словаре
        statistic.append(
            {'count_all': count_repairs,
             'count_done': count_repeirs_done,
             'date': date_begin}
        )
    return statistic


@login_required
def repairs_stat(request, year='', month='', csv_flag=False, last='month'):
    '''Функция формирования статистики по выполненным ремонтам
    year - стастика за конкретный год
    month - статистика за конкретный месяц
    last - статистика за последнее время
        last = 'month' - за последние 30 дней
        last = 'year' - за последний год
    '''
    from itertools import groupby
    from audit.crmdict import repair_status, cat_work

    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, repairs_stat.__name__, last, year, month)
    )

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    # Ищем в базе ремонты
    sql = '''SELECT t1.name, t1.description, t2.comment_c, t3.last_name,
t2.address_c, t4.name, t2.account_id_c, t2.status_c, t2.date_of_completion_c,
t1.id, t2.new_cat_work_c
FROM sugar.rep_repairs t1 LEFT JOIN sugar.rep_repairs_cstm t2 on t1.id=t2.id_c
LEFT JOIN sugar.users t3 on t2.user_id_c=t3.id
LEFT JOIN sugar.accounts t4 on t4.id=t2.account_id_c
WHERE t2.date_of_completion_c BETWEEN '%s' AND '%s'
AND t1.deleted = 0
ORDER BY t2.date_of_completion_c DESC
    ''' % (date_begin, date_end + timedelta(days=1))

    db = MySqlDB()

    repairs = db.sqlQuery(sql)

    repairs_list = [
        {'name': repair[0],
         'description': repair[1],
         'comment': repair[2],
         'user': repair[3] if repair[3] else 'Исполнитель не задан',
         'address': repair[4],
         'account': repair[5],
         'account_id': repair[6],
         'status': repair_status.get(repair[7], repair[7]),
         'date': repair[8],
         'id': repair[9],
         'cat_work': cat_work.get(repair[10], 'Категория работ не задана'),
         } for repair in repairs
    ]

    # Разбиваем отчётный период на отрезки
    periods = gen_report_periods(date_begin, date_end)

    # Формируем статистику
    repairs_man_stat = {}
    stat_period_all = gen_repairs_stat_periods(repairs_list, periods)
    repairs_man_stat['all'] = stat_period_all

    # Разбиваем работы по исполнителям и считаем статистику по каждому из них
    def sort_user(x): return x.get('user')
    for k, g in groupby(sorted(repairs_list, key=sort_user), sort_user):
        repairs_man = list(g)
        repairs_man_stat[k] = gen_repairs_stat_periods(repairs_man, periods)

    # Разбиваем работы по категориям работ и считаем по каждой статистику
    repairs_cat_work_stat = {}
    repairs_cat_work_stat['all'] = stat_period_all

    def sort_cat_work(x): return x.get('cat_work')
    for k, g in groupby(sorted(repairs_list, key=sort_cat_work),
                        sort_cat_work):
        repairs_cat_work = list(g)
        repairs_cat_work_stat[k] = gen_repairs_stat_periods(
            repairs_cat_work, periods
        )

    months_report = gen_last_months(last=12)
    years_report = gen_last_years(last=5)
    type_report = gen_type_report(year=year, month=month)

    context = {'repairs': repairs_list,
               'repairs_man_stat': repairs_man_stat,
               'repairs_cat_work_stat': repairs_cat_work_stat,
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'years': years_report,
               'type': type_report,
               'menu_url': '/audit/repairs/',
               }
    return render(request, 'audit/repairs.html', context)


@login_required
def top_tickets(request, year='', month='', last='month', csv_flag=False):
    '''Функция формирования абонентов с большим количеством тикетов
    year - стастика за конкретный год
    month - статистика за конкретный месяц
    last - статистика за последнее время
        last = 'month' - за последние 30 дней
        last = 'year' - за последний год
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, top_tickets.__name__, last, year, month)
    )

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    sql = '''SELECT t4.name, t4.billing_address_street, t3.account_id, \
COUNT(t1.id) count_bug
FROM bugs t1 LEFT JOIN bugs_cstm t2 ON t1.id = t2.id_c
LEFT JOIN accounts_bugs t3 ON t3.bug_id = t1.id
LEFT JOIN accounts t4 ON t4.id = t3.account_id
WHERE t1.date_entered >= '%s' AND t1.date_entered < '%s' AND t1.deleted = 0
AND t3.account_id IS NOT NULL AND t3.bug_id IS NOT NULL
AND NOT t3.account_id = '90657094-4fdd-9c4c-dc07-559b8ff0c6ea'
AND NOT t3.account_id = '581c9d33-2f3f-88e3-9d28-55e052c92010'
GROUP BY t3.account_id
ORDER BY count_bug DESC
    ''' % (date_begin, date_end + timedelta(days=1))

    db = MySqlDB()

    accounts = db.sqlQuery(sql)
    accounts_many_bugs_dicts = [
        {'account': account[0],
         'address': account[1],
         'account_id': account[2],
         'count_bug': account[3],
         } for account in accounts if account[3] > 1
    ]

    for account in accounts_many_bugs_dicts:
        # Запрашиваем все тикеты по данному контрагенту
        sql = '''SELECT t1.bug_number, t1.date_entered, t1.id
FROM bugs t1 LEFT JOIN bugs_cstm t2 ON t1.id = t2.id_c
LEFT JOIN accounts_bugs t3 ON t3.bug_id = t1.id
WHERE t3.account_id = '%s'
ORDER BY t1.bug_number DESC
        ''' % (account['account_id'])
        bugs = db.sqlQuery(sql)
        # Свежие тикеты
        account['bugs'] = [
            {'number': bug[0],
             'date': bug[1],
             'id': bug[2],
             } for bug in bugs if bug[1].date() >= date_begin
        ]
        # Старые тикеты
        account['bugs_old'] = [
            {'number': bug[0],
             'date': bug[1],
             'id': bug[2],
             } for bug in bugs if bug[1].date() < date_begin
        ]

    context = {'accounts': accounts_many_bugs_dicts,
               'date_begin': date_begin,
               'date_end': date_end,
               'menu_url': '/audit/top_tickets/',
               }
    return render(request, 'audit/top_tickets.html', context)


@login_required
def top_calls(request, year='', month='', last='month', csv_flag=False):
    '''Функция формирования топ телефонных звонков в тех. поддержку
    year - стастика за конкретный год
    month - статистика за конкретный месяц
    last - статистика за последнее время
        last = 'month' - за последние 30 дней
        last = 'year' - за последний год
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,

                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
            'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
            (request.user, top_calls.__name__, last, year, month)
        )

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    # Запрашиваем список телефонных номеров с количеством вонков в саппорт
    db = MySqlDB()
    sql = '''SELECT SUBSTRING_INDEX(SUBSTRING_INDEX(t1.name,' ', -3),' ',1) \
phone,
count(t1.id) count_calls, t2.accounts_calls_1accounts_ida account_id, t3.name
FROM sugar.calls t1 LEFT JOIN sugar.accounts_calls_1_c t2 \
ON t1.id = t2.accounts_calls_1calls_idb
LEFT JOIN accounts t3 ON t2.accounts_calls_1accounts_ida = t3.id
WHERE t1.direction = 'Inbound' AND t1.status = 'autoheld'
AND t1.created_by = "9daf7540-986e-8385-7040-55b63cc60145"
AND t1.date_start BETWEEN "%s"  AND "%s"
AND  NOT (t1.name LIKE "%%226333%%" OR t1.name LIKE "%%227485%%"
OR t1.name LIKE "%%227012%%" OR t1.name LIKE "%%226012%%"
OR t1.name LIKE "%%227081%%" OR t1.name LIKE "%%226081%%"
OR SUBSTRING_INDEX(SUBSTRING_INDEX(t1.name,' ', -3),' ',1) = "226002")
GROUP BY phone
ORDER BY count_calls DESC
    ''' % (date_begin, date_end)

    calls = db.sqlQuery(sql)

    calls_dicts = [
        {'number': call[0],
         'count_calls': call[1],
         'account_id': call[2],
         'account': call[3],
         } for call in calls
    ]
    for call in calls_dicts:
        # Запрашиваем список тикетов по каждому абонету
        sql = '''SELECT t1.bug_number, t1.date_entered, t1.id
FROM bugs t1 LEFT JOIN bugs_cstm t2 ON t1.id = t2.id_c
LEFT JOIN accounts_bugs t3 ON t3.bug_id = t1.id
WHERE t3.account_id = '%s'
ORDER BY t1.bug_number DESC
        ''' % call['account_id']

        bugs = db.sqlQuery(sql)
        # Свежие тикеты
        call['bugs'] = [
            {'number': bug[0],
             'date': bug[1],
             'id': bug[2],
             } for bug in bugs if bug[1].date() >= date_begin
        ]
        # Старые тикеты
        call['bugs_old'] = [
            {'number': bug[0],
             'date': bug[1],
             'id': bug[2],
             } for bug in bugs if bug[1].date() < date_begin
        ]

    context = {'calls': calls_dicts,
               'date_begin': date_begin,
               'date_end': date_end,
               'menu_url': '/audit/top_calls/',
               }
    return render(request, 'audit/top_calls.html', context)


def find_account_in_line(account, line):
    '''Поиск в строке названия организации
    возвращаем True, если название организации в строке найдено
    False - не найдено
    '''
    # Ищем в начале строки название организации
    find_acc = line[:10+len(account)].find(account)
    if find_acc == -1:
        return False

    # С целью уменьшения ложных срабатываний проверяем, что после названия
    # организации стоит пробел, точка, запятая или строка уже кончилась
    end_char = find_acc+len(account)
    if not (line[end_char:end_char+1] == '' or
            line[end_char:end_char+1] == ' ' or
            line[end_char:end_char+1] == '.' or
            line[end_char:end_char+1] == ','):
        return False

    # Перед названием организации должен быть пробел, или это начало строки
    if not (find_acc == 0 or line[find_acc-1:find_acc] == ' '):
        return False

    return True


def find_account_in_desc(account, description):
    '''Поиск в тексте описания тикета названия организации
    возвращаем True, если название организации в строке найдено
    False - не найдено
    '''

    # поскольку в описании название организации может не вполне
    # соответствовать записи в crm пытаемся удалить "лишнее"
    account = account.lower().replace(',', '').replace('ооо', '').\
        replace('зао', '').replace('ип', '').strip()
    if (account == 'точка' or account == 'мария' or
        account == 'статус' or account == 'объект' or
            account == 'виктория'):
        # Это особые организации, которые создаёт кучу ложных
        # срабатываний, поэтому сразу говорим, что ничего не нашли...
        return False

    # Флаг "найден ли контрагент"
    find_acc = False

    # Переформатируем description
    description = description.lower().replace(',', '').replace('\r', '').\
        replace('(', ' ').replace(')', ' ').replace('"', ' ').\
        replace('\'', ' ')
    for line in description.splitlines():
        # Смотрим описание построчно
        find_acc = find_account_in_line(account, line)
        if find_acc:
            # если контрагент найден, дальше строки смотреть не надо
            break

    return find_acc


def find_account_in_link_bugs(account_id, links_dicts):
    '''Функция поиска в связках accounts_bugs интересующего нас контрагента
    по id
    '''
    for link in links_dicts:
        # ищем в связях контрагент-тикет нашего контрагента
        if account_id == link['id']:
            # нашли абонента, больше нет смысла смотреть связки
            return True
    return False


def fetch_bugs_mass(date_begin, date_end):
    '''Получить список масовых тикетов
    '''
    db = MySqlDB()
    # Получаем все тикеты за интересующий нас период
    sql = '''SELECT t1.id, LOWER(t1.description), t1.date_entered, \
t1.bug_number
FROM sugar.bugs t1
WHERE t1.date_entered BETWEEN '%s' AND '%s'
AND NOT t1.description = ''
    ''' % (date_begin, date_end + timedelta(days=1))

    bugs = db.sqlQuery(sql)

    # Получаем всех контрагентов
    sql = '''SELECT t1.id, LOWER(t1.name)
FROM sugar.accounts t1 LEFT JOIN sugar.accounts_cstm t2 ON t1.id = t2.id_c
WHERE t2.status_acc_c= 'active' AND t2.company_acc_c = 1 AND t1.deleted = 0
    '''
    accounts = db.sqlQuery(sql)

    # ищем массовые тикеты
    bugs_mass = []
    for bug in bugs:
        # Запрашиваем все связи с контрагентами
        sql = '''SELECT t1.account_id, t2.name
FROM accounts_bugs t1 LEFT JOIN accounts t2 ON t1.account_id = t2.id
WHERE t1.bug_id = '%s'
        ''' % (bug[0])
        links = db.sqlQuery(sql)
        links_dicts = [
            {'id': link[0],
             'name': link[1],
             } for link in links
        ]

        accounts_dicts = []
        for account in accounts:
            # Ищем название организации в описании тикета
            acс_name = account[1]

            if not find_account_in_desc(account=acс_name, description=bug[1]):
                # Название организации в описании тикета не найдено
                # переходим к следующей итерации (смотрим следующего
                # контрагента)
                continue

            # Проверяем есть ли интересующий нас контрагент в связках
            # accounts_bugs
            link_flag = find_account_in_link_bugs(
                account_id=account[0], links_dicts=links_dicts
            )

            accounts_dicts.append(
                {'id': account[0],
                 'name': account[1],
                 'link': link_flag}
            )

        if len(accounts_dicts) > 0:
            bugs_mass.append(
                {'id': bug[0],
                 'number': bug[3],
                 'desc': bug[1],
                 'date': bug[2],
                 'accounts': accounts_dicts,
                 'links': links_dicts,
                 }
            )
    return bugs_mass


@login_required
def tickets_bad_fill_mass(request, year='', month='', last='week',
                          csv_flag=False):
    '''Функция формирования списка массовых тикетов с подозрением на
    неверное оформленние
    year - стастика за конкретный год
    month - статистика за конкретный месяц
    last - статистика за последнее время
        last = 'month' - за последние 30 дней
        last = 'year' - за последний год
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    logger.info(
            'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
            (request.user, tickets_bad_fill_mass.__name__, last, year, month)
        )
    # Запрашиваем список массовых тикетов
    bugs_mass = fetch_bugs_mass(date_begin, date_end)

    context = {'tickets': bugs_mass,
               'date_begin': date_begin,
               'date_end': date_end,
               'menu_url': '/audit/tickets/bad_fill_mass/',
               }
    return render(request, 'audit/tickets_bad_fill_mass.html', context)


def calc_distr_duration_no_service(accounts_list, interval=None):
    '''Распределение простоев сервиса
    всё что больше последнего элемента не учитывается
    '''
    # Формируем статистику распределения простоев
    if not interval:
        interval = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22,
                    24, 28, 32, 36, 40, 44, 48, 54, 60, 66, 72, 84, 96, 120,
                    144, 168, 192, 216, 240, 720)
    # Инициализируем словарь
    durations = {}
    for i in interval[1:]:
        durations[i] = 0

    for account in accounts_list:
        for i in range(len(interval)-1):
            if (account.get('duration') > interval[i] and
                    account.get('duration') <= interval[i+1]):
                durations[interval[i+1]] += 1
                break
    # durations = {1: count1, 2: count2, ...}

    # Рассчитываем вероятность устранение проблемы
    probability_dur = {}

    count_accounts = len(accounts_list)
    count_sum = 0
    for dur, count in sorted(durations.items()):
        probability_dur[dur] = \
            (count + count_sum)*100/count_accounts if count_accounts > 0 else 0
        count_sum += count

    # формируем словарь
    distribution = [
        {'time': i,
         'count': durations[i],
         'probability': probability_dur[i],
         } for i in interval[1:]
    ]

    return distribution


def calc_no_service_statistic_duration(durations):
    '''Рассчитываем статистику по остановкам сервиса по данным
    из списка продолжительностей остановок сервиса
    '''
    from math import sqrt
    durations.sort()

    # медиана
    mediana = durations[len(durations)//2] if durations else 0
    # Среднее арифметическое простоев
    avg = sum(durations)/len(durations) if durations else 0
    # Эмпирическая (выборочная) дисперсия
    disp = 0.0
    if len(durations) > 1:
        for time in durations:
            disp += (time - avg)**2
        disp = disp/(len(durations)-1)
    # Среднеквадратичное отклонение
    dev_sqrt = sqrt(disp)
    # Коэффицент вариации
    k_var = dev_sqrt/avg if avg else 0

    statistic = {
        'mediana': mediana,
        'avg': avg,
        'disp': disp,
        'dev_sqrt': dev_sqrt,
        'k_var': k_var,
        'count': len(durations),
    }
    return statistic


def calc_no_service_statistic(accounts_list):
    '''Функция расчёта статистических показателей по оставнокам сервиса
    у клиентов
    '''
    # Рассчитываем количество клиентов с низким коэфициентом готовности
    count_kg_bad = 0
    for account in accounts_list:
        if account['kg'] < 0.99:
            count_kg_bad += 1

    count_kg_bad_per = count_kg_bad*100/len(accounts_list)

    # Считаем статистику по списку остановок сервиса
    durations = [account['duration'] for account in accounts_list]
    statistic = calc_no_service_statistic_duration(durations)

    statistic['kg_bad'] = count_kg_bad
    statistic['kg_bad_per'] = count_kg_bad_per

    return statistic


def calc_no_service_statistic_bugs_periods(bug_list, periods):
    '''Функция расчёта статистических показателей по оставнокам сервиса
    у клиентов за каждый период в periods
    '''
    statistic_periods = []
    for date_begin, date_end in periods:
        # Формируем список продолжительности остановок сервиса
        durations = [
            bug['duration']
            for bug in bug_list
            if (bug['date'].date() >= date_begin and
                bug['date'].date() < date_end)
        ]
        # Считаем статистику
        statistic = calc_no_service_statistic_duration(durations)
        statistic['date'] = date_begin
        statistic_periods.append(statistic)
    return statistic_periods


def summ_hours_and_minutes(hours, minutes):
    '''Функция сложения часов и минут. Ответ возвращается в часах.
    '''
    result = hours if hours else 0.0
    if minutes:
        result += minutes/60
    return round(result, 2)


def fetch_bugs_no_service(db, date_begin, date_end):
    '''Функция формирования списка тикетов за заданое время, в которых
    зафиксировано пропадание сервиса
    '''
    # Запрашиваем список тикетов с ненулевыми остановками сервиса
    sql = '''SELECT t1.id, t1.bug_number, t1.date_entered, t2.duration_bug_c, \
t2.duration_min_c
FROM sugar.bugs t1 LEFT JOIN sugar.bugs_cstm t2 ON t1.id = t2.id_c
WHERE t1.date_entered BETWEEN '%s' AND '%s'
AND (t2.duration_bug_c > 0 OR t2.duration_min_c > 0)
    ''' % (date_begin, date_end)
    bugs = db.sqlQuery(sql)

    bugs_dicts = [
        {'id': bug[0],
         'number': bug[1],
         'date': bug[2],
         'duration': summ_hours_and_minutes(bug[3], bug[4]),
         } for bug in bugs
    ]
    return bugs_dicts


def fetch_accounts_bugs_no_service(db, bugs, date_begin, date_end):
    '''Функция получения контрагентов с информацией о времени недоступности
    сервиса и списке открытых тикетов, привязанных к контрагенту
    '''
    accounts = {}
    for bug in bugs:
        # Смотрим связанные с тикетом контрагентов
        sql = '''SELECT t2.name, t2.id, t3.company_acc_c, \
t2.billing_address_street
FROM sugar.accounts_bugs t1
LEFT JOIN sugar.accounts t2 ON t1.account_id = t2.id
LEFT JOIN sugar.accounts_cstm t3 ON t2.id = t3.id_c
WHERE t1.bug_id = '%s'
        ''' % (bug['id'])
        accounts_bugs = db.sqlQuery(sql)

        for account_bug in accounts_bugs:
            id_acc = account_bug[1]

            if id_acc in accounts:
                accounts[id_acc]['duration'] += bug['duration']
                accounts[id_acc]['bugs'].append(bug)
            else:
                # Создаём новую запись в словаре
                accounts[id_acc] = {
                    'duration': bug['duration'],
                    'name': account_bug[0],
                    'id': id_acc,
                    'company': account_bug[2],
                    'address': account_bug[3],
                    'bugs': [bug],
                }
    # Рассчитываем продолжительность отчётного периода в часах
    delta = (date_end - date_begin).total_seconds()/3600
    # Рассчитываем коэффициент готовности
    for id_acc in accounts:
        accounts[id_acc]['kg'] = 1 - accounts[id_acc]['duration']/delta

    return accounts.values()


@login_required
def top_no_service(request, year='', month='', last='week', csv_flag=False,):
    '''Функция вывода ТОП абонентов с максимальным простоем сервиса
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, top_no_service.__name__, last, year, month)
    )

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    db = MySqlDB()

    # Запрашиваем перечень тикетов, в которой были зафиксированы
    # остановки сервиса
    bugs = fetch_bugs_no_service(db, date_begin, date_end)

    # Запрашиваем перечень контрагентов, связанных с тикетами bugs
    accounts = fetch_accounts_bugs_no_service(db, bugs, date_begin, date_end)

    # Сортируем полученные данные и отделяем мух от котел (физиков от юриков)
    def acc_sort(x): return x['duration']
    accounts_company_list = [
        account
        for account in sorted(accounts, key=acc_sort, reverse=True)
        if account.get('company') == 1
    ]
    accounts_man_list = [
        account
        for account in sorted(accounts, key=acc_sort, reverse=True)
        if account.get('company') == 0
    ]

    # Формируем статистику распределения простоев
    durations_company = calc_distr_duration_no_service(accounts_company_list)
    durations_man = calc_distr_duration_no_service(accounts_man_list)

    # Рассчитываем статистику по всем клиентам
    statistic_all = calc_no_service_statistic(accounts)
    statistic_man = calc_no_service_statistic(accounts_man_list)
    statistic_company = calc_no_service_statistic(accounts_company_list)

    statistics = {
        'all': statistic_all,
        'man': statistic_man,
        'company': statistic_company,
    }

    # Формируем периоды
    periods = gen_report_periods(date_begin, date_end)

    # Считаем статистику по тикетам!!! не по контрагентам!!!
    statistics_periods = calc_no_service_statistic_bugs_periods(bugs, periods)

    if csv_flag:
        import csv
        # Формируем csv файл
        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=\
"top_no_service_%s_%s.csv"' % (date_begin.strftime('%Y%m%d'),
                               date_end.strftime('%Y%m%d'))

        writer = csv.writer(response)
        writer.writerow(['account', 'address', 'tickets', 'duration',
                         'availability'])

        # пишем в файл юриков
        for account in accounts_company_list:
            bugs = ['%d (%.2f)' % (bug.get('number'), bug.get('duration'))
                    for bug in account.get('bugs')]
            writer.writerow([account.get('name'), account.get('address'),
                             ', '.join(bugs),
                             round(account.get('duration'), 2),
                             account.get('kg')])
        # Добавляем разделитель
        writer.writerow(['']*5)
        # Пишем в файл физиков
        for account in accounts_man_list:
            bugs = ['%d (%.2f)' % (bug.get('number'), bug.get('duration'))
                    for bug in account.get('bugs')]
            writer.writerow([account.get('name'), account.get('address'),
                             ', '.join(bugs),
                             round(account.get('duration'), 2),
                             account.get('kg')])
        return response
    # Формируем html
    months_report = gen_last_months(last=12)
    years_report = gen_last_years(3)
    type_report = gen_type_report(year=year, month=month)

    context = {'accounts_company': accounts_company_list,
               'accounts_man': accounts_man_list,
               'durations_company': durations_company,
               'durations_man': durations_man,
               'statistics': statistics,
               'statistics_periods': statistics_periods,
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'years': years_report,
               'type': type_report,
               'menu_url': '/audit/tickets/top_no_service/',
               }
    return render(request, 'audit/top_no_service.html', context)


def fetch_tickets_mass(date_begin, date_end):
    '''Функция получения списка массовых тикетов
    '''
    from audit.crmdict import bug_localisation_list, bug_perform_list

    db = MySqlDB()

    sql = '''SELECT t1.id, t1.bug_number, t1.date_entered, t2.address_bugs_c,
t1.name, t1.description, t2.status_bugs_c, t2.duration_bug_c,
t2.duration_min_c, t2.perform_c, t2.localisation_c, count(t3.id),
GROUP_CONCAT(CONCAT_WS('^', t3.account_id, t4.name) SEPARATOR ';'),
t2.new_reason_for_closure_bugs_c
FROM sugar.bugs t1
LEFT JOIN sugar.bugs_cstm t2 ON t1.id = t2.id_c
LEFT JOIN sugar.accounts_bugs t3 ON t1.id = t3.bug_id
LEFT JOIN sugar.accounts t4 ON t3.account_id = t4.id
WHERE t1.date_entered BETWEEN '%s' AND '%s'
GROUP BY t1.bug_number
    ''' % (date_begin, date_end + timedelta(days=1))
    bugs = db.sqlQuery(sql)

    bugs_mass = []
    for bug in bugs:
        # Ищем тикеты, у которых есть несколько связей с контрагентами
        if bug[11] < 2:
            # Тикет не массовый, переходим к следующему
            continue
        # Считаем продолжительность отсутсвия сервиса
        duration = summ_hours_and_minutes(bug[7], bug[8])

        # Формируем список связанных с тикетом контрагентов
        accounts_list = [
            account.split('^')
            for account in bug[12].split(';')
        ]

        if bug[11] > len(accounts_list) or len(bug[12]) > 500:
            # Из-за ограничения GROUP_CONCAT (1024 символа)
            # реально строка получается меньше ловил 626 символов
            # (видимо из-за кирилицы)
            # можем потерять часть контрагентов
            # делаем запрос, что б узнать все связанные учётки

            sql = '''SELECT t1.id, t1.name
FROM sugar.accounts t1
LEFT JOIN sugar.accounts_bugs t2 ON t1.id = t2.account_id
WHERE bug_id = '%s'
            ''' % bug[0]
            accounts_list = db.sqlQuery(sql)

        # Формируем словарь, так удобнее для работы в шаблоне
        accounts_dicts = [
            {'id': account[0], 'name': account[1]}
            for account in accounts_list
        ]

        perform = [
            bug_perform_list.get(perform, perform)
            for perform in bug[9].split(',')
        ] if bug[9] else []

        localisation = [
            bug_localisation_list.get(loc, loc)
            for loc in bug[10].split(',')
        ] if bug[10] else []

        bugs_mass.append({'id': bug[0],
                          'number': bug[1],
                          'date': bug[2],
                          'address': bug[3],
                          'name': bug[4],
                          'description': bug[5],
                          'status': bug[6],
                          'duration': duration,
                          'perform': perform,
                          'localisation': localisation,
                          'accounts': accounts_dicts,
                          'reason_close': bug[13],
                          })
    return bugs_mass


@login_required
def tickets_mass(request, year='', month='', last='week', csv_flag=False):
    '''Генерация списка массовых тикетов
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, tickets_mass.__name__, last, year, month)
    )

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    # Получить массовые тикеты
    bugs_mass = fetch_tickets_mass(date_begin, date_end)

    months_report = gen_last_months(last=12)
    years_report = gen_last_years(3)
    type_report = gen_type_report(year=year, month=month)

    context = {'bugs': bugs_mass,
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'years': years_report,
               'type': type_report,
               'menu_url': '/audit/tickets/mass/',
               }
    return render(request, 'audit/tickets_mass.html', context)


def gen_stat_survey(surveys, date_begin=None, date_end=None):
    '''Формирование статаистики по осмотрам
    Если date_begin и date_end не заданы, считаем статистику за весь период,
    иначе считаем только по интересующему нам периоду
    date_begin - включительно
    date_end - не включительно
    Период [date_begin, date_end)
    '''
    from audit.crmdict import status_survey, status_rs, status_ess

    # Инициализация словарей
    statistics = {'count': 0}
    status_stat = {}
    status_rs_stat = {}
    status_ess_stat = {}

    # Можно было проверку проводить внутри цикла, но тогда увеличится
    # количество операций, хотя код станет проще (меньше)
    if date_begin and date_end:
        # Задан период
        statistics['date'] = date_begin
        # Инициилизируем словари (используем ключи словарей из audit.survey)
        for st in status_survey.keys():
            status_stat[st] = 0
        for st in status_rs.keys():
            status_rs_stat[st] = 0
        for st in status_ess.keys():
            status_ess_stat[st] = 0

        for survey in surveys:
            if (survey['date_entered'].date() < date_begin or
                    survey['date_entered'].date() >= date_end):
                    # Если запись не входит в интересующий период переходим
                    # к следующей записи
                    continue
            statistics['count'] += 1
            status_stat[survey.get('status_key')] += 1
            if survey.get('status_key') == 'accept':
                if survey.get('status_rs_key') in status_rs_stat:
                    status_rs_stat[survey.get('status_rs_key')] += 1
                if survey.get('status_ess_key') in status_ess_stat:
                    status_ess_stat[survey.get('status_ess_key')] += 1
    else:
        # Период не задан
        # Инициилизируем словари (используем значения словарей из audit.survey)
        for st in status_survey.values():
            status_stat[st] = 0
        for st in status_rs.values():
            status_rs_stat[st] = 0
        for st in status_ess.values():
            status_ess_stat[st] = 0

        statistics['count'] = len(surveys)
        # Обходим все записи и формируем статистику
        for survey in surveys:
            status_stat[survey.get('status')] += 1
            if survey.get('status') == status_survey.get('accept'):
                if survey.get('status_rs') in status_rs_stat:
                    status_rs_stat[survey.get('status_rs')] += 1
                if survey.get('status_ess') in status_ess_stat:
                    status_ess_stat[survey.get('status_ess')] += 1

    statistics['status'] = status_stat
    statistics['status_rs'] = status_rs_stat
    statistics['status_ess'] = status_ess_stat

    return statistics


def fetch_survey(date_begin, date_end):
    '''Получить список (словарь) осмотров
    '''
    from audit.crmdict import status_survey, status_rs, status_ess
    db = MySqlDB()

    # Запрос перечня осмотров за заданный период
    sql = '''SELECT t1.id, t1.status, t2.status_rs_c,
t2.permit_installation_c, t1.name, t1.address,
t1.date_entered,  t1.description, t1.description_survey, t1.resolution,
t2.ess_comment_c, t2.comment_rs_c,
t2.date_installation_c, CONCAT_WS(' ',t3.first_name, t3.last_name) manager
FROM sugar.ra_survey t1 LEFT JOIN sugar.ra_survey_cstm t2 ON t1.id = t2.id_c
LEFT JOIN sugar.users t3 ON t3.id = t1.created_by
WHERE t1.date_entered BETWEEN '%s' AND '%s' AND t1.deleted = 0
ORDER BY manager, t1.date_entered;
    ''' % (date_begin, date_end + timedelta(days=1))

    surveys = db.sqlQuery(sql)

    surveys_dict = [
        {'id': survey[0],
         'name': survey[4],
         'date_entered': survey[6],
         'address': survey[5],
         'description': survey[7],
         'manager': survey[13],
         'resolution': survey[9],
         'tu': survey[8],
         'status': status_survey.get(survey[1], survey[1]),
         'status_key': survey[1],
         'status_rs': status_rs.get(survey[2], survey[2]),
         'status_rs_key': survey[2],
         'status_ess': status_ess.get(survey[3], survey[3]),
         'status_ess_key': survey[3],
         'comment_rs': survey[11],
         'comment_ess': survey[10],
         } for survey in surveys
    ]
    return surveys_dict


def calc_surveys_statistic(surveys):
    from audit.crmdict import status_survey, status_rs, status_ess
    # Инициализация словарей
    statistics = {'count': len(surveys)}

    status_stat = {
        st: {'count': 0, 'name': status_survey[st]}
        for st in status_survey
    }
    status_rs_stat = {
        st: {'count': 0, 'name': status_rs[st]}
        for st in status_rs
    }
    status_ess_stat = {
        st: {'count': 0, 'name': status_ess[st]}
        for st in status_ess
    }

    # Обходим все записи и формируем статистику
    for survey in surveys:
        status_stat[survey.get('status_key')]['count'] += 1
        if survey.get('status_key') == status_survey.get('accept'):
            status_rs_stat[survey.get('status_rs_key')]['count'] += 1
            status_ess_stat[survey.get('status_ess_key')]['count'] += 1

    statistics['status'] = status_stat
    statistics['status_rs'] = status_rs_stat
    statistics['status_ess'] = status_ess_stat

    return statistics


def calc_survey_statistics_periods(surveys_dict, periods):
    '''Расчитываем статистику по осмотрам
    '''
    from itertools import groupby

    statistics = {'all': calc_surveys_statistic(surveys_dict)}

    # Группируем осмотры по менеджерам
    def sort_manager(x): return x.get('manager')
    for k, g in groupby(surveys_dict, sort_manager):
        statistics[k] = calc_surveys_statistic(list(g))

    # Считаем статистику по отчётным периодам
    statistics_periods = {}

    # Формируем общую статистику по каждому интересующему нас периоду
    statistics_all_managers_periods = []
    for date_begin, date_end in periods:
        # Формируем срез осмоторов, попадающий под текущий период
        surveys_period = [
            survey
            for survey in surveys_dict
            if (survey['date_entered'].date() >= date_begin and
                survey['date_entered'].date() < date_end)
        ]
        statistics_all_managers_periods.append(
            {'date': date_begin,
             'stat': calc_surveys_statistic(surveys_period)}
        )

    statistics_periods = {'all': statistics_all_managers_periods}

    # Считаем статистику открытых осмотров по каждому менеджеру
    for manager, g in groupby(surveys_dict, sort_manager):
        surveys_manager = list(g)
        statistics_manager_periods = []
        for date_begin, date_end in periods:
            # Формируем срез осмоторов менеджера, попадающий под текущий период
            surveys_period = [
                survey
                for survey in surveys_manager
                if (survey['date_entered'].date() >= date_begin and
                    survey['date_entered'].date() < date_end)
            ]
            statistics_manager_periods.append(
                {'date': date_begin,
                 'stat': calc_surveys_statistic(surveys_period)}
            )
        statistics_periods[manager] = statistics_manager_periods

    return {'total': statistics,
            'total_periods': statistics_periods}


@login_required
def survey_report(request, year='', month='', last='week', csv_flag=False):
    '''Генерация списка заявок на осмотры
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, survey_report.__name__, last, year, month)
    )

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    # Формируем отчётные периоды (список дат)
    periods = gen_report_periods(date_begin, date_end)

    # Получаем осмотры
    surveys_dict = fetch_survey(date_begin, date_end)

    # Формируем статистику по осмотрам
    statistics = calc_survey_statistics_periods(surveys_dict, periods)

    months_report = gen_last_months(last=12)
    years_report = gen_last_years(last=5)
    type_report = gen_type_report(year=year, month=month)

    context = {'surveys': surveys_dict,
               'statistics': statistics,
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'years': years_report,
               'type': type_report,
               'menu_url': '/audit/survey/',
               }
    return render(request, 'audit/survey.html', context)


def gen_stat_connections(connections_dict, date_begin=None, date_end=None):
    '''Рассчитываем статистику по плану подключений
    '''
    from audit.crmdict import connection_type
    statistics = {}

    # Инициализируем словарь типов работ
    types_con = {}
    for type_con in connection_type.values():
        types_con[type_con] = 0

    if date_begin and date_end:
        count = 0
        for con in connections_dict:
            if con.get('date') >= date_begin and con.get('date') < date_end:
                count += 1
                types_con[con['type']] += 1
        types_con_list = [{'type': type_con[0], 'count': type_con[1]}
                          for type_con in types_con.items()]
        statistics = {'date': date_begin,
                      'count': count,
                      'type': types_con_list,
                      }
    else:
        for con in connections_dict:
            types_con[con['type']] += 1
        types_con_list = [{'type': type_con[0], 'count': type_con[1]}
                          for type_con in types_con.items()]
        statistics = {'date': date_begin,
                      'count': len(connections_dict),
                      'type': types_con_list,
                      }
    # {'date': date, 'count':count, 'type':{'type': type, 'count': count}}
    return statistics


def gen_connections_period(connections, period):
    '''Рассчитываем количества работ в каждом периоде
    '''
    stat_period = []
    # Пробегаем по каждому отрезку периода
    for i in range(len(period[0:-1])):
        date_cur = period[i]
        date_next = period[i+1]
        count = 0
        # Смотрим все работы и ищем попадающие в нужный отрезок времени
        # считаем сколько таких
        for conn in connections:
            if (conn.get('date') >= date_cur and
                    conn.get('date') < date_next):
                count += 1
        stat_period.append({'date': date_cur, 'count': count})
    # [{'date': date, 'count': count},]
    return stat_period


def gen_week_period(date_begin, date_end):
    # Считаем статистику кратно 7 дням от конца периода
    # Смещаемся на начало текущей недели
    from calendar import weekday

    delta = date_end - date_begin
    delta_week = timedelta(days=weekday(date_end.year,
                                        date_end.month, date_end.day))
    begin_period = date_end - delta_week - timedelta(days=(delta.days//7)*7)
    period = [begin_period + timedelta(days=i)
              for i in range(0, delta.days+7, 7)]
    return period


@login_required
def connections_report(request, year='', month='', csv_flag=False,
                       last='week'):
    '''Функция генерации отчёта по плану работ
    '''
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, connections_report.__name__, last, year, month)
    )

    from itertools import groupby
    from audit.crmdict import connection_status, connection_type

    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    db = MySqlDB()

    # Запрос перечня осмотров за заданный период
    sql = '''SELECT t1.id, t1.name, t1.date_entered, t1.date_modified,
CONCAT(t3.first_name, ' ', t3.last_name) create_by,
CONCAT(t4.first_name, ' ', t4.last_name) modified_by,
t1.deleted, t2.address_plan_c, t2.date_connection_c,
t2.type_conn_c, t2.status_mount_c, t1.description,
t2.radio_c, t2.level_signal_c, t2.channel_speed_c, t2.comment_mount_c
FROM sugar.con_p_connections_plan t1
LEFT JOIN sugar.con_p_connections_plan_cstm t2 ON t1.id = t2.id_c
LEFT JOIN sugar.users t3 ON t1.created_by = t3.id
LEFT JOIN sugar.users t4 ON t1.modified_user_id = t4.id
WHERE t2.date_connection_c BETWEEN '%s' AND '%s'
ORDER BY t2.date_connection_c
    ''' % (date_begin, date_end)

    connections = db.sqlQuery(sql)

    # Список работ без удалённых записей
    connections_dict = [
        {'id': con[0],
         'name': con[1],
         'date_entered': con[2],
         'date_modified': con[3],
         'create_by': con[4],
         'modified_by': con[5],
         'address': con[7],
         'date': con[8],
         'type': connection_type.get(con[9]),
         'status': connection_status.get(con[10]),
         'desc': con[11],
         'radio': con[12],
         'level_signal': con[13],
         'channel_speed': con[14],
         'comment_mount': con[15],
         } for con in connections if con[6] == 0]
    # Список удалённых работ
    connections_del_dict = [
        {'id': con[0],
         'name': con[1],
         'date_entered': con[2],
         'date_modified': con[3],
         'create_by': con[4],
         'modified_by': con[5],
         'address': con[7],
         'date': con[8],
         'type': connection_type.get(con[9]),
         'status': connection_status.get(con[10]),
         'desc': con[11],
         'radio': con[12],
         'level_signal': con[13],
         'channel_speed': con[14],
         'comment_mount': con[15],
         } for con in connections if con[6] != 0]

    # Формируем статистику по работам
    statistics = gen_stat_connections(connections_dict)

    # Формируем отчётные периоды (список дат)
    period = gen_period(date_begin, date_end)

    # Расчитываем статистику подневную/понедельную/помесячную
    statistics_period = gen_connections_period(connections_dict, period)

    # Считаем статистику подневную/понедельную/помесячную по менеджерам
    # Скважность задана в списке period
    statistics_manager_period = []

    def sort_create_by(x): return x.get('create_by')
    for k, g in groupby(sorted(connections_dict, key=sort_create_by),
                        sort_create_by):
        connections_man = list(g)
        stat_period = gen_connections_period(connections=connections_man,
                                             period=period)
        statistics_manager_period.append({'man': k,
                                          'count': len(connections_man),
                                          'stat': stat_period})

    # Формируем статистику по типу работ
    # [{'type': type, 'count': count, 'stat': {'date': date, 'count': count}},]
    statistics_type_period = []

    # Группируем осмотры по типу
    def sort_type(x): return x.get('type')
    for k, g in groupby(sorted(connections_dict, key=sort_type), sort_type):
        connections_type = list(g)
        stat_period = gen_connections_period(connections=connections_type,
                                             period=period)
        statistics_type_period.append({'type': k,
                                       'count': len(connections_type),
                                       'stat': stat_period})

    months_report = gen_last_months(last=12)
    years_report = gen_last_years(last=5)
    type_report = gen_type_report(year=year, month=month)

    context = {'connections': connections_dict,
               'connections_del': connections_del_dict,
               'statistics': statistics,
               'statistics_period': statistics_period,
               'statistics_type_period': statistics_type_period,
               'statistics_manager_period': statistics_manager_period,
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'years': years_report,
               'type': type_report,
               'menu_url': '/audit/connections/',
               }
    return render(request, 'audit/connections.html', context)


def gen_noanswer_period(noanswers, period):
    stat_period = []
    # Пробегаем по каждому отрезку периода
    for i in range(len(period[0:-1])):
        date_cur = period[i]
        date_next = period[i+1]
        count_no_recall = 0     # Количество потерянных
        count_recall = 0        # Количество тем, кому перезвонили
        count_call = 0          # Кто дозвонился сам
        count = 0               # Всего
        for noanswer in noanswers:
            if (noanswer.calldate.date() >= date_cur and
                    noanswer.calldate.date() < date_next):
                count += 1
                if noanswer.done == 0:
                    count_no_recall += 1
                else:
                    if noanswer.retry == 0:
                        count_recall += 1
                    else:
                        count_call += 1
        stat_period.append({'date': date_cur,
                            'count_no_recall': count_no_recall,
                            'count_recall': count_recall,
                            'count_call': count_call,
                            'count': count,
                            })
    return stat_period


def calc_support_statistic_date(events, date_begin, date_end):
    # Выбираем события попадающий в интересующий нас отрезок времени
    events_curent = [
        event for event in events if (event.date_event.date() >= date_begin and
                                      event.date_event.date() < date_end)]

    # Считаем количество звонков, пропущенных звонков, собираем hold_time
    count_calls = 0
    count_complete = 0
    count_abandon = 0
    count_abandon_15 = 0
    hold_time = []
    hold_time_abandon = []
    for event in events_curent:
        if event.event == 'ENTERQUEUE':
            count_calls += 1
        elif (event.event == 'COMPLETECALLER' or
                event.event == 'COMPLETEAGENT'):
            count_complete += 1
            if event.data1.isnumeric():
                hold_time.append(int(event.data1))
        elif event.event == 'ABANDON':
            count_abandon += 1
            if event.data3.isnumeric():
                ht = int(event.data3)
                hold_time.append(ht)
                hold_time_abandon.append(ht)
    # Сортируем списки времени ожидания ответа
    hold_time.sort()
    hold_time_abandon.sort()

    # Расчитываем медианы времени ожидания
    mediana_hold_time = hold_time[len(hold_time) // 2] if len(hold_time) else 0

    mediana_hold_time_abandon = hold_time_abandon[
        len(hold_time_abandon) // 2] if len(hold_time_abandon) else 0

    # Считаем количество пропущенных вызовов с временм ожидания более 14 сек
    hold_time_abandon_15 = [ht for ht in hold_time_abandon if ht > 14]
    count_abandon_15 = len(hold_time_abandon_15)

    # Считаем количество вызовов, с временем ожидания менее 15 сек
    hold_time_15 = [ht for ht in hold_time if ht < 15]
    count_hold_time_15 = len(hold_time_15)

    return {'date': date_begin,
            'count': count_calls,
            'complete': count_complete,
            'abandon': count_abandon,
            'abandon_15': count_abandon_15,
            'hold_time': mediana_hold_time,
            'hold_time_abandon': mediana_hold_time_abandon,
            'count_hold_time_15': count_hold_time_15,
            }


def gen_support_period(events, period):
    '''Рассчитываем статистику звонков в саппорт в каждом периоде
    '''
    stat_period = []
    # Пробегаем по каждому отрезку периода
    for i in range(len(period[0:-1])):
        date_cur = period[i]
        date_next = period[i+1]
        stat_period.append(
            calc_support_statistic_date(events, date_cur, date_next))
    # [{'date': date, 'count': count, 'complete': count_complete,
    #   'abandon': count_abandon, 'abandon_15': count_abandon_15,
    #   'hold_time': mediana_hold_time,
    #   'hold_time_abandon': mediana_hold_time,
    #   'count_hold_time_15': count_hold_time_15}]
    return stat_period


@login_required
def support_report(request, year='', month='', csv_flag=False, last='week'):
    '''Функция генерации отчёта по работе callcenter техподдержки
    '''
    from .models import QueueLog, TpNoAnswered

    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, support_report.__name__, last, year, month)
    )
    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)
    if date_begin is None or date_end is None:
        context = {'user': request.user.username,
                   'error': 'Ошибка задания дат'
                   }
        return render(request, 'audit/error.html', context)

    # Запрашиваем события в очереди за нужный период
    events = QueueLog.objects.filter(
        date_event__gte=date_begin
    ).filter(
        date_event__lt=date_end
    ).exclude(
        callid__exact='NONE'
    ).order_by('date_event')

    # Формируем отчётные периоды (список дат)
    period = gen_period(date_begin, date_end)

    # Формируем распределённую (по датам) статистику
    # events_period = gen_support_period(events_dict, period)
    events_period = gen_support_period(events, period)

    # Запрашиваем из БД информацию "перезвонам"
    noanswers = TpNoAnswered.objects.filter(
        calldate__gte=date_begin
    ).filter(
        calldate__lt=date_end
    ).order_by('calldate')

    # Формируем распределённую по датам статистику
    noanswers_period = gen_noanswer_period(noanswers, period)

    # Формируем список потерянных звонков
    not_recalls = [{'callid': noanswer.callerid,
                    'date': noanswer.calldate,
                    'retry': noanswer.retry}
                   for noanswer in noanswers if noanswer.done == 0]

    months_report = gen_last_months(last=12)
    years_report = gen_last_years(last=5)
    type_report = gen_type_report(year=year, month=month)

    context = {'events': events,
               'events_period': events_period,
               'not_recalls': not_recalls,
               'noanswers_period': noanswers_period,
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'years': years_report,
               'type': type_report,
               'menu_url': '/audit/support/',
               }
    return render(request, 'audit/support.html', context)


def gen_quetions_period(questions, period):
    '''Генерация статистики за каждый период в списке периодов :)
    '''
    stat_period = []
    # Пробегаем по каждому отрезку периода
    for i in range(len(period[0:-1])):
        date_cur = period[i]
        date_next = period[i+1]
        count = 0
        for question in questions:
            if (question.get('date') >= date_cur and
                    question.get('date') < date_next):
                count += 1
        stat_period.append({'date': date_cur,
                            'count': count,
                            })
    return stat_period


def is_bad_feedback(question):
    '''Возвращает True если отзыв плохой, иначе False'''
    if (question.get('support_calls') == 'Раз в неделю' or
            question.get('support_calls') == 'Каждый день'):
        return True

    if (question.get('support') == 'Плохо' or
            question.get('support') == 'Очень плохо'):
        return True

    if (question.get('install') == 'Плохо' or
            question.get('install') == 'Очень плохо'):
        return True

    if (question.get('sell') == 'Плохо' or
            question.get('sell') == 'Очень плохо'):
        return True

    if (question.get('quality_client') == 'Очень высокие риски' or
            question.get('quality_client') == 'Высокие риски'):
        return True

    return False


@login_required
def acc_question_stat(request, year='', month='', csv_flag=False, last='week'):
    '''Функция генерации отчёта по работе callcenter техподдержки
    '''
    # Проверяем права пользователя
    if not request.user.groups.filter(name__exact='tickets').exists():
        context = {'user': request.user.username,
                   'error': 'Не хватает прав!'
                   }
        return render(request, 'audit/error.html', context)

    from audit.crmdict import quality_client, type_question, support_calls,\
        question_list

    logger.info(
        'user "%s" run function %s whith arguments last="%s" year="%s" \
month="%s"' %
        (request.user, acc_question_stat.__name__, last, year, month)
    )
    # Формируем даты начала и конца периода
    date_begin, date_end = gen_report_begin_end_date(year, month, last)

    db = MySqlDB()

    # Запрос перечня проведённых опросов
    sql = '''SELECT t1.id, t1.name, t2.last_name, t1.type, t1.date_question,
t4.name, t3.last_name, t1.user_accounts, t1.support_calls,
t1.support, t1.install, t1.sell, t1.quality_client, t1. description,
t1.service_problem, t1.account_id_c, t4.billing_address_street
FROM sugar.qu_question t1
LEFT JOIN sugar.users t2 ON t1.assigned_user_id = t2.id
LEFT JOIN sugar.users t3 ON t1.assigned_user_id = t3.id
LEFT JOIN sugar.accounts t4 ON t1.account_id_c = t4.id
WHERE t1.deleted = 0 AND date_question BETWEEN '%s' AND '%s'
    ''' % (date_begin, date_end)

    questions = db.sqlQuery(sql)

    # Формируем список словарей (удобнее работать)
    questions_dict = [
        {'id': question[0],
         'name': question[1],
         'user': question[2],
         'type': type_question.get(question[3]),
         'date': question[4],
         'account': question[5],
         'manager': question[6],
         'contact': question[7],
         'support_calls': support_calls.get(question[8]),
         'support': question_list.get(question[9]),
         'install': question_list.get(question[10]),
         'sell': question_list.get(question[11]),
         'quality_client': quality_client.get(question[12]),
         'description': question[13],
         'service_problem': question[14],
         'account_id': question[15],
         'address': question[16], } for question in questions]
    # Формируем список опросов с плохими отзывами
    bad_questions_dict = []
    for question in questions_dict:
        # Смотрим плохой ли отзыв
        if is_bad_feedback(question):
            # Отзыв плохой, ищем тикеты у контрагента и все сохраняем
            # в bad_questions_dict
            sql = '''SELECT t2.id, t2.bug_number FROM accounts_bugs t1
LEFT JOIN bugs t2 ON t1.bug_id = t2.id
WHERE t1.account_id = '%s'
ORDER BY t2.bug_number DESC
            ''' % question.get('account_id')
            bugs = db.sqlQuery(sql)
            bugs_dict = [{'id': bug[0], 'number': bug[1]} for bug in bugs]
            question['bugs'] = bugs_dict
            bad_questions_dict.append(question)

    # Формируем отчётные периоды (список дат)
    period = gen_period(date_begin, date_end)

    # Формируем распределённую по датам статистику
    questions_period = gen_quetions_period(questions_dict, period)
    bad_questions_period = gen_quetions_period(bad_questions_dict, period)

    months_report = gen_last_months(last=12)
    years_report = gen_last_years(last=5)
    type_report = gen_type_report(year=year, month=month)

    context = {'questions': bad_questions_dict,
               'questions_length': len(questions_dict),
               'questions_period': questions_period,
               'bad_questions_period': bad_questions_period,
               'date_begin': date_begin,
               'date_end': date_end,
               'months': months_report,
               'years': years_report,
               'type': type_report,
               'menu_url': '/audit/acc_question/',
               }
    return render(request, 'audit/acc_question.html', context)
