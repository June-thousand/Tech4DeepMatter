Full Data Pipeline: From Disk to Frontend Rendering

### 1. End-to-end Data Flow

### 1.1 Data Storage Location

```
H5 file → Stored on HDD / SSD
```

• The H5 file (cropped_volume_ROI.h5) is stored on a hard drive or SSD
• File size: 4.5 GB (compressed)
• Uncompressed: ~8 GB

### 1.2 Full Data Flow

```
┌─────────────┐
│   H5 File   │  ← Stored on HDD/SSD (4.5 GB compressed, 8 GB uncompressed)
│ (HDD / SSD) │
└──────┬──────┘
       │
       │ Step 1: Read from disk (slow)
       │ Time: ~825 ms per slice
       │ Or load everything at once: a few seconds (all slices)
       ↓
┌─────────────┐
│    RAM      │  ← NumPy array (full 3D array or a single slice)
│ (NumPy arr) │  Memory usage: ~8 GB (full) or ~3.7 MB (single slice)
└──────┬──────┘
       │
       │ Step 2: NumPy array indexing (very fast)
       │ Operation: data[slice_idx, :, :]
       │ Time: ~0.01 ms (microsecond level)
       ↓
┌─────────────┐
│   CPU Proc  │  ← Normalization, format conversion
│ (NumPy ops) │  Time: ~0.1–1 ms
└──────┬──────┘
       │
       │ Step 3: Convert to Qt format (QPixmap/QImage)
       │ Time: ~1–5 ms
       ↓
┌─────────────┐
│   GPU Draw  │  ← Qt rendering engine (optional, depends on hardware)
│ (Qt render) │  Time: ~1–10 ms (depends on image size)
└──────┬──────┘
       │
       │ Step 4: Display on screen
       │ Time: ~16 ms (60 FPS) or faster
       ↓
┌─────────────┐
│  Frontend   │  ← Image shown to the user
│ (UI screen) │
└─────────────┘
```

---

### 2. Detailed Breakdown of Each Step

### 2.1 Step 1: Read from HDD/SSD (the slowest part)

```python
with h5py.File('cropped_volume_ROI.h5', 'r') as f:
    dataset = f['data']
    slice_data = dataset[slice_idx, :, :]  # Read from disk
```

Performance:
• Time: ~825 ms per slice
• Bottleneck: disk I/O speed
• Influencing factors:
• SSD vs HDD: SSD is 10–100x faster
• Compression: gzip needs decompression time
• Access pattern: random access is slower than sequential access

This is exactly the part caching and prefetching aim to speed up.

### 2.2 Step 2: NumPy array indexing (very fast)

```python
data = self.h5_data[side]  # NumPy array already in RAM
slice_data = data[slice_idx, :, :]  # Direct indexing
```

Performance:
• Time: ~0.01 ms (10 microseconds)
• Bottleneck: RAM access speed
• Characteristics:
• Pure memory-to-memory access
• NumPy indexing is implemented in C, very fast
• Time cost is almost negligible

Your understanding is correct: this part is basically “almost free.”

### 2.3 Step 3: CPU processing (normalization, format conversion)

```python
# Normalize to 0–255
slice_min = np.min(slice_data)
slice_max = np.max(slice_data)
normalized = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)

# Convert to QImage
q_image = QImage(normalized.data, width, height, width, QImage.Format_Grayscale8)

```
Performance:
• Time: ~0.1–1 ms
• Bottleneck: CPU compute
• Operations:
• NumPy ops (min, max, normalization)
• Type conversion (float → uint8)
• Memory copy (NumPy → Qt format)

This step has some overhead, but it is small.

### 2.4 Step 4: Qt rendering (GPU/CPU rendering)

```python
pixmap = QPixmap.fromImage(q_image)
scene.addPixmap(pixmap)
view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
```

Performance:
• Time: ~1–10 ms
• Bottleneck:
• GPU rendering (if hardware acceleration)
• Or CPU rendering
• Operations:
• Qt graphics rendering
• Image scaling / fitting
• Display on screen

This step has noticeable overhead, but is still fast in absolute terms.

---

## 3. Key Questions

### 3.1 Which step is accelerated by caching and prefetching?

-> Only Step 1 (reading from disk).

```
┌─────────────┐
│  h5 file     │  ← cache and prefetch speed up this part
│ (hdd/SSD)  │  from ~825 ms → ~1 ms（if cache hit）
└──────┬──────┘
       │
       │ caching/prefetching speed up
       ↓
┌─────────────┐
│  RAM memory    │  ← data are already in the RAM
│ (numpy array) │
└──────┬──────┘
       │
       │ step2-4：these steps's cache/prefetch do not speed up
       │ data already in cache
       ↓
   frontend rendering
```

### 3.2 from RAM to frontend rendering, how long does it cost?

**->**：fast somehow

**time**：
- numpy indexing：~0.01 ms
- CPU normalization：~0.1-1 ms
- Qt rendering：~1-10 ms

**in total**：~1-11 ms

### 3.3 frontend rendering and cache / prefetch

**->**：**No direct relation** 

