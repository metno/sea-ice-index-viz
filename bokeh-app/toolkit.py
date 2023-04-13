import xarray as xr
from bokeh.models import ColumnDataSource
import numpy as np
import cmcrameri.cm as cm
import matplotlib
import itertools
import calendar
import requests


def download_and_extract_data(index, area, frequency, version):
    url_prefix = "https://thredds.met.no/thredds/dodsC/metusers/thomasl"
    version_dict = {"v2p1": "OSI420_moreRegions", "v3p0test": "OSI420_BetaFromSICv3"}

    url = f"{url_prefix}/{version_dict[version]}/{area}/osisaf_{area}_{index}_{frequency}.nc"

    # On 2023-04-12 an issue was experienced with the thredds server where it hung and did not properly serve the
    # data files it was supposed to serve. xarray's open_dataset function and the backend do not provide an easy way
    # to set a timeout interval, so to work around this we use the requests library.
    try:
        r = requests.head(f"{url}.html")
        r.raise_for_status()
    except requests.exceptions.RequestException:
        # Raise an OSError since this is the same error we check for in our try-except statement in the main scripts.
        raise OSError

    # Open the dataset with cache set to false, otherwise the plots will keep showing old data when updated data is
    # available.
    ds = xr.open_dataset(url, cache=False)

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


def calculate_monthly(da, month):
    # Select the subset of the data that contains the given month.
    subset = da.sel(time=da.time.dt.month.isin(month))

    # Create an array with date strings of the format "month year".
    date = np.char.add([calendar.month_name[month] + " "], subset.time.dt.year.astype(str))

    # Calculate the ranks of the index values. The lowest value has a rank of 1.
    rank = subset.rank("time").values

    cds_month = ColumnDataSource({"year": subset.time.dt.year.values,
                                  "index_values": subset.values,
                                  "date": date,
                                  "rank": rank})

    return cds_month


def monthly_trend(da, month, reference_period):
    # Select the subset of the data for the given month, and drop any values that are nans.
    subset = da.sel(time=da.time.dt.month.isin(month)).dropna("time")

    # Set the x-values to the years.
    x = subset.time.dt.year.values

    # In order to calculate a linear regression with numpy we need to add a column of ones to the right of the x-values.
    A = np.vstack([x, np.ones(len(x))]).T

    # Set the y-values to the index values.
    y = subset.values

    # m is the coefficient, and c is the constant.
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]

    # Calculate index values for the start and end of the trend line.
    first_year = (m * x[0]) + c
    last_year = (m * x[-1]) + c

    # Create a CDS for the trend line.
    cds_trend = ColumnDataSource({"year": [x[0], x[-1]], "start_end_line": [first_year, last_year]})

    # Get the absolute trend in thousands of square kilometers per year.
    absolute_trend = m * 1000

    # Create a new subset only containing the years of the reference period, and drop nan values.
    start_year = reference_period[0:4]
    end_year = reference_period[5:9]
    reference_period_subset = subset.sel(time=slice(start_year, end_year)).dropna("time")

    reference_period_index_mean = reference_period_subset.mean().values
    relative_means = 100 * (subset.values - reference_period_index_mean) / reference_period_index_mean

    # Again, m is the coefficient, and c is the constant.
    m, c = np.linalg.lstsq(A, relative_means, rcond=None)[0]

    # Get the relative trend coefficient and convert it to per decade.
    relative_trend = 10 * m

    return cds_trend, absolute_trend, relative_trend


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


def find_nice_yrange(monthly_data, trend_data, padding_mult, min_span):
    """Function to find a nice y-range that is not too narrow."""
    all_monthly_data = np.concatenate((monthly_data, trend_data))
    monthly_min = np.nanmin(all_monthly_data)
    monthly_max = np.nanmax(all_monthly_data)
    monthly_span = monthly_max - monthly_min

    if monthly_span < min_span:
        # Some months have an index value that hardly changes from year to year. By using Bokeh's autoscaling function
        # when new data gets loaded the trend line ends up being plotted incorrectly relatively to the monthly data
        # due to round-off errors. We avoid this by using a minimum span width.
        padding = min_span - monthly_span
        monthly_min -= padding / 2
        monthly_max += padding / 2
    else:
        padding = padding_mult * monthly_span
        monthly_min -= padding / 2
        monthly_max += padding / 2

    return monthly_min, monthly_max


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
