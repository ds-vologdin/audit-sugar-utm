from django.conf.urls import url, include
from django.views.decorators.cache import cache_page
from . import views

CACHE_TIME = 60 * 15

app_name = 'audit'
urlpatterns = [
    # ex. /audit/
    url(r'^$', views.index, name='index'),

    # ex. /audit/utmpays/last/...
    # last - week, month, quarter, year, 2year, 3year
    url(r'^utmpays/last/(?P<last>\w+)/$',
        cache_page(CACHE_TIME)(views.utmpays_statistic)),
    # ex. /audit/utmpays/2018/
    url(r'^utmpays/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.utmpays_statistic)),
    # ex. /audit/utmpays/2018/01/
    url(r'^utmpays/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.utmpays_statistic)),

    # ex. /audit/block/2017/07/
    url(r'^block/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.block_users_month)),
    # ex. /audit/block/2017/07/ods
    url(r'^block/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/ods$',
        cache_page(CACHE_TIME)(views.block_users_month), {'ods': True}),

    # ex. /audit/hwremove/2017/07/03/01/
    url(r'^hwremove/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.hardware_remove)),
    # ex. /audit/hwremove/2017/07/03/01/ods
    url(r'^hwremove/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/ods$',
        cache_page(CACHE_TIME)(views.hardware_remove), {'ods': True}),

    # ex. /audit/tickets/
    url(r'^tickets/$', (views.tickets_open)),
    # ex. /audit/tickets/2018/
    url(r'^tickets/(?P<year>[0-9]{4})/$',
        (views.tickets_open)),
    # ex. /audit/tickets/2018/01/
    url(r'^tickets/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        (views.tickets_open)),
    # ex. /audit/tickets/csv/
    url(r'^tickets/csv/$',
        (views.tickets_open), {'csv_flag': True}),
    # ex. /audit/tickets/2018/csv/
    url(r'^tickets/(?P<year>[0-9]{4})/csv/$',
        (views.tickets_open),
        {'csv_flag': True}),
    # ex. /audit/tickets/2018/01/csv/
    url(r'^tickets/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/csv/$',
        (views.tickets_open),
        {'csv_flag': True}),

    # ex. /audit/tickets/last/...
    url(r'^tickets/last/',
        include([url(r'^(?P<last>\w+)/$',
                     (views.tickets_open),),
                 url(r'^(?P<last>\w+)/csv/$',
                     (views.tickets_open),
                     {'csv_flag': True}), ])),
    # ex. /audit/tickets/bad_fill/
    url(r'^tickets/bad_fill/$', cache_page(CACHE_TIME)(views.tickets_bad_fill)),
    # ex. /audit/tickets/bad_fill/csv/
    url(r'^tickets/bad_fill/csv/$',
        cache_page(CACHE_TIME)(views.tickets_bad_fill),
        {'csv_flag': True}),
    # ex. /audit/tickets/bad_fill/2018/
    url(r'^tickets/bad_fill/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.tickets_bad_fill)),
    # ex. /audit/tickets/bad_fill/2018/csv/
    url(r'^tickets/bad_fill/(?P<year>[0-9]{4})/csv/$',
        cache_page(CACHE_TIME)(views.tickets_bad_fill), {'csv_flag': True}),
    # ex. /audit/tickets/bad_fill/2018/01/
    url(r'^tickets/bad_fill/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.tickets_bad_fill)),
    # ex. /audit/tickets/bad_fill/2018/01/csv/
    url(r'^tickets/bad_fill/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/csv/$',
        cache_page(CACHE_TIME)(views.tickets_bad_fill), {'csv_flag': True}),

    # ex. /audit/tickets/bad_fill/last
    url(r'^tickets/bad_fill/last/',
        include([url(r'^(?P<last>\w+)/$',
                     cache_page(CACHE_TIME)(views.tickets_bad_fill),),
                 url(r'^(?P<last>\w+)/csv/$',
                     cache_page(CACHE_TIME)(views.tickets_bad_fill),
                     {'csv_flag': True}), ])),
    # ex. /audit/repairs/
    url(r'^repairs/$', cache_page(CACHE_TIME)(views.repairs_dublicate),
        {'last': 'month'}),
    # ex. /audit/repairs/last/...
    url(r'^repairs/last/',
        include([url(r'^(?P<last>\w+)/$',
                cache_page(CACHE_TIME)(views.repairs_stat),), ])),
    # ex. /audit/repairs/2018/
    url(r'^repairs/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.repairs_stat)),
    # ex. /audit/repairs/2018/01/
    url(r'^repairs/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.repairs_stat)),

    # ex. /audit/repairs/dublicate/last/...
    # file_type - может быть ods
    # last - week, month, quarter, year, 2year, 3year
    url(r'^repairs/dublicate/last/',
        include([url(r'^(?P<last>\w+)/$',
                     cache_page(CACHE_TIME)(views.repairs_dublicate),),
                 url(r'^(?P<last>\w+)/(?P<file_type>\w+)/$',
                     cache_page(CACHE_TIME)(views.repairs_dublicate),), ])),
    # ex. /audit/repairs/dublicate/2018/
    url(r'^repairs/dublicate/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.repairs_dublicate)),
    url(r'^repairs/dublicate/(?P<year>[0-9]{4})/(?P<file_type>\w+)$',
        cache_page(CACHE_TIME)(views.repairs_dublicate)),
    # ex. /audit/repairs/dublicate/2018/01/
    url(r'^repairs/dublicate/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.repairs_dublicate)),
    url(r'^repairs/dublicate/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<file_type>\w+)/$',
        cache_page(CACHE_TIME)(views.repairs_dublicate)),

    # ex. /audit/top_tickets/
    url(r'^top_tickets/$', cache_page(CACHE_TIME)(views.top_tickets),
        {'last': 'month'}),
    # ex. /audit/top_tickets/last/...
    url(r'^top_tickets/last/',
        include([url(r'^(?P<last>\w+)/$',
                cache_page(CACHE_TIME)(views.top_tickets),), ])),
    # ex. /audit/top_calls/
    url(r'^top_calls/$', views.top_calls, {'last': 'month'}),
    # ex. /audit/top_calls/last/...
    url(r'^top_calls/last/',
        include([url(r'^(?P<last>\w+)/$',
                cache_page(CACHE_TIME)(views.top_calls),), ])),

    # ex. /audit/bad_fill_mass/last/...
    url(r'^tickets/bad_fill_mass/last/',
        include([url(r'^(?P<last>\w+)/$',
                     cache_page(CACHE_TIME)(views.tickets_bad_fill_mass),), ])),

    # ex. /audit/tickets/top_no_service/last/...
    url(r'^tickets/top_no_service/last/',
        include([url(r'^(?P<last>\w+)/$',
                 cache_page(CACHE_TIME)(views.top_no_service),),
                 url(r'^(?P<last>\w+)/csv/$',
                     cache_page(CACHE_TIME)(views.top_no_service),
                     {'csv_flag': True}), ])),
    # ex. /audit/tickets/top_no_service/2018/01/
    url(r'^tickets/top_no_service/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.top_no_service)),
    # ex. /audit/tickets/top_no_service/2018/01/csv/
    url(r'^tickets/top_no_service/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/csv/$',
        cache_page(CACHE_TIME)(views.top_no_service), {'csv_flag': True}),
    # ex. /audit/tickets/top_no_service/2018/
    url(r'^tickets/top_no_service/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.top_no_service)),
    # ex. /audit/tickets/top_no_service/2018/csv/
    url(r'^tickets/top_no_service/(?P<year>[0-9]{4})/csv/$',
        cache_page(CACHE_TIME)(views.top_no_service), {'csv_flag': True}),

    # ex. /audit/tickets/mass/last/...
    url(r'^tickets/mass/last/(?P<last>\w+)/$',
        cache_page(CACHE_TIME)(views.tickets_mass)),
    # ex. /audit/tickets/mass/2018/
    url(r'^tickets/mass/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.tickets_mass)),
    # ex. /audit/tickets/mass/2018/01/
    url(r'^tickets/mass/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.tickets_mass)),

    # ex. /audit/survey/last/...
    url(r'^survey/last/(?P<last>\w+)/$',
        cache_page(CACHE_TIME)(views.survey_report)),
    # ex. /audit/survey/2018/
    url(r'^survey/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.survey_report)),
    # ex. /audit/survey/2018/01/
    url(r'^survey/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.survey_report)),

    # ex. /audit/connections/last/...
    url(r'^connections/last/(?P<last>\w+)/$',
        cache_page(CACHE_TIME)(views.connections_report)),
    # ex. /audit/connections/2018/
    url(r'^connections/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.connections_report)),
    # ex. /audit/connections/2018/01/
    url(r'^connections/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.connections_report)),

    # ex. /audit/support/last/...
    url(r'^support/last/(?P<last>\w+)/$',
        cache_page(CACHE_TIME)(views.support_report)),
    # ex. /audit/support/2018/
    url(r'^support/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.support_report)),
    # ex. /audit/support/2018/01/
    url(r'^support/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.support_report)),

    # ex. /audit/acc_question/last/...
    # last - week, month, quarter, year, 2year, 3year
    url(r'^acc_question/last/(?P<last>\w+)/$',
        cache_page(CACHE_TIME)(views.acc_question_stat)),
    # ex. /audit/acc_question/2018/
    url(r'^acc_question/(?P<year>[0-9]{4})/$',
        cache_page(CACHE_TIME)(views.acc_question_stat)),
    # ex. /audit/acc_question/2018/01/
    url(r'^acc_question/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.acc_question_stat)),

    url(r'^login/$', views.LoginFormView.as_view()),
    url(r'^logout/$', views.LogoutView.as_view()),
]
