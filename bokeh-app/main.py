import xarray as xr
from bokeh.plotting import figure
from bokeh.models import Panel, Tabs, ColumnDataSource, AdaptiveTicker, Select, HoverTool, Range1d, Legend, CustomJS,\
    Paragraph, Dropdown
from bokeh.layouts import column, row
from bokeh.io import curdoc
import numpy as np
import cmcrameri.cm as cm
import matplotlib


def download_dataset(index, area):
    sie_dict = {"Northern Hemisphere": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/nh"
                                       "/osisaf_nh_sie_daily.nc",
                "Southern Hemisphere": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/sh"
                                       "/osisaf_sh_sie_daily.nc"}
    sia_dict = {"Northern Hemisphere": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/nh"
                                       "/osisaf_nh_sia_daily.nc",
                "Southern Hemisphere": "https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/sh"
                                       "/osisaf_sh_sia_daily.nc"}
    url_dict = {"Sea Ice Extent": sie_dict, "Sea Ice Area": sia_dict}

    return xr.open_dataset(url_dict[index][area])


def extract_data(ds, index):
    index_translation = {"Sea Ice Extent": "sie", "Sea Ice Area": "sia"}
    da = ds[index_translation[index]]
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
    first_year = da.time.dt.year[0].values
    second_to_last_year = da.time.dt.year[-2].values
    sliced_da = da.sel(time=slice(str(first_year), str(second_to_last_year)))

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


def find_line_colours(years):
    """Find a colors for the individual years."""
    normalised = np.linspace(0, 1, len(years))
    colours = cm.batlowS(normalised)
    colours_in_hex = [matplotlib.colors.to_hex(colour) for colour in colours]
    colour_dict = {year: colour for year, colour in zip(years, colours_in_hex)}

    return colour_dict


def update_plot(attr, old, new):
    # Update plot with new values from selectors.
    index = index_selector.value
    area = area_selector.value
    reference_period = reference_period_selector.value

    ds = download_dataset(index, area)
    extracted_data = extract_data(ds, index)
    da = extracted_data["da"]

    da_converted = convert_and_interpolate_calendar(da)

    start_year = reference_period[:4]
    end_year = reference_period[5:]
    percentiles_and_median_dict = calculate_percentiles_and_median(da_converted.sel(time=slice(start_year, end_year)))
    cds_percentile_1090.data.update(percentiles_and_median_dict["cds_percentile_1090"].data)
    cds_percentile_2575.data.update(percentiles_and_median_dict["cds_percentile_2575"].data)
    cds_median.data.update(percentiles_and_median_dict["cds_median"].data)

    min_max_dict = calculate_min_max(da_converted)
    cds_minimum.data.update(min_max_dict["cds_minimum"].data)
    cds_maximum.data.update(min_max_dict["cds_maximum"].data)

    # Calculate new columndatasources for the individual years.
    new_cds_individual_years = calculate_individual_years(da)
    # Update the existing columndatasources with the new data.
    for new_cds, old_cds in zip(new_cds_individual_years.values(), cds_individual_years.values()):
        old_cds.data.update(new_cds.data)

    # Set plot attributes.
    plot.title.text = extracted_data["title"]
    plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

    # Find new "nice" upper y-limit, and make sure that the reset upper y-limit is set to the same value.
    plot.y_range.end = find_nice_ylimit(da)
    plot.y_range.reset_end = find_nice_ylimit(da)


# Add dropdown menus for index and area selection.
index_selector = Select(title="Index:", value="Sea Ice Extent", options=["Sea Ice Extent", "Sea Ice Area"])
area_selector = Select(title="Area:", value="Northern Hemisphere",
                       options=["Northern Hemisphere", "Southern Hemisphere"])

# Add a dropdown menu for selecting the reference period of the percentile and median plots.
reference_period_selector = Select(title="Reference period of percentiles and median:",
                                   value="1981-2010",
                                   options=[("1981-2010", "1981-2010"),
                                            ("1991-2020", "1991-2020"),
                                            ("1980-1989", "1980s"),
                                            ("1990-1999", "1990s"),
                                            ("2000-2009", "2000s"),
                                            ("2010-2019", "2010s"),
                                            ("2020-2029", "2020s")])

# Download the data for the default index and area values.
ds = download_dataset(index_selector.value, area_selector.value)
extracted_data = extract_data(ds, index_selector.value)
da = extracted_data["da"]

# Calculate the percentiles and median, and the minimum and maximum value. We have to convert the dataset to use an
# all leap calendar and interpolate to fill in for the missing February 29th values.
da_converted = convert_and_interpolate_calendar(da)

percentiles_and_median_dict = calculate_percentiles_and_median(da_converted)
cds_percentile_1090 = percentiles_and_median_dict["cds_percentile_1090"]
cds_percentile_2575 = percentiles_and_median_dict["cds_percentile_2575"]
cds_median = percentiles_and_median_dict["cds_median"]

min_max_dict = calculate_min_max(da_converted)
cds_minimum = min_max_dict["cds_minimum"]
cds_maximum = min_max_dict["cds_maximum"]

# Calculate index of individual years.
cds_individual_years = calculate_individual_years(da)


# Plot the figure and make sure that it uses all of the available space.
plot = figure(title=extracted_data["title"])
plot.sizing_mode = "stretch_both"

# Create an empty list to store labels and glyphs for plotting legends.
legend_list = []

# Plot percentile ranges.
percentile_1090 = plot.varea(x="day_of_year",
                             y1="percentile_10",
                             y2="percentile_90",
                             source=cds_percentile_1090,
                             fill_alpha=0.6,
                             fill_color="darkgray")

legend_list.append(("10th-90th %", [percentile_1090]))

percentile_2575 = plot.varea(x="day_of_year",
                             y1="percentile_25",
                             y2="percentile_75",
                             source=cds_percentile_2575,
                             fill_alpha=0.6,
                             fill_color="gray")

legend_list.append(("25th-75th %", [percentile_2575]))

# Plot the median.
median = plot.line(x="day_of_year", y="median", source=cds_median, line_width=2, color="dimgray", alpha=0.6)
legend_list.append(("Median", [median]))

# Plot the minimum and maximum values.
minimum = plot.line(x="day_of_year",
                    y="minimum",
                    source=cds_minimum,
                    line_alpha=0.8,
                    color="black",
                    line_width=2,
                    line_dash="dashed")

legend_list.append(("Minimum", [minimum]))

plot.add_tools(HoverTool(renderers=[minimum], tooltips=[('Day of year', '$data_x'), ('Minimum value', '$data_y')]))

maximum = plot.line(x="day_of_year",
                    y="maximum",
                    source=cds_maximum,
                    line_alpha=0.8,
                    color="black",
                    line_width=2,
                    line_dash="dashed")

legend_list.append(("Maximum", [maximum]))

plot.add_tools(HoverTool(renderers=[maximum], tooltips=[('Day of year', '$data_x'), ('Maximum value', '$data_y')]))


# Plot the individual years.
colours_dict = find_line_colours(cds_individual_years.keys())
individual_years_glyphs = []
for year, cds_individual_year in cds_individual_years.items():
    line_glyph = plot.line(x="day_of_year",
                           y="index_values",
                           source=cds_individual_year,
                           line_width=2,
                           line_color=colours_dict[year])
    legend_list.append((year, [line_glyph]))
    individual_years_glyphs.append(line_glyph)

# Maximum number of elements in a sublist.
n = 23
legend_split = [legend_list[i:i+n] for i in range(0, len(legend_list), n)]

for sublist in legend_split:
    legend = Legend(items=sublist, location="top_center")
    legend.spacing = 1
    plot.add_layout(legend, "right")

plot.legend.click_policy = "hide"

# Add a hovertool to display the year, day of year, and index value of the individual years.
plot.add_tools(HoverTool(renderers=individual_years_glyphs,
                         tooltips=[("Date", "@date"),
                                   ('Day of year', '@day_of_year'),
                                   ('Index value', '@index_values')]))

plot.x_range = Range1d(start=1, end=366)
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

plot.xaxis.ticker = list(x_ticks.keys())
plot.xaxis.major_label_overrides = x_ticks
plot.xaxis.axis_label = "Date"

upper_y_lim = find_nice_ylimit(da)
plot.y_range = Range1d(start=0, end=upper_y_lim)
plot.yaxis.ticker = AdaptiveTicker(base=10, mantissas=[1, 2], num_minor_ticks=4, desired_num_ticks=10)
plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

# Create a dropdown button with plot shortcuts.
menu = [("Erase all", "erase_all"),
        ("Show all", "show_all"),
        ("Last 5 years", "last_5_years"),
        ("Last 2 years", "last_2_years")]

plot_shortcuts = Dropdown(label="Plot shortcuts", menu=menu)

# Callback code.
callback = CustomJS(args=dict(fig=plot), code='''
if (this.item === "erase_all") {
    for (var i = 0; i < fig.renderers.length; i++) {
        fig.renderers[i].visible = false};
        
} else if (this.item === "show_all") {
    for (var i = 0; i < fig.renderers.length; i++) {
        fig.renderers[i].visible = true};

} else if (this.item === "last_5_years") {
    for (var i = 5; i < fig.renderers.length; i++) {
        fig.renderers[i].visible=false};

    for (var i = fig.renderers.length; i > (fig.renderers.length - 5); i--) {
        fig.renderers[i-1].visible=true};

} else if (this.item === "last_2_years") {
    for (var i = 5; i < fig.renderers.length; i++) {
        fig.renderers[i].visible=false};

    for (var i = fig.renderers.length; i > (fig.renderers.length - 2); i--) {
        fig.renderers[i-1].visible=true};
}
''')

# Make sure that callback code runs when user clicks on one of the choices.
plot_shortcuts.js_on_event("menu_item_click", callback)

# Layout
inputs = column(index_selector, area_selector, reference_period_selector, plot_shortcuts)
row1 = row(plot, inputs)

# Create a label to signify that the tool is WIP.
text = Paragraph(text="UNDER DEVELOPMENT", style={"color": "#ff0000", "font-weight": "bold"})
column1 = column(text, row1)
column1.sizing_mode = "stretch_both"

index_selector.on_change('value', update_plot)
area_selector.on_change('value', update_plot)
reference_period_selector.on_change('value', update_plot)

curdoc().add_root(column1)
