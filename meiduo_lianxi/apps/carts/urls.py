# carts子路由

from django.conf.urls import url

from . import views
urlpatterns = [

    # 购物车
    url(r'^carts/$',views.CartsView.as_view()),

    # 全选购物车
    url(r'^carts/selection/$',views.CartsSelectAllView.as_view()),

    # 展示首页简单购物车
    url(r'^carts/simple/$',views.CartsSimpleView.as_view()),
]
