import re

from QQLoginTool.QQtool import OAuthQQ
from django import http
from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.views import View
from django_redis import get_redis_connection
from pymysql import DatabaseError

from apps.oauth.models import OAuthQQUser
from apps.users.models import User
from meiduo_lianxi.settings.dev import logger
from utils.response_code import RETCODE



#　用户登录ＱＱ后的回调处理
from utils.secret import SecretOauth


class QQAuthUserView(View):

    def get(self,request):
        '''Oauth2.0认证'''

        #　接收code
        code = request.GET.get('code')
        if not code:
            return http.HttpResponseForbidden('缺少code')

        #　创建工具对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI)

        try:
            # 使用code向ＱＱ服务器请求access_token
            access_token = oauth.get_access_token(code)

            #　使用access_token向ＱＱ服务器请求openid
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('OAuth2.0认证失败')

        #　使用openid判断该ＱＱ用户是否绑定过商城
        try:
            oauth_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 如果openid没绑定美多商城用户
            # 加密ｏｐｅｎｄｉｄ 使用isdangerous
            secret_openid = SecretOauth().dumps({'openid':openid})
            context = {'openid':secret_openid}
            return render(request,'oauth_callback.html',context)


        else:
            # 如果openid已绑定美多商城用户
            qq_user = oauth_user.user
            login(request,qq_user)

            # 响应结果
            next = request.GET.get('state')
            response = redirect(next)

            #　登录时候将用户名写入cookie
            response.set_cookie('username',qq_user.username,max_age=3600*24*14)

            return response

    def post(self, request):
        """美多商城用户绑定到openid"""
        # 接收参数
        mobile = request.POST.get('mobile')
        pwd = request.POST.get('password')
        sms_code_client = request.POST.get('sms_code')
        openid = request.POST.get('openid')

        # 校验参数
        # 判断参数是否齐全
        if not all([mobile, pwd, sms_code_client]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', pwd):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 判断短信验证码是否一致
        redis_conn = get_redis_connection('sms_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '无效的短信验证码'})
        if sms_code_client != sms_code_server.decode():
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '输入短信验证码有误'})
        # 解密出openid 再判断openid是否有效
        openid = SecretOauth().loads(openid).get('openid')
        if not openid:
            return render(request, 'oauth_callback.html', {'openid_errmsg': '无效的openid'})

        # 保存注册数据
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 用户不存在,新建用户
            user = User.objects.create_user(username=mobile, password=pwd, mobile=mobile)
        else:
            # 如果用户存在，检查用户密码
            if not user.check_password(pwd):
                return render(request, 'oauth_callback.html', {'account_errmsg': '用户名或密码错误'})

        # 将用户绑定openid
        try:
            OAuthQQUser.objects.create(openid=openid, user=user)
        except DatabaseError:
            return render(request, 'oauth_callback.html', {'qq_login_errmsg': 'QQ登录失败'})

        # 实现状态保持
        login(request, user)

        # 响应绑定结果
        next = request.GET.get('state')
        response = redirect(next)

        # 登录时用户名写入到cookie，有效期15天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        return response

# 提供QQ登录页面的网址
class QQAuthURLView(View):


    def get(self,request):

        # next表示从那个页面进入到登录页面，登录成功后就自动进入那个页面
        next = request.GET.get('next')

        # 获取QQ登录页面
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI, state=next)

        login_url = oauth.get_qq_url()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'login_url': login_url})
