import panel as pn
from bokeh.plotting import figure
from bokeh.models import HoverTool, Paragraph, Legend, Label
import logging
import param
import calendar
import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import toolkit as tk  # noqa: E402


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
    value = param.Parameter("v2p1")


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
        "Fram Strait-NP": "fram",
        "Kara Sea": "kara",
        "Laptev Sea": "lap",
        "Svalbard-NIS": "sval",
    },
    "Southern Hemisphere Regions": {
        "Amundsen-Bellingshausen Sea": "bell",
        "Indian Ocean": "indi",
        "Ross Sea": "ross",
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

# Add a dropdown menu for selecting the color map for plotting the individual months.
color_groups = {
    "Sequential colour maps": {
        "Viridis": "viridis",
        "Plasma": "plasma",
        "Batlow": "batlow",
    },
    "Non-sequential colour maps": {
        "BatlowS": "batlowS",
        "8 repeating colours": "cyclic_8",
        "17 repeating colours": "cyclic_17",
    }
}

color_scale_selector = pn.widgets.Select(name="Colour map:",
                                         groups=color_groups,
                                         value="viridis",
                                         sizing_mode="stretch_width")
pn.state.location.sync(color_scale_selector, {"value": "colour"})

trend_selector = pn.widgets.Select(name="Trend line:",
                                   options={"Full": "full", "Decadal": "decadal"},
                                   value="full",
                                   sizing_mode="stretch_width")
pn.state.location.sync(trend_selector, {"value": "trend"})

try:
    extracted_data = tk.download_and_extract_data(index_selector.value,
                                                  area_selector.value,
                                                  "monthly",
                                                  VersionUrlParameter.value)
    da = extracted_data["da"]

    # Trim the title to not contain a "Mean" substring, the version number, and to deduplicate "Sea" substrings.
    trimmed_title = tk.trim_title(extracted_data["title"])

    plot = figure(title=trimmed_title, tools="pan, wheel_zoom, box_zoom, save, reset")
    plot.sizing_mode = "stretch_both"

    legend_collection = []

    cds_all_months = tk.calculate_all_months(da)
    all_months_glyph = plot.line(x="x", y="index_values", source=cds_all_months, line_width=1.5, line_color="grey")
    all_months_glyph.visible = False
    legend_collection.append(("Monthly", [all_months_glyph]))

    colors_dict = tk.find_line_colors(calendar.month_name[1:], "viridis")
    cds_monthly_dict = tk.calculate_monthly(da, month_offset=False)
    reference_period_start = reference_period_selector.value[0:4]
    reference_period_end = reference_period_selector.value[5:9]
    trends = tk.Trends(da, reference_period_start, reference_period_end, False)
    cds_monthly_trend_dict = trends.calculate_monthly_trend()
    cds_decadal_trend_dict = trends.calculate_decadal_trend(edge_padding=0.1)

    current_month = datetime.now().strftime("%B")

    line_glyphs = []
    circle_glyphs = []
    trend_line_glyphs = []
    decade_trend_line_glyphs = []
    for month, cds_month in cds_monthly_dict.items():
        line_glyph = plot.line(x="x",
                               y="index_values",
                               source=cds_month,
                               line_width=2,
                               color=colors_dict[month])

        line_glyphs.append(line_glyph)

        circle_glyph = plot.circle(x="x",
                                   y="index_values",
                                   source=cds_month,
                                   size=10,
                                   line_width=2,
                                   color=colors_dict[month])

        circle_glyphs.append(circle_glyph)

        trend_line_glyph = plot.line(x="year",
                                     y="trend_line_values",
                                     source=cds_monthly_trend_dict[month],
                                     line_color=colors_dict[month],
                                     line_width=3)

        trend_line_glyphs.append(trend_line_glyph)

        decade_trend_glyphs_one_month = []
        for decadal_cds_unpacked in cds_decadal_trend_dict[month].values():
            decadal_trend_glyph = plot.line(x="year",
                                            y="trend_line_values",
                                            source=decadal_cds_unpacked,
                                            line_color=colors_dict[month],
                                            line_width=3)
            decade_trend_glyphs_one_month.append(decadal_trend_glyph)

        decade_trend_line_glyphs.append(decade_trend_glyphs_one_month)

        if trend_selector.value == "full":
            legend_collection.append((month, [line_glyph, circle_glyph, trend_line_glyph]))
            if month == current_month:
                for one_decade_glyph in decade_trend_glyphs_one_month:
                    one_decade_glyph.visible = False
        elif trend_selector.value == "decadal":
            legend_collection.append((month, [line_glyph, circle_glyph] + decade_trend_glyphs_one_month))
            if month == current_month:
                trend_line_glyph.visible = False

        if month != current_month:
            # Hide all months except the current one.
            line_glyph.visible = False
            circle_glyph.visible = False
            trend_line_glyph.visible = False
            for one_decade_glyph in decade_trend_glyphs_one_month:
                one_decade_glyph.visible = False

    legend = Legend(items=legend_collection, location="top_center")
    legend.spacing = 1
    plot.add_layout(legend, "right")
    plot.legend.click_policy = "hide"

    # Add axis labels.
    plot.xaxis.axis_label = "Year"
    plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

    # Add a hovertool to display the date, index value, and rank of the individual years.
    TOOLTIPS = """
        <div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Date:</span>
                <span style="font-size: 12px;">@month @year</span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Index:</span>
                <span style="font-size: 12px;">@index_values{0.000}</span>
                <span style="font-size: 12px;">mill. km<sup>2</sup></span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Rank (@month):</span>
                <span style="font-size: 12px;">@rank</span>
            </div>
        </div>
        """

    plot.add_tools(HoverTool(renderers=circle_glyphs, tooltips=TOOLTIPS, toggleable=False))

    # Add a hovertool to display the absolute and relative trends for a given month together with the reference period.
    TOOLTIPS = """
            <div>
                <div>
                    <span style="font-size: 12px; font-weight: bold">Month:</span>
                    <span style="font-size: 12px;">@month</span>
                </div>
                <div>
                    <span style="font-size: 12px; font-weight: bold">Absolute trend:</span>
                    <span style="font-size: 12px;">@absolute_trend{+0.0}</span>
                    <span style="font-size: 12px;">thousand km<sup>2</sup> yr<sup>-1</sup></span>
                </div>
                <div>
                    <span style="font-size: 12px; font-weight: bold">Relative trend:</span>
                    <span style="font-size: 12px;">@relative_trend{+0.0}% decade<sup>-1</sup></span>
                </div>
                <div>
                    <span style="font-size: 12px; font-weight: bold">Reference period:</span>
                    <span style="font-size: 12px;">@reference_period</span>
                </div>
            </div>
            """

    plot.add_tools(HoverTool(renderers=trend_line_glyphs, tooltips=TOOLTIPS, toggleable=False))

    # Add a hovertool to display the absolute and relative trends for a given month together with the reference period.
    TOOLTIPS = """
                <div>
                    <div>
                        <span style="font-size: 12px; font-weight: bold">Month:</span>
                        <span style="font-size: 12px;">@month (@decade)</span>
                    </div>
                    <div>
                        <span style="font-size: 12px; font-weight: bold">Absolute trend:</span>
                        <span style="font-size: 12px;">@absolute_trend{+0.0}</span>
                        <span style="font-size: 12px;">thousand km<sup>2</sup> yr<sup>-1</sup></span>
                    </div>
                    <div>
                        <span style="font-size: 12px; font-weight: bold">Relative trend:</span>
                        <span style="font-size: 12px;">@relative_trend{+0.0}% decade<sup>-1</sup></span>
                    </div>
                    <div>
                        <span style="font-size: 12px; font-weight: bold">Reference period:</span>
                        <span style="font-size: 12px;">@reference_period</span>
                    </div>
                </div>
                """

    decade_trend_glyphs_flattened = sum(decade_trend_line_glyphs, [])
    plot.add_tools(HoverTool(renderers=decade_trend_glyphs_flattened, tooltips=TOOLTIPS, toggleable=False))

    if extracted_data["ds_version"] == "v2p1":
        version_label = "v2.1"
    elif extracted_data["ds_version"] == "v3p0":
        version_label = "v3.0 (test version)"

    last_month_string = str(da.time[-1].dt.strftime('%Y-%m').values)

    label_text = f"{version_label} EUMETSAT OSI SAF data with R&D input from ESA CCI\n" \
                 "Source: EUMETSAT OSI SAF (https://osi-saf.eumetsat.int)\n" \
                 f"Latest monthly data: {last_month_string}"

    info_label = Label(x=5,
                       y=5,
                       x_units='screen',
                       y_units='screen',
                       text=label_text,
                       text_font_size='12px',
                       text_color='black')

    plot.add_layout(info_label)

    # Use a grid layout.
    gspec = pn.GridSpec(sizing_mode="stretch_both")

    inputs = pn.Column(index_selector,
                       area_selector,
                       reference_period_selector,
                       color_scale_selector,
                       trend_selector)


    def on_load():
        # Divide the layout into 5 columns. The plot uses 4 columns while the widgets get the last column.
        gspec[0, 0:4] = pn.pane.Bokeh(plot, sizing_mode="stretch_both")
        gspec[0, 4] = inputs

    # There is currently a bug in Bokeh 3.1.1 where it incorrectly calculates the amount of available space. To work
    # around this we load the gridspec elements after the page has finished loading.
    pn.state.onload(on_load)


    def update_data(event):
        with pn.param.set_values(gspec, loading=True):
            # Try fetching new data because it might not be available.
            try:
                # Update plot with new values from selectors.
                index = index_selector.value
                area = area_selector.value
                version = VersionUrlParameter.value

                # Download and extract new data.
                extracted_data = tk.download_and_extract_data(index, area, "monthly", version)
                da = extracted_data["da"]

                new_cds_line_all_data = tk.calculate_all_months(da)
                cds_all_months.data.update(new_cds_line_all_data.data)

                if all_months_glyph.visible:
                    month_offset = True
                else:
                    month_offset = False

                new_cds_monthly_dict = tk.calculate_monthly(da, month_offset)
                reference_period_start = reference_period_selector.value[0:4]
                reference_period_end = reference_period_selector.value[5:9]
                trends = tk.Trends(da, reference_period_start, reference_period_end, month_offset)
                new_cds_monthly_trend_dict = trends.calculate_monthly_trend()
                new_cds_decadal_trend_dict = trends.calculate_decadal_trend(edge_padding=0.1)

                for month, new_cds_month in new_cds_monthly_dict.items():
                    cds_monthly_dict[month].data.update(new_cds_month.data)
                    cds_monthly_trend_dict[month].data.update(new_cds_monthly_trend_dict[month].data)
                    for decadal_cds_unpacked, new_decadal_cds_unpacked in zip(cds_decadal_trend_dict[month].values(),
                                                                              new_cds_decadal_trend_dict[month].values()):
                        decadal_cds_unpacked.data.update(new_decadal_cds_unpacked.data)

                # Update the plot title and x-axis label.
                trimmed_title = tk.trim_title(extracted_data["title"])
                plot.title.text = trimmed_title
                plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

                last_month_string = str(da.time[-1].dt.strftime('%Y-%m').values)
                label_text = f"{version_label} EUMETSAT OSI SAF data with R&D input from ESA CCI\n" \
                             "Source: EUMETSAT OSI SAF (https://osi-saf.eumetsat.int)\n" \
                             f"Latest monthly data: {last_month_string}"
                info_label.text = label_text

            except OSError:
                # Raise an exception with a custom error message that will be displayed in error prompt for the user.
                raise ValueError("Data currently unavailable. Please try again later.")


    def update_color_map(event):
        with pn.param.set_values(gspec, loading=True):
            colors_dict = tk.find_line_colors(calendar.month_name[1:], color_scale_selector.value)
            for line_glyph, circle_glyph, trend_line_glyph, decade_trend_glyphs_one_month, color in zip(line_glyphs,
                                                                                                        circle_glyphs,
                                                                                                        trend_line_glyphs,
                                                                                                        decade_trend_line_glyphs,
                                                                                                        colors_dict.values()):
                line_glyph.glyph.line_color = color
                circle_glyph.glyph.fill_color = color
                circle_glyph.glyph.line_color = color
                trend_line_glyph.glyph.line_color = color
                for decade_trend_glyph in decade_trend_glyphs_one_month:
                    decade_trend_glyph.glyph.line_color = color


    def update_legend(event):
        with pn.param.set_values(gspec, loading=True):
            legend_collection = [("Monthly", [all_months_glyph])]

            if trend_selector.value == "full":
                for i, month in enumerate(calendar.month_name[1:]):
                    legend_collection.append((month, [line_glyphs[i], circle_glyphs[i], trend_line_glyphs[i]]))

                    if decade_trend_line_glyphs[i][0].visible:
                        for one_decade_trend_line_glyph in decade_trend_line_glyphs[i]:
                            one_decade_trend_line_glyph.visible = False
                        trend_line_glyphs[i].visible = True

                legend.items = legend_collection

            elif trend_selector.value == "decadal":
                for i, month in enumerate(calendar.month_name[1:]):
                    legend_collection.append((month, [line_glyphs[i], circle_glyphs[i]] + decade_trend_line_glyphs[i]))

                    if trend_line_glyphs[i].visible:
                        trend_line_glyphs[i].visible = False
                        for one_decade_trend_line_glyph in decade_trend_line_glyphs[i]:
                            one_decade_trend_line_glyph.visible = True

                legend.items = legend_collection


    def linking_callback(attr, old, new):
        """Create a wrapper function to use Bokeh callback functionality with a Panel callback function."""
        update_data(None)

    # Run callbacks when widget values change.
    index_selector.param.watch(update_data, "value")
    area_selector.param.watch(update_data, "value")
    reference_period_selector.param.watch(update_data, "value")
    color_scale_selector.param.watch(update_color_map, "value")
    trend_selector.param.watch(update_legend, "value")

    # Update the plot so that the monthly data points and trend lines are plotted with a monthly offset whenever the
    # line that runs through all data points is visible.
    all_months_glyph.on_change("visible", linking_callback)

    gspec.servable()

except OSError:
    # If the datafile is unavailable when the script starts display the message below instead of running the script.
    text = Paragraph(text="Sea ice data unavailable. Please try again in a few minutes.", style={"font-size": "30px"})

    bokeh_pane = pn.pane.Bokeh(text).servable()
