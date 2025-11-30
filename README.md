# A Summary of Technical Questions for DeepMatter


## Table of Contents
[** denotes ? sections]
|  Section   | Subsection  | Dates | Description |
|  ----  | ----  | ----  | ----  |
| Data  | [h5 file](#Data-h5-file) | 11.15 | Check format & info about h5 file  |
| Data  | [normalization](#Data-normalization) | 11.15 | Normalization in preparing data for deep learning network  |
| Preprocess  | [slices loading speed up](#Preprocess-speed-up) | 11.15 | Prefetching & Caching |
| Preprocess  | [data flow explanation](#Preprocess-data-flow) | 11.15 | Compare "load as whole" V.S. "load as move" |
| Qt  | [signal slot explanation](#Qt-signal-slot) | 11.15 | Explain Signal, Worker object and .connect function |



## Data
<a id = "Data-h5-file"></a>
### h5 file
[More codes and instruction to test h5 format](docs/H5.md)

<a id = "Data-normalization"></a>
### normalization
[More codes and instruction for using normalization](docs/NORMALIZATION_EXPLANATION.md)

## Preprocess
<a id = "Preprocess-speed-up"></a>
### slices loading speed up
[More codes and instruction of how preprocess was done](docs/PREPROCESS_H5_SLICE_SUMMARY.md)

<a id = "Preprocess-data-flow"></a>
### data flow explanation
[More codes and instruction explaining loading data from ssd -> RAM -> CPU (UI rendering)](docs/DATA_FLOW_EXPLANATION.md)

## Qt
<a id = "Qt-signal-slot"></a>
### signal slot explanation
[More codes and instruction of what is the signal slot in PySide6](docs/QT_SIGNAL_SLOT.md)

