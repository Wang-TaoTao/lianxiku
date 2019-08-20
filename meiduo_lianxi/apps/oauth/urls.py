# oauth 子路由

from django.conf.urls import url
from django.contrib import admin
from . import views
urlpatterns = [

    #　获取qq登录页面
    url(r'^qq/login/$', views.QQAuthURLView.as_view(), name='qqlogin'),

    #　用户登录ＱＱ后的回调处理
    url(r'^oauth_callback/$', views.QQAuthUserView.as_view()),
]
