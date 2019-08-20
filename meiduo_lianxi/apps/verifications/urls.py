# verifications 子路由

from django.conf.urls import url
from . import views
urlpatterns = [

    # 图形验证码
    url(r'^image_code/(?P<uuid>[\w-]+)/',views.ImageCodeView.as_view()),

    # 验证图形验证码
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/',views.SMSCodeView.as_view()),


]

