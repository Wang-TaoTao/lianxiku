# contents视图函数
from collections import OrderedDict

from django.shortcuts import render
from django.views import View

from apps.contents.models import ContentCategory
from apps.contents.utils import get_categories




# 首页广告
class IndexView(View):
    """首页广告"""

    def get(self, request):
       '''查询商品频道分类三级联动'''

       categories = get_categories()


       # 提供广告数据
       contents = {}

       content_categories = ContentCategory.objects.all()

       for cat in content_categories:
           contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

       # 渲染模板
       context = {
           'categories': categories,
           'contents':contents,

       }

       return render(request,'index.html',context)

