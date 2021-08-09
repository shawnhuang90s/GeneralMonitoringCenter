# -*- coding:utf-8 -*-
import peewee


class BaseModel(peewee.Model):
    """基本数据结构"""
    id = peewee.AutoField(primary_key=True)
    # 必填字段
    required_field = ()
    # 可选字段
    optional_field = ()

    @classmethod
    def get_table_page_vo(cls, page, size, limits=None, join_list=None, group_list=None):
        """分页设置"""
        if limits is None:
            query = cls.select(1)
        else:
            query = cls.select(1)
            for limit in limits:
                query = query.where(limit)
        if join_list is not None:
            for join in join_list:
                query = query.join(join[0], peewee.JOIN.LEFT_OUTER, on=join[1])
        if group_list is not None:
            for group in group_list:
                query = query.group_by(group)
        cnt = query.count()
        return {
            'currentPage': page,
            'pageSizes': size,
            'total': cnt,
        }

    @classmethod
    def query(cls, select=None, limit_list=None, join_list=None, group_list=None):
        """查询集"""
        if select is None:
            query = cls.select()
        else:
            query = cls.select(*select)
        if limit_list is not None:
            for limit in limit_list:
                query = query.where(limit)
        if join_list is not None:
            for join in join_list:
                query = query.join(join[0], peewee.JOIN.LEFT_OUTER, on=join[1])
        if group_list is not None:
            for group in group_list:
                query = query.group_by(group)

        return query
