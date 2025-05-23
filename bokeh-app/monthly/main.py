from bokeh.plotting import figure
from bokeh.models import Legend, HoverTool, CustomJSHover, Label
import panel as pn
import calendar
from datetime import datetime
import os

from toolkit import VisDataMonthly
from plot_tools import monthly_attrs

# Get the root directory of the app.
app_root = os.getenv('APP_ROOT')


def visualisation():
    pn.extension(loading_spinner='dots', loading_color='#696969', notifications=True)

    plot_type_selector = pn.widgets.Select(name='Plot type:',
                                           options={'Absolute values': 'abs', 'Anomalies': 'anom'},
                                           value='abs',
                                           sizing_mode='stretch_width')
    pn.state.location.sync(plot_type_selector, {'value': 'type'})

    index_selector = pn.widgets.Select(name='Index:',
                                       options={'Sea Ice Extent': 'sie', 'Sea Ice Area': 'sia'},
                                       value='sie',
                                       sizing_mode='stretch_width')
    pn.state.location.sync(index_selector, {'value': 'index'})

    area_groups = {
        'Global': {
            'Global': 'glb',
            'Northern Hemisphere': 'nh',
            'Southern Hemisphere': 'sh',
        },
        'Northern Hemisphere Regions': {
            'Baffin Bay and Labrador Seas': 'baffin',
            'Baltic Sea': 'baltic',
            'Barents Sea': 'barents',
            'Beaufort Sea': 'beaufort',
            'Bering Sea': 'bering',
            'Bohai and Yellow Seas': 'bohai',
            'Canadian Archipelago': 'canarch',
            'Central Arctic': 'centralarc',
            'Chukchi Sea': 'chukchi',
            'East Greenland Sea': 'greenland',
            'East Siberian Sea': 'ess',
            'Gulf of Alaska': 'alaska',
            'Gulf of St. Lawrence': 'lawrence',
            'Hudson Bay': 'hudson',
            'Kara Sea': 'kara',
            'Laptev Sea': 'laptev',
            'Sea of Japan': 'japan',
            'Sea of Okhotsk': 'okhotsk',
            'Svalbard': 'sval',
        },
        'Southern Hemisphere Regions': {
            'Amundsen-Bellingshausen Sea': 'bell',
            'Dronning Maud Land': 'drml',
            'Indian Ocean': 'indi',
            'Ross Sea': 'ross',
            'Troll Station': 'trol',
            'Weddell Sea': 'wedd',
            'Western Pacific Ocean': 'wpac',
        }
    }

    area_selector = pn.widgets.Select(name='Area:',
                                      groups=area_groups,
                                      value='nh',
                                      sizing_mode='stretch_width')
    pn.state.location.sync(area_selector, {'value': 'area'})

    reference_period_selector = pn.widgets.Select(name='Reference period (of anomalies and relative trends):',
                                                  options=['1981-2010', '1991-2020'],
                                                  value='1981-2010',
                                                  sizing_mode='stretch_width')
    pn.state.location.sync(reference_period_selector, {'value': 'ref'})

    color_groups = {
        'Sequential colour maps': {
            'Viridis': 'viridis',
            'Viridis (reversed)': 'viridis_r',
            'Plasma': 'plasma',
            'Plasma (reversed)': 'plasma_r',
            'Batlow': 'batlow',
            'Batlow (reversed)': 'batlow_r',
        },
        'Non-sequential colour maps': {
            'BatlowS': 'batlowS',
            '8 repeating colours': 'cyclic_8',
            '17 repeating colours': 'cyclic_17',
        }
    }

    cmap_selector = pn.widgets.Select(name='Colour map:',
                                      groups=color_groups,
                                      value='viridis',
                                      sizing_mode='stretch_width')
    pn.state.location.sync(cmap_selector, {'value': 'col'})

    trend_selector = pn.widgets.Select(name='Trend line:',
                                       options={'Full': 'full', 'Decadal': 'decadal'},
                                       value='full',
                                       sizing_mode='stretch_width')
    pn.state.location.sync(trend_selector, {'value': 'trend'})

    data = VisDataMonthly(plot_type_selector.value, index_selector.value, area_selector.value,
                          reference_period_selector.value, cmap_selector.value, False)

    title, ylabel, info_text = monthly_attrs(plot_type_selector.value, index_selector.value, area_selector.value,
                                             data.get_last_month())

    plot = figure(title=title, tools='pan, wheel_zoom, box_zoom, save, reset')
    plot.sizing_mode = 'stretch_both'
    plot.xaxis.axis_label = 'Year'
    plot.yaxis.axis_label = ylabel

    info_label = Label(x=5, y=5, x_units='screen', y_units='screen', text=info_text, text_font_size='12px',
                       text_color='black')
    plot.add_layout(info_label)

    legend_collection = []
    all_months_glyph = plot.line(x='year', y='value', source=data.cds_all, line_width=1.5, line_color='grey')
    all_months_glyph.visible = False
    legend_collection.append(('Monthly', [all_months_glyph]))

    current_month = datetime.now().month

    line_glyphs = []
    circle_glyphs = []
    trend_glyphs = []
    dec_trend_glyphs = []
    for month in range(1, 13):
        line_glyph = plot.line(x='x',
                               y='value',
                               source=data.cds_months[month],
                               line_width=2,
                               color=data.colours[month])

        line_glyphs.append(line_glyph)

        circle_glyph = plot.scatter(x='x',
                                    y='value',
                                    source=data.cds_months[month],
                                    size=10,
                                    line_width=2,
                                    color='colour')

        circle_glyphs.append(circle_glyph)

        trend_glyph = plot.line(x='year', y='value', source=data.cds_full_trends[month], line_width=3,
                                color=data.colours[month])
        trend_glyphs.append(trend_glyph)

        dec_trend_glyphs_ = []
        for dec, cds in data.cds_dec_trends[month].items():
            dec_trend_glyph = plot.line(x='year', y='value', source=cds, line_width=3, color=data.colours[month])
            dec_trend_glyphs_.append(dec_trend_glyph)

        dec_trend_glyphs.append(dec_trend_glyphs_)

        if trend_selector.value == 'full':
            legend_collection.append((calendar.month_name[month], [line_glyph, circle_glyph, trend_glyph]))
            if month == current_month:
                for dec_glyph in dec_trend_glyphs_:
                    dec_glyph.visible = False
        elif trend_selector.value == 'decadal':
            legend_collection.append((calendar.month_name[month], [line_glyph, circle_glyph] + dec_trend_glyphs_))
            if month == current_month:
                trend_glyph.visible = False

        if month != current_month:
            # Hide all months except the current one.
            line_glyph.visible = False
            circle_glyph.visible = False
            trend_glyph.visible = False
            for dec_glyph in dec_trend_glyphs_:
                dec_glyph.visible = False

    legend = Legend(items=legend_collection, location='top_center')
    legend.spacing = 1
    plot.add_layout(legend, 'right')
    plot.legend.click_policy = 'hide'

    # Function for custom formatting of rank values. If decimal is zero don't show it, otherwise show only one decimal.
    rank_custom = CustomJSHover(code="""
        if (Number.isInteger(value)) {
          return value.toFixed();
        } else {
          return value.toFixed(1);
        }
        """)

    tooltips = """
        <div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Date:</span>
                <span style="font-size: 12px;">@month @year</span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Index:</span>
                <span style="font-size: 12px;">@value{0.000}</span>
                <span style="font-size: 12px;">mill. km<sup>2</sup></span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Rank (@month):</span>
                <span style="font-size: 12px;">@rank{custom}</span>
            </div>
        </div>
        """

    if plot_type_selector.value == 'abs':
        circle_ht = HoverTool(renderers=circle_glyphs, tooltips=tooltips, formatters={'@rank': rank_custom},
                              visible=False)
    else:
        tt = tooltips.replace('0.000', '+0.000')
        circle_ht = HoverTool(renderers=circle_glyphs, tooltips=tt, formatters={'@rank': rank_custom}, visible=False)

    plot.add_tools(circle_ht)

    # Add a hovertool to display the absolute and relative trends for a given month together with the reference period.
    tooltips_abs = """
        <div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Month:</span>
                <span style="font-size: 12px;">@month</span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Absolute trend:</span>
                <span style="font-size: 12px;">@abs_trend{+0.0}</span>
                <span style="font-size: 12px;">thousand km<sup>2</sup> yr<sup>-1</sup></span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Relative trend:</span>
                <span style="font-size: 12px;">@rel_trend{+0.0}% decade<sup>-1</sup></span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Reference period:</span>
                <span style="font-size: 12px;">@ref_per</span>
            </div>
        </div>
        """

    tooltips_anom = """
        <div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Month:</span>
                <span style="font-size: 12px;">@month</span>
            </div>
            <div>
                <span style="font-size: 12px; font-weight: bold">Absolute trend:</span>
                <span style="font-size: 12px;">@abs_trend{+0.0}</span>
                <span style="font-size: 12px;">thousand km<sup>2</sup> yr<sup>-1</sup></span>
            </div>
        </div>
        """

    if plot_type_selector.value == 'abs':
        trend_ht = HoverTool(renderers=trend_glyphs, tooltips=tooltips_abs, visible=False)
    else:
        trend_ht = HoverTool(renderers=trend_glyphs, tooltips=tooltips_anom, visible=False)

    plot.add_tools(trend_ht)

    # Add a hovertool to display the absolute and relative trends for a given month together with the reference period.
    dec_trend_glyphs_flat = sum(dec_trend_glyphs, [])

    if plot_type_selector.value == 'abs':
        tt = tooltips_abs.replace('@month', '@month (@decade)')
        dec_trend_ht = HoverTool(renderers=dec_trend_glyphs_flat, tooltips=tt, visible=False)
    else:
        tt = tooltips_anom.replace('@month', '@month (@decade)')
        dec_trend_ht = HoverTool(renderers=dec_trend_glyphs_flat, tooltips=tt, visible=False)

    plot.add_tools(dec_trend_ht)

    # Use a grid layout.
    gspec = pn.GridSpec(sizing_mode='stretch_both')

    inputs = pn.Column(plot_type_selector,
                       index_selector,
                       area_selector,
                       reference_period_selector,
                       cmap_selector,
                       trend_selector)

    def update_data(event):
        with pn.param.set_values(gspec, loading=True):
            try:
                if all_months_glyph.visible:
                    data.update_data(plot_type_selector.value, index_selector.value, area_selector.value,
                                     reference_period_selector.value, True)
                else:
                    data.update_data(plot_type_selector.value, index_selector.value, area_selector.value,
                                     reference_period_selector.value, False)
            except OSError:
                pn.state.notifications.error(f'Unable to load data! Please try again later.', duration=5000)
            else:
                title, ylabel, info_text = monthly_attrs(plot_type_selector.value, index_selector.value,
                                                         area_selector.value, data.get_last_month())
                plot.title.text = title
                plot.yaxis.axis_label = ylabel
                info_label.text = info_text

                if plot_type_selector.value == 'abs':
                    circle_ht.tooltips = tooltips
                    trend_ht.tooltips = tooltips_abs
                    dec_trend_ht.tooltips = tooltips_abs.replace('@month', '@month (@decade)')
                else:
                    circle_ht.tooltips = tooltips.replace('0.000', '+0.000')
                    trend_ht.tooltips = tooltips_anom
                    dec_trend_ht.tooltips = tooltips_anom.replace('@month', '@month (@decade)')

    def update_color_map(event):
        with pn.param.set_values(gspec, loading=True):
            data.update_colour(cmap_selector.value)
            for line_glyph, trend_glyph, dec_trend_glyph, colour in zip(line_glyphs, trend_glyphs, dec_trend_glyphs,
                                                                        data.colours.values()):
                line_glyph.glyph.line_color = colour
                trend_glyph.glyph.line_color = colour

                for dec_glyph in dec_trend_glyph:
                    dec_glyph.glyph.line_color = colour

    def update_legend(event):
        with pn.param.set_values(gspec, loading=True):
            legend_collection = [('Monthly', [all_months_glyph])]

            if trend_selector.value == 'full':
                for i, month in enumerate(calendar.month_name[1:]):
                    legend_collection.append((month, [line_glyphs[i], circle_glyphs[i], trend_glyphs[i]]))

                    if dec_trend_glyphs[i][0].visible:
                        for one_decade_trend_line_glyph in dec_trend_glyphs[i]:
                            one_decade_trend_line_glyph.visible = False
                        trend_glyphs[i].visible = True

                legend.items = legend_collection

            elif trend_selector.value == 'decadal':
                for i, month in enumerate(calendar.month_name[1:]):
                    legend_collection.append((month, [line_glyphs[i], circle_glyphs[i]] + dec_trend_glyphs[i]))

                    if trend_glyphs[i].visible:
                        trend_glyphs[i].visible = False
                        for one_decade_trend_line_glyph in dec_trend_glyphs[i]:
                            one_decade_trend_line_glyph.visible = True

                legend.items = legend_collection

    def linking_callback(attr, old, new):
        """Create a wrapper function to use Bokeh callback functionality with a Panel callback function."""
        update_data(None)

    # Run callbacks when widget values change.
    plot_type_selector.param.watch(update_data, 'value')
    index_selector.param.watch(update_data, 'value')
    area_selector.param.watch(update_data, 'value')
    reference_period_selector.param.watch(update_data, 'value')
    cmap_selector.param.watch(update_color_map, 'value')
    trend_selector.param.watch(update_legend, 'value')

    # Update the plot so that the monthly data points and trend lines are plotted with a monthly offset whenever the
    # line that runs through all data points is visible.
    all_months_glyph.on_change('visible', linking_callback)

    # Divide the layout into 5 rows and 5 columns. The plot uses 5 rows and 4 columns,
    # the widgets get the last column and first 3 rows, and the logo gets the last 2 rows.
    gspec[0:5, 0:4] = pn.pane.Bokeh(plot)
    gspec[0:3, 4] = inputs
    gspec[3:5, 4] = pn.pane.PNG(f'{app_root}/assets/logo.png', sizing_mode='scale_both')

    gspec.servable()


try:
    visualisation()
except OSError:
    styles = {'background-color': '#F6F6F6', 'border': '2px solid black', 'border-radius': '5px', 'padding': '10px'}

    pane = pn.pane.HTML("""
        <!DOCTYPE html>
        <html lang="en">
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="X-UA-Compatible" content="ie=edge">
            <title>HTML 5 Boilerplate</title>
            <link rel="stylesheet" href="style.css">
          </head>
          <body>
            <h1>Unable to load data! Please try again later.</h1>
          </body>
        </html>
        """)

    pane.servable()
