# oauth 子路由

from django.conf.urls import url
from django.contrib import admin
from . import views
urlpatterns = [

    #　获取qq登录链接
    url(r'^qq/login/$', views.QQAuthURLView.as_view(), name='qqlogin'),

    #　用户登录ＱＱ后的回调处理
    url(r'^oauth_callback/$', views.QQAuthUserView.as_view()),

    # 获取sina登录链接
    url(r'^sina/login/$', views.WeiboAuthURLView.as_view()),

    # 用户登录微博后的回调处理
    url(r'^sina_callback/$', views.WeiboAuthCallBackView.as_view()),

]
