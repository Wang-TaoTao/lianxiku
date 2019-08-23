
from collections import OrderedDict

from django.shortcuts import render

from apps.goods.models import GoodsChannel



# 封装首页商品频道三级联动
def get_categories():
    # 获取查询商品频道和分类
    categories = OrderedDict()
    # 获取所有频道
    channels = GoodsChannel.objects.order_by('group_id', 'sequence')

    # 遍历频道
    for channel in channels:
        # 获取当前组
        group_id = channel.group_id

        if group_id not in categories:
            categories[group_id] = {'channels': [], 'sub_cats': []}

        # 获取当前频道的类别
        cat1 = channel.category

        # 追加当前频道
        categories[group_id]['channels'].append({
            'id': cat1.id,
            'name': cat1.name,
            'url': channel.url
        })

        # 获取当前类别的子类别
        for cat2 in cat1.subs.all():
            cat2.sub_cats = []

            for cat3 in cat2.subs.all():
                cat2.sub_cats.append(cat3)

            categories[group_id]['sub_cats'].append(cat2)


    return categories



