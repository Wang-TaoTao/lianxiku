# verifications 子路由

from django.conf.urls import url
from . import views
urlpatterns = [

    # 图形验证码
    url(r'^image_code/(?P<uuid>[\w-]+)/',views.ImageCodeView.as_view()),

    # 验证图形验证码
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/',views.SMSCodeView.as_view()),

    # 找回密码第一步 （验证用户名和图形验证码）
    url(r'^accounts/(?P<username>\w+)/sms/token/$',views.PwdOneView.as_view()),


    # 找回密码第二步 （接收token和发送短信验证码）
    url(r'^sms_codes/$',views.PwdTwoView.as_view()),

    # 找回密码第二步 （验证短信验证码）
    url(r'^accounts/(?P<username>\w+)/password/token/$',views.PwdTwoCodeView.as_view()),

    # 找回密码第三步 （修改密码）
    url(r'users/(?P<user_id>\d+)/password/',views.PwdThreeView.as_view()),

]

