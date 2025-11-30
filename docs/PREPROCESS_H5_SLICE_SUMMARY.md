## 1. H5

### 1.1 `preprocess.py`

```python
# ROI (Step 5)
output_cube_roi_path = os.path.join(output_cube_roi_dir, "cropped_volume_ROI.h5")
with h5py.File(output_cube_roi_path, "w") as f:
    f.create_dataset("data", data=d_slice_roi_cropped_array.astype(np.uint8), compression="gzip")

# Full (Step 7)
output_cube_full_path = os.path.join(output_cube_full_dir, "cropped_volume_FULL.h5")
with h5py.File(output_cube_full_path, "w") as f:
    f.create_dataset("data", data=d_slice_full_cropped_array.astype(np.uint8), compression="gzip")
```

**features**:
- use `gzip`compress file size
- key name `"data"`
- data type `uint8`
- output file naming format：
  - ROI: `cropped_volume_ROI.h5`
  - Full: `cropped_volume_FULL.h5`

---

## 2. H5 read

### 2.1 `data.py`

**@**: `data.py`, `models/stage1/data.py`

**func**: `read_image(path_image: str) -> np.ndarray`

**useage**: read multiple format image, include f5

**codes**:
```python
def read_image(path_image: str) -> np.ndarray:
    ext = os.path.splitext(path_image)[-1].lower()
    
    if ext == ".h5":
        with h5py.File(path_image, "r") as f:
            # Try "data" first, fallback to "image" if needed
            dataset_name = "data" if "data" in f else "image"
            image = f[dataset_name][:]
    # ... 
    return image
```

**feature**:
- auto detect dataset key name（first`"data"`，then`"image"`）
- use context management
- return（D, H, W）

### 2.2 `show_preprocess_results.py`

**@**: `views/widgets/show_preprocess_results.py`

**class**: `ProgressiveH5Loader`

**codes**:
```python
class ProgressiveH5Loader(QObject):
    def __init__(self, h5_file_path, side):
        self.h5_file_path = h5_file_path
        self.side = side
        self.chunk_size = 200  #
    
    def run(self):
        with h5py.File(self.h5_file_path, 'r') as f:
            #
            data_key = None
            possible_keys = ['data', 'image', 'volume', 'stack']
            
            #
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
            
            # 
            if total_slices > 1000:
                self.chunk_size = 300
            elif total_slices > 500:
                self.chunk_size = 200
            else:
                self.chunk_size = 100
            
            # 
            first_slice = dataset[0, :, :]
            self.first_slice_loaded.emit(self.side, first_slice, total_slices)
            
            # prefetch
            full_data = np.zeros(dataset.shape, dtype=dataset.dtype)
            
            for start_idx in range(0, total_slices, self.chunk_size):
                end_idx = min(start_idx + self.chunk_size, total_slices)
                full_data[start_idx:end_idx, :, :] = dataset[start_idx:end_idx, :, :]
                self.chunk_loaded.emit(self.side, start_idx, end_idx, total_slices)
            
            self.all_data_loaded.emit(self.side, full_data)
```



### 2.3 `slice_prefetcher.py` - H5

**@**: `views/widgets/slice_prefetcher.py`

**class**: `SlicePrefetchWorker`, `SlicePrefetcher`

```python
class SlicePrefetchWorker(QThread):
    def open_file(self):
        self.h5_file = h5py.File(self.h5_file_path, 'r')
        if self.dataset_key in self.h5_file:
            self.dataset = self.h5_file[self.dataset_key]
        else:
            # 
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
                # 
                if axis == 0:  # Z axis (XY plane)
                    slice_data = self.dataset[target_idx, :, :]
                elif axis == 1:  # Y axis (XZ plane)
                    slice_data = self.dataset[:, target_idx, :]
                elif axis == 2:  # X axis (YZ plane)
                    slice_data = self.dataset[:, :, target_idx]
                
                slice_array = np.array(slice_data)
                self.slice_prefetched.emit(axis, target_idx, slice_array)
```

---

## 3. slices

### 3.1 `show_preprocess_results.py` - rander

**@**: `views/widgets/show_preprocess_results.py`

**func**: `display_slice(side, slice_idx)`

```python
def display_slice(self, side, slice_idx):
    data = self.h5_data.get(side)
    if data is None:
        return
    
    axis = self.current_axis.get(side, 0)  # 0=Z, 1=Y, 2=X
    
    # 
    if len(data.shape) == 3:
        if axis == 0:  # Z
            if slice_idx >= data.shape[0]:
                slice_idx = data.shape[0] - 1
            slice_data = data[slice_idx, :, :]
            total_slices = data.shape[0]
        elif axis == 1:  # Y
            if slice_idx >= data.shape[1]:
                slice_idx = data.shape[1] - 1
            slice_data = data[:, slice_idx, :]
            total_slices = data.shape[1]
        elif axis == 2:  # X
            if slice_idx >= data.shape[2]:
                slice_idx = data.shape[2] - 1
            slice_data = data[:, :, slice_idx]
            total_slices = data.shape[2]
    
    # to 0-255
    slice_min = np.min(slice_data)
    slice_max = np.max(slice_data)
    if slice_max > slice_min:
        normalized = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
    else:
        normalized = np.zeros_like(slice_data, dtype=np.uint8)
    
    # transform to QImage and render
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

### 3.2 `preprocess.py`


**codes**:
```python
# 
d_idx_center_slice_full = len(slices_path_list_full)//2
d_center_slice_full = read_image(path_image=slices_path_list_full[d_idx_center_slice_full])

# 
for i, slice_path_roi in enumerate(slices_path_list_roi[:crop_d]):
    d_slice_roi = read_image(slice_path_roi).astype(np.float32)
    d_slice_roi_cropped = d_slice_roi[h_start:h_end, w_start:w_end]
    # ... 
    d_slice_roi_cropped_array[i] = d_slice_roi_cropped
```

---

## 4. slice cache and prefetch

### 4.1 `slice_cache.py` - LRU

**@**: `views/widgets/slice_cache.py`

**class**: `SliceCache`

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
            self.cache.move_to_end(key)  # 
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
                self.cache.popitem(last=False)  # 
        self.cache[key] = data.copy()
```


### 4.2 `slice_prefetcher.py`

**@**: `views/widgets/slice_prefetcher.py`

**class**: `SlicePrefetcher`

**code**:
```python
class SlicePrefetcher(QObject):
    def start_prefetching(self, axis: int, current_idx: int, prefetch_range: int = 2):
        # 
        prefetch_list = []
        for i in range(1, prefetch_range + 1):
            prefetch_list.append(i)   # 
            prefetch_list.append(-i)  # 
        
        # 
        self.worker = SlicePrefetchWorker(self.h5_file_path, self.dataset_key)
        self.worker.open_file()
        self.worker.axis = axis
        self.worker.current_idx = current_idx
        self.worker.prefetch_list = prefetch_list
        self.worker.start()
```

---

## 5. file search

### 5.1 `models/stage1/data_preprocess.py`

**func**: `find_data_files_by_project_id(project_id, history_id)`

```python
def find_data_files_by_project_id(project_id: str, history_id: Optional[str] = None) -> Tuple[str, str]:
    for preprocess_dir, resolved_history_id in _iter_candidate_preprocess_dirs(project_id, history_id):
        full_dir = os.path.join(preprocess_dir, "full")
        roi_dir = os.path.join(preprocess_dir, "roi")
        
        # 
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


### 5.2 `show_preprocess_results.py` - H5

**@**: `views/widgets/show_preprocess_results.py`

**func**: `load_h5_files(project_id, history_id)`

```python
def load_h5_files(self, project_id, history_id: Optional[str] = None):
    # recursion
    h5_files = []
    for dir_path in preprocess_dir:
        if dir_path.exists():
            h5_files.extend(dir_path.rglob("*.h5"))
    
    # 
    lr_file = None
    hr_file = None
    
    for h5_file in h5_files:
        filepath_lower = str(h5_file).lower()
        filename_lower = h5_file.name.lower()
        
        # file path first（full -> LR, roi -> HR）
        if "/full/" in filepath_lower or "\\full\\" in filepath_lower:
            lr_file = h5_file
        elif "/roi/" in filepath_lower or "\\roi\\" in filepath_lower:
            hr_file = h5_file
        # file name second
        elif "full" in filename_lower or "lr" in filename_lower:
            if lr_file is None:
                lr_file = h5_file
        elif "roi" in filename_lower or "hr" in filename_lower:
            if hr_file is None:
                hr_file = h5_file
    
    # 
    if lr_file is None and hr_file is None and len(h5_files) >= 2:
        lr_file = h5_files[0]
        hr_file = h5_files[1]
```
