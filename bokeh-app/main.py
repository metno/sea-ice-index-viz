import pandas as pd
import xarray as xr
from functools import reduce
import colorcet as cc
from bokeh.models import HoverTool
import holoviews as hv
import numpy as np
import pandas as pd
from holoviews import opts
import panel as pn

pn.extension()
hv.extension("bokeh", "matplotlib")
pn.extension(loading_spinner='dots', loading_color='#00aa41')
pn.param.ParamMethod.loading_indicator = True

def split_list(a, n):
    k, m = divmod(len(a), n)
    return list(
        list(a[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)]) for i in range(n)
    )


def get_ticks(df, pos):
    splitter = split_list(df.index, 12)
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    xticks_map = [i for i in zip([splitter[i][pos] for i in range(0, 12)], months)]
    return xticks_map


def transfer_metadata(df, cols):
    dataset_metadata = df.dataset_metadata
    variable_metadata = df.variable_metadata
    df = df[cols]
    df.dataset_metadata = ""
    df.dataset_metadata = dataset_metadata
    df.variable_metadata = ""
    df.variable_metadata = variable_metadata
    return df


def get_mplot(df, cols=None):
    if cols:
        df = transfer_metadata(df, cols)
    if len(df.columns) == 0:
        print("No coumns selected")
        return None
    grid_style = {
        "grid_line_color": "black",
        "grid_line_width": 1.1,
        # "ygrid_bounds": (0.3, 0.7),
        "minor_ygrid_line_color": "lightgray",
        "minor_xgrid_line_color": "lightgray",
        "xgrid_line_dash": [4, 4],
    }
    colors = cc.glasbey_light[: len(list(df.columns))]
    xticks_map = get_ticks(df, 15)
    multi_curve = [
        hv.Curve((df.index, df[v]), label=str(v)).opts(
            tools=[
                HoverTool(
                    tooltips=[
                        ("Year", str(v)),
                        ("DoY", "$index"),
                        (f"{df.variable_metadata['long_name']}", "@y"),
                    ],
                    toggleable=False,
                )
            ],
            xticks=xticks_map,
            xrotation=45,
            width=900,
            height=400,
            line_color=colors[i],
            gridstyle=grid_style,
            show_grid=True,
        )
        for i, v in enumerate(df)
    ]
    mplot = hv.Overlay(multi_curve)
    mplot.opts(
        title=f"{df.dataset_metadata['title']}",
        ylabel=f"{df.variable_metadata['long_name']} - {df.variable_metadata['units']}",
        xlabel="Day of the Year",
    )
    return mplot

def get_data(url):
    nc_url = url
    ds = xr.open_dataset(nc_url)
    ds = ds.sel(nv=0)
    df = ds.to_dataframe()
    try:
        new_data = {
            str(i): df["sie"].loc[df.index.groupby(df.index.year)[i]].values
            for i in df.index.groupby(df.index.year)
        }
    except AttributeError:
        print('multi index data using level 0')
        new_data = {
        str(i): df["sie"].loc[df.index.groupby(df.index.get_level_values(1).year)[i]].values  
        for i in df.index.get_level_values(1).groupby(df.index.get_level_values(1).year)
    }
    all_years = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in new_data.items()]))
    all_years.dataset_metadata = ""
    all_years.dataset_metadata = ds.attrs
    all_years.dataset_metadata["dimension"] = list(ds.dims)
    all_years.variable_metadata = ""
    all_years.variable_metadata = ds["sie"].attrs
    return all_years


# urls = ['https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/sh/osisaf_sh_sie_daily.nc', 
#         'https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/nh/osisaf_nh_sie_daily.nc',
#         'https://hyrax.epinux.com/opendap/local_data/osisaf_nh_iceextent_daily.nc']


urls_dict = {'South':'https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/sh/osisaf_sh_sie_daily.nc', 
        'North':'https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/index/v2p1/nh/osisaf_nh_sie_daily.nc'}

df = get_data(urls_dict['North'])

years = pn.widgets.MultiChoice(
    name="Years:", options=list(df.columns), margin=(0, 20, 0, 0)
)


dataset = pn.widgets.MultiChoice(
    name="Hemisphere", options=list(urls_dict.keys()), margin=(0, 20, 0, 0)
)

radio_group = pn.widgets.RadioButtonGroup(
    name='Hemisphere', options=['North', 'South'], button_type='success')



@pn.depends(years, radio_group)
def get_plot(years, radio_group):
    if radio_group:
        url = urls_dict[radio_group]
    else:
        url = urls_dict[list(urls_dict.keys())[0]]
    df = get_data(url=url)
    if years:
        df = transfer_metadata(df, years)
    mplot = get_mplot(df, years)
    return mplot

pn.panel(pn.Column("##Sea Ice Extent", "**Hemisphere:**", pn.Column(radio_group), get_plot, pn.Column(years), width_policy="max").servable(), loading_indicator=True)

