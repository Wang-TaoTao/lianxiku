# users视图函数
import json
import re
from django import http
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from itsdangerous import BadData
from pymysql import DatabaseError

from apps.carts.utils import merge_cart_cookie_to_redis
from apps.users.models import User, Address
from meiduo_lianxi.settings.dev import logger
from utils.response_code import RETCODE
from django.contrib.auth.mixins import LoginRequiredMixin









# 找回密码界面
class FindPwdView(View):

    def get(self,request):


        # 渲染找回密码界面
        return render(request,'find_password.html')






# 展示收货地址
class AddressView(LoginRequiredMixin,View):

    def get(self,request):

        # 获取用户列表
        login_user = request.user
        addresses = Address.objects.filter(user=login_user)

        address_dict_list = []

        for address in addresses:
            address_dict_list.append({
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email

            })

        context = {
            'default_address_id':login_user.default_address_id,
            'addresses':address_dict_list,
        }



        return render(request,'user_center_site.html',context)




# 验证链接提取user信息
def check_verify_email_token(token):
    """
    验证token并提取user
    :param token: 用户信息签名后的结果
    :return: user, None
    """
    from utils.secret import SecretOauth
    try:
        token_dict = SecretOauth().loads(token)
    except BadData:
        return None

    try:
        user = User.objects.get(id=token_dict['user_id'], email=token_dict['email'])
    except Exception as e:
        logger.error(e)
        return None
    else:
        return user



# 邮箱的验证
class VerifyEmailView(LoginRequiredMixin,View):
    """验证邮箱"""

    def get(self, request):
        """实现邮箱验证逻辑"""
        # 接收参数
        token = request.GET.get('token')

        # 校验参数：判断token是否为空和过期，提取user
        if not token:
            return http.HttpResponseBadRequest('缺少token')

        user = check_verify_email_token(token)
        if not user:
            return http.HttpResponseForbidden('无效的token')

        # 修改email_active的值为True
        try:
            request.user.email_active = True
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('激活邮件失败')

        # 返回邮箱验证结果
        return redirect(reverse('users:info'))


# 邮箱
class EmailView(LoginRequiredMixin,View):

    def put(self,request):
        '''实现邮箱添加逻辑'''

        # 接收参数
        json_str = request.body.decode()
        json_dict = json.loads(json_str)
        email = json_dict['email']
        print("邮箱是:",email)


        # 校验参数
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('参数email有误')

        # 赋值email字段
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '添加邮箱失败'})

        # 4.异步发送邮件

        from apps.users.utils import generate_verify_email_url
        verify_url = generate_verify_email_url(request.user)
        from celery_tasks.email.tasks import send_verify_email
        send_verify_email.delay(email, verify_url)




        # 响应添加邮箱结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加邮箱成功'})




# 个人中心
class UserInfoView(LoginRequiredMixin,View):

    def get(self,request):

        context = {
            'username':request.user.username,
            'mobile':request.user.mobile,
            'email':request.user.email,
            'email_active':request.user.email_active,
        }

        return render(request, 'user_center_info.html',context=context)





# 退出登录
class LogoutView(View):

    def get(self,request):

        # 清理session
        logout(request)
        # 退出登录,重定向到首页
        response = redirect(reverse('contents:index'))
        # 清楚cookie中的username
        response.delete_cookie('username')

        return response



# 用户登录功能
class LoginView(View):

    def get(self,request):
        '''登录界面'''
        return render(request,'login.html')


    def post(self,request):
        '''登录功能'''

        # 1.接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        # 2.校验参数
        if not all([username,password]):
            return http.HttpResponseForbidden('参数不齐全')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        # 验证用户名和密码 使用django自带的登录认证
        from django.contrib.auth import authenticate,login
        user = authenticate(username=username,password=password)

        # 校验是否正确
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})

        # 保持登录状态
        login(request,user)

        # 是否记住用户名
        if remembered != 'on':

            request.session.set_expiry(0)
        else:
            request.session.set_expiry(None)



        # 3响应登录结果
        # 翻转首页
        next = request.GET.get('next')
        if next:
            response = redirect(next)
        else:
            response = redirect(reverse('contents:index'))


        # 合并购物车功能
        response = merge_cart_cookie_to_redis(request,user,response)

        # 登录时用户名写入到cookie，有效期15天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        return response


# 判断手机号是否重复
class MobileCountView(View):

    def get(self,request,mobile):

        mobile_count = User.objects.filter(mobile=mobile).count()

        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK','count':mobile_count})



# 判断用户名是否重复
class UsernameCountView(View):

    def get(self,request,username):

        user_count = User.objects.filter(username=username).count()

        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK','count':user_count})


# 配置注册功能
class RegisterView(View):

    def get(self,request):

        return render(request,'register.html')


    def post(self,request):

        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        allow = request.POST.get('allow')
        sms_code = request.POST.get('msg_code')

        if not all([username, password, password2, mobile, allow, sms_code]):

            return http.HttpResponseForbidden('请将信息填写完整！')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$',username):

            return http.HttpResponseForbidden('请输入5-20位的用户名')

        if not re.match(r'^[0-9A-Za-z]{8,20}$',password):

            return http.HttpResponseForbidden('请输入8-20位的密码')

        if password != password2:

            return http.HttpResponseForbidden('两次密码输入不一致')

        if not re.match(r'^1[3-9]\d{9}$',mobile):

            return http.HttpResponseForbidden('请输入正确的手机号')

        if allow != 'on':

            return http.HttpResponseForbidden('请勾选用户协议')

        # 连接redis 取手机验证码
        from django_redis import get_redis_connection
        sms_code_client = get_redis_connection('sms_code')
        sms_code_redis = sms_code_client.get('sms_%s' % mobile)

        # 校验 如果为空说明过期
        if sms_code_redis is None:
            return render(request, 'register.html', {'sms_code_errmsg': '无效的短信验证码'})

        # 校验用户输入和数据库中的是否相等
        if sms_code != sms_code_redis.decode():
            return render(request, 'register.html', {'sms_code_errmsg': '输入短信验证码有误'})



        # 保存用户数据
        try:
            user = User.objects.create_user(username=username,password=password,mobile=mobile)

        except DatabaseError as e:

            return render(request,'register.html',{'register_msg':'注册失败'})




        # 保持登录状态
        login(request,user)

        # 注册成功重定向到首页
        # 响应注册结果
        response = redirect(reverse('contents:index'))

        # 注册时用户名写入到cookie，有效期15天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        return response

