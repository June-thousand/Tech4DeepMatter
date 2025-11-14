# -*- coding: utf-8 -*-
"""
切片预取模块
使用QThread在后台预取相邻切片
"""
import h5py
import numpy as np
from typing import Optional, List, Tuple
from PySide6.QtCore import QThread, Signal, QObject


class SlicePrefetchWorker(QThread):
    """
    后台线程：预取切片数据
    继承自QThread，在后台执行I/O操作，不阻塞UI
    """
    
    # 信号：切片预取完成
    slice_prefetched = Signal(int, int, np.ndarray)  # axis, slice_idx, data
    # 信号：预取错误
    prefetch_error = Signal(str)  # error_message
    
    def __init__(self, h5_file_path: str, dataset_key: str = 'data'):
        """
        初始化预取工作线程
        
        Args:
            h5_file_path: H5文件路径
            dataset_key: 数据集键名
        """
        super().__init__()
        self.h5_file_path = h5_file_path
        self.dataset_key = dataset_key
        self.h5_file: Optional[h5py.File] = None
        self.dataset: Optional[h5py.Dataset] = None
        self._stop_requested = False
        
        # 预取参数（由外部设置）
        self.axis = 0
        self.current_idx = 0
        self.prefetch_list: List[int] = []
    
    def open_file(self):
        """打开H5文件（在主线程调用）"""
        try:
            self.h5_file = h5py.File(self.h5_file_path, 'r')
            if self.dataset_key in self.h5_file:
                self.dataset = self.h5_file[self.dataset_key]
            else:
                # 尝试查找第一个3D数据集
                for key in self.h5_file.keys():
                    if isinstance(self.h5_file[key], h5py.Dataset) and len(self.h5_file[key].shape) == 3:
                        self.dataset = self.h5_file[key]
                        break
        except Exception as e:
            self.prefetch_error.emit(f"Failed to open H5 file: {e}")
    
    def close_file(self):
        """关闭H5文件"""
        if self.h5_file is not None:
            self.h5_file.close()
            self.h5_file = None
            self.dataset = None
    
    def prefetch_slices(self, axis: int, current_idx: int, prefetch_list: List[int]):
        """
        预取指定的切片列表（在线程中执行）
        
        Args:
            axis: 轴向 (0=Z, 1=Y, 2=X)
            current_idx: 当前切片索引
            prefetch_list: 要预取的切片索引列表（相对于current_idx的偏移）
        """
        if self.dataset is None:
            return
        
        self._stop_requested = False
        
        try:
            shape = self.dataset.shape
            max_idx = shape[axis] - 1
            
            for offset in prefetch_list:
                if self._stop_requested:
                    break
                
                target_idx = current_idx + offset
                if 0 <= target_idx <= max_idx:
                    # 根据轴向提取切片
                    if axis == 0:  # Z轴 (XY平面)
                        slice_data = self.dataset[target_idx, :, :]
                    elif axis == 1:  # Y轴 (XZ平面)
                        slice_data = self.dataset[:, target_idx, :]
                    elif axis == 2:  # X轴 (YZ平面)
                        slice_data = self.dataset[:, :, target_idx]
                    else:
                        continue
                    
                    # 转换为numpy数组并发送信号
                    slice_array = np.array(slice_data)
                    self.slice_prefetched.emit(axis, target_idx, slice_array)
        
        except Exception as e:
            self.prefetch_error.emit(f"Prefetch error: {e}")
    
    def run(self):
        """线程运行方法：执行预取任务"""
        if self.dataset is None:
            return
        
        self._stop_requested = False
        
        try:
            shape = self.dataset.shape
            max_idx = shape[self.axis] - 1
            
            for offset in self.prefetch_list:
                if self._stop_requested:
                    break
                
                target_idx = self.current_idx + offset
                if 0 <= target_idx <= max_idx:
                    # 根据轴向提取切片
                    if self.axis == 0:  # Z轴 (XY平面)
                        slice_data = self.dataset[target_idx, :, :]
                    elif self.axis == 1:  # Y轴 (XZ平面)
                        slice_data = self.dataset[:, target_idx, :]
                    elif self.axis == 2:  # X轴 (YZ平面)
                        slice_data = self.dataset[:, :, target_idx]
                    else:
                        continue
                    
                    # 转换为numpy数组并发送信号
                    slice_array = np.array(slice_data)
                    self.slice_prefetched.emit(self.axis, target_idx, slice_array)
        
        except Exception as e:
            self.prefetch_error.emit(f"Prefetch error: {e}")
    
    def stop(self):
        """停止预取"""
        self._stop_requested = True


class SlicePrefetcher(QObject):
    """
    切片预取管理器
    管理预取工作线程，提供高级接口
    """
    
    def __init__(self, h5_file_path: str, dataset_key: str = 'data'):
        """
        初始化预取管理器
        
        Args:
            h5_file_path: H5文件路径
            dataset_key: 数据集键名
        """
        super().__init__()
        self.h5_file_path = h5_file_path
        self.dataset_key = dataset_key
        self.worker: Optional[SlicePrefetchWorker] = None
        self.current_axis = 0
        self.current_idx = 0
    
    def start_prefetching(self, axis: int, current_idx: int, prefetch_range: int = 2):
        """
        开始预取相邻切片
        
        Args:
            axis: 当前轴向
            current_idx: 当前切片索引
            prefetch_range: 预取范围（前后各预取N个切片）
        """
        # 停止之前的预取
        self.stop_prefetching()
        
        # 构建预取列表（优先预取+1, +2，然后-1, -2）
        prefetch_list = []
        for i in range(1, prefetch_range + 1):
            prefetch_list.append(i)   # 向前预取
            prefetch_list.append(-i)  # 向后预取
        
        # 更新当前状态
        self.current_axis = axis
        self.current_idx = current_idx
        
        # 创建新的工作线程
        self.worker = SlicePrefetchWorker(self.h5_file_path, self.dataset_key)
        self.worker.open_file()
        
        # 连接信号
        self.worker.slice_prefetched.connect(self._on_prefetched)
        self.worker.prefetch_error.connect(self._on_error)
        
        # 设置预取参数并启动线程
        self.worker.axis = axis
        self.worker.current_idx = current_idx
        self.worker.prefetch_list = prefetch_list
        self.worker.start()  # 启动线程，会调用run方法
    
    def stop_prefetching(self):
        """停止预取"""
        if self.worker is not None:
            self.worker.stop()
            self.worker.quit()
            self.worker.wait(1000)  # 等待线程结束（最多1秒）
            self.worker.close_file()
            self.worker = None
    
    def _on_prefetched(self, axis: int, slice_idx: int, data: np.ndarray):
        """预取完成的回调（可以被子类重写）"""
        pass
    
    def _on_error(self, error_msg: str):
        """预取错误的回调（可以被子类重写）"""
        print(f"Prefetch error: {error_msg}")
    
    def cleanup(self):
        """清理资源"""
        self.stop_prefetching()

