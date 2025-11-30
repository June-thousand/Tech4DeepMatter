# Qt signal rule

## basic concept

###（Signal）
- like 'notification', when sth happened，object"emit"（emit）signal
- like bellring
- signal itself donot act, only inform

###（Slot）
- a func, receive operation from signal
- like sb open the door after hearing bellring
- slot is ordinary python func

### (Connect）
- connect signal and slot
- connect bellring and people
- `signal.connect(slot)`

## real cases

### case 1：simple signal - slot connection

```python
from PySide6.QtCore import QObject, Signal

class Worker(QObject):
    # 
    slice_prefetched = Signal(int, int, np.ndarray)  # para：axis, slice_idx, data
    
    def do_work(self):
        # 
        data = load_slice(0)
        # send signal
        self.slice_prefetched.emit(0, 0, data)  # sent

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = Worker()
        
        # connect signal to slot：when worker emit slice_prefetched，use self.on_slice_loaded
        self.worker.slice_prefetched.connect(self.on_slice_loaded)
    
    def on_slice_loaded(self, axis, slice_idx, data):
        """slot func: deal with slices"""
        print(f"load {slice_idx} done.")
        self.display_slice(data)
```

**execute process**：
1. `worker.do_work()` execution
2. `worker.slice_prefetched.emit(...)` emit signal
3. Qt use `main_widget.on_slice_loaded(...)`

## Receiver？

### define
- **Receiver**：#slot that received signal
- **use case**：examine how many func are listening to this signal

### why receivers？

in old Qt（PyQt4/PyQt5），use `signal.receivers` to examine：
```python
# old（PyQt5）
if signal.receivers(signal) > 0:
    print("signal connected")
```

but in **PySide6**，`Signal` object donot have `receivers` feature，error：
```
'PySide6.QtCore.SignalInstance' object has no attribute 'receivers'
```

### to solve this:
no examine. Qt allow multiple slot to conect to one signal

call all slot funcs when bellringed

### eg

```python
class Worker(QObject):
    slice_prefetched = Signal(int, int, np.ndarray)

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = Worker()
        
        # connect to the first slot func
        self.worker.slice_prefetched.connect(self.on_slice_loaded)
        
        # second
        self.worker.slice_prefetched.connect(self.update_cache)
        
        # third
        self.worker.slice_prefetched.connect(self.log_slice_info)
    
    def on_slice_loaded(self, axis, slice_idx, data):
        """slot func 1: """
        print(f"show slice {slice_idx}")
        self.display_slice(data)
    
    def update_cache(self, axis, slice_idx, data):
        """slot func 2："""
        print(f"cache slice {slice_idx}")
        self.cache.put(slice_idx, data)
    
    def log_slice_info(self, axis, slice_idx, data):
        """slot func 3："""
        print(f"record log：slice {slice_idx} loaded")
```

**process**（when `worker.slice_prefetched.emit(0, 5, data)` called）：
1. Qt call `on_slice_loaded(0, 5, data)` → show slice
2. Qt call `update_cache(0, 5, data)` → renew cache
3. Qt call `log_slice_info(0, 5, data)` → record log

**call process**：follow continum order to call


### cases

`show_preprocess_results.py`：

```python
# SlicePrefetcher - connect to signal inner
self.worker.slice_prefetched.connect(self._on_prefetched)  # inner

# connect another
self.worker.slice_prefetched.connect(
    lambda axis, idx, data, s=side: self._on_prefetched(s, axis, idx, data)
)  # outer
```

**prob**：suspend first：
```python
# error：try to visit receivers feature
if len(signal.receivers) == 0:  # PySide6 do not support！
    signal.connect(...)
```

### cases

```python
def _start_prefetching(self, side, slice_idx):
    # prefetch
    self.slice_prefetcher[side].start_prefetching(axis, slice_idx, prefetch_range)
    
    # connect to our method
    # attention：SlicePrefetcher connected to _on_prefetched
    # 2 slot funcs
    #   1. SlicePrefetcher._on_prefetched (inner)
    #   2. ShowPreprocessResults._on_prefetched (outer)
    if self.slice_prefetcher[side].worker:
        self.slice_prefetcher[side].worker.slice_prefetched.connect(
            lambda axis, idx, data, s=side: self._on_prefetched(s, axis, idx, data)
        )
```
