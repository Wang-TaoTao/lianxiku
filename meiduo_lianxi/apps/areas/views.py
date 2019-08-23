import json
import re
from django.urls import reverse

from django import http
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache

from django.shortcuts import render, redirect

from django.views import View




from apps.areas.models import Area
from apps.users.models import Address
from meiduo_lianxi.settings.dev import logger
from utils.response_code import RETCODE




# 修改密码
class ChangePasswordView(LoginRequiredMixin,View):

    # 显示修改密码页面
    def get(self,request):

        return render(request,'user_center_pass.html')


    # 修改密码功能
    def post(self,request):

        # 接收参数
        old_pwd = request.POST.get('old_pwd')
        new_pwd = request.POST.get('new_pwd')
        new_cpwd = request.POST.get('new_cpwd')

        # 校验参数
        if not all([old_pwd,new_pwd,new_cpwd]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 校验密码是否正确
        result = request.user.check_password(old_pwd)

        if not result:
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})

        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_pwd):
            return http.HttpResponseForbidden('密码最少8位，最长20位')

        if new_pwd != new_cpwd:
            return http.HttpResponseForbidden('两次输入的密码不一致')

        # 修改密码
        try:
            request.user.set_password(new_pwd)
            request.user.save()

        except Exception as e:
            logger.error(e)
            return render(request, 'user_center_pass.html', {'change_pwd_errmsg': '修改密码失败'})


        # 清除状态保持的信息
        logout(request)
        response = redirect(reverse('users:login'))
        response.delete_cookie('username')

        # 响应修改密码的结果，重定向到了登录页面
        return response


#　设置默认标题
class UpdateTitleAddressView(View):

    def put(self,request,address_id):



        # 接收参数
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')

        try:
            # 查询地址
            address = Address.objects.get(id=address_id)

            #　设置默认标题
            address.title = title
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置地址标题失败'})

            # 4.响应删除地址结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置地址标题成功'})



# 设置默认地址
class DefaultAddressView(View):

    def put(self,request,address_id):

        # 根据参数获取对象
        address = Address.objects.get(id=address_id)

        try:
            # 设置为默认地址
            request.user.default_address = address
            request.user.save()

        except Exception as e:
            logger.error(e)

            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置默认地址失败'})

        # 响应设置默认地址结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置默认地址成功'})




# 修改和删除地址
class UpdateDestroyAddressView(View):

    # 修改收货地址
    def put(self,request,address_id):

        # 接收参数
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 修改地址
        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
        )
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '更新地址失败'})
        # 构造响应数据
        address = Address.objects.get(id=address_id)
        address_dict = {
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

        }
        # 返回给前端
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '更新地址成功', 'address': address_dict})

    # 删除收货地址
    def delete(self,request,address_id):

        address = Address.objects.get(id=address_id)

        try:
            address.is_deleted = True
            address.save()

        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '删除地址失败'})

        # 响应删除结果给前端
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})



# 新增收货地址
class CreateAddressView(View):

    def post(self,request):

        # 判断地址是否大于20
        count = Address.objects.filter(user=request.user).count()

        if count > 20 :
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '超过地址数量上限'})

        # 接收参数
        json_str = request.body.decode()
        json_dict = json.loads(json_str)

        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')


        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')

        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 写入参数
        try:
            address = Address.objects.create(
                user = request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
            # 设置默认地址
            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()

        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '新增地址失败'})


        # 构造响应数据
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email,
            }

        # 响应保存结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '新增地址成功', 'address': address_dict})


# 提供省市区三级联动数据
class AreasView(LoginRequiredMixin,View):

    def get(self,request):

        # 接收参数
        area_id = request.GET.get('area_id')

        # 如果没有area_id ，说明没有省份数据
        if not area_id:
            # 读取省份缓存数据
            province_list = cache.get('province_list')
            # 判断是否有省数据的缓存
            if not province_list:
                # 提供省份数据
                try:
                    province_model_list = Area.objects.filter(parent__isnull=True)
                    # 遍历省份数据
                    province_list= []
                    for province_model in province_model_list:
                        province_list.append({
                            'id':province_model.id,
                            'name':province_model.name,
                        })
                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '省份数据错误'})
                # 写入省份缓存数据
                cache.set('province_list',province_list,3600)

            # 响应省份数据
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': province_list})

        else:
            # 读取市区缓存数据
            sub_data = cache.get('sub_area_' + area_id)

            # 判断是否有市区缓存的数据
            if not sub_data:
                # 提供市区数据
                try:
                    parent_model = Area.objects.get(id=area_id)
                    sub_model_list = parent_model.subs.all()

                    # 序列化市区数据
                    sub_list = []
                    for sub_model in sub_model_list:
                        sub_list.append({
                          'id':sub_model.id,
                          'name':sub_model.name,
                        })

                    sub_data = {
                        'id':parent_model.id,
                        'name':parent_model.name,
                        'subs': sub_list,
                    }

                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '城市或区数据错误'})

                # 存储市区缓存数据
                cache.get('sub_area_'+area_id,sub_data,3600)
            # 响应市区数据
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'sub_data': sub_data})
