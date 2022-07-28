import xarray as xr
from bokeh.models import ColumnDataSource
import numpy as np
import cmcrameri.cm as cm
import matplotlib


def download_dataset(index, area):
    sie_dict = {"NH": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/nh/osisaf_nh_sie_daily.nc",
                "SH": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/sh/osisaf_sh_sie_daily.nc"}
    sia_dict = {"NH": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/nh/osisaf_nh_sia_daily.nc",
                "SH": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/sh/osisaf_sh_sia_daily.nc"}
    url_dict = {"sie": sie_dict, "sia": sia_dict}

    return xr.open_dataset(url_dict[index][area])


def extract_data(ds, index):
    da = ds[index]
    title = ds.title
    long_name = da.attrs["long_name"]
    units = da.attrs["units"]

    return {"da": da, "title": title, "long_name": long_name, "units": units}


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
    percentile_10 = da.groupby("time.dayofyear").quantile(0.10).values
    percentile_90 = da.groupby("time.dayofyear").quantile(0.90).values
    percentile_25 = da.groupby("time.dayofyear").quantile(0.25).values
    percentile_75 = da.groupby("time.dayofyear").quantile(0.75).values
    median_array = da.groupby("time.dayofyear").median()
    day_of_year = median_array.dayofyear.values
    median = median_array.values

    cds_percentile_1090 = ColumnDataSource({"day_of_year": day_of_year,
                                            "percentile_10": percentile_10,
                                            "percentile_90": percentile_90})
    cds_percentile_2575 = ColumnDataSource({"day_of_year": day_of_year,
                                            "percentile_25": percentile_25,
                                            "percentile_75": percentile_75})
    cds_median = ColumnDataSource({"day_of_year": day_of_year, "median": median})

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


def calculate_individual_years(da):
    da_converted = da.convert_calendar("all_leap")
    years = get_list_of_years(da_converted)

    cds_dict = {year: None for year in years}
    for year in years:
        one_year_data = da_converted.sel(time=year)
        date = one_year_data.time.dt.strftime("%Y-%m-%d").values
        day_of_year = one_year_data.time.dt.dayofyear.values
        index_values = one_year_data.values
        cds_dict[year] = ColumnDataSource({"date": date, "day_of_year": day_of_year, "index_values": index_values})

    return cds_dict


def find_nice_ylimit(da):
    """Find a nice y-limit that's divisible by two."""
    return int(2 * round(da.max().values / 2) + 2)


def decade_colour_dict(decade, colour):
    normalisation = np.linspace(0, 0.5, 10)
    normalised_colour = [matplotlib.colors.to_hex(colour) for colour in colour(normalisation)]
    years_in_decade = np.arange(decade, decade + 10, 1).astype(str)

    return {year: year_colour for year, year_colour in zip(years_in_decade, normalised_colour)}


def find_line_colours(years, colour):
    """Find a colors for the individual years."""

    if colour == "decadal":
        decades = [1970, 1980, 1990, 2000, 2010, 2020]
        colours = [matplotlib.cm.Purples_r,
                   matplotlib.cm.Purples_r,
                   matplotlib.cm.Blues_r,
                   matplotlib.cm.Greens_r,
                   matplotlib.cm.Reds_r,
                   matplotlib.cm.Wistia_r]

        full_colour_dict = {}

        for decade, colour in zip(decades, colours):
            decade_dict = decade_colour_dict(decade, colour)
            full_colour_dict.update(decade_dict)

        colour_dict = {year: full_colour_dict[year] for year in years}
        # Set the color of the current year to black.
        colour_dict[list(years)[-1]] = "#000000"

    else:
        translation_dictionary = {"viridis": matplotlib.cm.viridis,
                                  "plasma": matplotlib.cm.plasma,
                                  "batlow": cm.batlow,
                                  "batlowS": cm.batlowS}

        normalised = np.linspace(0, 1, len(years))
        colours = translation_dictionary[colour](normalised)
        colours_in_hex = [matplotlib.colors.to_hex(colour) for colour in colours]
        colour_dict = {year: colour for year, colour in zip(years, colours_in_hex)}

    return colour_dict
