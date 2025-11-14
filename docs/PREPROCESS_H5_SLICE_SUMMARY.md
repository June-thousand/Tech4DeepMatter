# 预处理流程中H5文件加载和切片代码总结

## 目录
1. [H5文件写入（预处理生成）](#h5文件写入)
2. [H5文件读取](#h5文件读取)
3. [切片提取和显示](#切片提取和显示)
4. [切片缓存和预取优化](#切片缓存和预取优化)
5. [文件查找和路径管理](#文件查找和路径管理)

---

## 1. H5文件写入（预处理生成）

### 1.1 `preprocess.py` - 预处理主文件

**位置**: `preprocess.py`

**功能**: 在预处理流程的最后阶段，将裁剪后的3D体积数据保存为H5文件

**关键代码**:

```python
# ROI体积保存 (Step 5)
output_cube_roi_path = os.path.join(output_cube_roi_dir, "cropped_volume_ROI.h5")
with h5py.File(output_cube_roi_path, "w") as f:
    f.create_dataset("data", data=d_slice_roi_cropped_array.astype(np.uint8), compression="gzip")

# Full体积保存 (Step 7)
output_cube_full_path = os.path.join(output_cube_full_dir, "cropped_volume_FULL.h5")
with h5py.File(output_cube_full_path, "w") as f:
    f.create_dataset("data", data=d_slice_full_cropped_array.astype(np.uint8), compression="gzip")
```

**特点**:
- 使用`gzip`压缩减少文件大小
- 数据集键名为`"data"`
- 数据类型为`uint8`
- 输出文件命名规范：
  - ROI: `cropped_volume_ROI.h5`
  - Full: `cropped_volume_FULL.h5`

**数据流程**:
1. 从TIFF切片文件读取数据
2. 进行ROI检测和裁剪
3. 归一化到0-255范围
4. 保存为H5格式

---

## 2. H5文件读取

### 2.1 `data.py` - 通用图像读取函数

**位置**: `data.py`, `models/stage1/data.py`

**函数**: `read_image(path_image: str) -> np.ndarray`

**功能**: 支持多种格式的图像读取，包括H5文件

**关键代码**:
```python
def read_image(path_image: str) -> np.ndarray:
    ext = os.path.splitext(path_image)[-1].lower()
    
    if ext == ".h5":
        with h5py.File(path_image, "r") as f:
            # Try "data" first, fallback to "image" if needed
            dataset_name = "data" if "data" in f else "image"
            image = f[dataset_name][:]
    # ... 其他格式处理
    return image
```

**特点**:
- 自动检测数据集键名（优先`"data"`，其次`"image"`）
- 使用上下文管理器确保文件正确关闭
- 返回完整的3D数组（D, H, W）

### 2.2 `show_preprocess_results.py` - 渐进式H5加载器

**位置**: `views/widgets/show_preprocess_results.py`

**类**: `ProgressiveH5Loader`

**功能**: 在后台线程中渐进式加载H5文件，先显示第一个切片，然后继续加载完整数据

**关键代码**:
```python
class ProgressiveH5Loader(QObject):
    def __init__(self, h5_file_path, side):
        self.h5_file_path = h5_file_path
        self.side = side
        self.chunk_size = 200  # 每次加载的切片数量
    
    def run(self):
        with h5py.File(self.h5_file_path, 'r') as f:
            # 查找数据集
            data_key = None
            possible_keys = ['data', 'image', 'volume', 'stack']
            
            # 查找第一个3D数组
            for key in f.keys():
                if isinstance(f[key], h5py.Dataset):
                    if len(f[key].shape) == 3:
                        data_key = key
                        break
            
            if data_key is None:
                for key in possible_keys:
                    if key in f:
                        data_key = key
                        break
            
            dataset = f[data_key]
            total_slices = dataset.shape[0]
            
            # 动态调整chunk_size
            if total_slices > 1000:
                self.chunk_size = 300
            elif total_slices > 500:
                self.chunk_size = 200
            else:
                self.chunk_size = 100
            
            # 第一步：快速读取第一个切片
            first_slice = dataset[0, :, :]
            self.first_slice_loaded.emit(self.side, first_slice, total_slices)
            
            # 第二步：预分配完整数组，分块加载
            full_data = np.zeros(dataset.shape, dtype=dataset.dtype)
            
            for start_idx in range(0, total_slices, self.chunk_size):
                end_idx = min(start_idx + self.chunk_size, total_slices)
                full_data[start_idx:end_idx, :, :] = dataset[start_idx:end_idx, :, :]
                self.chunk_loaded.emit(self.side, start_idx, end_idx, total_slices)
            
            self.all_data_loaded.emit(self.side, full_data)
```

**特点**:
- 使用QThread在后台加载，不阻塞UI
- 先显示第一个切片，提升用户体验
- 分块加载，动态调整chunk大小
- 预分配数组，避免内存碎片
- 通过信号机制更新进度

**信号**:
- `first_slice_loaded(side, first_slice, total_slices)`: 第一个切片加载完成
- `chunk_loaded(side, start_idx, end_idx, total)`: 数据块加载进度
- `all_data_loaded(side, full_data)`: 完整数据加载完成
- `load_failed(side, error_message)`: 加载失败

### 2.3 `slice_prefetcher.py` - H5文件预取器

**位置**: `views/widgets/slice_prefetcher.py`

**类**: `SlicePrefetchWorker`, `SlicePrefetcher`

**功能**: 在后台预取相邻切片，提升浏览体验

**关键代码**:
```python
class SlicePrefetchWorker(QThread):
    def open_file(self):
        self.h5_file = h5py.File(self.h5_file_path, 'r')
        if self.dataset_key in self.h5_file:
            self.dataset = self.h5_file[self.dataset_key]
        else:
            # 尝试查找第一个3D数据集
            for key in self.h5_file.keys():
                if isinstance(self.h5_file[key], h5py.Dataset) and len(self.h5_file[key].shape) == 3:
                    self.dataset = self.h5_file[key]
                    break
    
    def prefetch_slices(self, axis: int, current_idx: int, prefetch_list: List[int]):
        shape = self.dataset.shape
        max_idx = shape[axis] - 1
        
        for offset in prefetch_list:
            target_idx = current_idx + offset
            if 0 <= target_idx <= max_idx:
                # 根据轴向提取切片
                if axis == 0:  # Z轴 (XY平面)
                    slice_data = self.dataset[target_idx, :, :]
                elif axis == 1:  # Y轴 (XZ平面)
                    slice_data = self.dataset[:, target_idx, :]
                elif axis == 2:  # X轴 (YZ平面)
                    slice_data = self.dataset[:, :, target_idx]
                
                slice_array = np.array(slice_data)
                self.slice_prefetched.emit(axis, target_idx, slice_array)
```

**特点**:
- 保持H5文件句柄打开，避免重复打开开销
- 支持三个轴向的切片预取
- 可配置预取范围（前后各N个切片）
- 使用QThread在后台执行，不阻塞UI

---

## 3. 切片提取和显示

### 3.1 `show_preprocess_results.py` - 切片显示

**位置**: `views/widgets/show_preprocess_results.py`

**函数**: `display_slice(side, slice_idx)`

**功能**: 从3D数据中提取指定轴向和索引的切片并显示

**关键代码**:
```python
def display_slice(self, side, slice_idx):
    data = self.h5_data.get(side)
    if data is None:
        return
    
    axis = self.current_axis.get(side, 0)  # 0=Z, 1=Y, 2=X
    
    # 根据轴向获取切片
    if len(data.shape) == 3:
        if axis == 0:  # Z轴 (XY平面)
            if slice_idx >= data.shape[0]:
                slice_idx = data.shape[0] - 1
            slice_data = data[slice_idx, :, :]
            total_slices = data.shape[0]
        elif axis == 1:  # Y轴 (XZ平面)
            if slice_idx >= data.shape[1]:
                slice_idx = data.shape[1] - 1
            slice_data = data[:, slice_idx, :]
            total_slices = data.shape[1]
        elif axis == 2:  # X轴 (YZ平面)
            if slice_idx >= data.shape[2]:
                slice_idx = data.shape[2] - 1
            slice_data = data[:, :, slice_idx]
            total_slices = data.shape[2]
    
    # 归一化到0-255
    slice_min = np.min(slice_data)
    slice_max = np.max(slice_data)
    if slice_max > slice_min:
        normalized = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
    else:
        normalized = np.zeros_like(slice_data, dtype=np.uint8)
    
    # 转换为QImage并显示
    height, width = normalized.shape
    q_image = QImage(normalized.data, width, height, width, QImage.Format_Grayscale8)
    pixmap = QPixmap.fromImage(q_image)
    
    scene = self.lr_scene if side == "lr" else self.hr_scene
    view = self.lr_view if side == "lr" else self.hr_view
    scene.clear()
    scene.addPixmap(pixmap)
    scene.setSceneRect(pixmap.rect())
    view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
```

**特点**:
- 支持三个轴向的切片提取（Z/Y/X）
- 自动边界检查，防止索引越界
- 动态归一化，适应不同数据范围
- 实时更新显示，响应滑块变化

**轴向映射**:
- `axis=0`: Z轴，XY平面切片（`data[slice_idx, :, :]`）
- `axis=1`: Y轴，XZ平面切片（`data[:, slice_idx, :]`）
- `axis=2`: X轴，YZ平面切片（`data[:, :, slice_idx]`）

### 3.2 `preprocess.py` - 预处理中的切片处理

**位置**: `preprocess.py`

**功能**: 在预处理流程中处理切片数据

**关键代码**:
```python
# 读取中心切片用于ROI检测
d_idx_center_slice_full = len(slices_path_list_full)//2
d_center_slice_full = read_image(path_image=slices_path_list_full[d_idx_center_slice_full])

# 处理每个切片
for i, slice_path_roi in enumerate(slices_path_list_roi[:crop_d]):
    d_slice_roi = read_image(slice_path_roi).astype(np.float32)
    d_slice_roi_cropped = d_slice_roi[h_start:h_end, w_start:w_end]
    # ... 归一化和保存
    d_slice_roi_cropped_array[i] = d_slice_roi_cropped
```

**特点**:
- 从TIFF切片文件读取
- 进行空间裁剪
- 归一化处理
- 累积为3D数组后保存为H5

---

## 4. 切片缓存和预取优化

### 4.1 `slice_cache.py` - LRU缓存

**位置**: `views/widgets/slice_cache.py`

**类**: `SliceCache`

**功能**: 使用LRU（最近最少使用）策略缓存切片数据

**关键代码**:
```python
class SliceCache:
    def __init__(self, max_size: int = 20):
        self.cache: OrderedDict[Tuple[int, int], np.ndarray] = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, axis: int, slice_idx: int) -> Optional[np.ndarray]:
        key = (axis, slice_idx)
        if key in self.cache:
            self.cache.move_to_end(key)  # 移到末尾（最近使用）
            self.hits += 1
            return self.cache[key].copy()
        else:
            self.misses += 1
            return None
    
    def put(self, axis: int, slice_idx: int, data: np.ndarray):
        key = (axis, slice_idx)
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)  # 删除最旧的
        self.cache[key] = data.copy()
```

**特点**:
- 使用`OrderedDict`实现LRU策略
- 缓存键为`(axis, slice_idx)`元组
- 返回数据副本，避免外部修改
- 提供缓存统计信息（命中率等）

### 4.2 `slice_prefetcher.py` - 切片预取

**位置**: `views/widgets/slice_prefetcher.py`

**类**: `SlicePrefetcher`

**功能**: 管理切片预取，在用户浏览时提前加载相邻切片

**关键代码**:
```python
class SlicePrefetcher(QObject):
    def start_prefetching(self, axis: int, current_idx: int, prefetch_range: int = 2):
        # 构建预取列表（优先预取+1, +2，然后-1, -2）
        prefetch_list = []
        for i in range(1, prefetch_range + 1):
            prefetch_list.append(i)   # 向前预取
            prefetch_list.append(-i)  # 向后预取
        
        # 创建预取工作线程
        self.worker = SlicePrefetchWorker(self.h5_file_path, self.dataset_key)
        self.worker.open_file()
        self.worker.axis = axis
        self.worker.current_idx = current_idx
        self.worker.prefetch_list = prefetch_list
        self.worker.start()
```

**特点**:
- 优先预取向前切片（用户更可能向前浏览）
- 可配置预取范围
- 自动管理线程生命周期
- 支持停止和清理

---

## 5. 文件查找和路径管理

### 5.1 `models/stage1/data_preprocess.py` - 数据文件查找

**位置**: `models/stage1/data_preprocess.py`

**函数**: `find_data_files_by_project_id(project_id, history_id)`

**功能**: 根据项目ID和历史ID查找预处理后的H5文件

**关键代码**:
```python
def find_data_files_by_project_id(project_id: str, history_id: Optional[str] = None) -> Tuple[str, str]:
    for preprocess_dir, resolved_history_id in _iter_candidate_preprocess_dirs(project_id, history_id):
        full_dir = os.path.join(preprocess_dir, "full")
        roi_dir = os.path.join(preprocess_dir, "roi")
        
        # 查找h5文件
        lr_file = next(
            (
                os.path.join(full_dir, file)
                for file in os.listdir(full_dir)
                if file.endswith(".h5") and "FULL" in file.upper()
            ),
            None,
        )
        hr_file = next(
            (
                os.path.join(roi_dir, file)
                for file in os.listdir(roi_dir)
                if file.endswith(".h5") and "ROI" in file.upper()
            ),
            None,
        )
        
        if lr_file and hr_file:
            return lr_file, hr_file
```

**特点**:
- 支持指定history_id或自动查找
- 按优先级查找多个候选目录
- 验证文件存在性和可读性
- 返回完整文件路径

### 5.2 `show_preprocess_results.py` - H5文件识别

**位置**: `views/widgets/show_preprocess_results.py`

**函数**: `load_h5_files(project_id, history_id)`

**功能**: 查找并识别LR/HR H5文件

**关键代码**:
```python
def load_h5_files(self, project_id, history_id: Optional[str] = None):
    # 递归查找所有.h5文件
    h5_files = []
    for dir_path in preprocess_dir:
        if dir_path.exists():
            h5_files.extend(dir_path.rglob("*.h5"))
    
    # 识别LR和HR文件
    lr_file = None
    hr_file = None
    
    for h5_file in h5_files:
        filepath_lower = str(h5_file).lower()
        filename_lower = h5_file.name.lower()
        
        # 优先根据目录名识别（full -> LR, roi -> HR）
        if "/full/" in filepath_lower or "\\full\\" in filepath_lower:
            lr_file = h5_file
        elif "/roi/" in filepath_lower or "\\roi\\" in filepath_lower:
            hr_file = h5_file
        # 其次根据文件名识别
        elif "full" in filename_lower or "lr" in filename_lower:
            if lr_file is None:
                lr_file = h5_file
        elif "roi" in filename_lower or "hr" in filename_lower:
            if hr_file is None:
                hr_file = h5_file
    
    # 如果没有通过文件名识别，就按顺序分配
    if lr_file is None and hr_file is None and len(h5_files) >= 2:
        lr_file = h5_files[0]
        hr_file = h5_files[1]
```

**特点**:
- 递归查找所有H5文件
- 多策略识别LR/HR文件（目录名 > 文件名 > 顺序）
- 支持跨平台路径（Windows/Linux）
- 处理文件缺失情况

---

## 6. 数据流程总结

### 6.1 预处理阶段（生成H5文件）

```
TIFF切片文件 → 读取切片 → ROI检测 → 裁剪 → 归一化 → 累积3D数组 → 保存H5文件
```

**关键步骤**:
1. 从TIFF文件读取切片（`read_image`）
2. 检测ROI区域（中心切片）
3. 计算裁剪范围
4. 两遍扫描：第一遍找min/max，第二遍归一化
5. 保存为H5格式（`h5py.File`，gzip压缩）

### 6.2 显示阶段（加载和显示H5文件）

```
查找H5文件 → 渐进式加载 → 提取切片 → 归一化 → Qt显示
```

**关键步骤**:
1. 根据project_id查找H5文件
2. 后台线程渐进式加载（先显示第一个切片）
3. 根据轴向和索引提取切片
4. 动态归一化到0-255
5. 转换为QImage/QPixmap显示

### 6.3 优化机制

```
切片缓存（LRU） ← 切片预取（后台线程） ← 用户浏览
```

**优化策略**:
1. **缓存**: 使用LRU缓存最近访问的切片（默认20个）
2. **预取**: 后台预取相邻切片（前后各2个）
3. **渐进加载**: 先显示第一个切片，后台继续加载
4. **分块加载**: 大数据集分块加载，避免内存峰值

---

## 7. 关键数据结构

### 7.1 H5文件结构

```
cropped_volume_FULL.h5 / cropped_volume_ROI.h5
├── data (Dataset)
    ├── shape: (D, H, W) - 3D数组
    ├── dtype: uint8
    └── compression: gzip
```

### 7.2 切片索引

- **Z轴（axis=0）**: `data[slice_idx, :, :]` - XY平面
- **Y轴（axis=1）**: `data[:, slice_idx, :]` - XZ平面
- **X轴（axis=2）**: `data[:, :, slice_idx]` - YZ平面

### 7.3 缓存键

- 格式: `(axis, slice_idx)`
- 示例: `(0, 100)` 表示Z轴第100个切片

---

## 8. 性能优化要点

1. **文件句柄管理**: 预取器保持H5文件打开，避免重复打开开销
2. **分块加载**: 大数据集分块加载，平衡内存和速度
3. **后台线程**: 所有I/O操作在后台线程执行，不阻塞UI
4. **缓存机制**: LRU缓存减少重复读取
5. **预取策略**: 预测用户行为，提前加载相邻切片
6. **渐进显示**: 先显示第一个切片，提升响应速度

---

## 9. 相关文件清单

### 核心文件
- `preprocess.py` - 预处理主流程，生成H5文件
- `data.py` - 通用图像读取函数
- `models/stage1/data.py` - Stage1数据读取
- `services/preprocess_service.py` - 预处理服务封装

### UI显示相关
- `views/widgets/show_preprocess_results.py` - 显示预处理结果，包含渐进式加载器
- `views/widgets/slice_cache.py` - 切片缓存实现
- `views/widgets/slice_prefetcher.py` - 切片预取实现

### 数据管理
- `models/stage1/data_preprocess.py` - 数据文件查找和路径管理

---

## 10. 注意事项

1. **数据集键名**: 优先查找`"data"`，其次`"image"`，最后查找第一个3D数据集
2. **文件路径**: 支持相对路径和绝对路径，跨平台兼容
3. **内存管理**: 大数据集使用分块加载，避免一次性加载导致内存溢出
4. **线程安全**: 所有H5文件操作在独立线程中执行，避免阻塞UI
5. **错误处理**: 完善的错误处理和用户提示机制
6. **缓存清理**: 切换项目时自动清理缓存，避免内存泄漏

---

**文档生成时间**: 2025-01-XX
**代码库版本**: DeepMatter-RandD-6.2

