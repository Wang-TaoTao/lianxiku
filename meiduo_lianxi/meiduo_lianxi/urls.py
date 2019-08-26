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

    # 配置goods路由
    url(r'^',include('apps.goods.urls',namespace = 'goods')),

    # 配置carts路由
    url(r'^',include('apps.carts.urls',namespace= 'carts')),

    # 配置第三方Haystack路由
    url(r'^search/', include('haystack.urls')),

]
