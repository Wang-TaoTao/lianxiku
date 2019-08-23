# areas 子路由

from django.conf.urls import url
from django.contrib import admin
from . import views

urlpatterns = [

    # 提供省市区三级联动数据
    url(r'^areas/',views.AreasView.as_view()),

    # 新增地址
    url(r'^addresses/create/$',views.CreateAddressView.as_view()),

    # 修改和删除地址
    url(r'addresses/(?P<address_id>\d+)/$',views.UpdateDestroyAddressView.as_view()),

    # 设置默认地址
    url(r'^addresses/(?P<address_id>\d+)/default/$',views.DefaultAddressView.as_view()),

    #　修改地址标题
    url(r'^addresses/(?P<address_id>\d+)/title/$',views.UpdateTitleAddressView.as_view()),

    # 修改密码
    url(r'^password/',views.ChangePasswordView.as_view()),

]
