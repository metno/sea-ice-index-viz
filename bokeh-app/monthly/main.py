import panel as pn
from bokeh.plotting import figure
from bokeh.models import HoverTool, Range1d, Paragraph, Label
import logging
import param
import calendar
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import toolkit as tk  # noqa: E402


# Specify a loading spinner wheel to display when data is being loaded.
pn.extension(loading_spinner='dots', loading_color='#696969', sizing_mode="stretch_both")


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
index_selector = pn.widgets.Select(name="Index:", options={"Sea Ice Extent": "sie", "Sea Ice Area": "sia"}, value="sie")
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

area_selector = pn.widgets.Select(name="Area:", groups=area_groups, value="nh")
pn.state.location.sync(area_selector, {"value": "area"})

# Add a dropdown menu for selecting the month that will be plotted.
month_dict = {"January": 1,
              "February": 2,
              "March": 3,
              "April": 4,
              "May": 5,
              "June": 6,
              "July": 7,
              "August": 8,
              "September": 9,
              "October": 10,
              "November": 11,
              "December": 12}

month_selector = pn.widgets.Select(name="Month", options=month_dict, value=1)
pn.state.location.sync(month_selector, {"value": "month"})

# Add a dropdown menu for selecting the reference period of the percentile and median plots, and sync to url parameter.
reference_period_selector = pn.widgets.Select(name="Reference period of percentiles and median:",
                                              options=["1981-2010", "1991-2020"],
                                              value="1981-2010")
pn.state.location.sync(reference_period_selector, {"value": "ref_period"})

try:
    extracted_data = tk.download_and_extract_data(index_selector.value,
                                                  area_selector.value,
                                                  "monthly",
                                                  VersionUrlParameter.value)
    da = extracted_data["da"]

    plot = figure(title=extracted_data["title"], tools="pan, wheel_zoom, box_zoom, save")
    plot.sizing_mode = "stretch_both"

    cds_month = tk.calculate_monthly(da, month_selector.value)

    monthly_line = plot.line(x="year", y="index_values", source=cds_month, line_width=4, line_color="red")
    monthly_circles = plot.circle(x="year",
                                  y="index_values",
                                  source=cds_month,
                                  size=10,
                                  line_width=2,
                                  line_color="red",
                                  fill_color="white")

    cds_trend, abs_trend, rel_trend = tk.monthly_trend(da,
                                                       month_selector.value,
                                                       reference_period_selector.value)

    trend_line = plot.line(x="year", y="start_end_line", source=cds_trend, line_color="black", line_width=3)

    # Add a hovertool to display the date, index value, and rank of the individual years.
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

    plot.add_tools(HoverTool(renderers=[monthly_circles], tooltips=TOOLTIPS, toggleable=False))

    # Find the version of the data in order to add it to the label, and give the v3p0 data a custom label.
    if extracted_data["ds_version"] == "v2p1":
        version_label = extracted_data["ds_version"]
    elif extracted_data["ds_version"] == "v3p0":
        version_label = extracted_data["ds_version"] + " (test version)"

    label_text = f"{calendar.month_name[month_selector.value]} trend: {abs_trend:.0f} thousand km²/year\n" \
                 f"Relative trend: {rel_trend:.1f}%/decade against "\
                 f"reference period {reference_period_selector.value}\n" \
                 f"{version_label} EUMETSAT OSI SAF data with R&D input from ESA CCI\n" \
                 "Source: EUMETSAT OSI SAF (https://osi-saf.eumetsat.int)"

    info_label = Label(x=5,
                       y=5,
                       x_units='screen',
                       y_units='screen',
                       text=label_text,
                       text_font_size='12px',
                       text_color='black')

    plot.add_layout(info_label)

    # Use 0.5 * y-span of data to pad the data. For data with very small spans make sure that the y-span of the plot
    # is at least 0.1.
    padding_multiplier = 0.5
    min_span = 0.1

    y_min, y_max = tk.find_nice_yrange(cds_month.data["index_values"],
                                       cds_trend.data["start_end_line"],
                                       padding_multiplier,
                                       min_span)
    plot.y_range = Range1d(start=y_min, end=y_max)

    # Use a grid layout.
    gspec = pn.GridSpec(sizing_mode="stretch_both")

    inputs = pn.Column(index_selector,
                       area_selector,
                       month_selector,
                       reference_period_selector,
                       sizing_mode="stretch_both")

    # Divide the layout into two rows and 4 columns. The plot takes up 2 rows and 3 columns, while the input widgets
    # take up 1 row and 1 column.
    gspec[0:2, :3] = pn.pane.Bokeh(plot, sizing_mode="stretch_both")
    gspec[0, 4] = inputs


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

                new_cds_month = tk.calculate_monthly(da, month_selector.value)
                cds_month.data.update(new_cds_month.data)

                new_cds_trend, abs_trend, rel_trend = tk.monthly_trend(da,
                                                                       month_selector.value,
                                                                       reference_period_selector.value)

                cds_trend.data.update(new_cds_trend.data)

                y_min, y_max = tk.find_nice_yrange(cds_month.data["index_values"],
                                                   cds_trend.data["start_end_line"],
                                                   padding_multiplier,
                                                   min_span)

                plot.y_range.start = y_min
                plot.y_range.reset_start = y_min
                plot.y_range.end = y_max
                plot.y_range.reset_end = y_max

                # Update the plot title and x-axis label.
                plot.title.text = extracted_data["title"]
                plot.yaxis.axis_label = f"{extracted_data['long_name']} - {extracted_data['units']}"

                label_text = f"{calendar.month_name[month_selector.value]} trend: {abs_trend:.0f} thousand km²/year\n" \
                             f"Relative trend: {rel_trend:.1f}%/decade against " \
                             f"reference period {reference_period_selector.value}\n" \
                             f"{version_label} EUMETSAT OSI SAF data with R&D input from ESA CCI\n" \
                             "Source: EUMETSAT OSI SAF (https://osi-saf.eumetsat.int)"

                info_label.text = label_text

            except OSError:
                # Raise an exception with a custom error message that will be displayed in error prompt for the user.
                raise ValueError("Data currently unavailable. Please try again later.")

    # Run callbacks when widget values change.
    index_selector.param.watch(update_data, "value")
    area_selector.param.watch(update_data, "value")
    month_selector.param.watch(update_data, "value")
    reference_period_selector.param.watch(update_data, "value")

    gspec.servable()

except OSError:
    # If the datafile is unavailable when the script starts display the message below instead of running the script.
    text = Paragraph(text="Sea ice data unavailable. Please try again in a few minutes.", style={"font-size": "30px"})

    bokeh_pane = pn.pane.Bokeh(text).servable()
