import panel as pn
from bokeh.plotting import figure
from bokeh.models import AdaptiveTicker, HoverTool, Range1d, Legend, Paragraph, Label, CustomJSHover
import logging
import param
import toolkit as tk

# Specify a loading spinner wheel to display when data is being loaded.
pn.extension(loading_spinner='dots', loading_color='#696969')


def exception_handler(ex):
    # Function used to handle exceptions by showing an error message to the user.
    logging.error("Error", exc_info=ex)
    pn.state.notifications.error(f'{ex}')


# Handle exceptions.
pn.extension('notifications')
pn.extension(exception_handler=exception_handler, notifications=True)


# Add a parameter for setting the desired version of the sea ice data, and sync to url parameter.
class VersionUrlParameter(param.Parameterized):
    value = param.Parameter("v2p2")


pn.state.location.sync(VersionUrlParameter, {"value": "version"})

# Add dropdown menu for index selection, and sync to url parameter.
index_selector = pn.widgets.Select(name="Index:",
                                   options={"Sea Ice Extent": "sie", "Sea Ice Area": "sia"},
                                   value="sie",
                                   sizing_mode="stretch_width")
pn.state.location.sync(index_selector, {"value": "index"})

# Add dropdown menu for area selection, and sync to url parameter.
area_groups = {
    "Global": {
        "Global": "glb",
        "Northern Hemisphere": "nh",
        "Southern Hemisphere": "sh",
    },
    "Northern Hemisphere Regions": {
        "Barents Sea": "bar",
        "Beaufort Sea": "beau",
        "Chukchi Sea": "chuk",
        "East Siberian Sea": "ess",
        "Fram Strait": "fram",
        "Kara Sea": "kara",
        "Laptev Sea": "lap",
        "Svalbard": "sval",
    },
    "Southern Hemisphere Regions": {
        "Amundsen-Bellingshausen Sea": "bell",
        "Dronning Maud Land": "drml",
        "Indian Ocean": "indi",
        "Ross Sea": "ross",
        "Troll Station": "trol",
        "Weddell Sea": "wedd",
        "Western Pacific Ocean": "wpac",
    }
}

area_selector = pn.widgets.Select(name="Area:",
                                  groups=area_groups,
                                  value="nh",
                                  sizing_mode="stretch_width")
pn.state.location.sync(area_selector, {"value": "area"})

# Add a dropdown menu for selecting the reference period of the percentile and median plots, and sync to url parameter.
reference_period_selector = pn.widgets.Select(name="Reference period of percentiles and median:",
                                              options=["1981-2010", "1991-2020"],
                                              value="1981-2010",
                                              sizing_mode="stretch_width")
pn.state.location.sync(reference_period_selector, {"value": "ref_period"})

# Create a dropdown button with plot shortcuts, and sync to url parameter.
plot_shortcuts = pn.widgets.MenuButton(name="Plot shortcuts",
                                       items=[("Erase all", "erase_all"),
                                              ("Show all", "show_all"),
                                              ("Last 5 years", "last_5_years"),
                                              ("2 years", "2_years")],
                                       sizing_mode="stretch_width")
pn.state.location.sync(plot_shortcuts, {"clicked": "shortcut"})

# Add a dropdown menu for different preselected zoom levels.
zoom_shortcuts = pn.widgets.MenuButton(name="Zoom shortcuts:",
                                       items=[("Year", "year"),
                                              ("Two months centred on latest observation", "current"),
                                              ("Min extent", "min_extent"),
                                              ("Max extent", "max_extent")],
                                       sizing_mode="stretch_width")

# Initialise the zoom shortcut state.
zoom_shortcuts.clicked = "year"

# Sync to url parameter.
pn.state.location.sync(zoom_shortcuts, {"clicked": "zoom"})

# Add a dropdown menu for selecting the colorscale that will be used for plotting the individual years,
# and sync parameter to url.
color_groups = {
    "Sequential colour maps": {
        "Viridis": "viridis",
        "Viridis (reversed)": "viridis_r",
        "Plasma": "plasma",
        "Plasma (reversed)": "plasma_r",
        "Batlow": "batlow",
        "Batlow (reversed)": "batlow_r",
        "Custom decadal": "decadal",
    },
    "Non-sequential colour maps": {
        "BatlowS": "batlowS",
        "8 repeating colours": "cyclic_8",
        "17 repeating colours": "cyclic_17",
    }
}

color_scale_selector = pn.widgets.Select(name="Color scale of yearly data:",
                                         groups=color_groups,
                                         value="viridis",
                                         sizing_mode="stretch_width")
pn.state.location.sync(color_scale_selector, {"value": "colour"})

# Sometimes the data files are not available on the thredds server, so use try/except to check this.
try:
    extracted_data = tk.download_and_extract_data(index_selector.value,
                                                  area_selector.value,
                                                  "daily",
                                                  VersionUrlParameter.value)
    da = extracted_data["da"]

    # Convert the calendar to an all_leap calendar and interpolate the missing February 29th values.
    da_converted = tk.convert_and_interpolate_calendar(da)

    reference_period = reference_period_selector.value
    start_year = reference_period[:4]
    end_year = reference_period[5:]

    # Calculate the reference period climatology (percentiles and median)
    percentiles_and_median_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice(start_year,
                                                                                                  end_year)))
    cds_percentile_1090 = percentiles_and_median_dict["cds_percentile_1090"]
    cds_percentile_2575 = percentiles_and_median_dict["cds_percentile_2575"]
    cds_median = percentiles_and_median_dict["cds_median"]

    # Calculate the maximum and minumum values of the index for the entire time series except the current year.
    min_max_dict = tk.calculate_min_max(da_converted)
    cds_minimum = min_max_dict["cds_minimum"]
    cds_maximum = min_max_dict["cds_maximum"]

    # Calculate the decadal climatology (0-100 percentile and median).
    clim_1980s_dict = tk.calculate_span_and_median(da_converted.sel(time=slice("1978", "1989")))
    clim_1990s_dict = tk.calculate_span_and_median(da_converted.sel(time=slice("1990", "1999")))
    clim_2000s_dict = tk.calculate_span_and_median(da_converted.sel(time=slice("2000", "2009")))
    clim_2010s_dict = tk.calculate_span_and_median(da_converted.sel(time=slice("2010", "2019")))

    cds_span_1980s = clim_1980s_dict["cds_span"]
    cds_median_1980s = clim_1980s_dict["cds_median"]
    cds_span_1990s = clim_1990s_dict["cds_span"]
    cds_median_1990s = clim_1990s_dict["cds_median"]
    cds_span_2000s = clim_2000s_dict["cds_span"]
    cds_median_2000s = clim_2000s_dict["cds_median"]
    cds_span_2010s = clim_2010s_dict["cds_span"]
    cds_median_2010s = clim_2010s_dict["cds_median"]

    # Calculate the index for the individual years.
    cds_individual_years = tk.calculate_individual_years(da, da_converted)

    # Calculate the yearly min and max values.
    data_years = tk.get_list_of_years(da)
    colors_dict = tk.find_line_colors(data_years, color_scale_selector.value)
    cds_yearly_max, cds_yearly_min = tk.find_yearly_min_max(da_converted, colors_dict)

    # Trim the title to not contain the version number, and to deduplicate "Sea" substrings.
    trimmed_title = tk.trim_title(extracted_data["title"])

    # Plot the figure and make sure that it uses all available space.
    plot = figure(title=trimmed_title, tools="pan, wheel_zoom, box_zoom, save")
    plot.sizing_mode = "stretch_both"

    # Plot the reference period climatology (percentiles and median).
    percentile_1090_glyph = plot.varea(x="day_of_year",
                                       y1="percentile_10",
                                       y2="percentile_90",
                                       source=cds_percentile_1090,
                                       fill_alpha=0.6,
                                       fill_color="darkgray")

    percentile_2575_glyph = plot.varea(x="day_of_year",
                                       y1="percentile_25",
                                       y2="percentile_75",
                                       source=cds_percentile_2575,
                                       fill_alpha=0.6,
                                       fill_color="gray")

    median_glyph = plot.line(x="day_of_year", y="median", source=cds_median, line_width=2, color="dimgray", alpha=0.6)

    # Plot the min and max lines based on the min and max values of the entire period except the current year.
    min_line_glyph = plot.line(x="day_of_year",
                               y="minimum",
                               source=cds_minimum,
                               line_alpha=0.8,
                               color="black",
                               line_width=1.5,
                               line_dash=[4, 1])

    max_line_glyph = plot.line(x="day_of_year",
                               y="maximum",
                               source=cds_maximum,
                               line_alpha=0.8,
                               color="black",
                               line_width=1.5,
                               line_dash=[4, 1])

    # Create a function for plotting the decadal climatology.
    def decadal_curves(plot, percentile_source, median_source, fill_color, line_color):
        percentile = plot.varea(x="day_of_year",
                                y1="minimum",
                                y2="maximum",
                                source=percentile_source,
                                fill_alpha=0.5,
                                fill_color=fill_color,
                                visible=False)

        median_outline = plot.line(x="day_of_year",
                                   y="median",
                                   source=median_source,
                                   line_width=2.2,
                                   color="black",
                                   alpha=0.6,
                                   visible=False)

        median = plot.line(x="day_of_year",
                           y="median",
                           source=median_source,
                           line_width=2,
                           color=line_color,
                           alpha=0.6,
                           visible=False)

        return [percentile, median_outline, median]

    # Plot the decadal climatology.
    curve_1980s_glyph_list = decadal_curves(plot,
                                            cds_span_1980s,
                                            cds_median_1980s,
                                            colors_dict["1984"],
                                            colors_dict["1984"])

    curve_1990s_glyph_list = decadal_curves(plot,
                                            cds_span_1990s,
                                            cds_median_1990s,
                                            colors_dict["1994"],
                                            colors_dict["1994"])

    curve_2000s_glyph_list = decadal_curves(plot,
                                            cds_span_2000s,
                                            cds_median_2000s,
                                            colors_dict["2004"],
                                            colors_dict["2004"])

    curve_2010s_glyph_list = decadal_curves(plot,
                                            cds_span_2010s,
                                            cds_median_2010s,
                                            colors_dict["2014"],
                                            colors_dict["2014"])

    # Plot the individual years.
    data_years = tk.get_list_of_years(da)
    colors_dict = tk.find_line_colors(data_years[:-1], color_scale_selector.value)
    individual_years_glyphs = []
    individual_years_glyphs_legend_list = []
    cds_individual_years_list = list(cds_individual_years.values())

    # Plot all lines except for current year.
    for year, cds_individual_year in zip(data_years[:-1], cds_individual_years_list[:-1]):
        line_glyph = plot.line(x="day_of_year",
                               y="index_values",
                               source=cds_individual_year,
                               line_width=2,
                               line_color=colors_dict[year])
        individual_years_glyphs.append(line_glyph)
        individual_years_glyphs_legend_list.append((year, [line_glyph]))

    # Plot the yearly max and min values as triangles and circles, respectively.
    yearly_max_glyph = plot.circle(x="day_of_year",
                                   y="index_value",
                                   color="color",
                                   size=6,
                                   source=cds_yearly_max,
                                   visible=False)

    yearly_min_glyph = plot.circle(x="day_of_year",
                                   y="index_value",
                                   color="color",
                                   size=6,
                                   source=cds_yearly_min,
                                   visible=False)

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
                                    line_dash=[4, 4],
                                    line_color="white")

    # Add only the current year outline to list of individual year glyphs since we only need one of the current year
    # glyphs to display the hovertool values.
    individual_years_glyphs.append(current_year_outline)

    # Add labels and glyphs to legend list to get the desired order.
    legend_list = [("Climatology", [percentile_1090_glyph, percentile_2575_glyph, median_glyph]),
                   ("Min/Max", [min_line_glyph, max_line_glyph]),
                   ("Yearly min/max", [yearly_max_glyph, yearly_min_glyph])]
    legend_list.extend([("1980s", curve_1980s_glyph_list),
                        ("1990s", curve_1990s_glyph_list),
                        ("2000s", curve_2000s_glyph_list),
                        ("2010s", curve_2010s_glyph_list)])
    legend_list.extend(individual_years_glyphs_legend_list)
    legend_list.append((data_years[-1], [current_year_outline, current_year_filler]))

    # To plot legends for the individual years we need to split the list of legends into several sublists. If we
    # don't do this the list will be so long that it's out of frame. The number below is the maximum number of
    # elements that can be inside one sublist. This number was determined with basic testing on one specific
    # computer. This is an issue because other clients can have computers with a different screen resolution which
    # can fit more legends. Keep this solution for now, but check if there's a better way to solve this.
    n = 23
    legend_split = [legend_list[i:i+n] for i in range(0, len(legend_list), n)]

    for sublist in legend_split:
        legend = Legend(items=sublist, location="top_center")
        legend.spacing = 1
        plot.add_layout(legend, "right")

    # Make the clicking the legend hide/show the given element.
    plot.legend.click_policy = "hide"

    # Add a hovertool to display the date, index value, and rank of the individual years.

    # Function for custom formatting of rank values. If decimal is zero don't show it, otherwise show only one decimal.
    rank_custom = CustomJSHover(code="""
    if (Number.isInteger(value)) {
      return value.toFixed();
    } else {
      return value.toFixed(1);
    }
    """)

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
            <span style="font-size: 12px;">@rank{custom}</span>
        </div>
    </div>
    """

    plot.add_tools(HoverTool(renderers=individual_years_glyphs,
                             tooltips=TOOLTIPS,
                             formatters={'@rank': rank_custom},
                             toggleable=False))

    # Add a hovertool to display the date, index value, and rank of the yearly max values.
    MAX_TOOLTIPS = """
        <div>
            <div>
                <span style="font-size: 14px; font-weight: bold;">Yearly maximum</span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Date:</span>
                <span style="font-size: 12px;">@date</span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Index:</span>
                <span style="font-size: 12px;">@index_value{0.000}</span>
                <span style="font-size: 12px;">mill. km<sup>2</sup></span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Rank:</span>
                <span style="font-size: 12px;">@rank{custom}</span>
            </div>
        </div>
        """

    plot.add_tools(HoverTool(renderers=[yearly_max_glyph],
                             tooltips=MAX_TOOLTIPS,
                             formatters={'@rank': rank_custom},
                             toggleable=False))

    # Add a hovertool to display the date, index value, and rank of the yearly min values.
    MIN_TOOLTIPS = """
        <div>
            <div>
                <span style="font-size: 14px; font-weight: bold;">Yearly minimum</span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Date:</span>
                <span style="font-size: 12px;">@date</span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Index:</span>
                <span style="font-size: 12px;">@index_value{0.000}</span>
                <span style="font-size: 12px;">mill. km<sup>2</sup></span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Rank:</span>
                <span style="font-size: 12px;">@rank{custom}</span>
            </div>
        </div>
        """

    plot.add_tools(HoverTool(renderers=[yearly_min_glyph],
                             tooltips=MIN_TOOLTIPS,
                             formatters={'@rank': rank_custom},
                             toggleable=False))

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

    # Find an upper y-limit and set y-tick properties and y-label.
    upper_y_lim = tk.find_nice_ylimit(da)
    plot.y_range = Range1d(start=0, end=upper_y_lim)
    plot.y_range.reset_end = upper_y_lim
    plot.yaxis.ticker = AdaptiveTicker(base=10, mantissas=[1, 2], num_minor_ticks=4, desired_num_ticks=10)
    plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

    # Find the day of year with the minimum and maximum values. These are used in the zoom shortcuts.
    doy_minimum = da_converted.groupby("time.dayofyear").median().idxmin().values.astype(int)
    doy_maximum = da_converted.groupby("time.dayofyear").median().idxmax().values.astype(int)

    # Add a bottom label with information about the data that's used to make the graphic.
    first_year = str(data_years[0])
    second_to_last_year = str(data_years[-2])
    last_date_string = str(da.time[-1].dt.strftime('%Y-%m-%d').values)

    # Find the version of the data in order to add it to the label, and give the v3p0 data a custom label.
    if extracted_data["ds_version"] == "v2p1":
        version_label = "v2.1"
        cdr_version = "v2.1"
    elif extracted_data["ds_version"] == "v2p2":
        version_label = "v2.2"
        cdr_version = "v3"

    label_text = f"Median and percentiles (25-75% and 10-90%) for {reference_period_selector.value}, " \
                 f"min/max for {first_year}-{second_to_last_year}\n" \
                 f"Data: Derived from OSI SAF Sea Ice Concentration CDRs {cdr_version}\n" \
                 "Source: EUMETSAT OSI SAF data with R&D input from ESA CCI\n" \
                 f"Last data point: {last_date_string}"

    info_label = Label(x=5,
                       y=5,
                       x_units='screen',
                       y_units='screen',
                       text=label_text,
                       text_font_size='12px',
                       text_color='black')

    plot.add_layout(info_label)

    # Create a callback for plot shortcuts to hide and show different elements of the plot.
    def plot_shortcuts_callback(event):
        if event.new == "erase_all":
            # All glyphs will be hidden.
            percentile_1090_glyph.visible = False
            percentile_2575_glyph.visible = False
            median_glyph.visible = False
            min_line_glyph.visible = False
            max_line_glyph.visible = False

            for i in range(3):
                curve_1980s_glyph_list[i].visible = False
                curve_1990s_glyph_list[i].visible = False
                curve_2000s_glyph_list[i].visible = False
                curve_2010s_glyph_list[i].visible = False

            for glyph in individual_years_glyphs:
                glyph.visible = False

            current_year_outline.visible = False
            current_year_filler.visible = False

            yearly_min_glyph.visible = False
            yearly_max_glyph.visible = False

        if event.new == "show_all":
            # All glyphs except for the decadal curves and yearly min/max markers will be visible.
            percentile_1090_glyph.visible = True
            percentile_2575_glyph.visible = True
            median_glyph.visible = True
            min_line_glyph.visible = True
            max_line_glyph.visible = True

            for i in range(3):
                curve_1980s_glyph_list[i].visible = False
                curve_1990s_glyph_list[i].visible = False
                curve_2000s_glyph_list[i].visible = False
                curve_2010s_glyph_list[i].visible = False

            for glyph in individual_years_glyphs:
                glyph.visible = True

            current_year_outline.visible = True
            current_year_filler.visible = True

            yearly_min_glyph.visible = False
            yearly_max_glyph.visible = False

        if event.new == "last_5_years":
            # Show: reference period climatology, current year and the 5 preceding years.
            # Hide: decadal curves, yearly min/max dots, all other individual years.
            percentile_1090_glyph.visible = True
            percentile_2575_glyph.visible = True
            median_glyph.visible = True
            min_line_glyph.visible = True
            max_line_glyph.visible = True

            for i in range(3):
                curve_1980s_glyph_list[i].visible = False
                curve_1990s_glyph_list[i].visible = False
                curve_2000s_glyph_list[i].visible = False
                curve_2010s_glyph_list[i].visible = False

            yearly_min_glyph.visible = False
            yearly_max_glyph.visible = False

            for glyph in individual_years_glyphs[:-5]:
                glyph.visible = False
            for glyph in individual_years_glyphs[-6:]:
                glyph.visible = True

            current_year_outline.visible = True
            current_year_filler.visible = True

        if event.new == "2_years":
            # Show: reference period climatology, current year, and 2 hemisphere-dependent years.
            # Hide: decadal curves and yearly min/max dots.

            percentile_1090_glyph.visible = True
            percentile_2575_glyph.visible = True
            median_glyph.visible = True
            min_line_glyph.visible = True
            max_line_glyph.visible = True

            for i in range(3):
                curve_1980s_glyph_list[i].visible = False
                curve_1990s_glyph_list[i].visible = False
                curve_2000s_glyph_list[i].visible = False
                curve_2010s_glyph_list[i].visible = False

            yearly_min_glyph.visible = False
            yearly_max_glyph.visible = False

            for glyph in individual_years_glyphs:
                glyph.visible = False

            current_year_outline.visible = True
            current_year_filler.visible = True

            if area_selector.value in ("nh", "bar", "beau", "chuk", "ess", "fram", "kara", "lap", "sval"):
                # Show years 2012 and 2020 for the northern hemisphere.
                year_2012_index = list(data_years).index("2012")
                year_2020_index = list(data_years).index("2020")

                individual_years_glyphs[year_2012_index].visible = True
                individual_years_glyphs[year_2020_index].visible = True

            else:
                # Show years 2014 and 2022 for the southern hemisphere.
                year_2014_index = list(data_years).index("2014")
                year_2022_index = list(data_years).index("2022")

                individual_years_glyphs[year_2014_index].visible = True
                individual_years_glyphs[year_2022_index].visible = True


    # Make sure that callback code runs when user clicks on one of the choices.
    plot_shortcuts.param.watch(plot_shortcuts_callback, "clicked", onlychanged=False)

    # Create a callback to update the label text based on whether the climatology glyphs are visible, and also when
    # the reference period changes.
    def update_label_text(attr, old, new):
        new_label = ""
        if percentile_1090_glyph.visible:
            new_label += f"Median and percentiles (25-75% and 10-90%) for {reference_period_selector.value}"
        if min_line_glyph.visible:
            if percentile_1090_glyph.visible:
                new_label += f", min/max for {first_year}-{second_to_last_year}"
            else:
                new_label += f"Min/max for {first_year}-{second_to_last_year}"

        new_label += "\n"
        new_label += f"Data: Derived from OSI SAF Sea Ice Concentration CDRs {cdr_version}\n" \
                     "Source: EUMETSAT OSI SAF data with R&D input from ESA CCI\n" \
                     f"Last data point: {last_date_string}"

        info_label.text = new_label

    # Check whether a change in the visibility state of the median and percentiles, and the min/max values has taken
    # place and run the callback function if so.
    percentile_1090_glyph.on_change("visible", update_label_text)
    min_line_glyph.on_change("visible", update_label_text)

    # Define the layout.
    inputs = pn.Column(index_selector,
                       area_selector,
                       reference_period_selector,
                       plot_shortcuts,
                       zoom_shortcuts,
                       color_scale_selector)

    # Use a grid layout.
    gspec = pn.GridSpec(sizing_mode="stretch_both")


    def on_load():
        # Divide the layout into 5 columns. The plot uses 4 columns while the widgets get the last column.
        gspec[0, 0:4] = pn.pane.Bokeh(plot)
        gspec[0, 4] = inputs

    # There is currently a bug in Bokeh 3.1.1 where it incorrectly calculates the amount of available space. To work
    # around this we load the gridspec elements after the page has finished loading.
    pn.state.onload(on_load)


    def update_reference_period(event):
        with pn.param.set_values(final_pane, loading=True):
            # Function that is used to update the climatology when the reference period is changed.
            reference_period = event.new

            start_year = reference_period[:4]
            end_year = reference_period[5:]
            percentiles_and_median_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice(start_year,
                                                                                                      end_year)))

            cds_percentile_1090.data.update(percentiles_and_median_dict["cds_percentile_1090"].data)
            cds_percentile_2575.data.update(percentiles_and_median_dict["cds_percentile_2575"].data)
            cds_median.data.update(percentiles_and_median_dict["cds_median"].data)

            # Update the label text to display the new reference period.
            update_label_text(None, None, None)


    def update_data(event):
        with pn.param.set_values(final_pane, loading=True):
            # Try fetching new data because it might not be available.
            try:
                # Update plot with new values from selectors.
                version = VersionUrlParameter.value
                index = index_selector.value
                area = area_selector.value

                # Download and extract new data.
                extracted_data = tk.download_and_extract_data(index, area, "daily", version)
                da = extracted_data["da"]

                # Make sure da_converted is global because it's used by other callback functions.
                global da_converted
                # Convert calendar to all_leap and interpolate missing February 29th values.
                da_converted = tk.convert_and_interpolate_calendar(da)

                # Recalculate and update the climatology plots (percentiles and median).
                reference_period_selector.param.trigger("value")

                # Update min/max lines.
                min_max_dict = tk.calculate_min_max(da_converted)
                cds_minimum.data.update(min_max_dict["cds_minimum"].data)
                cds_maximum.data.update(min_max_dict["cds_maximum"].data)

                # Update decadal climatology.
                clim_1980s_dict = tk.calculate_span_and_median(da_converted.sel(time=slice("1978", "1989")))
                clim_1990s_dict = tk.calculate_span_and_median(da_converted.sel(time=slice("1990", "1999")))
                clim_2000s_dict = tk.calculate_span_and_median(da_converted.sel(time=slice("2000", "2009")))
                clim_2010s_dict = tk.calculate_span_and_median(da_converted.sel(time=slice("2010", "2019")))

                cds_span_1980s.data.update(clim_1980s_dict["cds_span"].data)
                cds_median_1980s.data.update(clim_1980s_dict["cds_median"].data)
                cds_span_1990s.data.update(clim_1990s_dict["cds_span"].data)
                cds_median_1990s.data.update(clim_1990s_dict["cds_median"].data)
                cds_span_2000s.data.update(clim_2000s_dict["cds_span"].data)
                cds_median_2000s.data.update(clim_2000s_dict["cds_median"].data)
                cds_span_2010s.data.update(clim_2010s_dict["cds_span"].data)
                cds_median_2010s.data.update(clim_2010s_dict["cds_median"].data)

                # Update the individual years.
                new_cds_individual_years = tk.calculate_individual_years(da, da_converted)
                for new_cds, old_cds in zip(new_cds_individual_years.values(), cds_individual_years.values()):
                    old_cds.data.update(new_cds.data)

                # Update the yearly min/max values.
                new_cds_yearly_max, new_cds_yearly_min = tk.find_yearly_min_max(da_converted, colors_dict)
                cds_yearly_max.data.update(new_cds_yearly_max.data)
                cds_yearly_min.data.update(new_cds_yearly_min.data)

                # Update the plot title and x-axis label.
                trimmed_title = tk.trim_title(extracted_data["title"])
                plot.title.text = trimmed_title
                plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

                # Find the day of year for the average minimum and maximum values. These are global variables because
                # they are used in other callbacks.
                global doy_minimum
                doy_minimum = da_converted.groupby("time.dayofyear").median().idxmin().values.astype(int)
                global doy_maximum
                doy_maximum = da_converted.groupby("time.dayofyear").median().idxmax().values.astype(int)

                # Update the zoom to the new data using the current zoom state.
                zoom_shortcuts.param.trigger("clicked")

            except OSError:
                # Raise an exception with a custom error message that will be displayed in error prompt for the user.
                raise ValueError("Data currently unavailable. Please try again later.")


    def update_zoom(event):
        # The callback function that updates the zoom level when the zoom shortcut is used.
        with pn.param.set_values(final_pane, loading=True):
            if event.new == 'year':
                plot.x_range.start = 1
                plot.x_range.end = 366
                plot.y_range.start = 0
                plot.y_range.end = tk.find_nice_ylimit(da_converted)

            elif event.new == 'current':
                # Plot two months around the latest datapoint. Make sure that the lower bound is not less 1st of Jan
                # and upper bound is not more than 31st of Dec.
                x_range_start = current_year_outline.data_source.data['day_of_year'][-1] - 30
                x_range_end = current_year_outline.data_source.data['day_of_year'][-1] + 30
                plot.x_range.start = (x_range_start if x_range_start > 1 else 1)
                plot.x_range.end = (x_range_end if x_range_end < 366 else 366)
                set_zoom_yrange(padding_frac=0.05)

            elif event.new == 'min_extent':
                # Plot two months around the day of year with the lowest average minimum value. Make sure that the
                # lower bound is not less 1st of Jan and upper bound is not more than 31st of Dec.
                plot.x_range.start = (doy_minimum - 30 if doy_minimum - 30 > 1 else 1)
                plot.x_range.end = (doy_minimum + 30 if doy_minimum + 30 < 366 else 366)
                set_zoom_yrange(padding_frac=0.05)

            elif event.new == 'max_extent':
                # Plot two months around the day of year with the highest average maximum value. Make sure that the
                # lower bound is not less 1st of Jan and upper bound is not more than 31st of Dec.
                plot.x_range.start = (doy_maximum - 30 if doy_maximum - 30 > 1 else 1)
                plot.x_range.end = (doy_maximum + 30 if doy_maximum + 30 < 366 else 366)
                set_zoom_yrange(padding_frac=0.05)


    def set_zoom_yrange(padding_frac):
        # Set the y-range between the minimum and maximum values plus a little padding.

        # Find the x-range.
        doy_start = plot.x_range.start
        doy_end = plot.x_range.end

        # Find the min and max values for each day of year.
        dayofyear_min_values = da_converted.groupby("time.dayofyear").min()
        dayofyear_max_values = da_converted.groupby("time.dayofyear").max()

        # Find the lowest min and highest max values inside the x-range displayed.
        data_min_value = dayofyear_min_values.sel(dayofyear=slice(doy_start, doy_end)).min().values
        data_max_value = dayofyear_max_values.sel(dayofyear=slice(doy_start, doy_end)).max().values

        # Sometimes the minimum and maximum values are the same. Account for this to always have some padding.
        if data_max_value - data_min_value < 1E-3:
            padding = data_max_value * padding_frac
        else:
            padding = (data_max_value - data_min_value) * padding_frac

        # Set the y-range.
        plot.y_range.start = (data_min_value - padding if data_min_value - padding > 0 else 0)
        plot.y_range.end = data_max_value + padding


    def update_line_color(event):
        # Function that updates the colors of glyphs.
        with pn.param.set_values(final_pane, loading=True):
            color = event.new
            data_years = list(cds_individual_years.keys())
            colors_dict = tk.find_line_colors(data_years[:-1], color)

            curve_1980s_glyph_list[0].glyph.fill_color = colors_dict["1984"]
            curve_1980s_glyph_list[2].glyph.line_color = colors_dict["1984"]
            curve_1990s_glyph_list[0].glyph.fill_color = colors_dict["1994"]
            curve_1990s_glyph_list[2].glyph.line_color = colors_dict["1994"]
            curve_2000s_glyph_list[0].glyph.fill_color = colors_dict["2004"]
            curve_2000s_glyph_list[2].glyph.line_color = colors_dict["2004"]
            curve_2010s_glyph_list[0].glyph.fill_color = colors_dict["2014"]
            curve_2010s_glyph_list[2].glyph.line_color = colors_dict["2014"]

            for year, individual_year_glyph in zip(data_years[:-1], individual_years_glyphs[:-1]):
                individual_year_glyph.glyph.line_color = colors_dict[year]

            new_cds_yearly_max, new_cds_yearly_min = tk.find_yearly_min_max(da_converted, colors_dict)
            cds_yearly_max.data.update(new_cds_yearly_max.data)
            cds_yearly_min.data.update(new_cds_yearly_min.data)

    # Run callbacks when widget values change.
    index_selector.param.watch(update_data, "value")
    area_selector.param.watch(update_data, "value")
    reference_period_selector.param.watch(update_reference_period, "value")
    zoom_shortcuts.param.watch(update_zoom, "clicked", onlychanged=False)
    color_scale_selector.param.watch(update_line_color, "value")

    final_pane = gspec.servable()

    # Make sure plot shortcut and zoom get set correctly if url parameters are provided.
    plot_shortcuts.param.trigger("clicked")
    zoom_shortcuts.param.trigger("clicked")

except OSError:
    # If the datafile is unavailable when the script starts display the message below instead of running the script.
    text = Paragraph(text="Sea ice data unavailable. Please try again in a few minutes.", style={"font-size": "30px"})

    bokeh_pane = pn.pane.Bokeh(text).servable()
