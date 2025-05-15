from bokeh.plotting import figure
from bokeh.core.properties import value
from bokeh.events import DocumentReady
from bokeh.models import Legend, Label, Range1d, AdaptiveTicker
from bokeh.io import curdoc
import panel as pn
import os

from toolbox import VisDataDaily
from plot_tools import daily_attrs, Tooltips, year_zoom, now_zoom, min_zoom, max_zoom

# Get the root directory of the app.
app_root = os.getenv('APP_ROOT')


def visualisation():
    pn.extension(loading_spinner='dots', loading_color='#696969', notifications=True)

    # Add dropdown menu for plot type selection, and sync to url parameter.
    plot_type_selector = pn.widgets.Select(name='Plot type:',
                                           options={'Absolute values': 'abs', 'Anomalies': 'anom'},
                                           value='abs',
                                           sizing_mode='stretch_width')
    pn.state.location.sync(plot_type_selector, {'value': 'type'})

    # Add dropdown menu for index selection, and sync to url parameter.
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

    reference_period_selector = pn.widgets.Select(name='Reference period of percentiles and median:',
                                                  options=['1981-2010', '1991-2020'],
                                                  value='1981-2010',
                                                  sizing_mode='stretch_width')
    pn.state.location.sync(reference_period_selector, {'value': 'ref'})

    plot_shortcuts = pn.widgets.MenuButton(name='Plot shortcuts',
                                           items=[('Erase all', 'erase_all'),
                                                  ('Show all', 'show_all'),
                                                  ('Last 5 years', 'last_5_years'),
                                                  ('2 years', '2_years')],
                                           sizing_mode='stretch_width')
    pn.state.location.sync(plot_shortcuts, {'clicked': 'shortcut'})

    zoom_shortcuts = pn.widgets.MenuButton(name='Zoom shortcuts:',
                                           items=[('Year', 'year'),
                                                  ('Two months centred on latest observation', 'now'),
                                                  ('Min extent', 'min'),
                                                  ('Max extent', 'max')],
                                           sizing_mode='stretch_width')
    zoom_shortcuts.clicked = 'year'
    pn.state.location.sync(zoom_shortcuts, {'clicked': 'zoom'})

    colour_groups = {
        'Sequential colour maps': {
            'Viridis': 'viridis',
            'Viridis (reversed)': 'viridis_r',
            'Plasma': 'plasma',
            'Plasma (reversed)': 'plasma_r',
            'Batlow': 'batlow',
            'Batlow (reversed)': 'batlow_r',
            'Custom decadal': 'decadal',
        },
        'Non-sequential colour maps': {
            'BatlowS': 'batlowS',
            '8 repeating colours': 'cyclic_8',
            '17 repeating colours': 'cyclic_17',
        }
    }

    cmap_selector = pn.widgets.Select(name='Colour map:',
                                      groups=colour_groups,
                                      value='viridis',
                                      sizing_mode='stretch_width')
    pn.state.location.sync(cmap_selector, {'value': 'col'})

    data = VisDataDaily(plot_type_selector.value, index_selector.value, area_selector.value,
                        reference_period_selector.value, cmap_selector.value)

    first_year = int(data.ds_daily.time[0].dt.year.values)
    last_year = int(data.ds_daily.time[-1].dt.year.values)
    title, ylabel, info_text = daily_attrs(plot_type_selector.value, index_selector.value, area_selector.value,
                                           reference_period_selector.value, data.get_last_day(), True, True,
                                           first_year, last_year)

    plot = figure(title=title, tools='pan, wheel_zoom, box_zoom, save')
    plot.sizing_mode = 'stretch_both'

    plot.xaxis.axis_label = 'Date'
    plot.yaxis.axis_label = ylabel
    plot.x_range = Range1d(start=1, end=366)
    x_ticks = {1: '1 Jan', 32: '1 Feb', 61: '1 Mar', 92: '1 Apr', 122: '1 May', 153: '1 Jun', 183: '1 Jul', 214: '1 Aug',
               245: '1 Sep', 275: '1 Oct', 306: '1 Nov', 336: '1 Dec', 366: '31 Dec'}
    plot.xaxis.ticker = list(x_ticks.keys())
    plot.xaxis.major_label_overrides = x_ticks
    plot.y_range = Range1d()
    plot.yaxis.ticker = AdaptiveTicker(base=10, mantissas=[1, 2], num_minor_ticks=4, desired_num_ticks=10)

    info_label = Label(x=5, y=5, x_units='screen', y_units='screen', text=info_text, text_font_size='12px',
                       text_color='black')
    plot.add_layout(info_label)

    plot.hspan(y=0, line_color='#d0d0d0', line_dash=value([10, 10]), line_width=3)

    p10_90 = plot.varea(x='doy', y1='p10', y2='p90', source=data.cds_p10_90, fill_alpha=0.6, fill_color='darkgray')
    p25_75 = plot.varea(x='doy', y1='p25', y2='p75', source=data.cds_p25_75, fill_alpha=0.6, fill_color='gray')
    med = plot.line(x='doy', y='value', source=data.cds_median, line_width=2, color='dimgray', alpha=0.6)

    min_line = plot.line(x='doy', y='value', source=data.cds_min, line_alpha=0.8, color='black', line_width=1.5,
                         line_dash=[4, 1])
    max_line = plot.line(x='doy', y='value', source=data.cds_max, line_alpha=0.8, color='black', line_width=1.5,
                         line_dash=[4, 1])

    decades = []
    for decade, [cds_span, cds_median] in data.cds_decades.items():
        middle_year = str(int(decade[:4]) + 4)
        colour = data.colours[cmap_selector.value][middle_year]

        span = plot.varea(x='doy', y1='min', y2='max', source=cds_span, fill_alpha=0.5, fill_color=colour, visible=False)
        outer = plot.line(x='doy', y='value', source=cds_median, line_width=2.2, color='black', alpha=0.6, visible=False)
        inner = plot.line(x='doy', y='value', source=cds_median, line_width=2, color=colour, alpha=0.6, visible=False)

        decades.append((f'{decade[:4]}s', [span, outer, inner]))

    years = list(data.cds_yearly.keys())
    cds_yearly = list(data.cds_yearly.values())
    yearly = []
    for year, cds_year in zip(years[:-1], cds_yearly[:-1]):
        colour = data.colours[cmap_selector.value][year]
        one_year = plot.line(x='doy', y='value', source=cds_year, line_width=2, line_color=colour)
        yearly.append((year, [one_year]))

    yearly_min = plot.scatter(x='doy', y='value', color='colour', size=6, source=data.cds_yearly_min, visible=False)
    yearly_max = plot.scatter(x='doy', y='value', color='colour', size=6, source=data.cds_yearly_max, visible=False)

    last_year_outline = plot.line(x='doy', y='value', source=cds_yearly[-1], line_width=2, line_color='black',
                                  name='yearly')
    last_year_inner = plot.line(x='doy', y='value', source=cds_yearly[-1], line_width=2, line_dash=[4, 4],
                                line_color='white')

    legend_list = [('Climatology', [p10_90, p25_75, med]),
                   ('Min/max', [min_line, max_line]),
                   ('Yearly min/max', [yearly_min, yearly_max])]
    legend_list.extend(decades)
    legend_list.extend(yearly)
    legend_list.append((years[-1], [last_year_outline, last_year_inner]))

    n = 23
    legend_split = [legend_list[i:i + n] for i in range(0, len(legend_list), n)]

    for sublist in legend_split:
        legend = Legend(items=sublist, location='top_center')
        legend.spacing = 1
        plot.add_layout(legend, 'right')

    plot.legend.click_policy = 'hide'

    all_yearly_glyphs = [glyph[0] for year, glyph in yearly] + [last_year_outline]
    tooltips = Tooltips(plot_type_selector.value, all_yearly_glyphs, [yearly_min], [yearly_max])
    plot.add_tools(tooltips.yearly)
    plot.add_tools(tooltips.min)
    plot.add_tools(tooltips.max)

    def update_attrs(attr, old, new):
        first_year = int(data.ds_daily.time[0].dt.year.values)
        last_year = int(data.ds_daily.time[-1].dt.year.values)
        title, ylabel, info_text = daily_attrs(plot_type_selector.value, index_selector.value, area_selector.value,
                                               reference_period_selector.value, data.get_last_day(), p10_90.visible,
                                               min_line.visible, first_year, last_year)
        plot.title.text = title
        plot.yaxis.axis_label = ylabel
        info_label.text = info_text

    p10_90.on_change('visible', update_attrs)
    min_line.on_change('visible', update_attrs)

    def update_data(event):
        with pn.param.set_values(gspec, loading=True):
            try:
                data.update_data(plot_type_selector.value, index_selector.value, area_selector.value,
                                 reference_period_selector.value, cmap_selector.value)
            except OSError:
                pn.state.notifications.error(f'Unable to load data! Please try again later.', duration=5000)
            else:
                update_attrs(None, None, None)
                tooltips.update(plot_type_selector.value)

                zoom_shortcuts.param.trigger('clicked')

    def update_colour(event):
        with pn.param.set_values(gspec, loading=True):
            cmap = data.colours[cmap_selector.value]

            for decade, glyphs in decades:
                middle_year = str(int(decade[:4]) + 4)
                glyphs[0].glyph.fill_color = cmap[middle_year]
                glyphs[2].glyph.line_color = cmap[middle_year]

            for year, glyph in yearly:
                glyph[0].glyph.line_color = cmap[year]

            data.update_colour(cmap_selector.value)

    number_of_lines = 6
    label_height = float(info_label.text_font_size.rstrip('px')) * info_label.text_line_height * number_of_lines

    def shortcuts_callback(event):
        with pn.param.set_values(gspec, loading=True):
            if event.new == 'erase_all':
                p10_90.visible = False
                p25_75.visible = False
                med.visible = False
                min_line.visible = False
                max_line.visible = False

                for decade in decades:
                    for glyph in decade[1]:
                        glyph.visible = False

                for year in yearly:
                    year[1][0].visible = False

                last_year_outline.visible = False
                last_year_inner.visible = False

                yearly_min.visible = False
                yearly_max.visible = False

            elif event.new == 'show_all':
                p10_90.visible = True
                p25_75.visible = True
                med.visible = True
                min_line.visible = True
                max_line.visible = True

                for decade in decades:
                    for glyph in decade[1]:
                        glyph.visible = True

                for year in yearly:
                    year[1][0].visible = True

                last_year_outline.visible = True
                last_year_inner.visible = True

                yearly_min.visible = True
                yearly_max.visible = True

            elif event.new == 'last_5_years':
                p10_90.visible = True
                p25_75.visible = True
                med.visible = True
                min_line.visible = True
                max_line.visible = True

                for decade in decades:
                    for glyph in decade[1]:
                        glyph.visible = False

                yearly_min.visible = False
                yearly_max.visible = False

                for year in yearly[:-5]:
                    year[1][0].visible = False
                for year in yearly[-5:]:
                    year[1][0].visible = True

                last_year_outline.visible = True
                last_year_inner.visible = True

            else:
                p10_90.visible = True
                p25_75.visible = True
                med.visible = True
                min_line.visible = True
                max_line.visible = True

                for decade in decades:
                    for glyph in decade[1]:
                        glyph.visible = False

                yearly_min.visible = False
                yearly_max.visible = False

                last_year_outline.visible = True
                last_year_inner.visible = True

                if area_selector.value in ('nh', 'baffin', 'baltic', 'barents', 'beaufort', 'bering', 'bohai', 'canarch',
                                           'centralarc', 'chukchi', 'greenland', 'ess', 'alaska', 'lawrence', 'hudson',
                                           'kara', 'laptev', 'japan', 'okhotsk', 'sval'):
                    for year in yearly:
                        if year[0] in ['2012', '2020']:
                            year[1][0].visible = True
                        else:
                            year[1][0].visible = False
                else:
                    for year in yearly:
                        if year[0] in ['2014', '2022']:
                            year[1][0].visible = True
                        else:
                            year[1][0].visible = False

    def update_zoom(event):
        with pn.param.set_values(gspec, loading=True):
            da = data.ds_daily[index_selector.value]
            if event.new == 'year':
                year_zoom(plot, da, label_height, plot_type_selector.value)
            elif event.new == 'now':
                now_zoom(plot, da, label_height, plot_type_selector.value)
            elif event.new == 'min':
                min_zoom(plot, da, label_height, plot_type_selector.value)
            else:
                max_zoom(plot, da, label_height, plot_type_selector.value)

    inputs = pn.Column(plot_type_selector,
                       index_selector,
                       area_selector,
                       reference_period_selector,
                       plot_shortcuts,
                       zoom_shortcuts,
                       cmap_selector)

    gspec = pn.GridSpec(sizing_mode='stretch_both')
    gspec[0:5, 0:4] = pn.pane.Bokeh(plot)
    gspec[0:3, 4] = inputs
    gspec[3:5, 4] = pn.pane.PNG(f'{app_root}/assets/logo.png', sizing_mode='scale_both')

    plot_type_selector.param.watch(update_data, 'value')
    index_selector.param.watch(update_data, 'value')
    area_selector.param.watch(update_data, 'value')
    reference_period_selector.param.watch(update_data, 'value')
    plot_shortcuts.param.watch(shortcuts_callback, 'clicked', onlychanged=False)
    zoom_shortcuts.param.watch(update_zoom, 'clicked', onlychanged=False)
    cmap_selector.param.watch(update_colour, 'value')

    def read_params(event):
        # Make sure to read the zoom and shortcut URL parameters (if there are any) and update the plot accordingly.
        if plot_shortcuts.clicked:
            plot_shortcuts.param.trigger('clicked')

        zoom_shortcuts.param.trigger('clicked')

    curdoc().on_event(DocumentReady, read_params)

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
