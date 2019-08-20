# users子路由

from django.conf.urls import url
from . import views
urlpatterns = [

    # 注册界面
    url(r'^register/$',views.RegisterView.as_view()),

    # 用户名重复
    url(r'^username/(?P<username>[a-zA-Z0-9_-]{5,20})/count/',views.UsernameCountView.as_view()),

    # 手机号重复
    url(r'^mobile/(?P<mobile>1[3-9]\d{9})/count/',views.MobileCountView.as_view()),

    # 用户名登录
    url(r'^login/',views.LoginView.as_view()),

    # 退出登录
    url(r'^logout/',views.LogoutView.as_view()),

    # 个人中心
    url(r'^info/',views.UserInfoView.as_view(),name='info'),

    # 邮箱
    url(r'^emails/$',views.EmailView.as_view()),

    # 验证邮箱后端
    url(r'^emails/verification/',views.VerifyEmailView.as_view()),


]
