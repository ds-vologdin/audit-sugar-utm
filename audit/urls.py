from django.conf.urls import url, include
from django.views.decorators.cache import cache_page
from . import views

CACHE_TIME = 1 * 15


def get_url_year_month_last(view_function, csv_flag=False, ods_flag=False):
    # last - week, month, quarter, year, 2year, 3year
    urlpatterns = [
        url(r'^(?P<year>[0-9]{4})/$',
            cache_page(CACHE_TIME)(view_function)),
        url(r'^(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
            cache_page(CACHE_TIME)(view_function)),
        url(r'^last/(?P<last>\w+)/$',
            cache_page(CACHE_TIME)(view_function)),
    ]

    if csv_flag:
        urlpatterns += [
            url(r'^(?P<year>[0-9]{4})/csv/$',
                cache_page(CACHE_TIME)(view_function), {'csv_flag': True}),
            url(r'^(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/csv/$',
                cache_page(CACHE_TIME)(view_function), {'csv_flag': True}),
            url(r'^last/(?P<last>\w+)/csv/$',
                cache_page(CACHE_TIME)(view_function), {'csv_flag': True}),
        ]

    if ods_flag:
        urlpatterns += [
            url(r'^(?P<year>[0-9]{4})/ods/$',
                cache_page(CACHE_TIME)(view_function), {'ods_flag': True}),
            url(r'^(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/ods/$',
                cache_page(CACHE_TIME)(view_function), {'ods_flag': True}),
            url(r'^last/(?P<last>\w+)/ods/$',
                cache_page(CACHE_TIME)(view_function), {'ods_flag': True}),
        ]
    return urlpatterns


app_name = 'audit'
urlpatterns = [
    # ex. /audit/
    url(r'^$', views.index, name='index'),

    # ex. /audit/utmpays
    url(r'^utmpays/', include(
        get_url_year_month_last(views.utmpays_statistic)
    )),

    # ex. /audit/block/
    url(r'^block/', include(
        get_url_year_month_last(views.block_users_month, ods_flag=True)
    )),

    # ex. /audit/hwremove/2017/07/03/01/
    url(r'^hwremove/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/$',
        cache_page(CACHE_TIME)(views.hardware_remove)),
    # ex. /audit/hwremove/2017/07/03/01/ods
    url(r'^hwremove/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/ods/$',
        cache_page(CACHE_TIME)(views.hardware_remove), {'ods_flag': True}),

    # ex. /audit/tickets/
    url(r'^tickets/', include(
        get_url_year_month_last(views.tickets_open, csv_flag=True)
    )),

    # ex. /audit/tickets/bad_fill/
    url(r'^tickets/bad_fill/', include(
        get_url_year_month_last(views.tickets_bad_fill, csv_flag=True)
    )),

    # ex. /audit/repairs/
    url(r'^repairs/', include(
        get_url_year_month_last(views.repairs_stat)
    )),

    # ex. /audit/dublicate/
    url(r'^repairs/dublicate/', include(
        get_url_year_month_last(views.repairs_dublicate, ods_flag=True)
    )),

    # ex. /audit/top_tickets/
    url(r'^top_tickets/', include(
        get_url_year_month_last(views.top_tickets)
    )),

    # ex. /audit/top_calls/
    url(r'^top_calls/', include(
        get_url_year_month_last(views.top_calls)
    )),

    # ex. /audit/tickets/bad_fill_mass/
    url(r'^tickets/bad_fill_mass/', include(
        get_url_year_month_last(views.tickets_bad_fill_mass)
    )),

    # ex. /audit/tickets/top_no_service/
    url(r'^tickets/top_no_service/', include(
        get_url_year_month_last(views.top_no_service, csv_flag=True)
    )),

    # ex. /audit/tickets/mass/
    url(r'^tickets/mass/', include(
        get_url_year_month_last(views.tickets_mass)
    )),

    # ex. /audit/survey/
    url(r'^survey/', include(
        get_url_year_month_last(views.survey_report)
    )),

    # ex. /audit/connections/
    url(r'^connections/', include(
        get_url_year_month_last(views.connections_report)
    )),

    # ex. /audit/support/
    url(r'^support/', include(
        get_url_year_month_last(views.support_report)
    )),

    # ex. /audit/acc_question/
    url(r'^acc_question/', include(
        get_url_year_month_last(views.acc_question_stat)
    )),

    url(r'^login/$', views.LoginFormView.as_view()),
    url(r'^logout/$', views.LogoutView.as_view()),
]
