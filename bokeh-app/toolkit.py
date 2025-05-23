import xarray as xr
from bokeh.models import ColumnDataSource
import numpy as np
import cmcrameri.cm as cm
import matplotlib
import itertools
import calendar


def download_and_extract_data(index, area, frequency, version):
    url_prefix = "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index"

    url = f"{url_prefix}/{version}/{area}/osisaf_{area}_{index}_{frequency}.nc"

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


def calculate_monthly(da, month_offset=True):
    # Find which months are in the data.
    months = np.unique(da.time.dt.month)

    # Create a dictionary to store the ColumnDataSource of each month.
    cds_monthly_dict = {}

    for month in months:
        # Select the subset of the data that contains the given month.
        subset = da.sel(time=da.time.dt.month.isin(month))

        # Calculate the ranks of the index values. The lowest value has a rank of 1.
        rank = subset.rank("time").values

        if month_offset:
            x = subset.time.dt.year.values + ((subset.time.dt.month.values - 1) / 12)
        else:
            x = subset.time.dt.year.values

        cds_month = ColumnDataSource({"x": x,
                                      "index_values": subset.values,
                                      "year": subset.time.dt.year.values.astype(str),
                                      "month": np.full(len(subset), calendar.month_name[month]),
                                      "rank": rank})

        cds_monthly_dict.update({calendar.month_name[month]: cds_month})

    return cds_monthly_dict


def calculate_all_months(da):
    # Create a ColumnDataSource for plotting the line with all months in the monthly plot.

    x_values_all_months = da.time.dt.year.values + ((da.time.dt.month.values - 1) / 12)
    index_values = da.values

    return ColumnDataSource({"x": x_values_all_months, "index_values": index_values})


class Trends:
    def __init__(self, da, reference_period_start, reference_period_end, month_offset):
        self.da = da.dropna("time")
        self.reference_period_start = str(reference_period_start)
        self.reference_period_end = str(reference_period_end)
        self.month_offset = month_offset

        self.months = np.unique(da.time.dt.month)

        # Include all complete decades.
        decade_indices = np.argwhere(self.da.time.dt.year.values % 10 == 0).flatten()
        decade_start_years = np.unique(self.da.time.dt.year.values[decade_indices])
        self.decades = [(str(start_year), str(start_year + 9)) for start_year in decade_start_years[:-1]]

    def _find_regression_coefficients(self, da):
        if self.month_offset:
            year = da.time.dt.year.values + ((da.time.dt.month.values - 1) / 12)
        else:
            year = da.time.dt.year.values

        # In order to calculate a linear regression with numpy we need to add a column of ones to the right of the
        # x-values.
        year_stacked = np.vstack([year, np.ones(len(year))]).T

        index_values = da.values

        slope, constant = np.linalg.lstsq(year_stacked, index_values, rcond=None)[0]

        return slope, constant

    def _find_trends(self, da, da_reference, edge_padding=None):
        if self.month_offset:
            year = da.time.dt.year.values + ((da.time.dt.month.values - 1) / 12)
        else:
            year = da.time.dt.year.values

        if edge_padding:
            year = year.astype(float)
            year[0] = year[0] + edge_padding
            year[-1] = year[-1] + (1 - edge_padding)

        slope, constant = self._find_regression_coefficients(da)
        trend_line_values = slope * year + constant

        absolute_trend = 1000 * slope

        reference_period_index_mean = da_reference.mean().values
        relative_means = 100 * (da.values - reference_period_index_mean) / reference_period_index_mean
        da.values = relative_means

        relative_slope, _ = self._find_regression_coefficients(da)
        relative_trend = 10 * relative_slope

        return year, trend_line_values, absolute_trend, relative_trend

    def calculate_monthly_trend(self):
        da = self.da

        monthly_trends = {}
        for month in self.months:
            subset = da.sel(time=da.time.dt.month.isin(month))
            reference_subset = subset.sel(time=slice(self.reference_period_start, self.reference_period_end))

            year, trend_line_values, absolute_trend, relative_trend = self._find_trends(subset, reference_subset)
            reference_period = f"{self.reference_period_start}-{self.reference_period_end}"

            cds_trend = ColumnDataSource({"year": year,
                                          "trend_line_values": trend_line_values,
                                          "month": np.full(year.size, calendar.month_name[month]),
                                          "absolute_trend": np.full(year.size, absolute_trend),
                                          "relative_trend": np.full(year.size, relative_trend),
                                          "reference_period": np.full(year.size, reference_period)})

            monthly_trends.update({calendar.month_name[month]: cds_trend})

        return monthly_trends

    def calculate_decadal_trend(self, edge_padding):
        da = self.da

        monthly_trends = {}
        for month in self.months:
            month_subset = da.sel(time=da.time.dt.month.isin(month))
            reference_subset = month_subset.sel(time=slice(self.reference_period_start, self.reference_period_end))

            decadal_trends = {}
            for decade_start, decade_end in self.decades:
                decade_subset = month_subset.sel(time=slice(decade_start, decade_end))

                year, trend_line_values, absolute_trend, relative_trend = self._find_trends(decade_subset,
                                                                                            reference_subset,
                                                                                            edge_padding)
                reference_period = f"{self.reference_period_start}-{self.reference_period_end}"
                decade = f"{decade_start}-{decade_end}"

                cds_trend = ColumnDataSource({"year": year,
                                              "trend_line_values": trend_line_values,
                                              "month": np.full(year.size, calendar.month_name[month]),
                                              "decade": np.full(year.size, decade),
                                              "absolute_trend": np.full(year.size, absolute_trend),
                                              "relative_trend": np.full(year.size, relative_trend),
                                              "reference_period": np.full(year.size, reference_period)})

                decadal_trends.update({decade: cds_trend})
            monthly_trends.update({calendar.month_name[month]: decadal_trends})

        return monthly_trends


def find_yearly_min_max(da_converted, da_converted_anomaly, fill_colors_dict):
    # Find the years we have data for, except the current one. Select the data from those years and group it by year.
    years = get_list_of_years(da_converted)[:-1].tolist()

    # Remove 1978 because the data does not cover the entire year.
    try:
        years.remove("1978")
    except ValueError:
        pass

    da_sliced_and_grouped = da_converted.sel(time=slice(years[0], years[-1])).groupby("time.year")

    # Find the yearly max/min date, day of year, and index value.
    yearly_max_date = da_sliced_and_grouped.apply(lambda x: x.idxmax(dim="time"))
    yearly_max_doy = da_converted.sel(time=yearly_max_date).time.dt.dayofyear

    yearly_min_date = da_sliced_and_grouped.apply(lambda x: x.idxmin(dim="time"))
    yearly_min_doy = da_converted.sel(time=yearly_min_date).time.dt.dayofyear

    yearly_max_index_value = da_converted_anomaly.sel(time=yearly_max_date)
    yearly_min_index_value = da_converted_anomaly.sel(time=yearly_min_date)

    # Use the same colours as the lines of the individual years.
    colors = [fill_colors_dict[year] for year in years]

    # Convert the max/min date to a string for use in hovertool display.
    hovertool_max_date = yearly_max_date.dt.strftime("%Y-%m-%d")
    hovertool_min_date = yearly_min_date.dt.strftime("%Y-%m-%d")

    # Find the rank of the max/min values. The ranks are such that the lowest value for both min and max has a rank
    # of 1.
    yearly_max_rank = yearly_max_index_value.rank("year")
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
                                  "viridis_r": matplotlib.cm.viridis_r,
                                  "plasma": matplotlib.cm.plasma,
                                  "plasma_r": matplotlib.cm.plasma_r,
                                  "batlow": cm.batlow,
                                  "batlow_r": cm.batlow_r,
                                  "batlowS": cm.batlowS}

        normalised = np.linspace(0, 1, len(years))
        colors = translation_dictionary[color](normalised)
        colors_in_hex = [matplotlib.colors.to_hex(color) for color in colors]
        color_dict = {year: color for year, color in zip(years, colors_in_hex)}

    return color_dict


def trim_title(title, plot_type):
    new_title = title.replace("(v2p1)", "v2.1").replace("(v2p2)", "v2.2")
    new_title = new_title.replace("Mean ", "")
    new_title = new_title.replace(" from EUMETSAT OSI SAF", "")

    if new_title.count("Sea ") > 1:
        # In case there is more than one Sea substring in the title remove one to deduplicate.
        new_title = new_title.replace("Sea ", "", 1)

    if plot_type == 'anomaly':
        new_title = new_title.replace('Ice Area', 'Ice Area Anomaly')
        new_title = new_title.replace('Ice Extent', 'Ice Extent Anomaly')

    return new_title
