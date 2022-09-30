import panel as pn
from bokeh.plotting import figure
from bokeh.models import AdaptiveTicker, Select, HoverTool, Range1d, Legend, CustomJS, Paragraph, Dropdown, Label
from bokeh.layouts import column, row
import toolkit as tk

# Specify a loading spinner wheel to display when data is being loaded.
pn.extension(loading_spinner='dots', loading_color='#696969', sizing_mode="stretch_both")

# Add dropdown menus for index and area selection.
index_selector = Select(title="Index:", value="sie",
                        options=[("sie", "Sea Ice Extent"), ("sia", "Sea Ice Area")])
area_selector = Select(title="Area:", value="NH",
                       options=[("NH", "Northern Hemisphere"),
                                ("bar", "Barents Sea"),
                                ("beau", "Beaufort Sea"),
                                ("chuk", "Chukchi Sea"),
                                ("ess", "East Siberian Sea"),
                                ("fram", "Fram Strait-NP"),
                                ("kara", "Kara Sea"),
                                ("lap", "Laptev Sea"),
                                ("sval", "Svalbard-NIS"),
                                ("SH", "Southern Hemisphere"),
                                ("bell", "Amundsen-Bellingshausen Sea"),
                                ("indi", "Indian Ocean"),
                                ("ross", "Ross Sea"),
                                ("wedd", "Weddell Sea"),
                                ("wpac", "Western Pacific Ocean")])

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

# Add a dropdown menu for different preselected zoom levels.
zoom_shortcuts = Select(title="Zoom shortcuts:",
                        value="year",
                        options=[("year", "Year"),
                                 ("zoom", "Two months centred on latest observation"),
                                 ("min_extent", "Min extent"),
                                 ("max_extent", "Max extent")])

# Add a dropdown menu for selecting the colorscale that will be used for plotting the individual years.
color_scale_selector = Select(title="Color scale of yearly data:",
                              value="viridis",
                              options=[("viridis", "Viridis"),
                                       ("plasma", "Plasma"),
                                       ("batlow", "Batlow"),
                                       ("batlowS", "BatlowS"),
                                       ("decadal", "Custom decadal")])

# Download the data for the default index and area values.
ds = tk.download_dataset(index_selector.value, area_selector.value)
extracted_data = tk.extract_data(ds, index_selector.value)
da = extracted_data["da"]

# Calculate the percentiles and median, and the minimum and maximum value. We have to convert the dataset to use an
# all leap calendar and interpolate to fill in for the missing February 29th values.
da_converted = tk.convert_and_interpolate_calendar(da)

reference_period = reference_period_selector.value
start_year = reference_period[:4]
end_year = reference_period[5:]

percentiles_and_median_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice(start_year, end_year)))
cds_percentile_1090 = percentiles_and_median_dict["cds_percentile_1090"]
cds_percentile_2575 = percentiles_and_median_dict["cds_percentile_2575"]
cds_median = percentiles_and_median_dict["cds_median"]

min_max_dict = tk.calculate_min_max(da_converted)
cds_minimum = min_max_dict["cds_minimum"]
cds_maximum = min_max_dict["cds_maximum"]

# Calculate index of individual years.
cds_individual_years = tk.calculate_individual_years(da, da_converted)


# Plot the figure and make sure that it uses all available space.
plot = figure(title=extracted_data["title"], tools="pan, wheel_zoom, box_zoom, save")
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

percentile_2575 = plot.varea(x="day_of_year",
                             y1="percentile_25",
                             y2="percentile_75",
                             source=cds_percentile_2575,
                             fill_alpha=0.6,
                             fill_color="gray")

# Plot the median.
median = plot.line(x="day_of_year", y="median", source=cds_median, line_width=2, color="dimgray", alpha=0.6)

legend_list.append(("Climatology", [percentile_1090, percentile_2575, median]))

# Plot the minimum and maximum values.
minimum = plot.line(x="day_of_year",
                    y="minimum",
                    source=cds_minimum,
                    line_alpha=0.8,
                    color="black",
                    line_width=2,
                    line_dash="dashed")

maximum = plot.line(x="day_of_year",
                    y="maximum",
                    source=cds_maximum,
                    line_alpha=0.8,
                    color="black",
                    line_width=2,
                    line_dash="dashed")

legend_list.append(("Min/Max", [minimum, maximum]))


# Plot the individual years.
data_years = tk.get_list_of_years(da)
colours_dict = tk.find_line_colours(data_years[:-1], color_scale_selector.value)
individual_years_glyphs = []
cds_individual_years_list = list(cds_individual_years.values())

# Plot lines for all years except current one.
for year, cds_individual_year in zip(data_years[:-1], cds_individual_years_list[:-1]):
    line_glyph = plot.line(x="day_of_year",
                           y="index_values",
                           source=cds_individual_year,
                           line_width=2,
                           line_color=colours_dict[year])
    legend_list.append((year, [line_glyph]))
    individual_years_glyphs.append(line_glyph)

# Plot the current year as two lines on top of each other (black and white dashed line).
current_year_outline = plot.line(x="day_of_year",
                                 y="index_values",
                                 source=cds_individual_years_list[-1],
                                 line_width=3,
                                 line_color="black")

current_year_filler = plot.line(x="day_of_year",
                                y="index_values",
                                source=cds_individual_years_list[-1],
                                line_width=2,
                                line_dash=[5, 5],
                                line_color="white")

legend_list.append((data_years[-1], [current_year_outline, current_year_filler]))
individual_years_glyphs.append(current_year_outline)

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
TOOLTIPS = """
    <div>
        <div>
            <span style="font-size: 12px; font-weight: bold">Date:</span>
            <span style="font-size: 12px;">@date</span>
        </div>
        <div>
            <span style="font-size: 12px; font-weight: bold">Index:</span>
            <span style="font-size: 12px;">@index_values{0.000}</span>
            <span style="font-size: 12px;">mill. km<sup>2</sup></span>
        </div>
        <div>
            <span style="font-size: 12px; font-weight: bold">Rank:</span>
            <span style="font-size: 12px;">@rank</span>
        </div>
    </div>
"""

plot.add_tools(HoverTool(renderers=individual_years_glyphs,
                         tooltips=TOOLTIPS))

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
plot.y_range.reset_end = upper_y_lim
plot.yaxis.ticker = AdaptiveTicker(base=10, mantissas=[1, 2], num_minor_ticks=4, desired_num_ticks=10)
plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

# Find the day of year with the minimum and maximum values.
doy_minimum = da_converted.groupby("time.dayofyear").mean().idxmin().values.astype(int)
doy_maximum = da_converted.groupby("time.dayofyear").mean().idxmax().values.astype(int)

# Add a bottom label with information about the data that's used to make the graphic.
first_year = data_years[0]
second_to_last_year = data_years[-2]
last_date_string = da.time[-1].dt.strftime('%Y-%m-%d').values


def label_text(reference_period, first_year, second_to_last_year, last_date_string):
    """Produces a string with climatology and data info."""

    label_text = f"Median and percentiles for {reference_period}, " \
                 f"min/max for {first_year}-{second_to_last_year}\n" \
                 "v2p1 EUMETSAT OSI SAF data with R&D input from ESA CCI\n" \
                 "Source: EUMETSAT OSI SAF (https://osi-saf.eumetsat.int)\n" \
                 f"Last data point: {last_date_string}"

    return label_text


citation_text = label_text(reference_period_selector.value, first_year, second_to_last_year, last_date_string)

citation = Label(x=5,
                 y=5,
                 x_units='screen',
                 y_units='screen',
                 text=citation_text,
                 text_font_size='12px',
                 text_color='black')

plot.add_layout(citation)

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

    for (var i = fig.renderers.length; i > (fig.renderers.length - 6); i--) {
        fig.renderers[i-1].visible=true};

} else if (this.item === "last_2_years") {
    for (var i = 5; i < fig.renderers.length; i++) {
        fig.renderers[i].visible=false};

    for (var i = fig.renderers.length; i > (fig.renderers.length - 3); i--) {
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
    with pn.param.set_values(bokeh_pane, loading=True):
        # Update plot with new values from selectors.
        index = index_selector.value
        area = area_selector.value
        reference_period = reference_period_selector.value

        ds = tk.download_dataset(index, area)
        extracted_data = tk.extract_data(ds, index)
        da = extracted_data["da"]

        global da_converted
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
        new_cds_individual_years = tk.calculate_individual_years(da, da_converted)
        # Update the existing columndatasources with the new data.
        for new_cds, old_cds in zip(new_cds_individual_years.values(), cds_individual_years.values()):
            old_cds.data.update(new_cds.data)

        # Set plot attributes.
        plot.title.text = extracted_data["title"]
        plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

        # Find the day of year for the average minimum and maximum values.
        global doy_minimum
        doy_minimum = da_converted.groupby("time.dayofyear").mean().idxmin().values.astype(int)
        global doy_maximum
        doy_maximum = da_converted.groupby("time.dayofyear").mean().idxmax().values.astype(int)

        last_date_string = da.time[-1].dt.strftime('%Y-%m-%d').values
        citation.text = label_text(reference_period,
                                   first_year,
                                   second_to_last_year,
                                   last_date_string)


def update_zoom(attr, old, new):
    with pn.param.set_values(bokeh_pane, loading=True):
        if zoom_shortcuts.value == 'year':
            plot.x_range.start = 1
            plot.x_range.end = 366
            plot.y_range.start = 0
            plot.y_range.end = tk.find_nice_ylimit(da_converted)

        elif zoom_shortcuts.value == 'zoom':
            # Plot two months around the latest datapoint. Make sure that the lower bound is not less 1st of Jan and
            # upper bound is not more than 31st of Dec.
            x_range_start = current_year_outline.data_source.data['day_of_year'][-1] - 30
            x_range_end = current_year_outline.data_source.data['day_of_year'][-1] + 30
            plot.x_range.start = (x_range_start if x_range_start > 1 else 1)
            plot.x_range.end = (x_range_end if x_range_end < 366 else 366)
            set_zoom_yrange(padding_frac=0.05)

        elif zoom_shortcuts.value == 'min_extent':
            # Plot two months around the day of year with the lowest average minimum value. Make sure that the lower
            # bound is not less 1st of Jan and upper bound is not more than 31st of Dec.
            plot.x_range.start = (doy_minimum - 30 if doy_minimum - 30 > 1 else 1)
            plot.x_range.end = (doy_minimum + 30 if doy_minimum + 30 < 366 else 366)
            set_zoom_yrange(padding_frac=0.05)

        elif zoom_shortcuts.value == 'max_extent':
            # Plot two months around the day of year with the highest average maximum value. Make sure that the lower
            # bound is not less 1st of Jan and upper bound is not more than 31st of Dec.
            plot.x_range.start = (doy_maximum - 30 if doy_maximum - 30 > 1 else 1)
            plot.x_range.end = (doy_maximum + 30 if doy_maximum + 30 < 366 else 366)
            set_zoom_yrange(padding_frac=0.05)


def set_zoom_yrange(padding_frac):
    # Set the y-range between the minimum and maximum values plus a little padding.
    doy_start = plot.x_range.start - 1
    doy_end = plot.x_range.end - 1

    data_minimum = da_converted.groupby("time.dayofyear").min().sel(dayofyear=slice(doy_start, doy_end)).min().values
    data_maximum = da_converted.groupby("time.dayofyear").max().sel(dayofyear=slice(doy_start, doy_end)).max().values

    # Sometimes the minimum and maximum values are the same. Account for this to always have some padding.
    if data_maximum - data_minimum < 1E-3:
        padding = data_maximum * padding_frac
    else:
        padding = (data_maximum - data_minimum) * padding_frac

    plot.y_range.start = (data_minimum - padding if data_minimum - padding > 0 else 0)
    plot.y_range.end = data_maximum + padding


def update_line_colour(attr, old, new):
    with pn.param.set_values(bokeh_pane, loading=True):
        colour = color_scale_selector.value
        data_years = list(cds_individual_years.keys())
        colours_dict = tk.find_line_colours(data_years[:-1], colour)

        for year, individual_year_glyph in zip(data_years[:-1], individual_years_glyphs[:-1]):
            individual_year_glyph.glyph.line_color = colours_dict[year]


index_selector.on_change('value', update_data)
area_selector.on_change('value', update_data)
reference_period_selector.on_change('value', update_data)

# The zoom level doesn't only depend on the current selection in the zoom shortcut, but also on the index and area.
zoom_shortcuts.on_change('value', update_zoom)
index_selector.on_change('value', update_zoom)
area_selector.on_change('value', update_zoom)

color_scale_selector.on_change('value', update_line_colour)

bokeh_pane = pn.pane.Bokeh(column1).servable()
