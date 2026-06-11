# Huayu-Global

**Real-time, quasi-global precipitation retrieval from a multi-satellite geostationary constellation**

Huayu-Global is a deep-learning precipitation monitoring system that combines
multispectral observations from GOES ABI, Meteosat SEVIRI, and FengYun-4B AGRI.
Sensor-specific Huayu models retrieve precipitation over the Americas,
Europe-Africa, and Asia-Pacific sectors, and the regional estimates are
reprojected and blended into a common quasi-global product.

This repository provides the Huayu-Global inference and mosaicking pipeline.

## Highlights

- Quasi-global coverage from `60°S` to `60°N`.
- Common `0.05°` latitude-longitude output grid (`2400 × 7200` cells).
- Independent models for ABI, AGRI, and SEVIRI observations.
- High-frequency input handling: 10-minute GOES scans and 15-minute
  FengYun/Meteosat scans.
- Overlap-aware averaging across geostationary satellite sectors.
- GeoTIFF output for both precipitation estimates and per-pixel observation
  counts.
- Optional local caching of preprocessed satellite tensors.

## System Overview

| Sector | Operational satellites | Instrument | Native sampling | Model |
| --- | --- | --- | --- | --- |
| Americas | GOES-16/19 East and GOES-18 West | ABI | 2 km / 10 min | Huayu-ABI |
| Europe-Africa | Meteosat-10/11 and Meteosat-9 IODC | SEVIRI | 3 km / 15 min | Huayu-SEVIRI |
| Asia-Pacific | FengYun-4B | AGRI | 4 km / 15 min | Huayu-AGRI |

For each inference timestamp, `HuayuGlobal.py`:

1. Locates the required FY-4B, GOES, and Meteosat observations.
2. Loads and preprocesses the sensor-specific multispectral arrays.
3. Runs the three Huayu retrieval models in `800 × 800` pixel tiles.
4. Maps each sector estimate to the common `0.05°` grid.
5. Averages overlapping estimates, applies spatial smoothing, and removes
   precipitation values below `0.1 mm`.
6. Writes the precipitation field and coverage count as GeoTIFF files.

## Evaluation Summary

Huayu-Global was evaluated against seven satellite precipitation products
using `5,395` independent stations and `1,847,967` matched 3-hour records from
July-December 2022 and January-June 2025.

| Metric | Huayu-Global | Reported result |
| --- | ---: | --- |
| Critical success index (CSI) | **0.441** | Highest among evaluated products |
| Accuracy (ACC) | 0.896 | Close to the best evaluated result |
| R² | **0.362** | Highest among evaluated products |
| Correlation coefficient (CC) | 0.605 | Close to IMERG Final Run (0.613) |
| RMSE | **1.961 mm** | Lowest among evaluated products |

These values summarize the independent evaluation and are not produced by the
inference example in this repository. The station validation datasets and the
complete training/evaluation pipeline are not included in this code release.

## Repository Layout

```text
Huayu-Global/
├── HuayuGlobal.py          # Inference, sector mosaicking, and GeoTIFF export
├── assets/                # Model weights, normalization data, and masks
│   ├── ABI/
│   │   ├── config.yml
│   │   ├── mean_std.npy
│   │   └── model.pt
│   ├── AGRI/
│   ├── SEVIRI/
│   ├── count_2022.tif
│   └── count_2025.tif
├── data/                   # Raw geostationary observations
│   ├── fy/4b/
│   ├── goes/{16,18,19}/
│   └── metsat/{0,IODC}/
├── cache/                  # Preprocessed tensor cache
└── results/                # Generated GeoTIFF products
```


> [!WARNING]
> A Git clone contains source code and placeholder files only. Model weights,
> normalization arrays, coverage masks, satellite observations, caches, output
> products, and ZIP archives are intentionally excluded by `.gitignore`.
> Cloning this repository alone is therefore not sufficient to run inference.

## Requirements

The reference implementation was developed with Python 3.12, PyTorch, and
Linux. A CUDA-capable GPU is strongly recommended because all three
241.78-million-parameter sector models are loaded for inference.

Direct dependencies used by `HuayuGlobal.py` include:

- `numpy`
- `scipy`
- `rasterio`
- `Pillow`
- `tqdm`
- PyTorch, through the Huayu model implementation
- The companion `jacksung` package, which supplies model, satellite-reader,
  geospatial, timing, and task-execution utilities

The companion `jacksung` package is installed separately and is not part of
this repository. Install a compatible version before running the example.
Install PyTorch using the command appropriate for your CUDA runtime from the
[official PyTorch installation guide](https://pytorch.org/get-started/locally/).

One minimal environment setup is:

```bash
conda create -n huayu-global python=3.12
conda activate huayu-global
python -m pip install numpy scipy rasterio pillow tqdm
# Install a CUDA-compatible PyTorch build and the companion jacksung package.
```

## Data and Model Setup

### Download

The trained model bundle, demonstration satellite observations, and
preprocessed demonstration cache are publicly available from the
[Huayu-Global Google Drive folder](https://drive.google.com/drive/folders/1NwqR6k46gymsIS95bsrkzvV4oWkiMHc5?usp=sharing).

`assets.zip` is always required. For the bundled `2025-01-02 00:00 UTC`
example, choose exactly one input option:

1. **Preprocessed cache:** download `cache_20250102_0000.pkl`. This is the
   shortest path to inference and does not require `data.zip`.
2. **Raw observations:** download `data.zip`. The pipeline reads and
   preprocesses the original FY-4B, GOES, and Meteosat files, then creates the
   same cache locally.

### Required External Files

The model bundle is required, followed by either the cache or the raw
observation bundle:

| Component | Required | Download | Approximate size | Final location |
| --- | --- | --- | ---: | --- |
| Trained models and support files | Yes | [`assets.zip`](https://drive.google.com/drive/folders/1NwqR6k46gymsIS95bsrkzvV4oWkiMHc5?usp=sharing) | 7.85 GiB compressed / 8.69 GiB extracted | `./assets/` |
| Preprocessed demonstration cache | Option A | [`cache_20250102_0000.pkl`](https://drive.google.com/drive/folders/1NwqR6k46gymsIS95bsrkzvV4oWkiMHc5?usp=sharing) | Approximately 3.11 GiB | `./cache/cache_20250102_0000.pkl` |
| Raw demonstration observations | Option B | [`data.zip`](https://drive.google.com/drive/folders/1NwqR6k46gymsIS95bsrkzvV4oWkiMHc5?usp=sharing) | 1.76 GiB compressed / 2.31 GiB extracted | `./data/` |
| Observations for another timestamp | Yes for custom runs | Downloaded from the satellite data providers | Depends on period | `./data/` |
| Companion `jacksung` Python package | Yes | Separate Python dependency | Environment-dependent | Active Python environment |

The `results/` directory is populated locally during inference. The `cache/`
directory either contains the downloaded PKL file or is populated
automatically while raw observations are preprocessed.

The checkpoint, normalization array, and sensor configuration in each model
directory form a matched set and must be kept together.

### Model Directory

After downloading and extracting the model bundle, the following files must
exist exactly at these paths:

```text
assets/
├── ABI/
│   ├── config.yml
│   ├── mean_std.npy
│   └── model.pt
├── AGRI/
│   ├── config.yml
│   ├── mean_std.npy
│   └── model.pt
├── SEVIRI/
│   ├── config.yml
│   ├── mean_std.npy
│   └── model.pt
├── count_2022.tif
└── count_2025.tif
```

| File | Purpose |
| --- | --- |
| `ABI/model.pt` | Huayu-ABI checkpoint for GOES observations |
| `AGRI/model.pt` | Huayu-AGRI checkpoint for FY-4B observations |
| `SEVIRI/model.pt` | Huayu-SEVIRI checkpoint for Meteosat observations |
| `*/mean_std.npy` | Sensor-specific channel normalization statistics |
| `*/config.yml` | Sensor and network configuration used to load the checkpoint |
| `count_2022.tif` | Expected coverage mask for timestamps before `2024-01-31` |
| `count_2025.tif` | Expected coverage mask for timestamps on or after `2024-01-31` |

All three model directories are required. The application initializes all
three networks at startup and does not currently support a single-sector
configuration.

### Satellite Input Directory

This section applies to the raw-observation option. It can be skipped when a
complete cache matching the inference timestamp is installed.

Satellite files are organized by platform and UTC acquisition date:

```text
data/
├── fy/4b/YYYY/M/D/
├── goes/16/YYYY/M/D/
├── goes/18/YYYY/M/D/
├── goes/19/YYYY/M/D/
├── metsat/0/YYYY/M/D/
└── metsat/IODC/YYYY/M/D/
```

`YYYY`, `M`, and `D` are the four-digit year, numeric month, and numeric day.
The supplied demonstration archive uses paths such as
`data/goes/16/2025/1/2/`. Preserve the original provider filenames because the
reader utilities extract platform, channel, and acquisition time from those
names.

For one Huayu-Global inference timestamp `T`, the current pipeline searches for:

| Input stream | Required product and format | Files around `T` | Destination |
| --- | --- | ---: | --- |
| FY-4B AGRI | Level-1 full-disk FDI multispectral product, 4 km, `.HDF` | 2 scans at `T+00` and `T+15 min` | `data/fy/4b/YYYY/M/D/` |
| GOES East | ABI Level-1b full-disk radiance, Mode 6, channels C08-C16, `.nc` | 9 channels × 3 scans at `T+00`, `T+10`, and `T+20 min` | `data/goes/16/...` or `data/goes/19/...` |
| GOES West | ABI Level-1b full-disk radiance, Mode 6, channels C08-C16, `.nc` | 9 channels × 3 scans at `T+00`, `T+10`, and `T+20 min` | `data/goes/18/YYYY/M/D/` |
| Meteosat prime service | SEVIRI full-disk native-format observation, `.nat` | 2 scans at `T+00` and `T+15 min` | `data/metsat/0/YYYY/M/D/` |
| Meteosat IODC | SEVIRI full-disk native-format observation, `.nat` | 2 scans at `T+00` and `T+15 min` | `data/metsat/IODC/YYYY/M/D/` |

All timestamps are interpreted as UTC. A complete quasi-global output normally
requires every stream in the table. Missing scans may leave uncovered pixels,
causing the final coverage check to reject the precipitation GeoTIFF.

GOES East uses:

- GOES-16 for timestamps before `2025-04-02`.
- GOES-19 for timestamps on or after `2025-04-02`.

The coverage mask changes at `2024-01-31` to account for the FY-4B
sub-satellite longitude change from `133°E` to `105°E`.

### Official Observation Sources

Raw observations can be obtained from their original providers:

- **GOES-16/18/19 ABI:** NOAA
  [GOES-R ABI/GLM data access](https://www.ncei.noaa.gov/products/goes-terrestrial-weather-abi-glm)
  or the public
  [NOAA GOES cloud archive](https://registry.opendata.aws/noaa-goes/).
  Select `ABI-L1b-RadF` full-disk radiance files for channels C08-C16.
- **Meteosat SEVIRI:** the
  [EUMETSAT Data Store](https://data.eumetsat.int/).
  Select full-disk SEVIRI Level-1.5 data in native format for both the prime
  service and Indian Ocean Data Coverage. An EUMETSAT account may be required.
- **FY-4B AGRI:** the
  [National Satellite Meteorological Center](https://www.nsmc.org.cn/nsmc/en/home/index.html)
  data service. Select FY-4B AGRI Level-1 full-disk FDI data at 4 km
  resolution. Registration and acceptance of the provider's data policy may be
  required.

Provider interfaces and product availability can change. Confirm the product
name, platform, acquisition time, scan mode, spatial coverage, and usage terms
before downloading large volumes.

For GOES cloud storage, the directory convention is
`ABI-L1b-RadF/YYYY/DDD/HH/`, where `DDD` is the zero-padded day of year and
`HH` is the UTC hour. For example, the demonstration timestamp is under day
`002` of 2025:

```bash
aws s3 ls s3://noaa-goes16/ABI-L1b-RadF/2025/002/00/ --no-sign-request
aws s3 ls s3://noaa-goes18/ABI-L1b-RadF/2025/002/00/ --no-sign-request
```

Download only the C08-C16 files for the three required scans, then place them
under the local `data/goes/<satellite>/YYYY/M/D/` hierarchy.

### Demonstration Data Manifest

For the raw-observation option, `data.zip` reproduces the input expected by the
default timestamp in `HuayuGlobal.py`. After extraction, it should contain:

| Directory | Expected observation files |
| --- | ---: |
| `data/fy/4b/2025/1/2/` | 2 FY-4B AGRI `.HDF` files |
| `data/goes/16/2025/1/2/` | 27 GOES-16 ABI `.nc` files |
| `data/goes/18/2025/1/2/` | 27 GOES-18 ABI `.nc` files |
| `data/goes/19/2025/1/2/` | 0 files; not used before `2025-04-02` |
| `data/metsat/0/2025/1/2/` | 2 Meteosat prime-service `.nat` files |
| `data/metsat/IODC/2025/1/2/` | 2 Meteosat IODC `.nat` files |

### Extracting Downloaded Archives

Place `assets.zip` in the repository root and extract its **contents** into
`assets/`:

```powershell
Expand-Archive .\assets.zip -DestinationPath .\assets -Force
```

```bash
unzip -o assets.zip -d assets
```

For **Option A**, place the downloaded cache at:

```text
cache/cache_20250102_0000.pkl
```

PowerShell:

```powershell
New-Item -ItemType Directory -Path .\cache -Force | Out-Null
Move-Item .\cache_20250102_0000.pkl .\cache\cache_20250102_0000.pkl
```

```bash
mkdir -p cache
mv cache_20250102_0000.pkl cache/cache_20250102_0000.pkl
```

For **Option B**, extract the raw observations:

```powershell
Expand-Archive .\data.zip -DestinationPath .\data -Force
```

```bash
unzip -o data.zip -d data
```

Do not create `assets/assets/` or `data/data/`. The expected checkpoint path,
for example, is `assets/ABI/model.pt`, not `assets/assets/ABI/model.pt`.

The archives may be deleted after successful extraction if disk space is
limited. Keep a verified copy elsewhere if reinstallation is expected.

### Preflight Check

On PowerShell, verify the required model files and the bundled demonstration
input before starting inference:

```powershell
$requiredModels = @(
  ".\assets\ABI\config.yml",
  ".\assets\ABI\mean_std.npy",
  ".\assets\ABI\model.pt",
  ".\assets\AGRI\config.yml",
  ".\assets\AGRI\mean_std.npy",
  ".\assets\AGRI\model.pt",
  ".\assets\SEVIRI\config.yml",
  ".\assets\SEVIRI\mean_std.npy",
  ".\assets\SEVIRI\model.pt",
  ".\assets\count_2022.tif",
  ".\assets\count_2025.tif"
)

$missing = $requiredModels | Where-Object { -not (Test-Path -LiteralPath $_) }
if ($missing) {
  $missing | ForEach-Object { Write-Error "Missing required file: $_" }
} else {
  Write-Host "Model bundle is complete."
}
```

For **Option A**, verify the cache:

```powershell
Get-Item .\cache\cache_20250102_0000.pkl
```

For **Option B**, verify the raw observation counts:

```powershell
Get-ChildItem .\data\fy\4b\2025\1\2\ -Filter *.HDF | Measure-Object
Get-ChildItem .\data\goes\16\2025\1\2\ -Filter *.nc | Measure-Object
Get-ChildItem .\data\goes\18\2025\1\2\ -Filter *.nc | Measure-Object
Get-ChildItem .\data\metsat\0\2025\1\2\ -Filter *.nat | Measure-Object
Get-ChildItem .\data\metsat\IODC\2025\1\2\ -Filter *.nat | Measure-Object
```

The expected demonstration counts are `2`, `27`, `27`, `2`, and `2`,
respectively. File counts alone do not guarantee valid data; filenames,
timestamps, channels, and file integrity must also match the requirements
above.

## Quick Start

After installing the dependencies, extracting `assets.zip`, and preparing
either the PKL cache or raw observations, run the bundled example:

```bash
python HuayuGlobal.py
```

The script creates a timestamped directory under `results/` and writes:

```text
count_YYYYMMDD_HHMM.tif   # Number of valid estimates contributing per cell
Huayu_YYYYMMDD_HHMM.tif   # Retrieved 3-hour precipitation accumulation
```

Both files use the following geographic definition:

| Property | Value |
| --- | --- |
| CRS layout | Regular latitude-longitude grid |
| Longitude | `-180°` to `180°` |
| Latitude | `60°N` to `60°S` |
| Resolution | `0.05° × 0.05°` |
| Raster shape | `7200` columns × `2400` rows |
| Data type | `float32` |

The precipitation GeoTIFF is written only when every cell required by the
selected standard coverage mask has at least one valid estimate. Inspect the
`count_*.tif` file when coverage validation fails.

## Python API

The pipeline can also be called from another Python module:

```python
from datetime import datetime

from HuayuGlobal import Huayu_Global

timestamp = datetime(2025, 1, 2, 0, 0)

pipeline = Huayu_Global(
  root_path="./results/example",
  model_dir="./assets",
  fy4b_file_dir="./data/fy/4b",
  goesE_file_dir="./data/goes/16",
  goesW_file_dir="./data/goes/18",
  msg0_file_dir="./data/metsat/0",
  msgIODC_file_dir="./data/metsat/IODC",
  cache_path="./cache",
  count_2022_path="./assets/count_2022.tif",
  count_2025_path="./assets/count_2025.tif",
)

precipitation, count = pipeline.predict(timestamp)
```

All path arguments used by the constructor are operationally required by the
current implementation, even though their function signatures default to
`None`.

`predict()` also accepts `exclude_idxs`, a list of scan keys to omit manually,
such as `["goesE+10", "ms+15"]`. This is useful when a known-bad scan should
not contribute to a mosaic.

## Caching and Operational Notes

- Cache files are named `cache_YYYYMMDD_HHMM.pkl`.
- A cache is valid only for the exact UTC timestamp encoded in its filename.
- When a matching complete cache exists, it supplies the preprocessed tensors,
  so `data.zip` is not required.
- When no matching cache exists, the pipeline reads the raw observations and
  writes a new cache under `cache_path`.
- Keep `ignore_cache_exist=False` when using a downloaded cache.
- Cache content is Python `pickle` data. Load only cache files created by a
  trusted Huayu-Global source. Pickle files can execute code while loading.
- GOES patches with values greater than or equal to `4095` are rejected.
- SEVIRI patches with more than `2%` missing values are rejected.
- Remaining SEVIRI and GOES gaps are filled with local-window means before
  inference.
- Warning filters in the entry point intentionally suppress runtime,
  non-georeferenced raster, and user warnings. Re-enable them while diagnosing
  data-quality or georeferencing issues.

## Scientific Scope and Limitations

Huayu-Global is designed for low-latency monitoring across geostationary
satellite domains. It is not a complete global precipitation solution:

- Regions poleward of `60°` are outside the output domain.
- Station-based validation is spatially uneven.
- Cloud-top radiances do not uniquely determine surface precipitation.
- Warm rain, snow, orographic precipitation, rapidly evolving convection, and
  heavy-rainfall magnitude remain challenging retrieval cases.
- Operational latency depends on upstream satellite delivery, preprocessing,
  inference, quality control, mosaicking, and product dissemination.

Users should independently validate the output for their region and
application before using it in operational or safety-critical workflows.

## Data Sources

Huayu-Global builds on observations and products provided by NOAA, EUMETSAT,
the National Satellite Meteorological Center of China, NASA/JAXA, the Met
Office Hadley Centre, and the China Meteorological Administration. Users are
responsible for complying with each provider's access and redistribution
terms.

## License

Copyright 2026 Huayu-Global Authors.

The source code and original documentation in this repository are licensed
under the [Apache License 2.0](LICENSE). Commercial use is permitted subject to
the license terms, including preservation of the license and attribution
notices. See [NOTICE](NOTICE) for the project attribution notice.

Separately downloaded satellite observations and other third-party materials
are not relicensed by this repository. Their use and redistribution remain
subject to the terms of their respective providers.
