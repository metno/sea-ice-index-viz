from bokeh.plotting import figure
from bokeh.models import AdaptiveTicker, Select, HoverTool, Range1d, Legend, CustomJS, Paragraph, Dropdown
from bokeh.layouts import column, row
from bokeh.io import curdoc
import toolkit as tk


# Add dropdown menus for index and area selection.
index_selector = Select(title="Index:", value="sie",
                        options=[("sie", "Sea Ice Extent"), ("sia", "Sea Ice Area")])
area_selector = Select(title="Area:", value="NH",
                       options=[("NH", "Northern Hemisphere"), ("SH", "Southern Hemisphere")])

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

# Make a dropdown list with preselected zoom levels.
zoom_shortcuts_menu = [("Year", "year"),
                       ("Two months centered on latest observation", "zoom"),
                       ("Min extent", "min_extent"),
                       ("Max extent", "max_extent")]

zoom_shortcuts = Dropdown(label="Zoom shortcuts", menu=zoom_shortcuts_menu)

# Add a dropdown menu for selecting the colorscale that will be used for plotting the individual years.
color_scale_selector = Select(title="Color scale of yearly data:",
                              value="decadal",
                              options=[("decadal", "By decade"),
                                       ("viridis", "viridis (CVD friendly)"),
                                       ("plasma", "plasma (CVD friendly)"),
                                       ("batlow", "batlow (CVD friendly)"),
                                       ("batlowS", "batlowS (CVD friendly)")])

# Download the data for the default index and area values.
ds = tk.download_dataset(index_selector.value, area_selector.value)
extracted_data = tk.extract_data(ds, index_selector.value)
da = extracted_data["da"]

# Calculate the percentiles and median, and the minimum and maximum value. We have to convert the dataset to use an
# all leap calendar and interpolate to fill in for the missing February 29th values.
da_converted = tk.convert_and_interpolate_calendar(da)

percentiles_and_median_dict = tk.calculate_percentiles_and_median(da_converted)
cds_percentile_1090 = percentiles_and_median_dict["cds_percentile_1090"]
cds_percentile_2575 = percentiles_and_median_dict["cds_percentile_2575"]
cds_median = percentiles_and_median_dict["cds_median"]

min_max_dict = tk.calculate_min_max(da_converted)
cds_minimum = min_max_dict["cds_minimum"]
cds_maximum = min_max_dict["cds_maximum"]

# Calculate index of individual years.
cds_individual_years = tk.calculate_individual_years(da)


# Plot the figure and make sure that it uses all available space.
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
colours_dict = tk.find_line_colours(cds_individual_years.keys(), color_scale_selector.value)
individual_years_glyphs = []
for year, cds_individual_year in cds_individual_years.items():
    line_glyph = plot.line(x="day_of_year",
                           y="index_values",
                           source=cds_individual_year,
                           line_width=2,
                           line_color=colours_dict[year])
    legend_list.append((year, [line_glyph]))
    individual_years_glyphs.append(line_glyph)

# Make sure the current year has a thicker line than the other years.
line_glyph.glyph.line_width = 3

# To plot legends for the individual years we need to split the list of legends into several sublists. If we don't do
# this the list will be so long that it's out of frame. The number below is the maximum number of elements that can
# be inside one sublist. This number was determined with basic testing on one specific computer. This is an issue
# because other clients can have computers with a different screen resolution which can fit more legends. Keep this
# solution for now, but check if there's a better way to solve this.
n = 23
legend_split = [legend_list[i:i+n] for i in range(0, len(legend_list), n)]

for sublist in legend_split:
    legend = Legend(items=sublist, location="top_center")
    legend.spacing = 1
    plot.add_layout(legend, "right")

# Make the clicking the legend hide/show the given element.
plot.legend.click_policy = "hide"

# Add a hovertool to display the year, day of year, and index value of the individual years.
plot.add_tools(HoverTool(renderers=individual_years_glyphs,
                         tooltips=[("Date", "@date"),
                                   ('Day of year', '@day_of_year'),
                                   ('Index value', '@index_values')]))

# Hardcode the x-ticks (day_of_year, date).
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

# Find a nice upper y-limit divisible by two.
upper_y_lim = tk.find_nice_ylimit(da)
plot.y_range = Range1d(start=0, end=upper_y_lim)
plot.yaxis.ticker = AdaptiveTicker(base=10, mantissas=[1, 2], num_minor_ticks=4, desired_num_ticks=10)
plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

# Create a dropdown button with plot shortcuts.
menu = [("Erase all", "erase_all"),
        ("Show all", "show_all"),
        ("Last 5 years", "last_5_years"),
        ("Last 2 years", "last_2_years")]

plot_shortcuts = Dropdown(label="Plot shortcuts", menu=menu)

# The plot shortcuts use the following javascript callback code.
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
inputs = column(index_selector,
                area_selector,
                reference_period_selector,
                plot_shortcuts,
                zoom_shortcuts,
                color_scale_selector)
row1 = row(plot, inputs)

# Create a label to signify that the tool is WIP.
text = Paragraph(text="UNDER DEVELOPMENT", style={"color": "#ff0000", "font-weight": "bold"})
column1 = column(text, row1)
column1.sizing_mode = "stretch_both"


def update_data(attr, old, new):
    # Reset the x-range in case the plot has been zoomed in.
    plot.x_range.start = 1
    plot.x_range.end = 366

    # Update plot with new values from selectors.
    index = index_selector.value
    area = area_selector.value
    reference_period = reference_period_selector.value

    ds = tk.download_dataset(index, area)
    extracted_data = tk.extract_data(ds, index)
    da = extracted_data["da"]

    da_converted = tk.convert_and_interpolate_calendar(da)

    start_year = reference_period[:4]
    end_year = reference_period[5:]
    percentiles_and_median_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice(start_year, end_year)))
    cds_percentile_1090.data.update(percentiles_and_median_dict["cds_percentile_1090"].data)
    cds_percentile_2575.data.update(percentiles_and_median_dict["cds_percentile_2575"].data)
    cds_median.data.update(percentiles_and_median_dict["cds_median"].data)

    min_max_dict = tk.calculate_min_max(da_converted)
    cds_minimum.data.update(min_max_dict["cds_minimum"].data)
    cds_maximum.data.update(min_max_dict["cds_maximum"].data)

    # Calculate new columndatasources for the individual years.
    new_cds_individual_years = tk.calculate_individual_years(da)
    # Update the existing columndatasources with the new data.
    for new_cds, old_cds in zip(new_cds_individual_years.values(), cds_individual_years.values()):
        old_cds.data.update(new_cds.data)

    # Set plot attributes.
    plot.title.text = extracted_data["title"]
    plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

    # Find new "nice" upper y-limit, and make sure that the reset upper y-limit is set to the same value.
    plot.y_range.end = tk.find_nice_ylimit(da)
    plot.y_range.reset_end = plot.y_range.end


def update_zoom(new_zoom):
    if new_zoom.item == 'year':
        plot.x_range.start = 1
        plot.x_range.end = 366

    elif new_zoom.item == 'zoom':
        # Plot two months around the latest datapoint. Make sure that the lower bound is not less 1st of Jan and
        # upper bound is not more than 31st of Dec.
        x_range_start = line_glyph.data_source.data['day_of_year'][-1] - 30
        x_range_end = line_glyph.data_source.data['day_of_year'][-1] + 30
        plot.x_range.start = (x_range_start if x_range_start > 1 else 1)
        plot.x_range.end = (x_range_end if x_range_end < 366 else 366)

    elif new_zoom.item == 'min_extent':
        # The day of year with the minimum value depends on which hemisphere is considered. Choose 15th of September
        # for the NH and 15th of February for the SH.
        min_doy = (259 if area_selector.value == "NH" else 46)
        plot.x_range.start = min_doy - 30
        plot.x_range.end = min_doy + 30

    elif new_zoom.item == 'max_extent':
        # The day of year with the maximum value depends on which hemisphere is considered. Choose 15th of March
        # for the NH and 15th of September for the SH.
        doy_max = (61 if area_selector.value == "NH" else 259)
        plot.x_range.start = doy_max - 30
        plot.x_range.end = doy_max + 30


def update_line_colour(attr, old, new):
    colour = color_scale_selector.value
    colours_dict = tk.find_line_colours(cds_individual_years.keys(), colour)

    for year, individual_year_glyph in zip(cds_individual_years.keys(), individual_years_glyphs):
        individual_year_glyph.glyph.line_color = colours_dict[year]


index_selector.on_change('value', update_data)
area_selector.on_change('value', update_data)
reference_period_selector.on_change('value', update_data)
zoom_shortcuts.on_click(update_zoom)
color_scale_selector.on_change('value', update_line_colour)

curdoc().add_root(column1)
