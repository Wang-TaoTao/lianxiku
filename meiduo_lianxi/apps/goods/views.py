import json

from django import http
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render
from django.views import View

from apps.contents.utils import get_categories
from apps.goods.models import GoodsCategory, SKU, GoodsVisitCount
from apps.goods.utils import get_breadcrumb
from apps.verifications import constants






from utils.response_code import RETCODE




# 用户浏览记录
class UserBrowseHistory(LoginRequiredMixin,View):

    def post(self,request):
        '''保存浏览记录'''

        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        # 校验参数 查出商品信息
        try:
            sku = SKU.objects.get(id = sku_id)

        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在!')
        # 连接redis
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection('history')
        # 构造用户 键
        user_key = 'history_%s' % request.user.id

        p1 = redis_conn.pipeline()
        # 去重
        p1.lrem(user_key,0,sku_id)
        # 添加
        p1.lpush(user_key,sku_id)
        # 截取
        p1.ltrim(user_key,0,4)
        p1.execute()


        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

    def get(self,request):
        '''查询浏览记录'''

        # 连接redis
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection('history')
        # 取出所有浏览记录
        redis_data = redis_conn.lrange('history_%s' % request.user.id,0,-1)

        skus= []
        for sku_id in redis_data:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                'id':sku.id,
                'name':sku.name,
                'default_image_url':sku.default_image.url,
                'price':sku.price,
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})




# 分类统计商品访问量
class DetailVisitView(View):

    def post(self,request,category_id):

        # 根据三级cotegort_id获取当前商品类别
        try:

            category = GoodsCategory.objects.get(id=category_id)

        except:
            return http.HttpResponseNotFound('缺少必传参数')

        # 构造查询日期
        from datetime import datetime
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_date = datetime.strptime(today_str,'%Y-%m-%d')

        # 查询当前商品类别在表中今天是否已经有记录
        try:
            # 如果有 就累加数量
            count_data = category.goodsvisitcount_set.get(date=today_date)
        except Exception as e:
            # 如果没有 就新建一条记录 再增加数量
            count_data = GoodsVisitCount()

        # 修改访问量
        try:
            count_data.count += 1
            count_data.category = category
            count_data.save()
        except Exception as e:
            return http.HttpResponseServerError('新增失败')

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})




# 商品详情页
class DetailView(View):

    def get(self,request,sku_id):

        # 查看当前sku的信息
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return render(request, '404.html')


        # 调用商品频道三级分类
        categories = get_categories()

        # 掉用面包屑组件
        breadcrumb = get_breadcrumb(sku.category)


        # 构建当前商品的规格键
        sku_specs = sku.specs.order_by('spec_id')
        sku_key = []
        for spec in sku_specs:
            sku_key.append(spec.option.id)

        # 获取当前商品的所有SKU
        skus = sku.spu.sku_set.all()
        # 构建不同的规格参数（选项）的sku字典
        spec_sku_map = {}
        for s in skus:
            # 获取sku的规格参数
            s_specs = s.specs.order_by('spec_id')
            # 用于形成规格参数-sku字典的键
            key = []
            for spec in s_specs:
                key.append(spec.option.id)
            # 向规格参数-sku字典添加记录
            spec_sku_map[tuple(key)] = s.id

        # 获取当前商品的规格信息
        goods_specs = sku.spu.specs.order_by('id')
        # 若当前sku的规格信息不完整，则不再继续
        if len(sku_key) < len(goods_specs):
            return
        for index,spec in enumerate(goods_specs):
            # 复制当前的sku的规格键
            key = sku_key[:]
            # 该规格的选项
            spec_options = spec.options.all()

            for option in spec_options:
                # 在规格参数sku字典中查找符合当前规格的sku
                key[index] = option.id
                option.sku_id = spec_sku_map.get(tuple(key))
            spec.spec_options = spec_options

        # 渲染页面
        context = {
            'categories':categories,
            'breadcrumb':breadcrumb,
            'sku':sku,
            'specs': goods_specs,
        }
        return render(request, 'detail.html', context)





# 热销排行
class HotGoodsView(View):

    def get(self,request,category_id):

        # 热销排行  [:2] 取出前两名
        skus = SKU.objects.filter(category=category_id,is_launched=True).order_by('-sales')[:2]

        # 构造前端需要的数据
        hot_skus = []
        for sku in skus:
            hot_skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price,
            })

        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'hot_skus': hot_skus})




# 商品列表页  ---商品频道-->面包屑组件-->排序-->分页
class ListView(View):

    def get(self,request,category_id,page_num):

        # 判断category_id是否正确
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound('GoodsCategory does not exist')

        # 调用商品频道三级联动
        categories = get_categories()

        # 调用面包屑导航
        breadcrumb = get_breadcrumb(category)



        # 排序
        # 1 接收参数
        sort = request.GET.get('sort','default')
        # 2 校验参数
        if sort == 'price':
            sort_filed = 'price'
        elif sort == 'hot':
            sort_filed = '-sales'
        else:
            sort_filed = 'create_time'

        # 3 对商品信息进行排序
        skus = SKU.objects.filter(category=category,is_launched=True).order_by(sort_filed)

        # 分页
        # 1 创建分页器对象
        paginator = Paginator(skus,constants.GOODS_LIST_LIMIT)
        # 2 获取每页的数据
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，默认给用户404
            return http.HttpResponseNotFound('empty page')
        # 3 获取总页数
        total_page = paginator.num_pages

        # 构造前端需要的数据  渲染页面
        context = {
            'categories': categories,  # 频道分类
            'breadcrumb': breadcrumb,  # 面包屑导航
            'sort': sort,  # 排序字段
            'category': category,  # 第三级分类
            'page_skus': page_skus,  # 分页后数据
            'total_page': total_page,  # 总页数
            'page_num': page_num,  # 当前页码
        }

        return render(request,'list.html',context)