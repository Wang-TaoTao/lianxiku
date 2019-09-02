# verifications 视图函数
import json
import re
from random import randint

from django import http
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View


# 校验图形验证码
from django_redis import get_redis_connection

from apps.users.models import User
from apps.verifications import constants
from celery_tasks.sms.tasks import ccp_send_sms_code
from meiduo_lianxi.settings.dev import logger
from utils.cookiesecret import CookieSecret
from utils.response_code import RETCODE






# 找回密码第三步 （修改密码）
class PwdThreeView(View):

    def post(self,request,user_id):

        # 接收参数
        json_dict = json.loads(request.body.decode())
        access_token = json_dict.get('access_token')
        password = json_dict.get('password')
        password2 = json_dict.get('password2')

        # 校验参数
        token = CookieSecret.loads(access_token)
        user_mobile = token['mobile']
        try:
            user = User.objects.get(id=user_id,mobile=user_mobile)
        except:
            return http.JsonResponse({'error': '数据错误'}, status=400)

        if not all([password,password2,access_token]):
            return http.JsonResponse({'error': '数据错误'}, status=400)

        if not re.match(r'^[0-9A-Za-z_]{8,20}',password):
            return http.JsonResponse({'error': '数据错误'}, status=400)
        if password != password2:
            return http.JsonResponse({'error': '数据错误'}, status=400)

        #　修改密码
        user.set_password(password)
        user.save()

        # 响应结果
        return http.JsonResponse({'message': 'ok'})




# 找回密码第二步 (验证短信验证码）
class PwdTwoCodeView(View):

    def get(self,request,username):

        # 接收参数
        sms_code = request.GET.get('sms_code')

        # 验证参数
        try:
            user = User.objects.get(username=username)
        except:
            return http.JsonResponse({'error': '数据错误'}, status=400)


        redis_conn = get_redis_connection('sms_code')
        redis_sms_code = redis_conn.get('sms_%s' % user.mobile)

        if redis_sms_code is None:
            return http.JsonResponse({'error': '数据错误'}, status=400)

        if sms_code != redis_sms_code.decode():
            return http.JsonResponse({'error': '数据错误'}, status=400)

        # 加密token
        access_token = CookieSecret.dumps({'user_id':user.id,'mobile':user.mobile})


        # 响应结果
        return http.JsonResponse({'user_id':user.id,'access_token':access_token})





# 找回密码第二步 （验证token，发送短信验证码）
class PwdTwoView(View):

    def get(self,request):

        # 接收token
        access_token = request.GET.get('access_token')

        # 解密
        token = CookieSecret.loads(access_token)

        # 验证token
        user_id = token['user_id']
        user_mobile = token['mobile']

        try:
            user = User.objects.get(id=user_id,mobile=user_mobile)
        except:
            return http.JsonResponse({'error':'数据错误'},status=400)

        # 生成短信验证码
        sms_code = '%06d' % randint(0,999999)
        # 写入redis
        redis_conn = get_redis_connection('sms_code')
        redis_conn.setex('sms_%s' % user_mobile,300,sms_code)

        # 异步发送短信验证码
        ccp_send_sms_code.delay(user_mobile,sms_code)
        print("短信验证码是:",sms_code)

        # 响应结果
        return http.JsonResponse({'message':'ok'})





# 找回密码第一步
class PwdOneView(View):

    def get(self,request,username):

        # 接收参数
        uuid = request.GET.get('image_code_id')
        image_code = request.GET.get('text')

        # 校验参数
        try:
            user = User.objects.get(username=username)
        except:
            return http.JsonResponse({'error': '数据错误'}, status=400)

        redis_conn = get_redis_connection('verify_image_code')
        redis_image_code = redis_conn.get(uuid)


        if redis_image_code is None:
            return http.JsonResponse({'error': '数据错误'}, status=400)

        if image_code.lower() != redis_image_code.decode().lower():
            return http.JsonResponse({'error': '数据错误'}, status=400)

        # 构造token
        access_token = CookieSecret.dumps({'user_id':user.id,'mobile':user.mobile})

        # 响应结果
        return http.JsonResponse({'mobile':user.mobile,'access_token':access_token})







# 验证图片验证码和手机验证码
class SMSCodeView(View):

    def get(self,request,mobile):
        # 接收参数
        uuid = request.GET.get('image_code_id')
        image_code = request.GET.get('image_code')
        print("---------------")
        print("图片 uuid",uuid)
        print("---------------")
        print("用户输入验证码内容",image_code)
        print("---------------")

        # 和图片验证码redis连接取uuid
        from django_redis import get_redis_connection
        image_redis_client = get_redis_connection('verify_image_code')
        redis_img_code = image_redis_client.get(uuid)

        # 校验
        if redis_img_code is None:
            return JsonResponse({'code':"4001",'errmsg':"图形验证码失效了"})
        # 删除
        try:
            image_redis_client.delete(uuid)

        except Exception as e:
            logger.error(e)

        # 将用户输入图片验证码和Redis中的验证码进行对比
        if image_code.lower() != redis_img_code.decode().lower():

            return JsonResponse({'code':'4001','errmsg':'输入图形验证码有误'})


        # 生成短信验证码,在redis中存储
        from random import randint
        sms_code = "%06d" % randint(0,999999)
        sms_code_redis = get_redis_connection('sms_code')


        # 判断发送短信是否频繁
        send_flag = sms_code_redis.get('send_flag_%s' % mobile )
        if send_flag:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '发送短信过于频繁'})

        # 创建redis管道
        p1 = sms_code_redis.pipeline()
        # 保存短信验证码
        p1.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # 重新写入send_flag
        p1.setex('send_flag_%s' % mobile,constants.SEND_SMS_CODE_INTERVAL, 1)
        # 执行管道请求
        p1.execute()

        # 让第三方 容联云 发送短信
        # from libs.yuntongxun.sms import CCP
        # CCP().send_template_sms(mobile,[sms_code,5],1)

        # 实现异步发送短信
        from celery_tasks.sms.tasks import ccp_send_sms_code
        ccp_send_sms_code.delay(mobile,sms_code)

        print("当前手机验证码是:",sms_code)

        # 响应前端结果
        return http.JsonResponse({'code': '0', 'errmsg': '发送短信成功'})






# 生成图形验证码
class ImageCodeView(View):

    def get(self,request,uuid):

        # 生成图片验证码
        from libs.captcha.captcha import captcha
        text ,image =captcha.generate_captcha()

        # 保存图片验证码
        from django_redis import get_redis_connection
        redis_client = get_redis_connection('verify_image_code')
        redis_client.setex(uuid,300,text)

        # 响应图形验证码
        return http.HttpResponse(image,content_type = 'image/jpeg')

