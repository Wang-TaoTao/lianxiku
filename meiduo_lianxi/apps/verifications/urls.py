# verifications 子路由

from django.conf.urls import url
from . import views
urlpatterns = [

    # 图形验证码
    url(r'^image_code/(?P<uuid>[\w-]+)/',views.ImageCodeView.as_view()),
]

