import xarray as xr
from bokeh.models import ColumnDataSource
import numpy as np
import cmcrameri.cm as cm
import matplotlib
import itertools


def download_and_extract_data(version, index, area):
    url_prefix = "https://thredds.met.no/thredds/dodsC"

    sie_dict_v2 = {"NH": f"{url_prefix}/osisaf/met.no/ice/index/v2p1/nh/osisaf_nh_sie_daily.nc",
                   "bar": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/bar/osisaf_bar_sie_daily.nc",
                   "beau": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/beau/osisaf_beau_sie_daily.nc",
                   "chuk": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/chuk/osisaf_chuk_sie_daily.nc",
                   "ess": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/ess/osisaf_ess_sie_daily.nc",
                   "fram": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/fram/osisaf_fram_sie_daily.nc",
                   "kara": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/kara/osisaf_kara_sie_daily.nc",
                   "lap": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/lap/osisaf_lap_sie_daily.nc",
                   "sval": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/sval/osisaf_sval_sie_daily.nc",
                   "SH": f"{url_prefix}/osisaf/met.no/ice/index/v2p1/sh/osisaf_sh_sie_daily.nc",
                   "bell": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/bell/osisaf_bell_sie_daily.nc",
                   "indi": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/indi/osisaf_indi_sie_daily.nc",
                   "ross": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/ross/osisaf_ross_sie_daily.nc",
                   "wedd": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/wedd/osisaf_wedd_sie_daily.nc",
                   "wpac": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/wpac/osisaf_wpac_sie_daily.nc",
                   "GLOBAL": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/glb/osisaf_glb_sie_daily.nc"}

    sie_dict_v3 = {"NH": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/nh/osisaf_nh_sie_daily.nc",
                   "bar": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/bar/osisaf_bar_sie_daily.nc",
                   "beau": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/beau/osisaf_beau_sie_daily.nc",
                   "chuk": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/chuk/osisaf_chuk_sie_daily.nc",
                   "ess": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/ess/osisaf_ess_sie_daily.nc",
                   "fram": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/fram/osisaf_fram_sie_daily.nc",
                   "kara": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/kara/osisaf_kara_sie_daily.nc",
                   "lap": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/lap/osisaf_lap_sie_daily.nc",
                   "sval": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/sval/osisaf_sval_sie_daily.nc",
                   "SH": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/sh/osisaf_sh_sie_daily.nc",
                   "bell": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/bell/osisaf_bell_sie_daily.nc",
                   "indi": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/indi/osisaf_indi_sie_daily.nc",
                   "ross": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/ross/osisaf_ross_sie_daily.nc",
                   "wedd": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/wedd/osisaf_wedd_sie_daily.nc",
                   "wpac": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/wpac/osisaf_wpac_sie_daily.nc",
                   "GLOBAL": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/glb/osisaf_glb_sie_daily.nc"}

    sia_dict_v2 = {"NH": f"{url_prefix}/osisaf/met.no/ice/index/v2p1/nh/osisaf_nh_sia_daily.nc",
                "bar": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/bar/osisaf_bar_sia_daily.nc",
                "beau": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/beau/osisaf_beau_sia_daily.nc",
                "chuk": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/chuk/osisaf_chuk_sia_daily.nc",
                "ess": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/ess/osisaf_ess_sia_daily.nc",
                "fram": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/fram/osisaf_fram_sia_daily.nc",
                "kara": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/kara/osisaf_kara_sia_daily.nc",
                "lap": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/lap/osisaf_lap_sia_daily.nc",
                "sval": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/sval/osisaf_sval_sia_daily.nc",
                "SH": f"{url_prefix}/osisaf/met.no/ice/index/v2p1/sh/osisaf_sh_sia_daily.nc",
                "bell": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/bell/osisaf_bell_sia_daily.nc",
                "indi": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/indi/osisaf_indi_sia_daily.nc",
                "ross": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/ross/osisaf_ross_sia_daily.nc",
                "wedd": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/wedd/osisaf_wedd_sia_daily.nc",
                "wpac": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/wpac/osisaf_wpac_sia_daily.nc",
                "GLOBAL": f"{url_prefix}/metusers/thomasl/OSI420_moreRegions/glb/osisaf_glb_sia_daily.nc"}

    sia_dict_v3 = {"NH": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/nh/osisaf_nh_sia_daily.nc",
                   "bar": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/bar/osisaf_bar_sia_daily.nc",
                   "beau": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/beau/osisaf_beau_sia_daily.nc",
                   "chuk": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/chuk/osisaf_chuk_sia_daily.nc",
                   "ess": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/ess/osisaf_ess_sia_daily.nc",
                   "fram": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/fram/osisaf_fram_sia_daily.nc",
                   "kara": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/kara/osisaf_kara_sia_daily.nc",
                   "lap": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/lap/osisaf_lap_sia_daily.nc",
                   "sval": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/sval/osisaf_sval_sia_daily.nc",
                   "SH": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/sh/osisaf_sh_sia_daily.nc",
                   "bell": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/bell/osisaf_bell_sia_daily.nc",
                   "indi": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/indi/osisaf_indi_sia_daily.nc",
                   "ross": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/ross/osisaf_ross_sia_daily.nc",
                   "wedd": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/wedd/osisaf_wedd_sia_daily.nc",
                   "wpac": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/wpac/osisaf_wpac_sia_daily.nc",
                   "GLOBAL": f"{url_prefix}/metusers/thomasl/OSI420_BetaFromSICv3/glb/osisaf_glb_sia_daily.nc"}

    version_2 = {"sie": sie_dict_v2, "sia": sia_dict_v2}
    version_3 = {"sie": sie_dict_v3, "sia": sia_dict_v3}
    version_dict = {"v2p1": version_2, "v3p0test": version_3}

    ds = xr.open_dataset(version_dict[version][index][area], cache=False)

    da = ds[index]
    title = ds.title
    ds_version = ds.version
    long_name = da.attrs["long_name"]
    units = da.attrs["units"]

    return {"da": da, "title": title, "ds_version": ds_version, "long_name": long_name, "units": units}


def get_list_of_years(da):
    return np.unique(da.time.dt.year.values).astype(str)


def convert_and_interpolate_calendar(da):
    # Convert the calendar to leap years for all years in the data, and fill the missing day with -999 as value.
    da = da.convert_calendar("all_leap", missing=-999)

    # Replace the -999 values with interpolated values between the preceding and succeeding day.
    for i, val in enumerate(da.values):
        if val == -999:
            da.values[i] = (da.values[i-1] + da.values[i+1]) / 2

    return da


def calculate_percentiles_and_median(da):
    percentile_10 = da.groupby("time.dayofyear").quantile(0.10)
    percentile_90 = da.groupby("time.dayofyear").quantile(0.90)
    cds_percentile_1090 = ColumnDataSource({"day_of_year": percentile_10.dayofyear.values,
                                            "percentile_10": percentile_10.values,
                                            "percentile_90": percentile_90.values})

    percentile_25 = da.groupby("time.dayofyear").quantile(0.25)
    percentile_75 = da.groupby("time.dayofyear").quantile(0.75)
    cds_percentile_2575 = ColumnDataSource({"day_of_year": percentile_25.dayofyear.values,
                                            "percentile_25": percentile_25.values,
                                            "percentile_75": percentile_75.values})

    median_array = da.groupby("time.dayofyear").median()
    day_of_year = median_array.dayofyear.values
    cds_median = ColumnDataSource({"day_of_year": day_of_year, "median": median_array.values})

    return {"cds_percentile_1090": cds_percentile_1090,
            "cds_percentile_2575": cds_percentile_2575,
            "cds_median": cds_median}


def calculate_min_max(da):
    # Min/max values are calculated based on the data in the entire period except for the current year.
    years_list = get_list_of_years(da)
    sliced_da = da.sel(time=slice(years_list[0], years_list[-2]))

    minimum = sliced_da.groupby("time.dayofyear").min().values
    maximum_array = sliced_da.groupby("time.dayofyear").max()
    day_of_year = maximum_array.dayofyear.values
    maximum = maximum_array.values

    cds_minimum = ColumnDataSource({"day_of_year": day_of_year, "minimum": minimum})
    cds_maximum = ColumnDataSource({"day_of_year": day_of_year, "maximum": maximum})

    return {"cds_minimum": cds_minimum, "cds_maximum": cds_maximum}


def calculate_span_and_median(da):
    minimum = da.groupby("time.dayofyear").min()
    maximum = da.groupby("time.dayofyear").max()
    cds_span = ColumnDataSource({"day_of_year": minimum.dayofyear.values,
                                 "minimum": minimum.values,
                                 "maximum": maximum.values})

    median_array = da.groupby("time.dayofyear").median()
    day_of_year = median_array.dayofyear.values
    cds_median = ColumnDataSource({"day_of_year": day_of_year, "median": median_array.values})

    return {"cds_span": cds_span, "cds_median": cds_median}


def calculate_individual_years(da, da_interpolated):
    da_converted = da.convert_calendar("all_leap")
    years = get_list_of_years(da_converted)

    # Calculate the rank of the index value for each day.
    rank = da_interpolated.groupby("time.dayofyear").map(lambda x: x.rank("time"))

    cds_dict = {year: None for year in years}
    for year in years:
        one_year_data = da_converted.sel(time=year)
        date = one_year_data.time.dt.strftime("%Y-%m-%d").values
        day_of_year = one_year_data.time.dt.dayofyear.values
        index_values = one_year_data.values
        rank_values = rank.sel(time=one_year_data.time.values).values
        cds_dict[year] = ColumnDataSource({"day_of_year": day_of_year,
                                           "index_values": index_values,
                                           "date": date,
                                           "rank": rank_values})

    return cds_dict


def find_yearly_min_max(da_converted, fill_colors_dict):
    # Find the years we have data for, except the current one. Select the data from those years and group it by year.
    years = get_list_of_years(da_converted)[:-1]
    da_sliced_and_grouped = da_converted.sel(time=slice(years[0], years[-1])).groupby("time.year")

    # Find the yearly max/min date, day of year, and index value.
    yearly_max_date = da_sliced_and_grouped.apply(lambda x: x.idxmax(dim="time"))
    yearly_max_doy = da_converted.sel(time=yearly_max_date).time.dt.dayofyear
    yearly_max_index_value = da_converted.sel(time=yearly_max_date)

    yearly_min_date = da_sliced_and_grouped.apply(lambda x: x.idxmin(dim="time"))
    yearly_min_doy = da_converted.sel(time=yearly_min_date).time.dt.dayofyear
    yearly_min_index_value = da_converted.sel(time=yearly_min_date)

    # Use the same colours as the lines of the individual years.
    colors = [fill_colors_dict[year] for year in years]

    # Convert the max/min date to a string for use in hovertool display.
    hovertool_max_date = yearly_max_date.dt.strftime("%Y-%m-%d")
    hovertool_min_date = yearly_min_date.dt.strftime("%Y-%m-%d")

    # Find the rank of the max/min values. Reverse the max rank such that the highest value has a rank of 1.
    yearly_max_rank = (-yearly_max_index_value).rank("year")
    yearly_min_rank = yearly_min_index_value.rank("year")

    cds_yearly_max = ColumnDataSource({"day_of_year": yearly_max_doy.values,
                                       "index_value": yearly_max_index_value.values,
                                       "color": colors,
                                       "date": hovertool_max_date.values,
                                       "rank": yearly_max_rank.values})
    cds_yearly_min = ColumnDataSource({"day_of_year": yearly_min_doy.values,
                                       "index_value": yearly_min_index_value.values,
                                       "color": colors,
                                       "date": hovertool_min_date.values,
                                       "rank": yearly_min_rank.values})

    return cds_yearly_max, cds_yearly_min


def find_nice_ylimit(da):
    """Find an upper y-limit with 10 percent added to the maximum value of the data."""
    return 1.10 * da.max().values


def decade_color_dict(decade, color):
    # Don't use the full breadth of the colormap, only go up till middle (halfway) to avoid the light colors.
    normalisation = np.linspace(0, 0.5, 10)
    normalised_color = [matplotlib.colors.to_hex(color) for color in color(normalisation)]
    years_in_decade = np.arange(decade, decade + 10, 1).astype(str)

    return {year: year_color for year, year_color in zip(years_in_decade, normalised_color)}


def find_line_colors(years, color):
    """Find a colors for the individual years."""

    if color == "decadal":
        decades = [1970, 1980, 1990, 2000, 2010, 2020]
        colors = [matplotlib.cm.Purples_r,
                   matplotlib.cm.Purples_r,
                   matplotlib.cm.Blues_r,
                   matplotlib.cm.Greens_r,
                   matplotlib.cm.Reds_r,
                   matplotlib.cm.Wistia_r]

        full_color_dict = {}

        for decade, color in zip(decades, colors):
            decade_dict = decade_color_dict(decade, color)
            full_color_dict.update(decade_dict)

        color_dict = {year: full_color_dict[year] for year in years}

    elif color == "cyclic_8":
        colors = ["#ffe119", "#4363d8", "#f58231", "#dcbeff", "#800000", "#000075", "#a9a9a9", "#000000"]

        cyclic_colors = itertools.cycle(colors)
        color_dict = {year: next(cyclic_colors) for year in years}

    elif color == "cyclic_17":
        colors = ["#e6194B",
                  "#3cb44b",
                  "#ffe119",
                  "#4363d8",
                  "#f58231",
                  "#42d4f4",
                  "#f032e6",
                  "#fabed4",
                  "#469990",
                  "#dcbeff",
                  "#9A6324",
                  "#fffac8",
                  "#800000",
                  "#aaffc3",
                  "#000075",
                  "#a9a9a9",
                  "#000000"]

        cyclic_colors = itertools.cycle(colors)
        color_dict = {year: next(cyclic_colors) for year in years}

    else:
        translation_dictionary = {"viridis": matplotlib.cm.viridis,
                                  "plasma": matplotlib.cm.plasma,
                                  "batlow": cm.batlow,
                                  "batlowS": cm.batlowS}

        normalised = np.linspace(0, 1, len(years))
        colors = translation_dictionary[color](normalised)
        colors_in_hex = [matplotlib.colors.to_hex(color) for color in colors]
        color_dict = {year: color for year, color in zip(years, colors_in_hex)}

    return color_dict
