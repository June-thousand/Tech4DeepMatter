# -*- coding: utf-8 -*-
"""
Slice prefetch module
Use QThread to prefetch neighboring slices in the background.
"""
import h5py
import numpy as np
from typing import Optional, List, Tuple
from PySide6.QtCore import QThread, Signal, QObject


class SlicePrefetchWorker(QThread):
    """
    Background thread: prefetch slice data.
    Inherits from QThread, performs I/O in the background
    without blocking the UI.
    """
    
    # Signal: slice prefetch completed
    slice_prefetched = Signal(int, int, np.ndarray)  # axis, slice_idx, data
    # Signal: prefetch error
    prefetch_error = Signal(str)  # error_message
    
    def __init__(self, h5_file_path: str, dataset_key: str = 'data'):
        """
        Initialize the prefetch worker thread.
        
        Args:
            h5_file_path: Path to the H5 file.
            dataset_key: Dataset key name.
        """
        super().__init__()
        self.h5_file_path = h5_file_path
        self.dataset_key = dataset_key
        self.h5_file: Optional[h5py.File] = None
        self.dataset: Optional[h5py.Dataset] = None
        self._stop_requested = False
        
        # Prefetch parameters (set externally)
        self.axis = 0
        self.current_idx = 0
        self.prefetch_list: List[int] = []
    
    def open_file(self):
        """Open the H5 file (call in main thread)."""
        try:
            self.h5_file = h5py.File(self.h5_file_path, 'r')
            if self.dataset_key in self.h5_file:
                self.dataset = self.h5_file[self.dataset_key]
            else:
                # Try to find the first 3D dataset
                for key in self.h5_file.keys():
                    if isinstance(self.h5_file[key], h5py.Dataset) and len(self.h5_file[key].shape) == 3:
                        self.dataset = self.h5_file[key]
                        break
        except Exception as e:
            self.prefetch_error.emit(f"Failed to open H5 file: {e}")
    
    def close_file(self):
        """Close the H5 file."""
        if self.h5_file is not None:
            self.h5_file.close()
            self.h5_file = None
            self.dataset = None
    
    def prefetch_slices(self, axis: int, current_idx: int, prefetch_list: List[int]):
        """
        Prefetch the specified list of slices (executed in the thread).
        
        Args:
            axis: Axis (0=Z, 1=Y, 2=X).
            current_idx: Current slice index.
            prefetch_list: List of slice offsets to prefetch
                           (relative to current_idx).
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
                    # Extract slice based on axis
                    if axis == 0:  # Z axis (XY plane)
                        slice_data = self.dataset[target_idx, :, :]
                    elif axis == 1:  # Y axis (XZ plane)
                        slice_data = self.dataset[:, target_idx, :]
                    elif axis == 2:  # X axis (YZ plane)
                        slice_data = self.dataset[:, :, target_idx]
                    else:
                        continue
                    
                    # Convert to NumPy array and emit signal
                    slice_array = np.array(slice_data)
                    self.slice_prefetched.emit(axis, target_idx, slice_array)
        
        except Exception as e:
            self.prefetch_error.emit(f"Prefetch error: {e}")
    
    def run(self):
        """Thread entry point: execute prefetch task."""
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
                    # Extract slice based on axis
                    if self.axis == 0:  # Z axis (XY plane)
                        slice_data = self.dataset[target_idx, :, :]
                    elif self.axis == 1:  # Y axis (XZ plane)
                        slice_data = self.dataset[:, target_idx, :]
                    elif self.axis == 2:  # X axis (YZ plane)
                        slice_data = self.dataset[:, :, target_idx]
                    else:
                        continue
                    
                    # Convert to NumPy array and emit signal
                    slice_array = np.array(slice_data)
                    self.slice_prefetched.emit(self.axis, target_idx, slice_array)
        
        except Exception as e:
            self.prefetch_error.emit(f"Prefetch error: {e}")
    
    def stop(self):
        """Request the prefetching to stop."""
        self._stop_requested = True


class SlicePrefetcher(QObject):
    """
    Slice prefetch manager.
    Manages the worker thread and provides a higher-level interface.
    """
    
    def __init__(self, h5_file_path: str, dataset_key: str = 'data'):
        """
        Initialize the prefetch manager.
        
        Args:
            h5_file_path: Path to the H5 file.
            dataset_key: Dataset key name.
        """
        super().__init__()
        self.h5_file_path = h5_file_path
        self.dataset_key = dataset_key
        self.worker: Optional[SlicePrefetchWorker] = None
        self.current_axis = 0
        self.current_idx = 0
    
    def start_prefetching(self, axis: int, current_idx: int, prefetch_range: int = 2):
        """
        Start prefetching neighboring slices.
        
        Args:
            axis: Current axis.
            current_idx: Current slice index.
            prefetch_range: Prefetch range (prefetch N slices before and after).
        """
        # Stop any previous prefetch
        self.stop_prefetching()
        
        # Build prefetch list (prioritize +1, +2, then -1, -2)
        prefetch_list = []
        for i in range(1, prefetch_range + 1):
            prefetch_list.append(i)   # forward
            prefetch_list.append(-i)  # backward
        
        # Update current state
        self.current_axis = axis
        self.current_idx = current_idx
        
        # Create a new worker thread
        self.worker = SlicePrefetchWorker(self.h5_file_path, self.dataset_key)
        self.worker.open_file()
        
        # Connect signals
        self.worker.slice_prefetched.connect(self._on_prefetched)
        self.worker.prefetch_error.connect(self._on_error)
        
        # Set prefetch parameters and start the thread
        self.worker.axis = axis
        self.worker.current_idx = current_idx
        self.worker.prefetch_list = prefetch_list
        self.worker.start()  # This will call run()
    
    def stop_prefetching(self):
        """Stop prefetching."""
        if self.worker is not None:
            self.worker.stop()
            self.worker.quit()
            self.worker.wait(1000)  # Wait up to 1 second for the thread to finish
            self.worker.close_file()
            self.worker = None
    
    def _on_prefetched(self, axis: int, slice_idx: int, data: np.ndarray):
        """Callback when a slice has been prefetched (override in subclass if needed)."""
        pass
    
    def _on_error(self, error_msg: str):
        """Callback when a prefetch error occurs (override in subclass if needed)."""
        print(f"Prefetch error: {error_msg}")
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_prefetching()
