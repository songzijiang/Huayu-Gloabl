import os.path
import random
import traceback

from jacksung.ai.GeoAttX import Huayu
from jacksung.utils.data_convert import np2tif, Coordinate, fill_nan_with_window_mean_fast
from jacksung.ai.utils.fy import get_agri_file_path, getNPfromHDF
from jacksung.ai.utils.goes import get_filename_by_date_from_dir, getNPfromDir
from jacksung.ai.utils.metsat import get_seviri_file_path, getNPfromNAT
from datetime import datetime, timedelta
from jacksung.utils.multi_task import MultiTasks, ThreadingLock
from tqdm import tqdm
import numpy as np
from jacksung.utils.time import Stopwatch
from scipy.ndimage import uniform_filter
import pickle
from rasterio.errors import NotGeoreferencedWarning
import warnings
from PIL import Image

# Suppress RuntimeWarning messages.
warnings.filterwarnings("ignore", category=RuntimeWarning)
# Suppress rasterio warnings for arrays without embedded georeferencing.
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)
warnings.filterwarnings("ignore", category=UserWarning)


class Huayu_Global:
    def __init__(self, root_path='./results', model_dir=None, fy4b_file_dir=None, goesW_file_dir=None,
                 goesE_file_dir=None, msg0_file_dir=None, msgIODC_file_dir=None, cache_path=None,
                 count_2022_path=None, count_2025_path=None):
        st = Stopwatch()
        self.model_dir = model_dir
        self.cache_path = cache_path
        self.agri_model_dir = os.path.join(self.model_dir, 'AGRI')
        self.abi_model_dir = os.path.join(self.model_dir, 'ABI')
        self.seviri_model_dir = os.path.join(self.model_dir, 'SEVIRI')
        self.fy4b_file_dir = fy4b_file_dir
        self.goesW_file_dir = goesW_file_dir
        self.goesE_file_dir = goesE_file_dir
        self.msg0_file_dir = msg0_file_dir
        self.msgIODC_file_dir = msgIODC_file_dir
        self.root_path = root_path
        self.count_2022_path = count_2022_path
        self.count_2025_path = count_2025_path
        if os.path.exists(self.count_2022_path):
            self.standard_count_22 = np.array(Image.open(self.count_2022_path))
        else:
            print('The standard 2022 count file was not found.')
            self.standard_count_22 = None
        if os.path.exists(self.count_2025_path):
            self.standard_count_25 = np.array(Image.open(self.count_2025_path))
        else:
            print('The standard 2025 count file was not found.')
            self.standard_count_25 = None
        self.standard_count = None
        self.agri_net = Huayu(norm_path=self.agri_model_dir, model_path=rf'{self.agri_model_dir}/model.pt',
                              config=rf'{self.agri_model_dir}/config.yml', root_path=self.root_path)
        self.abi_net = Huayu(norm_path=self.abi_model_dir, model_path=rf'{self.abi_model_dir}/model.pt',
                             config=rf'{self.abi_model_dir}/config.yml', root_path=self.root_path)
        self.seviri_net = Huayu(norm_path=self.seviri_model_dir, model_path=rf'{self.seviri_model_dir}/model.pt',
                                config=rf'{self.seviri_model_dir}/config.yml', root_path=self.root_path)
        print(f"Models loaded in {st.reset()} seconds.")

    # ignore_cache_exist: overwrite the existing cache; otherwise update it incrementally.
    def predict(self, current_date, ignore_cache_exist=False, exclude_idxs=[]):
        if current_date < datetime(2024, 1, 31):
            self.standard_count = self.standard_count_22
        else:
            self.standard_count = self.standard_count_25
        st = Stopwatch()
        st_all = Stopwatch()
        goesW_dir = self.goesW_file_dir
        goesE_dir = self.goesE_file_dir
        cache_name = current_date.strftime('cache_%Y%m%d_%H%M.pkl')
        if (self.cache_path is not None and os.path.exists(
                os.path.join(self.cache_path, cache_name))) or ignore_cache_exist:
            with open(os.path.join(self.cache_path, cache_name), "rb") as f:
                lefts, nps = pickle.load(f)
        else:
            nps = dict()
            lefts = dict()
        fy_lock = ThreadingLock()
        goes_lock = ThreadingLock()
        metsat_lock = ThreadingLock()
        # lock = None
        mt = MultiTasks(3, desc="Data Loading")
        for delta_time in range(0, 30, 15):
            select_date = current_date + timedelta(minutes=delta_time)
            fy_path = get_agri_file_path(self.fy4b_file_dir, select_date)
            metsat_path = get_seviri_file_path(self.msg0_file_dir, select_date)
            metsat_IODC_path = get_seviri_file_path(self.msgIODC_file_dir, select_date)
            fy_key = rf'fy+{delta_time}'
            if fy_path is not None and fy_key not in nps:
                print(rf'add {fy_key} in data reading')
                mt.add_task(rf'fy+{delta_time}', getNPfromHDF, [fy_path, 'FDI', fy_lock, None, True, False])
            ms_key = rf'ms+{delta_time}'
            if metsat_path is not None and ms_key not in nps:
                print(rf'add {ms_key} in data reading')
                mt.add_task(ms_key, getNPfromNAT, [metsat_path, False, metsat_lock, True, False])
            ms_IODC_key = rf'ms_IODC+{delta_time}'
            if metsat_IODC_path is not None and ms_IODC_key not in nps:
                print(rf'add {ms_IODC_key} in data reading')
                mt.add_task(ms_IODC_key, getNPfromNAT, [metsat_IODC_path, False, metsat_lock, True, False])
        for delta_time in range(0, 30, 10):
            select_date = current_date + timedelta(minutes=delta_time)
            goesE_key = rf'goesE+{delta_time}'
            if goesE_key not in nps:
                print(rf'add {goesE_key} in data reading')
                mt.add_task(goesE_key, getNPfromDir,
                            [goesE_dir, select_date, 'G19' if select_date >= datetime(2025, 4, 2) else 'G16', goes_lock,
                             True, None, None])
            goesW_key = rf'goesW+{delta_time}'
            if goesW_key not in nps:
                print(rf'add {goesW_key} in data reading')
                mt.add_task(goesW_key, getNPfromDir,
                            [goesW_dir, select_date, 'G18', goes_lock, True, None, None])
        results = mt.execute_task()
        select_dict = dict()
        for key, result in results.items():
            if type(result) == tuple and result[0] is not None:
                select_dict[key] = results[key]
        results = select_dict
        for k, result in results.items():
            np_data = result[0]
            nps[k] = np_data
            lefts[k] = result[1].left
        if self.cache_path is not None and len(results) > 0:
            os.makedirs(self.cache_path, exist_ok=True)
            with open(os.path.join(self.cache_path, cache_name), "wb") as f:
                pickle.dump((lefts, nps), f)
            print(f"Cached data at {os.path.join(self.cache_path, cache_name)}", end='\t')
        print(f"Data loading completed in {st.reset()} seconds.")
        Huayu_out = np.zeros((2400, 7200))
        count = np.zeros((2400, 7200))
        total_task = 3 * 3 * len(nps)
        pbar = tqdm(total=total_task, desc="Processing")
        for i in range(0, 2400, 800):
            for j in range(0, 2400, 800):
                batch_add = {}
                # Apply final invalid-value and missing-value handling before inference.
                for k, each in nps.items():
                    # Exclude selected scan keys manually for Huayu's 30-minute output interval.
                    if k in exclude_idxs:
                        hy_each = None
                    else:
                        if 'fy' in k:
                            hy_each = self.agri_net.predict(np_data=each[2:, i: i + 800, j: j + 800])
                        elif 'goes' in k:
                            each_patch = each[:, i: i + 800, j: j + 800]
                            # Reject a GOES patch when it contains invalid values.
                            if np.max(each_patch) >= 4095:
                                print(rf"{k} GOES data contain an invalid value ({np.max(each_patch)}); "
                                      rf"the patch cannot be processed.")
                                hy_each = None
                            else:
                                each_patch = fill_nan_with_window_mean_fast(each_patch, window_size=(3, 3))
                                hy_each = self.abi_net.predict(np_data=each_patch)
                        elif 'ms' in k:
                            each_patch = each[:, i: i + 800, j: j + 800]
                            # Fill NaN values in an individual patch with a local window mean.
                            nan_percent = round(
                                np.isnan(each_patch).sum() / (
                                        each_patch.shape[0] * each_patch.shape[1] * each_patch.shape[2]) * 100, 2)
                            if nan_percent > 2:
                                print(rf"{k} contains too much missing data and cannot be processed: "
                                      rf"nan_percent={nan_percent}%")
                                hy_each = None
                            else:
                                each_patch = fill_nan_with_window_mean_fast(each_patch, window_size=(9, 9))
                                if np.isnan(each_patch).sum() > 0:
                                    print(rf"{k} contains missing values that could not be filled; "
                                          rf"the patch cannot be processed.")
                                    hy_each = None
                                else:
                                    hy_each = self.seviri_net.predict(np_data=each_patch)
                        else:
                            raise Exception(f"Unknown data source {k}; the input cannot be processed.")
                    batch_add[k] = hy_each
                    pbar.update(1)
                for k, hy in batch_add.items():
                    if hy is not None:
                        jds = [[int((lefts[k] + 180) / 0.05) + j, int((lefts[k] + 180) / 0.05) + j + 800]]
                        hys = [[0, 800]]
                        if jds[0][0] < 0:
                            jds = [[jds[0][0] + 7200, 7200], [0, jds[0][1]]]
                            hys = [[0, jds[0][1] - jds[0][0]], [jds[0][1] - jds[0][0], 800]]
                        elif jds[0][1] > 7200:
                            jds = [[jds[0][0], 7200], [0, jds[0][1] - 7200]]
                            hys = [[0, jds[0][1] - jds[0][0]], [jds[0][1] - jds[0][0], 800]]
                        for hy_dx, jdx in enumerate(jds):
                            Huayu_out[i:i + 800, jdx[0]:jdx[1]] += hy[0, :, hys[hy_dx][0]:hys[hy_dx][1]]
                            count[i:i + 800, jdx[0]:jdx[1]] += 1
        pbar.close()
        print(f"Inference completed in {st.reset()} seconds.")
        Huayu_out[count > 0] = Huayu_out[count > 0] / count[count > 0]
        Huayu_out = uniform_filter(Huayu_out, size=5, mode='nearest')
        # Huayu[count > 1] = Huayu_smooth[count > 1]
        Huayu_out[Huayu_out < 0.1] = 0
        print(f"Total runtime: {st_all.reset()} seconds.")
        return Huayu_out, count


if __name__ == '__main__':
    current_date = datetime(year=2025, month=1, day=2, hour=0, minute=0)
    root_path = rf'./results/{current_date.strftime("%Y-%m-%d-%H%M")}-{random.randint(1000, 9999)}'
    huayu = Huayu_Global(model_dir=rf'./assests', root_path=root_path,
                         fy4b_file_dir=rf'./data/fy/4b', cache_path=rf'./cache',
                         goesE_file_dir=rf'./data/goes/' + ('16' if current_date < datetime(2025, 4, 2) else '19'),
                         goesW_file_dir=rf'./data/goes/18', msg0_file_dir=rf'./data/metsat/0',
                         msgIODC_file_dir=rf'./data/metsat/IODC', count_2022_path=rf'./assests/count_2022.tif',
                         count_2025_path=rf'./assests/count_2025.tif')
    Huayu_out, count = huayu.predict(current_date)
    if count is not None:
        np2tif(count, save_path=root_path, out_name=rf'count_{current_date.strftime("%Y%m%d_%H%M")}',
               coord=Coordinate(left=-180, top=60, x_res=0.05, y_res=0.05, right=180, bottom=-60),
               dtype=np.float32, print_log=False)
    if count is None or Huayu_out is None:
        raise Exception("No output was generated. Check the input data.")
    if huayu.standard_count is None or np.sum(count[huayu.standard_count > 0] == 0) > 0:
        raise Exception("Some regions have no data coverage. The GeoTIFF cannot be saved; "
                        "inspect the count file for coverage details.")
    if Huayu_out is not None:
        np2tif(Huayu_out, save_path=root_path, out_name=rf'Huayu_{current_date.strftime("%Y%m%d_%H%M")}',
               coord=Coordinate(left=-180, top=60, x_res=0.05, y_res=0.05, right=180, bottom=-60),
               dtype=np.float32, print_log=False)
