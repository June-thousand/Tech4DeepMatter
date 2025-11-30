"""
H5 File Structure Demo
Demonstrate how a 3D array is stored in an actual project H5 file
"""
import numpy as np
import h5py
import os

def demo_h5_structure():
    """
    Demonstrate H5 file structure and storage format using actual project data
    """
    print("=" * 80)
    print("H5 File Structure Demo (Using Actual Project Data)")
    print("=" * 80)
    
    # ==========================================
    # Use actual H5 files from the project
    # ==========================================
    # Try to locate an available H5 file
    h5_files = [
        "data/project_test/history_001/preprocess/full/cropped_volume_FULL.h5",
        "data/project_test/history_001/preprocess/roi/cropped_volume_ROI.h5",
        "data/project_001/preprocess/full/cropped_volume_FULL.h5",
        "data/project_001/preprocess/roi/cropped_volume_ROI.h5",
    ]
    
    h5_path = None
    for path in h5_files:
        if os.path.exists(path):
            h5_path = path
            break
    
    if h5_path is None:
        print(" No available H5 file found. Please ensure preprocessing has been executed.")
        return
    
    print(f"\n[Step 1] Load an actual H5 file from the project")
    print("-" * 80)
    print(f"File Path: {h5_path}")
    print(f"File Size: {os.path.getsize(h5_path) / (1024**2):.2f} MB")
    
    # ==========================================
    # Read and inspect H5 file structure
    # ==========================================
    print("\n[Step 2] Inspect H5 File Structure")
    print("-" * 80)
    
    with h5py.File(h5_path, "r") as f:
        print(f"Keys in H5 file: {list(f.keys())}")
        print(f"\nDetails of dataset 'data':")
        dataset = f["data"]
        print(f"  Shape: {dataset.shape}")
        print(f"  Dimensions: {dataset.ndim}D")
        print(f"  Data Type: {dataset.dtype}")
        print(f"  Compression: {dataset.compression}")
        print(f"  Uncompressed Data Size: {dataset.nbytes / (1024**2):.2f} MB")
        print(f"  Compressed File Size: {os.path.getsize(h5_path) / (1024**2):.2f} MB")
        print(f"  Compression Ratio: {(1 - os.path.getsize(h5_path) / dataset.nbytes) * 100:.1f}%")
        
        # Read partial data (avoid reading entire file if too large)
        print(f"\n[Step 3] Read Sample Data")
        print("-" * 80)
        
        # Read first slice
        first_slice = dataset[0, :, :]
        print(f"First Slice (dataset[0, :, :]):")
        print(f"  Shape: {first_slice.shape}")
        print(f"  Data Type: {first_slice.dtype}")
        print(f"  Value Range: [{first_slice.min()}, {first_slice.max()}]")
        print(f"  Mean: {first_slice.mean():.2f}")
        
        # Show top-left 10x10 region
        print(f"\nTop-left 10×10 region of first slice:")
        print(first_slice[:10, :10])
        
        # Read middle slice
        mid_idx = dataset.shape[0] // 2
        mid_slice = dataset[mid_idx, :, :]
        print(f"\nMiddle Slice (dataset[{mid_idx}, :, :]):")
        print(f"  Shape: {mid_slice.shape}")
        print(f"  Value Range: [{mid_slice.min()}, {mid_slice.max()}]")
        print(f"  Mean: {mid_slice.mean():.2f}")
        
        # Read last slice
        last_slice = dataset[-1, :, :]
        print(f"\nLast Slice (dataset[-1, :, :]):")
        print(f"  Shape: {last_slice.shape}")
        print(f"  Value Range: [{last_slice.min()}, {last_slice.max()}]")
        print(f"  Mean: {last_slice.mean():.2f}")
        
        # Read full data (if not too large)
        print(f"\n[Step 4] Read Full 3D Array")
        print("-" * 80)
        
        if dataset.nbytes < 500 * 1024 * 1024:  # <500MB
            print("Data size is small, reading full array...")
            loaded_data = dataset[:]
            print(f"  Full Array Shape: {loaded_data.shape}")
            print(f"  Full Array Type: {type(loaded_data)}")
            print(f"  Full Array Data Type: {loaded_data.dtype}")
            print(f"  Value Range: [{loaded_data.min()}, {loaded_data.max()}]")
            print(f"  Mean: {loaded_data.mean():.2f}")
            print(f"  Median: {np.median(loaded_data):.2f}")
        else:
            print("Data size is large, reading statistics only...")
            print("  Computing statistics...")
            min_val = dataset[:].min()
            max_val = dataset[:].max()
            mean_val = dataset[:].mean()
            print(f"  Value Range: [{min_val}, {max_val}]")
            print(f"  Mean: {mean_val:.2f}")
        
        # Explain 3D dimension meaning
        print(f"\n[Step 5] Explanation of 3D Array Dimensions")
        print("-" * 80)
        D, H, W = dataset.shape
        print(f"Shape (D, H, W) = ({D}, {H}, {W})")
        print(f"  D (Depth / Number of Slices) = {D}")
        print(f"  H (Height) = {H} pixels")
        print(f"  W (Width) = {W} pixels")
        print(f"  Total Pixel Count: {D * H * W:,}")
        print(f"  Pixels per Slice: {H} × {W} = {H * W:,}")
    
    # ==========================================
    # H5 file features and advantages
    # ==========================================
    print("\n[Step 6] Features of H5 Files")
    print("-" * 80)
    
    print("Features of H5 (HDF5) format:")
    print("  1. Can store NumPy arrays of any dimension (1D, 2D, 3D, 4D...)")
    print("  2. Supports compression (gzip, lzf, etc.) to save disk space")
    print("  3. Supports partial reads (read slices without loading entire file)")
    print("  4. Can store multiple datasets")
    print("  5. Can store metadata")
    print("  6. Cross-platform and multi-language support")
    
    print("\nIn this project, the H5 file stores:")
    print("  - A single 3D array (shape: D × H × W)")
    print("  - Dataset name: 'data'")
    print("  - Data type: uint8 (0–255, normalized)")
    print("  - Compression: gzip")
    print("  - Source: cropped volume generated in preprocess.py")
    
    # ==========================================
    # Partial read demonstration
    # ==========================================
    print("\n[Step 7] Partial Read Demonstration")
    print("-" * 80)
    
    with h5py.File(h5_path, "r") as f:
        dataset = f["data"]
        D, H, W = dataset.shape
        
        print("You can read specific slices without loading the full dataset:")
        print(f"  Read slice 0: dataset[0, :, :] → shape {dataset[0, :, :].shape}")
        print(f"  Read slice {D//4}: dataset[{D//4}, :, :] → shape {dataset[D//4, :, :].shape}")
        print(f"  Read slice {D//2}: dataset[{D//2}, :, :] → shape {dataset[D//2, :, :].shape}")
        print(f"  Read last slice: dataset[-1, :, :] → shape {dataset[-1, :, :].shape}")
        print(f"  Read a cropped region: dataset[{D//2}, {H//4}:{H*3//4}, {W//4}:{W*3//4}] → shape {dataset[D//2, H//4:H*3//4, W//4:W*3//4].shape}")
        
        print("\n✔ This partial reading ability is extremely useful for large 3D datasets!")
    
    # ==========================================
    # Connection to preprocess.py
    # ==========================================
    print("\n[Step 8] Connection to preprocess.py")
    print("-" * 80)
    
    print("How this H5 file was generated (workflow in preprocess.py):")
    print("""
    1. Build a 3D array:
       d_slice_cropped_array = np.zeros((crop_d, crop_h, crop_w), dtype=np.float32)
       # Read TIF slices one by one, crop and normalize...
       for i in range(crop_d):
           d_slice = read_image(slice_path).astype(np.float32)
           d_slice_cropped = d_slice[h_start:h_end, w_start:w_end]
           d_slice_cropped = ((d_slice_cropped - global_min) / (global_max - global_min)) * 255
           d_slice_cropped_array[i] = d_slice_cropped
    
    2. Save to H5:
       with h5py.File("cropped_volume_ROI.h5", "w") as f:
           f.create_dataset("data", data=d_slice_cropped_array.astype(np.uint8), compression="gzip")
    
    3. H5 file content:
       - A 3D NumPy array
       - Stored in dataset 'data'
       - Shape: (D, H, W) = depth × height × width
       - Type: uint8 (0–255, normalized)
       - Compression: gzip
    """)
    
    # ==========================================
    # Final summary
    # ==========================================
    print("\n" + "=" * 80)
    print("✔ Summary: An H5 file is simply a container storing 3D arrays!")
    print("=" * 80)
    
    # Open again for final info
    with h5py.File(h5_path, "r") as f:
        dataset = f["data"]
        print(f"  Current File: {h5_path}")
        print(f"  File Size: {os.path.getsize(h5_path) / (1024**2):.2f} MB")
        print(f"  Data Shape: {dataset.shape}")
        print(f"  Data Type: {dataset.dtype} (0–255)")
        print(f"  Compression: {dataset.compression}")
    print("=" * 80)


if __name__ == "__main__":
    demo_h5_structure()
