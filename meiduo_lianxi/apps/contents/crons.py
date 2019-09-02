


# 生成首页静态化 定时器
import os
import time

from django.conf import settings
from django.template import loader

from apps.contents.models import ContentCategory
from apps.contents.utils import get_categories


def generate_static_index_html():

    # 测试
    print("%s:generate_static_index_html" % time.ctime())

    # 获取商品频道和分类
    categories = get_categories()

    # 获取所有广告类别

    content_category = ContentCategory.objects.all()

    contents ={}
    # 遍历广告类别 取出广告信息
    for category in content_category:
        contents[category.key] = category.content_set.filter(status=True).order_by('sequence')

    # 渲染模板
    context = {
        'categories': categories,
        'contents': contents
    }

    # 获取首页模板
    template = loader.get_template('index.html')
    # 渲染成html_text
    html_text = template.render(context)

    # 将html_text写入指定目录
    file_path = os.path.join(settings.STATICFILES_DIRS[0],'index.html')
    with open(file_path,'w',encoding='utf-8') as file:
        file.write(html_text)