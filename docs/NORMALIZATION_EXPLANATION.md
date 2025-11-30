# normalization - preprocess.py

## why Normalization？

**normalize** make it within [0, 1] or [0, 255]

1. **data range**：different scanning of original voxel can be very large（ ~ 0-65535、1000-50000...）
2. **training stability**：nn converge better for this input 
3. **save space**：[0, 255] store in uint8
4. **better for visualization**：better for image processing

---

## preprocess.py --> locate where is normalization

### **function define**（line 121-144 ）

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
    min_val = image.min()  # find minimum
    max_val = image.max()  # find maximum

    if max_val == min_val:
        return np.zeros_like(image, dtype=np.uint8 if norm_type[1] == 255 else np.float32)

    # core normalization formula：
    # 1. first [0, 1]
    image = (image - min_val) / (max_val - min_val)
    # 2. second [norm_type[0], norm_type[1]]
    image = image * (norm_type[1] - norm_type[0]) + norm_type[0]

    if norm_type[1] == 255:
        return image.astype(np.uint8)  # transform to 8 bit unsign int（0-255）
    else:
        return image.astype(np.float32)  # to 32 bits float（0-1）
```

**math formula**：
```
normalized_value = (original_value - min) / (max - min) * (target_max - target_min) + target_min
```

---

### **normalization use cases**

#### case A：ROI circle tesing（line 259 ）

```python
d_center_slice_roi = read_image(path_image=slices_path_list_roi[d_idx_center_slice_roi])

d_center_slice_roi_uint8 = normalize_image_minmax(d_center_slice_roi, norm_type=[0, 255])
```

#### case B：ROI volume normalization（line 334-352）

```python
# Step 4: ROI Pass 1 - find global min & max
global_min, global_max = float("inf"), float("-inf")
for i, slice_path_full in enumerate(slices_path_list_roi[:crop_d]):
    slice_path_roi = slices_path_list_roi[i]
    d_slice_roi = read_image(slice_path_roi).astype(np.float32)  # read original tif，transform to float32
    d_slice_roi_cropped = d_slice_roi[h_start:h_end, w_start:w_end]  # crop ROI region
    
    # use（1% & 99%）to aviod outliers
    global_min = min(global_min, np.percentile(d_slice_roi_cropped, 1))
    global_max = max(global_max, np.percentile(d_slice_roi_cropped, 99))

# Step 5: ROI Pass 2 - apply normalization and save
for i, slice_path_full in enumerate(slices_path_list_roi[:crop_d]):
    slice_path_roi = slices_path_list_roi[i]
    d_slice_roi = read_image(slice_path_roi).astype(np.float32)
    d_slice_roi_cropped = d_slice_roi[h_start:h_end, w_start:w_end]
    
    # do it manually [0, 255]
    d_slice_roi_cropped = ((d_slice_roi_cropped - global_min) / (global_max - global_min)) * 255
    d_slice_roi_cropped_array[i] = d_slice_roi_cropped

# save as H5（uint8)
with h5py.File(output_cube_roi_path, "w") as f:
    f.create_dataset("data", data=d_slice_roi_cropped_array.astype(np.uint8), compression="gzip")
```


#### case C：Full volume norm（line 382-408）

same as B，only Full：

```python
# Step 6: Full Pass 1 - find global min & max
global_min, global_max = float("inf"), float("-inf")
for i, slice_path_full in enumerate(slices_path_list_full[...]):
    d_slice_full = read_image(slice_path_full).astype(np.float32)
    d_slice_full_cropped = d_slice_full[h_start:h_end, w_start:w_end]
    global_min = min(global_min, np.percentile(d_slice_full_cropped, 1))
    global_max = max(global_max, np.percentile(d_slice_full_cropped, 99))

# Step 7: Full Pass 2 - apply normalization and save
for i, slice_path_full in enumerate(slices_path_list_full[...]):
    d_slice_full = read_image(slice_path_full).astype(np.float32)
    d_slice_full_cropped = d_slice_full[h_start:h_end, w_start:w_end]
    
    # norm to [0, 255]
    d_slice_full_cropped = ((d_slice_full_cropped - global_min) / (global_max - global_min)) * 255
    d_slice_full_cropped_array[i] = d_slice_full_cropped
```

### example for percentage use case

```python
input = [1000, 1200, 1300, ..., 48000, 50000, 999999]  # 999999

min_val = np.percentile(input, 1)  # ≈ 1200
max_val = np.percentile(input, 99)  # ≈ 50000
```

---

## summary

| datatype | source | before norm | after norm | use case |
|---------|------|---------|---------|------|
| **NumPy array** | from TIF file | uint16 or float32<br/>data range：0-65535 or larger | uint8<br/> range：0-255 | save to H5 file |
| **volume info** | 3D volume data<br/>（D, H, W） | original scanning <br/> | to [0, 255] | training input |
| **single slice** | 2D image<br/>（H, W） | original | uint8 [0, 255] | OpenCV processing |

---

## whole dataset processing flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. tif input                                            │
│    - format：.tif                                       │
│    - type：uint16 or float32                            │
│    - range：0-65535                                    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ read_image()
┌─────────────────────────────────────────────────────────┐
│ 2. NumPy array（in ram）                                 │
│    - size：(D, H, W) or (H, W)                           │
│    - data type：float32（after transform）                │
│    - data range：keep origin                             │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ crop ROI
┌─────────────────────────────────────────────────────────┐
│ 3. array                                                │
│    - size：(crop_d, crop_h, crop_w)                      │
│    - range：(1000-50000)                                 │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ Pass 1: min/max
┌─────────────────────────────────────────────────────────┐
│ 4. stat                                                 │
│    - global_min = np.percentile(..., 1)  # eg 1200      │
│    - global_max = np.percentile(..., 99)  # eg 48000    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ Pass 2: normalize
┌─────────────────────────────────────────────────────────┐
│ 5. normalization                                        │
│    - formula：((value - global_min) / (global_max - global_min)) * 255 │
│    - data range：[0, 255]                               │
│    - datatype：float32                                  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓ astype(np.uint8)
┌─────────────────────────────────────────────────────────┐
│ 6. save as                                              │
│    - data type：uint8                                    │
│    - data range：[0, 255]                               │
│    - save format：H5 file compressed or TIF file        │
└─────────────────────────────────────────────────────────┘
```

---

## function position

- **normalization**：`preprocess.py` line 121-144
- **ROI circle detection normalization**：`preprocess.py` line 259
- **ROI volume normalization**：`preprocess.py` line 334-352
- **Full volume normalization**：`preprocess.py` line 382-408
- **image reading**：`data.py` line 18-48

