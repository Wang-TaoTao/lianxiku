# orders子路由

from django.conf.urls import url
from django.contrib import admin
from . import views
urlpatterns = [


    # 结算订单页面
    url(r'^orders/settlement/$',views.OrderSettlementView.as_view()),

    # 保存订单基本信息和订单商品信息
    url(r'^orders/commit/$',views.OrderCommitView.as_view()),

    # 展示提交成功界面
    url(r'^orders/success/$',views.OrderSuccessView.as_view()),


]
