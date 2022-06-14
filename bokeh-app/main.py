import xarray as xr
from bokeh.plotting import figure
from bokeh.models import Panel, Tabs, ColumnDataSource, AdaptiveTicker, Select, MultiChoice, HoverTool
from bokeh.layouts import column, row
from bokeh.io import curdoc
import numpy as np


def download_and_extract(index, area):
    sie_dict = {"North": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/nh/osisaf_nh_sie_daily.nc",
                "South": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/sh/osisaf_sh_sie_daily.nc"}
    sia_dict = {'North': 'https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/nh/osisaf_nh_sia_daily.nc',
                'South': 'https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/sh/osisaf_sh_sia_daily.nc'}

    index_dict = {"Sea Ice Extent": sie_dict, "Sea Ice Area": sia_dict}
    dataset = xr.open_dataset(index_dict[index][area])

    title = dataset.title

    array_index = {"Sea Ice Extent": "sie", "Sea Ice Area": "sia"}
    data_array = dataset[array_index[index]]

    stripped_data = {str(year): values.values for year, values in data_array.groupby("time.year")}
    is_leap_year = {year: data_array.time.sel(time=f"{year}-01-01").dt.is_leap_year for year in stripped_data.keys()}
    long_name = data_array.attrs["long_name"]
    units = data_array.attrs["units"]

    return {"stripped_data": stripped_data,
            "is_leap_year": is_leap_year,
            "title": title,
            "long_name": long_name,
            "units": units}


def prepare_plot_data(index, area, years):
    extracted_dict = download_and_extract(index, area)

    # x-locations for leap years, which have 366 days.
    doy_leap = np.arange(1, 367, 1)
    # Non-leap years have the same x-locations except for day 60 (29th of February).
    doy_not_leap = doy_leap[np.arange(len(doy_leap)) != 59]

    data = []
    day_of_year = []
    year_array = []

    for year in years:
        data.append(extracted_dict["stripped_data"][year])

        # Make sure that day of year array is of the same length as the data array. This accounts for years that are
        # not yet over in the data.
        if extracted_dict["is_leap_year"][year]:
            day_of_year.append(doy_leap[:len(data[-1])])
            year_array.append(year)
        else:
            day_of_year.append(doy_not_leap[:len(data[-1])])
            year_array.append(year)

    plot_dict = {"day_of_year": day_of_year, "data": data, "year": year_array}
    column_data_source = ColumnDataSource(plot_dict)

    return {"column_data_source": column_data_source,
            "years": list(extracted_dict["stripped_data"].keys()),
            "title": extracted_dict["title"],
            "long_name": extracted_dict["long_name"],
            "units": extracted_dict["units"]}


def make_plot(column_data_source, title, long_name, units):
    inner_plot = figure(title=title, x_range=(1, 366), y_range=(0, 18))
    inner_plot.multi_line(xs="day_of_year", ys="data", source=column_data_source, line_width=2)

    x_ticks = {1: '1 Jan',
               32: '1 Feb',
               61: '1 Mar',
               92: '1 Apr',
               122: '1 May',
               153: '1 Jun',
               183: '1 Jul',
               214: '1 Aug',
               245: '1 Sep',
               275: '1 Oct',
               306: '1 Nov',
               336: '1 Dec',
               366: '31 Dec'}

    inner_plot.xaxis.ticker = list(x_ticks.keys())
    inner_plot.xaxis.major_label_overrides = x_ticks
    inner_plot.xaxis.axis_label = "Day of the year"

    # Make sure that the y-axis has ticks equaling multiples of 2.
    inner_plot.yaxis.ticker = AdaptiveTicker(base=10, mantissas=[2])
    inner_plot.yaxis.axis_label = f"{long_name} - {units}"

    inner_plot.add_tools(
        HoverTool(
            show_arrow=False,
            line_policy='next',
            tooltips=[
                ("Year", "@year"),
                ('Day of year', '$data_x'),
                ('Index value', '$data_y')
            ]
            )
        )

    return inner_plot


def update_plot(attr, old, new):
    # Update plot with new values from selectors.
    index = index_selector.value
    area = area_selector.value
    years = years_selector.value

    new_plot_data = prepare_plot_data(index, area, years)
    plot.title.text = new_plot_data["title"]
    source.data.update(new_plot_data["column_data_source"].data)


index_selector = Select(title="Index:", value="Sea Ice Extent", options=["Sea Ice Extent", "Sea Ice Area"])
area_selector = Select(title="Area:", value="North", options=["North", "South"])

year_list = list(download_and_extract(index_selector.value, area_selector.value)["stripped_data"].keys())
years_selector = MultiChoice(value=year_list, options=year_list)

plot_data = prepare_plot_data(index_selector.value, area_selector.value, years_selector.value)
source = plot_data["column_data_source"]

plot = make_plot(source, plot_data["title"], plot_data["long_name"], plot_data["units"])

# Layout
inputs = column(index_selector, area_selector, years_selector)
row1 = row(plot, inputs)
tab_managed = Panel(child=row1)

layout = Tabs(tabs=[tab_managed])

index_selector.on_change('value', update_plot)
area_selector.on_change('value', update_plot)
years_selector.on_change('value', update_plot)

curdoc().add_root(layout)
