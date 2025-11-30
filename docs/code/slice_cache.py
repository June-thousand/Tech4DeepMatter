# -*- coding: utf-8 -*-
"""
Slice caching and prefetching module
Implements LRU Cache and prefetching optimizations
"""
from collections import OrderedDict
from typing import Optional, Tuple
import numpy as np


class SliceCache:
    """
    LRU Cache implementation - cache recently accessed slices
    Implemented with OrderedDict, most recently used at the end,
    oldest at the front.
    """
    
    def __init__(self, max_size: int = 20):
        """
        Initialize the LRU cache.
        
        Args:
            max_size: Maximum number of slices to cache.
        """
        self.cache: OrderedDict[Tuple[int, int], np.ndarray] = OrderedDict()
        self.max_size = max_size
        self.hits = 0    # cache hit count
        self.misses = 0  # cache miss count
    
    def get(self, axis: int, slice_idx: int) -> Optional[np.ndarray]:
        """
        Get a cached slice.
        
        Args:
            axis: Axis (0=Z, 1=Y, 2=X)
            slice_idx: Slice index.
            
        Returns:
            Cached slice data, or None if it does not exist.
        """
        key = (axis, slice_idx)
        if key in self.cache:
            # Hit: move to end to mark as most recently used
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key].copy()  # return a copy to avoid external modification
        else:
            self.misses += 1
            return None
    
    def put(self, axis: int, slice_idx: int, data: np.ndarray):
        """
        Add a slice to the cache.
        
        Args:
            axis: Axis.
            slice_idx: Slice index.
            data: Slice data.
        """
        key = (axis, slice_idx)
        
        # If it already exists, reorder it (will be updated below)
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            # If cache is full, remove the oldest item (front)
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)  # last=False means pop from the front
        
        # Add new data at the end
        self.cache[key] = data.copy()  # store a copy
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            A dict containing statistics such as hit rate.
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
        """Remove a specific cache entry."""
        key = (axis, slice_idx)
        if key in self.cache:
            del self.cache[key]
