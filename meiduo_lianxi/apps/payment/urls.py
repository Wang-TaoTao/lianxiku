# payment子路由

from django.conf.urls import url
from django.contrib import admin
from . import views
urlpatterns = [

    # 生成支付宝登录支付链接
    url(r'^payment/(?P<order_id>\d+)/$',views.PaymentView.as_view()),


    # 保存订单支付结果 支付宝回调美多商城
    url(r'^payment/status/$',views.PaymentStatusView.as_view()),
]
