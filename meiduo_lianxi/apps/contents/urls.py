# contents子路由

from django.conf.urls import url
from django.contrib import admin
from . import views
urlpatterns = [

    # 首页界面
    url(r'^$',views.IndexView.as_view(),name='index'),
]
