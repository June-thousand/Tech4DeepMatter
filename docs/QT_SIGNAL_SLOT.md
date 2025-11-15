# Qt 信号和槽机制详解

## 基本概念

### 信号（Signal）
- **定义**：信号是一个"通知"，当某个事件发生时，对象会"发射"（emit）信号
- **类比**：就像门铃，按一下就会响
- **特点**：信号本身不执行任何操作，只是通知"有事情发生了"

### 槽（Slot）
- **定义**：槽是一个函数，用来"接收"信号并执行相应的操作
- **类比**：就像听到门铃后去开门的人
- **特点**：槽是普通的 Python 函数或方法

### 连接（Connect）
- **定义**：将信号和槽"连接"起来，当信号发射时，槽函数会被自动调用
- **类比**：把门铃和开门的人连接起来
- **语法**：`signal.connect(slot)`

## 实际例子

### 例子 1：简单的信号-槽连接

```python
from PySide6.QtCore import QObject, Signal

class Worker(QObject):
    # 定义一个信号：切片预取完成
    slice_prefetched = Signal(int, int, np.ndarray)  # 参数：axis, slice_idx, data
    
    def do_work(self):
        # 做一些工作...
        data = load_slice(0)
        # 发射信号，通知"切片预取完成"
        self.slice_prefetched.emit(0, 0, data)  # 发射信号

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = Worker()
        
        # 连接信号到槽：当 worker 发射 slice_prefetched 信号时，调用 self.on_slice_loaded
        self.worker.slice_prefetched.connect(self.on_slice_loaded)
    
    def on_slice_loaded(self, axis, slice_idx, data):
        """槽函数：处理切片加载完成"""
        print(f"切片 {slice_idx} 加载完成！")
        self.display_slice(data)
```

**执行流程**：
1. `worker.do_work()` 执行
2. `worker.slice_prefetched.emit(...)` 发射信号
3. Qt 自动调用 `main_widget.on_slice_loaded(...)`

## Receiver（接收者）是什么？

### 定义
- **Receiver**：连接到信号的槽函数的数量
- **用途**：检查有多少个函数在"监听"这个信号

### 为什么会有 receivers？

在旧版本的 Qt（PyQt4/PyQt5），可以使用 `signal.receivers` 来检查：
```python
# 旧代码（PyQt5）
if signal.receivers(signal) > 0:
    print("信号已连接")
```

但在 **PySide6** 中，`Signal` 对象没有 `receivers` 属性，所以会报错：
```
'PySide6.QtCore.SignalInstance' object has no attribute 'receivers'
```

### 解决方案
不需要检查是否已连接，直接连接即可。Qt 允许多个槽函数连接同一个信号。

## 多个槽函数连接同一个信号

### 概念
**一个信号可以连接多个槽函数**，当信号发射时，所有连接的槽函数都会被调用。

### 例子

```python
class Worker(QObject):
    slice_prefetched = Signal(int, int, np.ndarray)

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = Worker()
        
        # 连接第一个槽函数
        self.worker.slice_prefetched.connect(self.on_slice_loaded)
        
        # 连接第二个槽函数（同一个信号！）
        self.worker.slice_prefetched.connect(self.update_cache)
        
        # 连接第三个槽函数（还是同一个信号！）
        self.worker.slice_prefetched.connect(self.log_slice_info)
    
    def on_slice_loaded(self, axis, slice_idx, data):
        """槽函数 1：显示切片"""
        print(f"显示切片 {slice_idx}")
        self.display_slice(data)
    
    def update_cache(self, axis, slice_idx, data):
        """槽函数 2：更新缓存"""
        print(f"缓存切片 {slice_idx}")
        self.cache.put(slice_idx, data)
    
    def log_slice_info(self, axis, slice_idx, data):
        """槽函数 3：记录日志"""
        print(f"记录日志：切片 {slice_idx} 已加载")
```

**执行流程**（当 `worker.slice_prefetched.emit(0, 5, data)` 被调用时）：
1. Qt 自动调用 `on_slice_loaded(0, 5, data)` → 显示切片
2. Qt 自动调用 `update_cache(0, 5, data)` → 更新缓存
3. Qt 自动调用 `log_slice_info(0, 5, data)` → 记录日志

**调用顺序**：按照连接的顺序依次调用

## 在我们的代码中的应用

### 问题场景

在 `show_preprocess_results.py` 中：

```python
# SlicePrefetcher 内部已经连接了信号
self.worker.slice_prefetched.connect(self._on_prefetched)  # 内部连接

# 我们想要额外连接一个槽函数
self.worker.slice_prefetched.connect(
    lambda axis, idx, data, s=side: self._on_prefetched(s, axis, idx, data)
)  # 外部连接
```

**问题**：之前的代码尝试先断开连接：
```python
# ❌ 错误：尝试访问 receivers 属性
if len(signal.receivers) == 0:  # PySide6 不支持！
    signal.connect(...)
```

**解决方案**：
```python
# ✅ 正确：直接连接，不需要检查
# Qt 允许多个槽函数连接同一个信号
signal.connect(slot1)  # 连接第一个
signal.connect(slot2)  # 连接第二个（不会覆盖第一个）
```

### 实际代码

```python
def _start_prefetching(self, side, slice_idx):
    # 启动预取
    self.slice_prefetcher[side].start_prefetching(axis, slice_idx, prefetch_range)
    
    # 连接信号到我们的方法
    # 注意：SlicePrefetcher 内部已经连接了信号到自己的 _on_prefetched
    # 我们这里再连接一个，这样两个函数都会被调用：
    #   1. SlicePrefetcher._on_prefetched (内部)
    #   2. ShowPreprocessResults._on_prefetched (外部)
    if self.slice_prefetcher[side].worker:
        self.slice_prefetcher[side].worker.slice_prefetched.connect(
            lambda axis, idx, data, s=side: self._on_prefetched(s, axis, idx, data)
        )
```

## 总结

1. **Receiver**：连接到信号的槽函数数量（PySide6 不支持直接访问）
2. **多个槽函数连接同一信号**：Qt 允许，信号发射时所有槽函数都会被调用
3. **不需要检查是否已连接**：直接 `connect()` 即可，不会覆盖已有的连接
4. **断开连接**：如果需要断开，使用 `signal.disconnect(slot)`，但通常不需要

## 最佳实践

```python
# ✅ 推荐：直接连接，不需要检查
signal.connect(slot1)
signal.connect(slot2)  # 可以多次连接

# ❌ 不推荐：尝试检查是否已连接（PySide6 不支持）
if signal.receivers == 0:  # 错误！
    signal.connect(slot)

# ✅ 如果需要避免重复连接，可以这样做：
try:
    signal.disconnect(slot)  # 先断开（如果已连接）
except:
    pass  # 如果没连接，忽略错误
signal.connect(slot)  # 再连接
```

