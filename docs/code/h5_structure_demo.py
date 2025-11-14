"""
H5 文件结构演示
使用项目中实际的 H5 文件展示 3D 数组的存储方式
"""
import numpy as np
import h5py
import os

def demo_h5_structure():
    """
    使用项目中实际的 H5 文件演示结构和存储方式
    """
    print("=" * 80)
    print("H5 文件结构演示（使用项目实际数据）")
    print("=" * 80)
    
    # ==========================================
    # 使用项目中实际的 H5 文件
    # ==========================================
    # 尝试找到可用的 H5 文件
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
        print("❌ 未找到可用的 H5 文件，请确保已运行预处理流程")
        return
    
    print(f"\n【步骤 1】读取项目中的实际 H5 文件")
    print("-" * 80)
    print(f"文件路径: {h5_path}")
    print(f"文件大小: {os.path.getsize(h5_path) / (1024**2):.2f} MB")
    
    # ==========================================
    # 读取并检查 H5 文件结构
    # ==========================================
    print("\n【步骤 2】检查 H5 文件结构")
    print("-" * 80)
    
    with h5py.File(h5_path, "r") as f:
        print(f"H5 文件中的键（keys）: {list(f.keys())}")
        print(f"\n数据集 'data' 的详细信息:")
        dataset = f["data"]
        print(f"  形状: {dataset.shape}")
        print(f"  维度: {dataset.ndim}D")
        print(f"  数据类型: {dataset.dtype}")
        print(f"  压缩方式: {dataset.compression}")
        print(f"  数据大小（未压缩）: {dataset.nbytes / (1024**2):.2f} MB")
        print(f"  实际文件大小（压缩后）: {os.path.getsize(h5_path) / (1024**2):.2f} MB")
        print(f"  压缩率: {(1 - os.path.getsize(h5_path) / dataset.nbytes) * 100:.1f}%")
        
        # 读取部分数据（不读取全部，避免内存过大）
        print(f"\n【步骤 3】读取数据样本")
        print("-" * 80)
        
        # 读取第一层切片
        first_slice = dataset[0, :, :]
        print(f"第一层切片 (dataset[0, :, :]):")
        print(f"  形状: {first_slice.shape}")
        print(f"  数据类型: {first_slice.dtype}")
        print(f"  值范围: [{first_slice.min()}, {first_slice.max()}]")
        print(f"  平均值: {first_slice.mean():.2f}")
        
        # 显示第一层的前10x10区域
        print(f"\n第一层切片的前10x10区域:")
        print(first_slice[:10, :10])
        
        # 读取中间层切片
        mid_idx = dataset.shape[0] // 2
        mid_slice = dataset[mid_idx, :, :]
        print(f"\n中间层切片 (dataset[{mid_idx}, :, :]):")
        print(f"  形状: {mid_slice.shape}")
        print(f"  值范围: [{mid_slice.min()}, {mid_slice.max()}]")
        print(f"  平均值: {mid_slice.mean():.2f}")
        
        # 读取最后一层切片
        last_slice = dataset[-1, :, :]
        print(f"\n最后一层切片 (dataset[-1, :, :]):")
        print(f"  形状: {last_slice.shape}")
        print(f"  值范围: [{last_slice.min()}, {last_slice.max()}]")
        print(f"  平均值: {last_slice.mean():.2f}")
        
        # 读取完整数据（如果不太大）
        print(f"\n【步骤 4】读取完整 3D 数组")
        print("-" * 80)
        
        if dataset.nbytes < 500 * 1024 * 1024:  # 如果小于 500MB，读取全部
            print("数据量较小，读取完整数组...")
            loaded_data = dataset[:]
            print(f"  完整数组形状: {loaded_data.shape}")
            print(f"  完整数组类型: {type(loaded_data)}")
            print(f"  完整数组数据类型: {loaded_data.dtype}")
            print(f"  完整数组值范围: [{loaded_data.min()}, {loaded_data.max()}]")
            print(f"  完整数组平均值: {loaded_data.mean():.2f}")
            print(f"  完整数组中位数: {np.median(loaded_data):.2f}")
        else:
            print("数据量较大，仅读取统计信息...")
            # 使用分块读取计算统计信息
            print("  正在计算统计信息（可能需要一些时间）...")
            min_val = dataset[:].min()
            max_val = dataset[:].max()
            mean_val = dataset[:].mean()
            print(f"  值范围: [{min_val}, {max_val}]")
            print(f"  平均值: {mean_val:.2f}")
        
        # 展示 3D 数组的维度含义
        print(f"\n【步骤 5】3D 数组维度说明")
        print("-" * 80)
        D, H, W = dataset.shape
        print(f"形状 (D, H, W) = ({D}, {H}, {W})")
        print(f"  D (深度/切片数) = {D} 层")
        print(f"  H (高度) = {H} 像素")
        print(f"  W (宽度) = {W} 像素")
        print(f"  总像素数: {D * H * W:,}")
        print(f"  每层切片大小: {H} × {W} = {H * W:,} 像素")
    
    # ==========================================
    # H5 文件的特点和优势
    # ==========================================
    print("\n【步骤 6】H5 文件的特点")
    print("-" * 80)
    
    print("H5 文件（HDF5 格式）的特点：")
    print("  1. ✅ 可以存储任意维度的 NumPy 数组（1D, 2D, 3D, 4D...）")
    print("  2. ✅ 支持压缩（gzip, lzf 等），节省存储空间")
    print("  3. ✅ 支持部分读取（不需要加载整个文件，可以按需读取切片）")
    print("  4. ✅ 可以存储多个数据集（多个数组）")
    print("  5. ✅ 可以存储元数据（metadata）")
    print("  6. ✅ 跨平台、跨语言支持")
    
    print("\n在这个项目中，H5 文件存储的是：")
    print("  - 单个 3D 数组（形状: D × H × W）")
    print("  - 数据集名称: 'data'")
    print("  - 数据类型: uint8 (0-255，归一化后的值）")
    print("  - 压缩方式: gzip")
    print("  - 来源: preprocess.py 处理后的裁剪体积")
    
    # ==========================================
    # 展示部分读取的优势
    # ==========================================
    print("\n【步骤 7】H5 文件部分读取演示")
    print("-" * 80)
    
    with h5py.File(h5_path, "r") as f:
        dataset = f["data"]
        D, H, W = dataset.shape
        
        print("可以按需读取特定切片，而不需要加载整个文件：")
        print(f"  读取第 0 层: dataset[0, :, :]  → 形状 {dataset[0, :, :].shape}")
        print(f"  读取第 {D//4} 层: dataset[{D//4}, :, :]  → 形状 {dataset[D//4, :, :].shape}")
        print(f"  读取第 {D//2} 层: dataset[{D//2}, :, :]  → 形状 {dataset[D//2, :, :].shape}")
        print(f"  读取最后 1 层: dataset[-1, :, :]  → 形状 {dataset[-1, :, :].shape}")
        print(f"  读取中间区域: dataset[{D//2}, {H//4}:{H*3//4}, {W//4}:{W*3//4}]  → 形状 {dataset[D//2, H//4:H*3//4, W//4:W*3//4].shape}")
        
        print("\n✅ 这种部分读取能力非常适合处理大型 3D 数据！")
    
    # ==========================================
    # 与 preprocess.py 的关联
    # ==========================================
    print("\n【步骤 8】与 preprocess.py 的关联")
    print("-" * 80)
    
    print("这个 H5 文件是如何生成的（preprocess.py 流程）：")
    print("""
    1. 累积 3D 数组：
       d_slice_cropped_array = np.zeros((crop_d, crop_h, crop_w), dtype=np.float32)
       # 逐片读取 TIF 文件，裁剪并归一化...
       for i in range(crop_d):
           d_slice = read_image(slice_path).astype(np.float32)
           d_slice_cropped = d_slice[h_start:h_end, w_start:w_end]
           d_slice_cropped = ((d_slice_cropped - global_min) / (global_max - global_min)) * 255
           d_slice_cropped_array[i] = d_slice_cropped
    
    2. 保存为 H5：
       with h5py.File("cropped_volume_ROI.h5", "w") as f:
           f.create_dataset("data", data=d_slice_cropped_array.astype(np.uint8), compression="gzip")
    
    3. H5 文件内容：
       - 就是一个 3D NumPy 数组
       - 存储在名为 "data" 的数据集中
       - 形状: (D, H, W) = 深度 × 高度 × 宽度
       - 类型: uint8 (0-255，归一化后的值)
       - 压缩: gzip（节省存储空间）
    """)
    
    # ==========================================
    # 最终总结
    # ==========================================
    print("\n" + "=" * 80)
    print("✅ 总结：H5 文件就是存储 3D 数组的格式！")
    print("=" * 80)
    
    # 再次打开文件获取最终信息
    with h5py.File(h5_path, "r") as f:
        dataset = f["data"]
        print(f"  当前文件: {h5_path}")
        print(f"  文件大小: {os.path.getsize(h5_path) / (1024**2):.2f} MB")
        print(f"  数据形状: {dataset.shape}")
        print(f"  数据类型: {dataset.dtype} (0-255)")
        print(f"  压缩方式: {dataset.compression}")
    print("=" * 80)


if __name__ == "__main__":
    demo_h5_structure()

