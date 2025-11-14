# 归一化处理详解 - preprocess.py

## 📚 什么是归一化（Normalization）？

**归一化**是将数据按比例缩放，使其落入一个特定的数值范围（通常是 [0, 1] 或 [0, 255]）的过程。

### 为什么需要归一化？

1. **统一数据范围**：不同扫描的原始体素值范围可能差异很大（例如：0-65535、1000-50000等）
2. **提高模型训练稳定性**：神经网络训练时，输入数据在统一范围内更容易收敛
3. **节省存储空间**：归一化到 [0, 255] 可以用 uint8 存储，比 float32 节省 75% 空间
4. **便于可视化**：标准化的数值范围更容易进行图像显示和处理

---

## 🔍 preprocess.py 中的归一化代码位置

### 1️⃣ **归一化函数定义**（第 121-144 行）

```python
def normalize_image_minmax(image, norm_type=[0, 255]):
    """
    Normalize image to a given range, e.g., [0, 255] or [0, 1].
    
    Parameters:
        image (np.ndarray): Input image (grayscale or array).
        norm_type (list): Normalization range, e.g., [0, 255] or [0, 1].
    
    Returns:
        np.ndarray: Normalized image.
    """
    min_val = image.min()  # 找到图像中的最小值
    max_val = image.max()  # 找到图像中的最大值

    if max_val == min_val:
        return np.zeros_like(image, dtype=np.uint8 if norm_type[1] == 255 else np.float32)

    # 核心归一化公式：
    # 1. 先缩放到 [0, 1]
    image = (image - min_val) / (max_val - min_val)
    # 2. 再缩放到目标范围 [norm_type[0], norm_type[1]]
    image = image * (norm_type[1] - norm_type[0]) + norm_type[0]

    if norm_type[1] == 255:
        return image.astype(np.uint8)  # 转换为 8 位无符号整数（0-255）
    else:
        return image.astype(np.float32)  # 转换为 32 位浮点数（0-1）
```

**数学公式**：
```
normalized_value = (original_value - min) / (max - min) * (target_max - target_min) + target_min
```

---

### 2️⃣ **归一化的使用场景**

#### 场景 A：ROI 圆形检测时的归一化（第 259 行）

```python
# 读取 ROI 中心切片（原始 tif 文件，可能是 uint16，值范围 0-65535）
d_center_slice_roi = read_image(path_image=slices_path_list_roi[d_idx_center_slice_roi])

# 归一化到 [0, 255] 用于 OpenCV 的圆形检测
d_center_slice_roi_uint8 = normalize_image_minmax(d_center_slice_roi, norm_type=[0, 255])
```

**目的**：OpenCV 的圆形检测算法需要 uint8 类型（0-255 范围）的图像

**数据流**：
```
原始 TIF 文件 (uint16, 0-65535)
    ↓ read_image()
NumPy 数组 (可能是 uint16 或 float32)
    ↓ normalize_image_minmax()
NumPy 数组 (uint8, 0-255) ← 用于圆形检测
```

---

#### 场景 B：ROI 体积归一化（第 334-352 行）

```python
# Step 4: ROI Pass 1 - 查找全局最小值和最大值
global_min, global_max = float("inf"), float("-inf")
for i, slice_path_full in enumerate(slices_path_list_roi[:crop_d]):
    slice_path_roi = slices_path_list_roi[i]
    d_slice_roi = read_image(slice_path_roi).astype(np.float32)  # 读取原始 tif，转为 float32
    d_slice_roi_cropped = d_slice_roi[h_start:h_end, w_start:w_end]  # 裁剪 ROI 区域
    
    # 使用百分位数（1% 和 99%）来避免异常值影响
    global_min = min(global_min, np.percentile(d_slice_roi_cropped, 1))
    global_max = max(global_max, np.percentile(d_slice_roi_cropped, 99))

# Step 5: ROI Pass 2 - 应用归一化并保存
for i, slice_path_full in enumerate(slices_path_list_roi[:crop_d]):
    slice_path_roi = slices_path_list_roi[i]
    d_slice_roi = read_image(slice_path_roi).astype(np.float32)
    d_slice_roi_cropped = d_slice_roi[h_start:h_end, w_start:w_end]
    
    # 手动归一化到 [0, 255]
    d_slice_roi_cropped = ((d_slice_roi_cropped - global_min) / (global_max - global_min)) * 255
    d_slice_roi_cropped_array[i] = d_slice_roi_cropped

# 保存为 H5 文件（uint8 格式，节省空间）
with h5py.File(output_cube_roi_path, "w") as f:
    f.create_dataset("data", data=d_slice_roi_cropped_array.astype(np.uint8), compression="gzip")
```

**目的**：将整个 ROI 体积归一化到统一范围，便于后续训练

**数据流**：
```
多个 TIF 切片文件（每个切片的原始体素值范围可能不同）
    ↓ read_image() + 裁剪
NumPy 数组 (float32, 原始体素值，例如 1000-50000)
    ↓ 计算全局 min/max（使用百分位数避免异常值）
全局 min = 1200, 全局 max = 48000
    ↓ 归一化公式
NumPy 数组 (float32, 0-255)
    ↓ astype(np.uint8)
NumPy 数组 (uint8, 0-255) ← 保存到 H5 文件
```

---

#### 场景 C：Full 体积归一化（第 382-408 行）

与场景 B 完全相同，只是针对 Full 扫描数据：

```python
# Step 6: Full Pass 1 - 查找全局最小值和最大值
global_min, global_max = float("inf"), float("-inf")
for i, slice_path_full in enumerate(slices_path_list_full[...]):
    d_slice_full = read_image(slice_path_full).astype(np.float32)
    d_slice_full_cropped = d_slice_full[h_start:h_end, w_start:w_end]
    global_min = min(global_min, np.percentile(d_slice_full_cropped, 1))
    global_max = max(global_max, np.percentile(d_slice_full_cropped, 99))

# Step 7: Full Pass 2 - 应用归一化并保存
for i, slice_path_full in enumerate(slices_path_list_full[...]):
    d_slice_full = read_image(slice_path_full).astype(np.float32)
    d_slice_full_cropped = d_slice_full[h_start:h_end, w_start:w_end]
    
    # 归一化到 [0, 255]
    d_slice_full_cropped = ((d_slice_full_cropped - global_min) / (global_max - global_min)) * 255
    d_slice_full_cropped_array[i] = d_slice_full_cropped
```

---

## 📊 具体数据示例

### 示例 1：原始 TIF 文件数据

假设从 TIF 文件读取的原始数据：
```python
# 原始体素值（可能是 uint16，范围 0-65535）
原始数组 = np.array([
    [1200, 3500, 8900],
    [2100, 4500, 12000],
    [1500, 3800, 9500]
], dtype=np.uint16)

# 最小值 = 1200, 最大值 = 12000
```

### 示例 2：归一化过程

```python
# 步骤 1：缩放到 [0, 1]
normalized_0_1 = (原始数组 - 1200) / (12000 - 1200)
# 结果：
# [[0.0,   0.213,  0.713],
#  [0.083, 0.306,  1.0],
#  [0.028, 0.241,  0.769]]

# 步骤 2：缩放到 [0, 255]
normalized_0_255 = normalized_0_1 * 255
# 结果（转换为 uint8）：
# [[0,   54,  182],
#  [21,  78,  255],
#  [7,   61,  196]]
```

### 示例 3：使用百分位数的原因

```python
# 假设某个切片的数据：
原始数据 = [1000, 1200, 1300, ..., 48000, 50000, 999999]  # 999999 是异常值

# 如果直接用 min/max：
min_val = 1000
max_val = 999999  # 异常值会压缩正常数据的范围！

# 使用百分位数（1% 和 99%）：
min_val = np.percentile(原始数据, 1)  # ≈ 1200（忽略最小的 1%）
max_val = np.percentile(原始数据, 99)  # ≈ 50000（忽略最大的 1%）
# 这样异常值不会影响归一化范围
```

---

## 🎯 针对的数据类型总结

| 数据类型 | 来源 | 归一化前 | 归一化后 | 用途 |
|---------|------|---------|---------|------|
| **NumPy 数组** | 从 TIF 文件读取 | uint16 或 float32<br/>值范围：0-65535 或更大 | uint8<br/>值范围：0-255 | 存储到 H5 文件 |
| **体素信息** | 3D 体积数据<br/>（D, H, W） | 原始扫描值<br/>（可能每个切片范围不同） | 统一范围 [0, 255] | 训练模型输入 |
| **单张切片** | 2D 图像<br/>（H, W） | 原始值 | uint8 [0, 255] | OpenCV 处理 |

---

## 🔄 完整数据流程图

```
┌─────────────────────────────────────────────────────────┐
│ 1. 原始 TIF 文件（多个切片）                              │
│    - 格式：.tif                                          │
│    - 数据类型：uint16 或 float32                         │
│    - 值范围：0-65535 或更大（每个切片可能不同）          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ read_image()
┌─────────────────────────────────────────────────────────┐
│ 2. NumPy 数组（内存中）                                   │
│    - 形状：(D, H, W) 或 (H, W)                           │
│    - 数据类型：float32（转换后）                          │
│    - 值范围：保持原始值                                   │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ 裁剪 ROI 区域
┌─────────────────────────────────────────────────────────┐
│ 3. 裁剪后的数组                                           │
│    - 形状：(crop_d, crop_h, crop_w)                      │
│    - 值范围：原始值（例如 1000-50000）                    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ Pass 1: 计算全局 min/max（百分位数）
┌─────────────────────────────────────────────────────────┐
│ 4. 全局统计值                                             │
│    - global_min = np.percentile(..., 1)  # 例如 1200     │
│    - global_max = np.percentile(..., 99)  # 例如 48000   │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ Pass 2: 应用归一化公式
┌─────────────────────────────────────────────────────────┐
│ 5. 归一化后的数组                                         │
│    - 公式：((value - global_min) / (global_max - global_min)) * 255 │
│    - 值范围：[0, 255]                                     │
│    - 数据类型：float32                                    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ astype(np.uint8)
┌─────────────────────────────────────────────────────────┐
│ 6. 最终保存的数据                                         │
│    - 数据类型：uint8                                      │
│    - 值范围：[0, 255]                                     │
│    - 存储格式：H5 文件（压缩）或 TIF 文件                 │
│    - 文件大小：比原始 float32 小 75%                      │
└─────────────────────────────────────────────────────────┘
```

---

## 💡 关键要点

1. **归一化针对的是 NumPy 数组**：无论是从 TIF 还是 H5 读取，最终都是 NumPy 数组
2. **原始数据来源**：主要是从 TIF 文件读取的体素数据（3D 体积的切片）
3. **归一化目的**：
   - 统一数据范围（便于模型训练）
   - 节省存储空间（uint8 vs float32）
   - 适配处理工具（如 OpenCV 需要 uint8）
4. **使用百分位数**：避免异常值（噪声、伪影）影响归一化范围
5. **两遍扫描**：
   - Pass 1：计算全局 min/max
   - Pass 2：应用归一化并保存

---

## 🔗 相关代码位置

- **归一化函数**：`preprocess.py` 第 121-144 行
- **ROI 圆形检测归一化**：`preprocess.py` 第 259 行
- **ROI 体积归一化**：`preprocess.py` 第 334-352 行
- **Full 体积归一化**：`preprocess.py` 第 382-408 行
- **图像读取函数**：`data.py` 第 18-48 行

