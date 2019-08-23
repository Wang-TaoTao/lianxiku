# 主路由
from django.conf.urls import url, include
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    # 配置users路由
    url(r'^',include('apps.users.urls',namespace = 'users')),

    # 配置contents路由
    url(r'^',include('apps.contents.urls',namespace ='contents')),

    # 配置verifications路由
    url(r'^',include('apps.verifications.urls',namespace ='verifications')),

    # 配置oauth路由
    url(r'^',include('apps.oauth.urls',namespace = 'oauth')),

    # 配置areas路由
    url(r'^',include('apps.areas.urls',namespace = 'areas')),

]
