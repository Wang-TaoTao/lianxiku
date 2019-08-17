# users视图函数


import re
from django import http
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from pymysql import DatabaseError
from apps.users.models import User
from utils.response_code import RETCODE



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
        print(username)

        if not all([username, password, password2, mobile, allow]):

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


        # 保存用户数据
        try:
            user = User.objects.create_user(username=username,password=password,mobile=mobile)

        except DatabaseError as e:

            return render(request,'register.html',{'register_msg':'注册失败'})


        # 保持登录状态
        login(request,user)

        # 注册成功重定向到首页
        return redirect(reverse('contents:index'))

