from bokeh.models import HoverTool, CustomJSHover
from bokeh.plotting import figure
from xarray import DataArray


def monthly_attrs(index: str, area: str, last_month: str):
    index_name = {'sie': 'Sea Ice Extent', 'sia': 'Sea Ice Area'}
    area_name = {'glb': 'Global', 'nh': 'Northern Hemisphere', 'sh': 'Southern Hemisphere',
                 'baffin': 'Baffin Bay and Labrador Seas', 'baltic': 'Baltic Sea', 'barents': 'Barents Sea',
                 'beaufort': 'Beaufort Sea', 'bering': 'Bering Sea', 'bohai': 'Bohai and Yellow Seas',
                 'canarch': 'Canadian Archipelago', 'centralarc': 'Central Arctic', 'chukchi': 'Chukchi Sea',
                 'greenland': 'East Greenland Sea', 'ess': 'East Siberian Sea', 'alaska': 'Gulf of Alaska',
                 'lawrence': 'Gulf of St. Lawrence', 'hudson': 'Hudson Bay', 'kara': 'Kara Sea', 'laptev': 'Laptev Sea',
                 'japan': 'Sea of Japan', 'okhotsk': 'Sea of Okhotsk', 'sval': 'Svalbard',
                 'bell': 'Amundsen-Bellingshausen Sea', 'drml': 'Dronning Maud Land', 'indi': 'Indian Ocean',
                 'ross': 'Ross Sea', 'trol': 'Troll Station', 'wedd': 'Weddell Sea', 'wpac': 'Western Pacific Ocean'}

    title = f'Monthly Mean {index_name[index]} v3.0, {area_name[area]}'
    yaxis = f'{index_name[index]} [million km²]'
    label = 'Data: Derived from OSI SAF Sea Ice Concentration CDRs v3\n' \
            'Source: EUMETSAT OSI SAF data with R&D input from ESA CCI\n' \
            f'Last data point: {last_month}'

    return title, yaxis, label


def daily_attrs(anomaly: str, index: str, area: str, ref_per: str, last_date: str, pct_vis: bool, minmax_vis: bool,
                first_year: int, last_year: int):
    index_name = {'sie': 'Sea Ice Extent', 'sia': 'Sea Ice Area'}
    area_name = {'glb': 'Global', 'nh': 'Northern Hemisphere', 'sh': 'Southern Hemisphere',
                 'baffin': 'Baffin Bay and Labrador Seas', 'baltic': 'Baltic Sea', 'barents': 'Barents Sea',
                 'beaufort': 'Beaufort Sea', 'bering': 'Bering Sea', 'bohai': 'Bohai and Yellow Seas',
                 'canarch': 'Canadian Archipelago', 'centralarc': 'Central Arctic', 'chukchi': 'Chukchi Sea',
                 'greenland': 'East Greenland Sea', 'ess': 'East Siberian Sea', 'alaska': 'Gulf of Alaska',
                 'lawrence': 'Gulf of St. Lawrence', 'hudson': 'Hudson Bay', 'kara': 'Kara Sea', 'laptev': 'Laptev Sea',
                 'japan': 'Sea of Japan', 'okhotsk': 'Sea of Okhotsk', 'sval': 'Svalbard',
                 'bell': 'Amundsen-Bellingshausen Sea', 'drml': 'Dronning Maud Land', 'indi': 'Indian Ocean',
                 'ross': 'Ross Sea', 'trol': 'Troll Station', 'wedd': 'Weddell Sea', 'wpac': 'Western Pacific Ocean'}

    if anomaly == 'abs':
        title = f'Daily {index_name[index]} v3.0, {area_name[area]}'
        ylabel = f'{index_name[index]} [million km²]'
    else:
        title = f'Daily {index_name[index]} Anomaly v3.0, {area_name[area]}'
        ylabel = f'{index_name[index]} Anomaly [million km²]'

    if anomaly == 'abs':
        label = ''
    else:
        label = f'Anomalies calculated relative to mean of {ref_per}\n'

    if pct_vis:
        label += f'Median and percentiles (25-75% and 10-90%) for {ref_per}'
        if minmax_vis:
            label += f', min/max for {first_year}-{last_year - 1}\n'
        else:
            label += '\n'
    else:
        if minmax_vis:
            label += f'Min/max for {first_year}-{last_year - 1}\n'

    label += f'Data: Derived from OSI SAF Sea Ice Concentration CDRs v3\n' \
             'Source: EUMETSAT OSI SAF data with R&D input from ESA CCI\n' \
             f'Last data point: {last_date}'

    return title, ylabel, label


class Tooltips:
    def __init__(self, anom: str, yearly_glyphs: list, min_glyphs: list, max_glyphs: list) -> None:
        self.yearly = HoverTool(renderers=yearly_glyphs,
                                tooltips=self._yr_tooltips(self._value_fmt(anom)),
                                formatters={'@rank': self._rank_fmt()},
                                visible=False)
        self.min = HoverTool(renderers=min_glyphs,
                             tooltips=self.yr_min_tooltips(self._value_fmt(anom)),
                             formatters={'@rank': self._rank_fmt()},
                             visible=False)
        self.max = HoverTool(renderers=max_glyphs,
                             tooltips=self.yr_max_tooltips(self._value_fmt(anom)),
                             formatters={'@rank': self._rank_fmt()},
                             visible=False)

    def update(self, anom: str) -> None:
        self.yearly.update(tooltips=self._yr_tooltips(self._value_fmt(anom)))
        self.min.update(tooltips=self.yr_min_tooltips(self._value_fmt(anom)))
        self.max.update(tooltips=self.yr_max_tooltips(self._value_fmt(anom)))

    def _value_fmt(self, anom: str) -> str:
        if anom == 'abs':
            fmt = '0.000'
        else:
            fmt = '+0.000'

        return fmt

    def _yr_tooltips(self, fmt: str) -> str:
        tooltips = f"""
            <div>
                <div>
                    <span style="font-size: 12px; font-weight: bold">Date:</span>
                    <span style="font-size: 12px;">@date</span>
                </div>
                <div>
                    <span style="font-size: 12px; font-weight: bold">Index:</span>
                    <span style="font-size: 12px;">@value{{{fmt}}}</span>
                    <span style="font-size: 12px;">mill. km<sup>2</sup></span>
                </div>
                <div>
                    <span style="font-size: 12px; font-weight: bold">Rank:</span>
                    <span style="font-size: 12px;">@rank{{custom}}</span>
                </div>
            </div>
            """

        return tooltips

    def yr_min_tooltips(self, fmt: str) -> str:
        tooltips = f"""
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
                    <span style="font-size: 12px;">@value{{{fmt}}}</span>
                    <span style="font-size: 12px;">mill. km<sup>2</sup></span>
                </div>
                <div>
                    <span style="font-size: 12px; font-weight: bold">Rank:</span>
                    <span style="font-size: 12px;">@rank{{custom}}</span>
                </div>
            </div>
            """

        return tooltips

    def yr_max_tooltips(self, fmt: str) -> str:
        tooltips = f"""
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
                    <span style="font-size: 12px;">@value{{{fmt}}}</span>
                    <span style="font-size: 12px;">mill. km<sup>2</sup></span>
                </div>
                <div>
                    <span style="font-size: 12px; font-weight: bold">Rank:</span>
                    <span style="font-size: 12px;">@rank{{custom}}</span>
                </div>
            </div>
            """

        return tooltips

    def _rank_fmt(self) -> CustomJSHover:
        rank_fmt = CustomJSHover(code="""
        if (Number.isInteger(value)) {
          return value.toFixed();
        } else {
          return value.toFixed(1);
        }
        """)

        return rank_fmt


def set_zoom_yrange(plot: figure, da: DataArray, offset: float, anom: str, padding_frac: float = 0.05) -> None:
    # Set the y-range between the minimum and maximum values plus a little padding. Also account for the height
    # of the text label in the lower left corner by lowering the start value of the y-range accordingly.

    # Find the x-range.
    doy_start = plot.x_range.start
    doy_end = plot.x_range.end

    # Find the min and max values for each day of year.
    min_per_doy = da.groupby('time.dayofyear').min()
    max_per_doy = da.groupby('time.dayofyear').max()

    # Find the lowest min and highest max values inside the x-range displayed.
    visible_min = min_per_doy.sel(dayofyear=slice(doy_start, doy_end)).min().values
    visible_max = max_per_doy.sel(dayofyear=slice(doy_start, doy_end)).max().values

    label_fraction = offset / plot.inner_height

    if anom == 'abs':
        text_label_height = label_fraction * (visible_max - visible_min)
    else:
        # We use the absolute max value since anomalies are centred on y=0.
        visible_max = max(abs(visible_min), abs(visible_max))
        text_label_height = label_fraction * 2 * visible_max

    # Sometimes the minimum and maximum values are the same. Account for this to always have some padding.
    if visible_max - visible_min < 1E-3:
        padding = visible_max * padding_frac
    else:
        padding = (visible_max - visible_min) * padding_frac

    # Set the y-range.
    if anom == 'abs':
        plot.y_range.start = visible_min - (text_label_height + padding)
        plot.y_range.end = visible_max + padding
    else:
        plot.y_range.start = -(visible_max + text_label_height + padding)
        plot.y_range.end = visible_max + padding


def year_zoom(plot: figure, da: DataArray, offset: float, anom: str) -> None:
    plot.x_range.start = 1
    plot.x_range.end = 366
    set_zoom_yrange(plot, da, offset, anom)


def now_zoom(plot: figure, da: DataArray, offset: float, anom: str) -> None:
    last_doy = da.time.dt.dayofyear.values[-1]
    x_range_start = last_doy - 30
    x_range_end = last_doy + 30
    plot.x_range.start = (x_range_start if x_range_start > 1 else 1)
    plot.x_range.end = (x_range_end if x_range_end < 366 else 366)
    set_zoom_yrange(plot, da, offset, anom)


def min_zoom(plot: figure, da: DataArray, offset: float, anom: str) -> None:
    doy_min = da.groupby('time.dayofyear').median().idxmin().values.astype(int)
    plot.x_range.start = (doy_min - 30 if doy_min - 30 > 1 else 1)
    plot.x_range.end = (doy_min + 30 if doy_min + 30 < 366 else 366)
    set_zoom_yrange(plot, da, offset, anom)


def max_zoom(plot: figure, da: DataArray, offset: float, anom: str) -> None:
    doy_max = da.groupby('time.dayofyear').median().idxmax().values.astype(int)
    plot.x_range.start = (doy_max - 30 if doy_max - 30 > 1 else 1)
    plot.x_range.end = (doy_max + 30 if doy_max + 30 < 366 else 366)
    set_zoom_yrange(plot, da, offset, anom)
