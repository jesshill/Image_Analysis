
import os
from skimage import io
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from rme_parser import *

class KeemPlot:
    '''
    A class to process images into barcodes, store metadata, and update a pandas DataFrame with the processed data.
    
    Attributes:
        metadata: Contains metadata obtained by parsing a README.txt file in the provided path.
        header: Header from the parsed metadata.
        dbdata: Information about the group number from the metadata.
        _max_value: Maximum value for normalization.
        _final_len: Length of the interpolated array.
        _threshold: Threshold value for noise reduction.
        Raw_Arrays: List of raw image arrays.
        flatdata_ni: Processed image data without interpolation.
        flatdata: Interpolated and thresholded image data.
        flatdata_ut: Interpolated but not thresholded image data.
        barcodes: Barcodes generated from processed image data.
        df: DataFrame to store processed data.
    '''
    def __init__(self, path, group_number=1, max_value=65535, threshold=0, final_len=3500):
        '''
        Initializes the KeemPlot class with the given path and optional parameters.
        
        Parameters:
            path: The path where the image files are located.
            group_number: The position that the group is located in within the README. 1 is the first group and so on. Default is 1.
            max_value: The maximum value for normalization. Default is 65535.
            threshold: The threshold for noise reduction. Default is 0.
            final_len: The final length of the interpolated array. Default is 3500.
        '''
        if path[-1] != "/":
            path += "/"
        self.metadata = rme_parser(path + "README.txt")
        self.header = self.metadata.header
        self.dbdata = self.metadata.infos[group_number-1]
        self._max_value = max_value
        self._final_len = final_len
        self._threshold = threshold / max_value
        self.Raw_Arrays = self._gen_raw_arrays(path)
        self.flatdata_ni, self.flatdata, self.flatdata_ut, self.barcodes = self._process(self.Raw_Arrays)

    def _gen_raw_arrays(self, path):
        '''
        Generates raw image arrays from the image files located in the provided path.
        
        Parameters:
            path: The path where the image files are located.
        
        Returns:
            A list of raw image arrays.
        '''
        image_names = [i for i in os.listdir(path) if not i.startswith(".") and not i.endswith(".txt")]
        Raw_Images = []
        for i, name in enumerate(image_names):
            Raw_Images.append(io.imread(path+name)[0,:,:])

        return Raw_Images

    def _interp1d(self, array, new_len):
        '''
        Interpolates a given array to the specified new length.
        
        Parameters:
            array: The array to be interpolated.
            new_len: The new length of the interpolated array.
        
        Returns:
            The interpolated array.
        '''
        la = len(array)
        return np.interp(np.linspace(0, la - 1, num=new_len), np.arange(la), array)

    def create_barcode(self, arr):
        '''
        Creates a barcode from a given array.
        
        Parameters:
            arr: The array from which to create the barcode.
        
        Returns:
            A barcode created from the array.
        '''
        height = len(arr) // 20 if len(arr) >= 20 else 1    # Adjust height scaling so that barcodes don't look dumb
        return np.vstack([arr for k in range(height)])

    def _process(self, Raw_data):
        '''
        Processes raw image data. This includes collapsing 2D images into vectors, normalizing, interpolating, and thresholding.
        
        Parameters:
            Raw_data: The raw image data to process.
        
        Returns:
            A tuple containing lists of processed data in different stages: flatdata_ni, flatdata, flatdata_ut, barcodes.
        '''
        flatdata_ni = []                                        # Flat data no interpolation
        flatdata = []
        flatdata_ut = []
        barcodes = []

        for _, image in enumerate(Raw_data):
            arr = image.max(axis=0)                             # Collapse 2d image into vector based on max value in each column
            arr = arr/self._max_value                           # Normalize to values between 0 and 1.
            flatdata_ni.append(np.copy(arr))                    # Append uninterpolated arrays

            arr_int = self._interp1d(arr, self._final_len)      # Interpolate the vector into 10000 values.

            flatdata_ut.append(np.copy(arr_int))                # Append unthresholded arrays
            arr_int[arr_int < self._threshold] = 0              # Threshold out noise/unwanted dim signal.
            flatdata.append(np.copy(arr_int))
            barcodes.append(self.create_barcode(arr_int))
            
        return flatdata_ni, flatdata, flatdata_ut, barcodes

    def plot_barcodes(self, barcodes, save=None):
        '''
        Plots the given barcodes.
        
        Parameters:
            barcodes: The barcodes to plot.
            save: The path where to save the plot. If None, the plot is not saved.
        '''
        fig, axes = plt.subplots(len(barcodes), 1)

        for i, bar in enumerate(barcodes):
            axes[i].imshow(bar, cmap="Greys_r", vmin = 0, vmax=1.0)
            axes[i].axis("off")

        fig.tight_layout(pad=0)
        
        if save is not None:
            fig.savefig(save, dpi=1200)

    def generate_db(self):
        '''
        Generates a pandas DataFrame to store processed data and metadata.
        '''
        self.df = pd.DataFrame(columns=self.header, data=self.dbdata)
        self.df["array_vals"] = self.flatdata_ut
        self.df["array_vals_ni"] = self.flatdata_ni

    def update_db(self, path):
        '''
        Updates the pandas DataFrame stored in the given path with the DataFrame of this instance.
        
        Parameters:
            path: The path where the DataFrame to update is located.
        '''
        old = pd.read_pickle(path)
        new = pd.concat([old, self.df], axis=0, ignore_index=True, join="outer")
        new = new.drop_duplicates(subset=["ID"], keep="last")
        new.reset_index(drop=True, inplace=True)
        new.to_pickle(path)
