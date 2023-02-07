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

area_options = {
    "Global": [
        ("GLOBAL", "Global"),
        ("NH", "Northern Hemisphere"),
        ("SH", "Southern Hemisphere"),
    ],
    "Northern Hemisphere Regions": [
        ("bar", "Barents Sea"),
        ("beau", "Beaufort Sea"),
        ("chuk", "Chukchi Sea"),
        ("ess", "East Siberian Sea"),
        ("fram", "Fram Strait-NP"),
        ("kara", "Kara Sea"),
        ("lap", "Laptev Sea"),
        ("sval", "Svalbard-NIS"),
    ],
    "Southern Hemisphere Regions": [
        ("bell", "Amundsen-Bellingshausen Sea"),
        ("indi", "Indian Ocean"),
        ("ross", "Ross Sea"),
        ("wedd", "Weddell Sea"),
        ("wpac", "Western Pacific Ocean"),
    ]
}

area_selector = Select(title="Area:", value="NH", options=area_options)

# Add a dropdown menu for selecting the reference period of the percentile and median plots.
reference_period_selector = Select(title="Reference period of percentiles and median:",
                                   value="1981-2010",
                                   options=[("1981-2010", "1981-2010"),
                                            ("1991-2020", "1991-2020")])

# Add a dropdown menu for different preselected zoom levels.
zoom_shortcuts = Dropdown(label="Zoom shortcuts:",
                          menu=[("Year", "year"),
                                ("Two months centred on latest observation", "zoom"),
                                ("Min extent", "min_extent"),
                                ("Max extent", "max_extent")])

# Add a dropdown menu for selecting the colorscale that will be used for plotting the individual years.
color_scale_selector = Select(title="Color scale of yearly data:",
                              value="viridis",
                              options=[("viridis", "Viridis"),
                                       ("plasma", "Plasma"),
                                       ("batlow", "Batlow"),
                                       ("batlowS", "BatlowS"),
                                       ("decadal", "Custom decadal")])

# Sometimes the data files are not available on the thredds server, so use try/except to check this.
try:
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

    percentiles_and_median_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice(start_year,
                                                                                                  end_year)))
    cds_percentile_1090 = percentiles_and_median_dict["cds_percentile_1090"]
    cds_percentile_2575 = percentiles_and_median_dict["cds_percentile_2575"]
    cds_median = percentiles_and_median_dict["cds_median"]

    min_max_dict = tk.calculate_min_max(da_converted)
    cds_minimum = min_max_dict["cds_minimum"]
    cds_maximum = min_max_dict["cds_maximum"]

    clim_1980s_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice("1978", "1989")),
                                                          percentile2575=False,
                                                          percentile1090=False,
                                                          percentile0100=True)
    clim_1990s_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice("1990", "1999")),
                                                          percentile2575=False,
                                                          percentile1090=False,
                                                          percentile0100=True)
    clim_2000s_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice("2000", "2009")),
                                                          percentile2575=False,
                                                          percentile1090=False,
                                                          percentile0100=True)
    clim_2010s_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice("2010", "2019")),
                                                          percentile2575=False,
                                                          percentile1090=False,
                                                          percentile0100=True)

    cds_percentile_1980s = clim_1980s_dict["cds_percentile_0100"]
    cds_median_1980s = clim_1980s_dict["cds_median"]
    cds_percentile_1990s = clim_1990s_dict["cds_percentile_0100"]
    cds_median_1990s = clim_1990s_dict["cds_median"]
    cds_percentile_2000s = clim_2000s_dict["cds_percentile_0100"]
    cds_median_2000s = clim_2000s_dict["cds_median"]
    cds_percentile_2010s = clim_2010s_dict["cds_percentile_0100"]
    cds_median_2010s = clim_2010s_dict["cds_median"]

    # Calculate index of individual years.
    data_years = tk.get_list_of_years(da)
    colours_dict = tk.find_line_colours(data_years, color_scale_selector.value)

    cds_individual_years = tk.calculate_individual_years(da, da_converted)

    cds_yearly_max, cds_yearly_min = tk.find_yearly_min_max(da_converted, colours_dict)

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

    # Plot the minimum and maximum values.
    minimum = plot.line(x="day_of_year",
                        y="minimum",
                        source=cds_minimum,
                        line_alpha=0.8,
                        color="black",
                        line_width=1.5,
                        line_dash=[4, 1])

    maximum = plot.line(x="day_of_year",
                        y="maximum",
                        source=cds_maximum,
                        line_alpha=0.8,
                        color="black",
                        line_width=1.5,
                        line_dash=[4, 1])

    # Plot decadal climatology.

    curve_1980s = tk.decadal_curves(plot,
                                    cds_percentile_1980s,
                                    cds_median_1980s,
                                    colours_dict["1984"],
                                    colours_dict["1984"])

    curve_1990s = tk.decadal_curves(plot,
                                    cds_percentile_1990s,
                                    cds_median_1990s,
                                    colours_dict["1994"],
                                    colours_dict["1994"])

    curve_2000s = tk.decadal_curves(plot,
                                    cds_percentile_2000s,
                                    cds_median_2000s,
                                    colours_dict["2004"],
                                    colours_dict["2004"])

    curve_2010s = tk.decadal_curves(plot,
                                    cds_percentile_2010s,
                                    cds_median_2010s,
                                    colours_dict["2014"],
                                    colours_dict["2014"])

    # Plot the individual years.
    data_years = tk.get_list_of_years(da)
    colours_dict = tk.find_line_colours(data_years[:-1], color_scale_selector.value)
    individual_years_glyphs = []
    individual_years_glyphs_legend_list = []
    cds_individual_years_list = list(cds_individual_years.values())

    # Plot lines for all years except current one.
    for year, cds_individual_year in zip(data_years[:-1], cds_individual_years_list[:-1]):
        line_glyph = plot.line(x="day_of_year",
                               y="index_values",
                               source=cds_individual_year,
                               line_width=2,
                               line_color=colours_dict[year])
        individual_years_glyphs.append(line_glyph)
        individual_years_glyphs_legend_list.append((year, [line_glyph]))

    yearly_max_glyph = plot.triangle(x="day_of_year",
                                     y="index_value",
                                     color="colour",
                                     size=6,
                                     source=cds_yearly_max,
                                     visible=False)

    yearly_min_glyph = plot.circle(x="day_of_year",
                                   y="index_value",
                                   color="colour",
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

    individual_years_glyphs.append(current_year_outline)

    # Add a hovertool to display the year, day of year, and index value of the individual years.
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
            <span style="font-size: 12px;">@rank</span>
        </div>
    </div>
    """

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
            <span style="font-size: 12px;">@rank</span>
        </div>
    </div>
    """

    plot.add_tools(HoverTool(renderers=[yearly_max_glyph], tooltips=MAX_TOOLTIPS))
    plot.add_tools(HoverTool(renderers=[yearly_min_glyph], tooltips=MIN_TOOLTIPS))

    # Add labels and glyphs to legend list to get the desired order.
    legend_list.append(("Climatology", [percentile_1090, percentile_2575, median]))
    legend_list.append(("Min/Max", [minimum, maximum]))
    legend_list.append(("Yearly min/max", [yearly_max_glyph, yearly_min_glyph]))
    legend_list.extend([("1980s", curve_1980s),
                        ("1990s", curve_1990s),
                        ("2000s", curve_2000s),
                        ("2010s", curve_2010s)])
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

    plot.add_tools(HoverTool(renderers=individual_years_glyphs, tooltips=TOOLTIPS))

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
    first_year = str(data_years[0])
    second_to_last_year = str(data_years[-2])
    last_date_string = str(da.time[-1].dt.strftime('%Y-%m-%d').values)

    label_text = f"Median and percentiles (25-75% and 10-90%) for {reference_period_selector.value}, " \
                 f"min/max for {first_year}-{second_to_last_year}\n" \
                 "v2p1 EUMETSAT OSI SAF data with R&D input from ESA CCI\n" \
                 "Source: EUMETSAT OSI SAF (https://osi-saf.eumetsat.int)\n" \
                 f"Last data point: {last_date_string}"

    info_label = Label(x=5,
                       y=5,
                       x_units='screen',
                       y_units='screen',
                       text=label_text,
                       text_font_size='12px',
                       text_color='black')

    plot.add_layout(info_label)

    # Create a dropdown button with plot shortcuts.
    menu = [("Erase all", "erase_all"),
            ("Show all", "show_all"),
            ("Last 5 years", "last_5_years"),
            ("2 years", "2_years")]

    plot_shortcuts = Dropdown(label="Plot shortcuts", menu=menu)

    def plot_shortcuts_callback(new_value):
        if new_value.item == "erase_all":
            # All glyphs will be hidden.
            percentile_1090.visible = False
            percentile_2575.visible = False
            median.visible = False
            minimum.visible = False
            maximum.visible = False

            for glyph in curve_1980s:
                glyph.visible = False
            for glyph in curve_1990s:
                glyph.visible = False
            for glyph in curve_2000s:
                glyph.visible = False
            for glyph in curve_2010s:
                glyph.visible = False

            for glyph in individual_years_glyphs:
                glyph.visible = False
            current_year_filler.visible = False

            yearly_min_glyph.visible = False
            yearly_max_glyph.visible = False

        if new_value.item == "show_all":
            # All glyphs except for the decadal curves will be visible.
            percentile_1090.visible = True
            percentile_2575.visible = True
            median.visible = True
            minimum.visible = True
            maximum.visible = True

            for glyph in curve_1980s:
                glyph.visible = False
            for glyph in curve_1990s:
                glyph.visible = False
            for glyph in curve_2000s:
                glyph.visible = False
            for glyph in curve_2010s:
                glyph.visible = False

            for glyph in individual_years_glyphs:
                glyph.visible = True
            current_year_filler.visible = True

            yearly_min_glyph.visible = True
            yearly_max_glyph.visible = True

        if new_value.item == "last_5_years":
            # Hide decadal curves and make sure the last 5 years a visible.
            for glyph in curve_1980s:
                glyph.visible = False
            for glyph in curve_1990s:
                glyph.visible = False
            for glyph in curve_2000s:
                glyph.visible = False
            for glyph in curve_2010s:
                glyph.visible = False

            for glyph in individual_years_glyphs[:-4]:
                glyph.visible = False
            for glyph in individual_years_glyphs[-5:]:
                glyph.visible = True
            current_year_filler.visible = True

        if new_value.item == "2_years":
            # Hide decadal curves and all individual years, and show 2 hemisphere-dependent years.
            for glyph in curve_1980s:
                glyph.visible = False
            for glyph in curve_1990s:
                glyph.visible = False
            for glyph in curve_2000s:
                glyph.visible = False
            for glyph in curve_2010s:
                glyph.visible = False
            for glyph in individual_years_glyphs:
                glyph.visible = False
            current_year_filler.visible = False

            if area_selector.value in ("NH", "bar", "beau", "chuk", "ess", "fram", "kara", "lap", "sval"):
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
    plot_shortcuts.on_click(plot_shortcuts_callback)

    label_callback = CustomJS(args=dict(info_label=info_label,
                                        refper=reference_period_selector,
                                        first_year=first_year,
                                        second_to_last_year=second_to_last_year,
                                        last_date_string=last_date_string,
                                        climatology=percentile_1090,
                                        min_max=minimum), code='''
    // initialise an empty string
    let label_text = ``;
    
    if (climatology.visible === true) {
        label_text = label_text
                     + `Median and percentiles (25-75% and 10-90%) for `
                     + `${refper.value.slice(0,4)}-${refper.value.slice(5)}`;

        if (min_max.visible === false) {
            // when the min/max lines are not visible add a newline
            label_text = label_text + `\n`;
        }
    }
            
    if (min_max.visible === true) {
        // the added string is different depending on whether the climatology glyphs are visible
        if (climatology.visible === true) {
            label_text = label_text + `, min/max for ${first_year}-${second_to_last_year}\n`;
        } else {
            label_text = label_text + `Min/max for ${first_year}-${second_to_last_year}\n`;
        }
    }
            
    label_text = label_text
                 + `v2p1 EUMETSAT OSI SAF data with R&D input from ESA CCI\n`
                 + `Source: EUMETSAT OSI SAF (https://osi-saf.eumetsat.int)\n`
                 + `Last data point: ${last_date_string}`;
    
    info_label.text = label_text
    ''')

    # Check whether a change in the visibility state of the median and percentiles, and the min/max values has taken
    # place
    percentile_1090.js_on_change("visible", label_callback)
    minimum.js_on_change("visible", label_callback)

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
            percentiles_and_median_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice(start_year,
                                                                                                          end_year)))
            cds_percentile_1090.data.update(percentiles_and_median_dict["cds_percentile_1090"].data)
            cds_percentile_2575.data.update(percentiles_and_median_dict["cds_percentile_2575"].data)
            cds_median.data.update(percentiles_and_median_dict["cds_median"].data)

            min_max_dict = tk.calculate_min_max(da_converted)
            cds_minimum.data.update(min_max_dict["cds_minimum"].data)
            cds_maximum.data.update(min_max_dict["cds_maximum"].data)

            clim_1980s_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice("1978", "1989")),
                                                                  percentile2575=False,
                                                                  percentile1090=False,
                                                                  percentile0100=True)
            clim_1990s_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice("1990", "1999")),
                                                                  percentile2575=False,
                                                                  percentile1090=False,
                                                                  percentile0100=True)
            clim_2000s_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice("2000", "2009")),
                                                                  percentile2575=False,
                                                                  percentile1090=False,
                                                                  percentile0100=True)
            clim_2010s_dict = tk.calculate_percentiles_and_median(da_converted.sel(time=slice("2010", "2019")),
                                                                  percentile2575=False,
                                                                  percentile1090=False,
                                                                  percentile0100=True)

            cds_percentile_1980s.data.update(clim_1980s_dict["cds_percentile_0100"].data)
            cds_median_1980s.data.update(clim_1980s_dict["cds_median"].data)
            cds_percentile_1990s.data.update(clim_1990s_dict["cds_percentile_0100"].data)
            cds_median_1990s.data.update(clim_1990s_dict["cds_median"].data)
            cds_percentile_2000s.data.update(clim_2000s_dict["cds_percentile_0100"].data)
            cds_median_2000s.data.update(clim_2000s_dict["cds_median"].data)
            cds_percentile_2010s.data.update(clim_2010s_dict["cds_percentile_0100"].data)
            cds_median_2010s.data.update(clim_2010s_dict["cds_median"].data)

            # Calculate new columndatasources for the individual years.
            new_cds_individual_years = tk.calculate_individual_years(da, da_converted)
            # Update the existing columndatasources with the new data.
            for new_cds, old_cds in zip(new_cds_individual_years.values(), cds_individual_years.values()):
                old_cds.data.update(new_cds.data)

            new_cds_yearly_max, new_cds_yearly_min = tk.find_yearly_min_max(da, colours_dict)
            cds_yearly_max.data.update(new_cds_yearly_max.data)
            cds_yearly_min.data.update(new_cds_yearly_min.data)

            # Update the zoom to the new data using the current zoom state.
            update_zoom(zoom_state)

            # Set plot attributes.
            plot.title.text = extracted_data["title"]
            plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

            # Find the day of year for the average minimum and maximum values.
            global doy_minimum
            doy_minimum = da_converted.groupby("time.dayofyear").mean().idxmin().values.astype(int)
            global doy_maximum
            doy_maximum = da_converted.groupby("time.dayofyear").mean().idxmax().values.astype(int)


    def update_zoom(new_zoom):
        with pn.param.set_values(bokeh_pane, loading=True):
            if new_zoom == 'year':
                plot.x_range.start = 1
                plot.x_range.end = 366
                plot.y_range.start = 0
                plot.y_range.end = tk.find_nice_ylimit(da_converted)

            elif new_zoom == 'zoom':
                # Plot two months around the latest datapoint. Make sure that the lower bound is not less 1st of Jan
                # and upper bound is not more than 31st of Dec.
                x_range_start = current_year_outline.data_source.data['day_of_year'][-1] - 30
                x_range_end = current_year_outline.data_source.data['day_of_year'][-1] + 30
                plot.x_range.start = (x_range_start if x_range_start > 1 else 1)
                plot.x_range.end = (x_range_end if x_range_end < 366 else 366)
                set_zoom_yrange(padding_frac=0.05)

            elif new_zoom == 'min_extent':
                # Plot two months around the day of year with the lowest average minimum value. Make sure that the
                # lower bound is not less 1st of Jan and upper bound is not more than 31st of Dec.
                plot.x_range.start = (doy_minimum - 30 if doy_minimum - 30 > 1 else 1)
                plot.x_range.end = (doy_minimum + 30 if doy_minimum + 30 < 366 else 366)
                set_zoom_yrange(padding_frac=0.05)

            elif new_zoom == 'max_extent':
                # Plot two months around the day of year with the highest average maximum value. Make sure that the
                # lower bound is not less 1st of Jan and upper bound is not more than 31st of Dec.
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


    def zoom_wrapper(event):
        # Wrap the zoom update function in order to use it with on_click from the Dropdown widget. Update the zoom state
        # value.
        global zoom_state
        zoom_state = event.item
        update_zoom(zoom_state)


    def update_line_colour(attr, old, new):
        with pn.param.set_values(bokeh_pane, loading=True):
            colour = color_scale_selector.value
            data_years = list(cds_individual_years.keys())
            colours_dict = tk.find_line_colours(data_years[:-1], colour)

            curve_1980s[0].glyph.fill_color = colours_dict["1984"]
            curve_1980s[2].glyph.line_color = colours_dict["1984"]
            curve_1990s[0].glyph.fill_color = colours_dict["1994"]
            curve_1990s[2].glyph.line_color = colours_dict["1994"]
            curve_2000s[0].glyph.fill_color = colours_dict["2004"]
            curve_2000s[2].glyph.line_color = colours_dict["2004"]
            curve_2010s[0].glyph.fill_color = colours_dict["2014"]
            curve_2010s[2].glyph.line_color = colours_dict["2014"]

            for year, individual_year_glyph in zip(data_years[:-1], individual_years_glyphs[:-1]):
                individual_year_glyph.glyph.line_color = colours_dict[year]

            new_cds_yearly_max, new_cds_yearly_min = tk.find_yearly_min_max(da_converted, colours_dict)
            cds_yearly_max.data.update(new_cds_yearly_max.data)
            cds_yearly_min.data.update(new_cds_yearly_min.data)


    # Initialise the zoom state.
    zoom_state = 'year'

    index_selector.on_change('value', update_data)
    area_selector.on_change('value', update_data)
    reference_period_selector.on_change('value', update_data)
    reference_period_selector.js_on_change('value', label_callback)
    zoom_shortcuts.on_click(zoom_wrapper)
    color_scale_selector.on_change('value', update_line_colour)

    bokeh_pane = pn.pane.Bokeh(column1).servable()

except OSError:
    text = Paragraph(text="Sea ice data unavailable. Please try again in a few minutes.", style={"font-size": "30px"})

    bokeh_pane = pn.pane.Bokeh(text).servable()
