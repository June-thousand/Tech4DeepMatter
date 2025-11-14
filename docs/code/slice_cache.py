# -*- coding: utf-8 -*-
"""
切片缓存和预取模块
实现LRU Cache和Prefetching优化
"""
from collections import OrderedDict
from typing import Optional, Tuple
import numpy as np


class SliceCache:
    """
    LRU Cache实现 - 缓存最近访问的切片
    使用OrderedDict实现，最近使用的在末尾，最旧的在前端
    """
    
    def __init__(self, max_size: int = 20):
        """
        初始化LRU Cache
        
        Args:
            max_size: 最大缓存切片数量
        """
        self.cache: OrderedDict[Tuple[int, int], np.ndarray] = OrderedDict()
        self.max_size = max_size
        self.hits = 0  # 缓存命中次数
        self.misses = 0  # 缓存未命中次数
    
    def get(self, axis: int, slice_idx: int) -> Optional[np.ndarray]:
        """
        获取缓存的切片
        
        Args:
            axis: 轴向 (0=Z, 1=Y, 2=X)
            slice_idx: 切片索引
            
        Returns:
            缓存的切片数据，如果不存在返回None
        """
        key = (axis, slice_idx)
        if key in self.cache:
            # 命中：移到末尾（标记为最近使用）
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key].copy()  # 返回副本，避免外部修改
        else:
            self.misses += 1
            return None
    
    def put(self, axis: int, slice_idx: int, data: np.ndarray):
        """
        添加切片到缓存
        
        Args:
            axis: 轴向
            slice_idx: 切片索引
            data: 切片数据
        """
        key = (axis, slice_idx)
        
        # 如果已存在，先移除（后面会重新添加）
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            # 如果缓存已满，删除最旧的（最前面的）
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)  # last=False表示从前面删除
        
        # 添加新数据到末尾
        self.cache[key] = data.copy()  # 保存副本
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            包含命中率等统计信息的字典
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'total_requests': total
        }
    
    def remove(self, axis: int, slice_idx: int):
        """移除指定的缓存项"""
        key = (axis, slice_idx)
        if key in self.cache:
            del self.cache[key]

