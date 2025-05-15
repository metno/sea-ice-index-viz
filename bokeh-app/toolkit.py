import calendar
from bokeh.models import ColumnDataSource
import xarray as xr
import numpy as np
import matplotlib
import itertools
import cmcrameri.cm as cmc
from numpy.typing import NDArray

type StringsInArrayLike = NDArray[str] | list[str]
type ArrayLike = NDArray | list


class VisDataDaily:
    def __init__(self, anomaly: str, index: str, area: str, ref_period: str, cmap: str) -> None:
        self.ds_daily, ds_clim, ds_decades = self._download_data(anomaly, index, area, ref_period)

        self.cds_p10_90 = ColumnDataSource(self._p10_90(ds_clim, index))
        self.cds_p25_75 = ColumnDataSource(self._p25_75(ds_clim, index))
        self.cds_median = ColumnDataSource(self._median(ds_clim, index))
        self.cds_min = ColumnDataSource(self._min(self.ds_daily))
        self.cds_max = ColumnDataSource(self._max(self.ds_daily))

        self.cds_decades = {}
        for decade, decadal_data in ds_decades.items():
            cds_span = ColumnDataSource(self._span(decadal_data, index))
            cds_median = ColumnDataSource(self._decade_median(decadal_data, index))

            self.cds_decades[decade] = [cds_span, cds_median]

        years = np.unique(self.ds_daily.time.dt.year.values).astype(str)

        da = self.ds_daily[index].convert_calendar('all_leap')
        self.cds_yearly = {}
        for year in years:
            subset = da.sel(time=year)
            rank = self.ds_daily.rank_per_doy.sel(time=year)
            self.cds_yearly[year] = ColumnDataSource(self._yearly(subset, rank))

        self.colours = self._get_colours(years[:-1])
        cols = [self.colours[cmap][str(year)] for year in self.ds_daily.year.values]

        self.cds_yearly_min = ColumnDataSource(self._year_min(self.ds_daily, cols))
        self.cds_yearly_max = ColumnDataSource(self._year_max(self.ds_daily, cols))

    def update_data(self, anomaly: str, index: str, area: str, ref_period: str, cmap: str) -> None:
        self.ds_daily, ds_clim, ds_decades = self._download_data(anomaly, index, area, ref_period)

        self.cds_p10_90.data.update(self._p10_90(ds_clim, index))
        self.cds_p25_75.data.update(self._p25_75(ds_clim, index))
        self.cds_median.data.update(self._median(ds_clim, index))
        self.cds_min.data.update(self._min(self.ds_daily))
        self.cds_max.data.update(self._max(self.ds_daily))

        for decade, decadal_data in ds_decades.items():
            self.cds_decades[decade][0].data.update(self._span(decadal_data, index))
            self.cds_decades[decade][1].data.update(self._decade_median(decadal_data, index))

        years = np.unique(self.ds_daily.time.dt.year.values).astype(str)

        da = self.ds_daily[index].convert_calendar('all_leap')
        for year in years:
            subset = da.sel(time=year)
            rank = self.ds_daily.rank_per_doy.sel(time=year)
            self.cds_yearly[year].data.update(self._yearly(subset, rank))

        self.colours = self._get_colours(years[:-1])
        cols = [self.colours[cmap][str(year)] for year in self.ds_daily.year.values]

        self.cds_yearly_min.data.update(self._year_min(self.ds_daily, cols))
        self.cds_yearly_max.data.update(self._year_max(self.ds_daily, cols))

    def update_colour(self, cmap: str) -> None:
        cols = [self.colours[cmap][str(year)] for year in self.ds_daily.year.values]

        yearly_min = self.cds_yearly_min.data
        yearly_min['colour'] = cols
        yearly_max = self.cds_yearly_max.data
        yearly_max['colour'] = cols

        self.cds_yearly_min.data.update(yearly_min)
        self.cds_yearly_max.data.update(yearly_max)

    def _download_data(self, anomaly: str, index: str, area: str, ref_period: str)\
            -> tuple[xr.Dataset, xr.Dataset, dict[str, xr.Dataset]]:
        dir = f'https://thredds.met.no/thredds/dodsC/metusers/signeaa/test-data-sii-v3p0/{area}'

        index_translation = {'sie': 'ice_extent', 'sia': 'ice_area'}
        path = f'{dir}/{index_translation[index]}_{area}_sii-v3p0_daily.nc'
        ds_daily = xr.open_dataset(path, cache=False).load()

        # Change to get test files working: use hardcoded climatology paths.
        ds_clims = {}
        ds_decades = {}
        clim_periods = ['1981-2010', '1991-2020']
        decades = ['1980-1989', '1990-1999', '2000-2009', '2010-2019']

        for clim in clim_periods:
            ds = xr.open_dataset(f'{dir}/{index_translation[index]}_nh_sii-v3p0_daily-climatology-{clim}.nc',
                                 cache=False).load()
            ds_clims[ds.attrs['climatology_period']] = ds

        for dec in decades:
            ds = xr.open_dataset(f'{dir}/{index_translation[index]}_nh_sii-v3p0_daily-climatology-{dec}.nc',
                                 cache=False).load()
            ds_decades[ds.attrs['climatology_period']] = ds

        ds_clim = ds_clims[ref_period]

        if anomaly == 'anom':
            ds_daily, ds_clim, ds_decades = self._get_anomaly(index, ref_period, ds_daily, ds_clim, ds_decades)

        return ds_daily, ds_clim, ds_decades

    def _get_anomaly(self, index: str, ref_period: str, ds_daily: xr.Dataset, ds_clim: xr.Dataset,
                     ds_decades: dict[str, xr.Dataset]) -> tuple[xr.Dataset, xr.Dataset, dict[str, xr.Dataset]]:
        start = ref_period[:4]
        end = ref_period[5:]

        da = ds_daily[index].convert_calendar('all_leap', missing=-999)

        for i, val in enumerate(da.values):
            if val == -999:
                da.values[i] = (da.values[i - 1] + da.values[i + 1]) / 2

        mean = da.sel(time=slice(start, end)).groupby('time.dayofyear').mean()

        ds_clim[f'{index}_10pctile'].values = ds_clim[f'{index}_10pctile'].values - mean.values
        ds_clim[f'{index}_90pctile'].values = ds_clim[f'{index}_90pctile'].values - mean.values

        ds_clim[f'{index}_25pctile'].values = ds_clim[f'{index}_25pctile'].values - mean.values
        ds_clim[f'{index}_75pctile'].values = ds_clim[f'{index}_75pctile'].values - mean.values

        ds_clim[f'{index}_median'].values = ds_clim[f'{index}_median'].values - mean.values

        ds_daily['min_per_doy'].values = ds_daily.min_per_doy.values - mean.values
        ds_daily['max_per_doy'].values = ds_daily.max_per_doy.values - mean.values

        for decade in ds_decades.keys():
            ds_decades[decade][f'{index}_min'].values = ds_decades[decade][f'{index}_min'].values - mean.values
            ds_decades[decade][f'{index}_max'].values = ds_decades[decade][f'{index}_max'].values - mean.values
            ds_decades[decade][f'{index}_median'].values = ds_decades[decade][f'{index}_median'].values - mean.values

        da = ds_daily[index].convert_calendar('all_leap')
        ds_daily[index].values = (da.groupby('time.dayofyear') - mean).values

        year_min = ds_daily['yearly_min_value'].values
        year_max = ds_daily['yearly_max_value'].values

        for i, year in enumerate(ds_daily['year'].values):
            doy_min = ds_daily.sel(year=year).yearly_min_date.dt.dayofyear.values
            doy_max = ds_daily.sel(year=year).yearly_max_date.dt.dayofyear.values

            year_min[i] = year_min[i] - mean.sel(dayofyear=doy_min).values
            year_max[i] = year_max[i] - mean.sel(dayofyear=doy_max).values

        ds_daily['yearly_min_value'].values = year_min
        ds_daily['yearly_max_value'].values = year_max

        return ds_daily, ds_clim, ds_decades

    def _p10_90(self, ds: xr.Dataset, index: str) -> dict[str, NDArray[float]]:
        return {'doy': ds.time.dt.dayofyear.values, 'p10': ds[f'{index}_10pctile'].values,
                'p90': ds[f'{index}_90pctile'].values}

    def _p25_75(self, ds: xr.Dataset, index: str) -> dict[str, NDArray[float]]:
        return {'doy': ds.time.dt.dayofyear.values, 'p25': ds[f'{index}_25pctile'].values,
                'p75': ds[f'{index}_75pctile'].values}

    def _median(self, ds: xr.Dataset, index: str) -> dict[str, NDArray[float]]:
        return {'doy': ds.time.dt.dayofyear.values, 'value': ds[f'{index}_median'].values}

    def _min(self, ds: xr.Dataset) -> dict[str, NDArray[float]]:
        return {'doy': ds.dayofyear.values, 'value': ds.min_per_doy.values}

    def _max(self, ds: xr.Dataset) -> dict[str, NDArray[float]]:
        return {'doy': ds.dayofyear.values, 'value': ds.max_per_doy.values}

    def _span(self, ds: xr.Dataset, index: str) -> dict[str, NDArray[float]]:
        return {'doy': ds.time.dt.dayofyear.values, 'min': ds[f'{index}_min'].values, 'max': ds[f'{index}_max'].values}

    def _decade_median(self, ds: xr.Dataset, index: str) -> dict[str, NDArray[float]]:
        return {'doy': ds.time.dt.dayofyear.values, 'value': ds[f'{index}_median'].values}

    def _yearly(self, da: xr.Dataset, rank: xr.DataArray) -> dict[str, NDArray[float]]:
        return {'doy': da.time.dt.dayofyear.values, 'value': da.values, 'date': da.time.dt.strftime('%Y-%m-%d').values,
                'rank': rank.values}

    def _year_min(self, ds: xr.Dataset, colours: NDArray[str] | list[str]):
        return {'doy': ds.yearly_min_date.dt.dayofyear.values, 'value': ds.yearly_min_value.values,
                'date': ds.yearly_min_date.dt.strftime('%Y-%m-%d').values, 'rank': ds.yearly_min_rank.values,
                'colour': colours}

    def _year_max(self, ds: xr.Dataset, colours: NDArray[str] | list[str]):
        return {'doy': ds.yearly_max_date.dt.dayofyear.values, 'value': ds.yearly_max_value.values,
                'date': ds.yearly_max_date.dt.strftime('%Y-%m-%d').values, 'rank': ds.yearly_max_rank.values,
                'colour': colours}

    def _get_colours(self, years: NDArray) -> dict[str, NDArray[str]]:
        colours = {}

        colours['decadal'] = self._decadal_colours()

        cyclic_8 = ['#ffe119', '#4363d8', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#000000']
        colours['cyclic_8'] = self._cyclic_colours(cyclic_8, years)

        cyclic_17 = ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#42d4f4', '#f032e6', '#fabed4', '#469990',
                     '#dcbeff', '#9A6324', '#fffac8', '#800000', '#aaffc3', '#000075', '#a9a9a9', '#000000']
        colours['cyclic_17'] = self._cyclic_colours(cyclic_17, years)

        names = ['viridis', 'viridis_r', 'plasma', 'plasma_r', 'batlow', 'batlow_r', 'batlowS']
        cmaps = [matplotlib.cm.viridis, matplotlib.cm.viridis_r, matplotlib.cm.plasma, matplotlib.cm.plasma_r,
                 cmc.batlow, cmc.batlow_r, cmc.batlowS]

        for name, cmap in zip(names, cmaps):
            colours[name] = self._cmap_colours(years, cmap)

        return colours

    def _decadal_colours(self) -> dict[str, str]:
        decades = [1970, 1980, 1990, 2000, 2010, 2020]
        cmaps = [matplotlib.cm.Purples_r, matplotlib.cm.Purples_r, matplotlib.cm.Blues_r, matplotlib.cm.Greens_r,
                 matplotlib.cm.Reds_r, matplotlib.cm.Wistia_r]

        colours = {}
        # Don't use the full breadth of the colourmap, only go up till middle (halfway) to avoid the light colours.
        normalisation = np.linspace(0, 0.5, 10)

        for decade, cmap in zip(decades, cmaps):
            hex_cols = [matplotlib.colors.to_hex(cols) for cols in cmap(normalisation)]
            years_in_decade = np.arange(decade, decade + 10, 1).astype(str)

            for year, col in zip(years_in_decade, hex_cols):
                colours[year] = col

        return colours

    def _cyclic_colours(self, cols, years):
        c_iter = itertools.cycle(cols)

        return {year: next(c_iter) for year in years}

    def _cmap_colours(self, years, cmap):
        normalised = np.linspace(0, 1, len(years))
        colours = cmap(normalised)
        hex_col = [matplotlib.colors.to_hex(color) for color in colours]

        colours = {}
        for year, colour in zip(years, hex_col):
            colours[year] = colour

        return colours

    def get_last_day(self):
        return str(self.ds_daily.time[-1].dt.strftime('%Y-%m-%d').values)


class VisDataMonthly:
    def __init__(self, index: str, area: str, ref_per: str, cmap: str, offset: bool) -> None:
        self.ds = self._download_data(index, area)
        self.da = self.ds[index]

        self.cds_all = self._all(self.da)

        self.colours = self._get_colours()[cmap]
        self.cds_months = {}
        self.cds_full_trends = {}
        self.cds_dec_trends = {}
        for month in range(1, 13):
            self.cds_months[month] = self._month(self.da, month, self.colours[month], offset)
            self.cds_full_trends[month] = self._full_trend(self.ds, self.da, month, ref_per, offset)
            self.cds_dec_trends[month] = self._dec_trend(self.da, month, ref_per, offset)

    def _download_data(self, index: str, area: str):
        dir = f'https://thredds.met.no/thredds/dodsC/metusers/signeaa/test-data-sii-v3p0/{area}'

        index_translation = {'sie': 'ice_extent', 'sia': 'ice_area'}
        path = f'{dir}/{index_translation[index]}_{area}_sii-v3p0_monthly.nc'
        ds = xr.open_dataset(path, cache=False).load()

        return ds

    def _all(self, da):
        return ColumnDataSource({'year': da.time.dt.year.values + ((da.time.dt.month.values - 1) / 12),
                                 'value': da.values})

    def _month(self, da, month, colours, offset: bool):
        subset = da.sel(time=da.time.dt.month.isin(month))

        year = subset.time.dt.year.values
        if offset:
            x = year + ((subset.time.dt.month.values - 1) / 12)
        else:
            x = year

        return ColumnDataSource({'x': x,
                                 'value': subset.values,
                                 'rank': subset.rank('time').values,
                                 'year': year,
                                 'month': np.full(len(subset), calendar.month_name[month]),
                                 'colour': np.full(len(subset), colours)})

    def _full_trend(self, ds, da, month, ref_per, offset: bool):
        absolute = ds['absolute_trend'].sel(month=month).values
        relative = ds[f'relative_trend_{ref_per.replace('-', '_')}'].sel(month=month).values

        subset = da.sel(time=ds.time.dt.month.isin(month)).dropna('time')
        year = np.arange(subset.time.dt.year.values[0], subset.time.dt.year.values[-1]+1, 1)

        year_mean = subset.time.dt.year.mean().values
        value_mean = subset.mean().values

        thousand_per_million = 1000
        value = value_mean - ((absolute / thousand_per_million) * (year_mean - year))

        if offset:
            year = year + ((subset.time.dt.month.values[0] - 1) / 12)

        return ColumnDataSource({'year': year,
                                 'value': value,
                                 'abs_trend': np.full(len(year), absolute),
                                 'rel_trend': np.full(len(year), relative),
                                 'ref_per': np.full(len(year), ref_per),
                                 'month': np.full(len(year), calendar.month_name[month])})

    def _reg_coeffs(self, da):
        x = da.time.dt.year.values - da.time.dt.year.values[0]
        x_stacked = np.vstack([x, np.ones(len(x))]).T
        slope, constant = np.linalg.lstsq(x_stacked, da.values, rcond=None)[0]

        return slope, constant

    def _dec_trend(self, da, month, ref_per, offset: bool, decades=(1980, 1990, 2000, 2010), padding=0.1):
        subset = da.sel(time=da.time.dt.month.isin(month))
        ref_baseline = subset.sel(time=slice(ref_per[:4], ref_per[5:])).mean().values

        trends = {}
        for decade in decades:
            start = str(decade)
            end = str(decade + 9)

            dec_subset = subset.sel(time=slice(start, end)).dropna('time')
            slope, constant = self._reg_coeffs(dec_subset)
            absolute_trend = 1000 * slope

            x = np.arange(0, 10, 1, dtype=float)
            x[0] = x[0] + padding
            x[-1] = x[-1] + (1 - padding)
            values = constant + (slope * x)

            relative_means = 100 * (dec_subset - ref_baseline) / ref_baseline
            slope, _ = self._reg_coeffs(relative_means)
            relative_trend = 10 * slope

            years = np.arange(decade, decade + 10, 1, dtype=float)
            if offset:
                years = years + (month / 12)

            years[0] = years[0] + padding
            years[-1] = years[-1] + (1 - padding)

            trends[f'{start}-{end}'] = ColumnDataSource({'year': years,
                                                         'value': values,
                                                         'month': np.full(len(years), calendar.month_name[month]),
                                                         'decade': np.full(len(years), f'{start}-{end}'),
                                                         'abs_trend': np.full(len(years), absolute_trend),
                                                         'rel_trend': np.full(len(years), relative_trend),
                                                         'ref_per': np.full(len(years), ref_per)})

        return trends

    def update_data(self, index: str, area: str, ref_per: str, offset: bool):
        self.ds = self._download_data(index, area)
        self.da = self.ds[index]

        self.cds_all.data.update(self._all(self.da).data)

        for month in range(1, 13):
            self.cds_months[month].data.update(self._month(self.da, month, self.colours[month], offset).data)
            self.cds_full_trends[month].data.update(self._full_trend(self.ds, self.da, month, ref_per, offset).data)

            for decade in self.cds_dec_trends[month].keys():
                self.cds_dec_trends[month][decade].data.update(self._dec_trend(self.da, month, ref_per, offset)[decade].data)

    def _get_colours(self):
        months = [m for m in range(1, 13)]
        colours = {}

        cyclic_8 = ['#ffe119', '#4363d8', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#000000']
        colours['cyclic_8'] = self._cyclic_colours(cyclic_8, months)

        cyclic_17 = ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#42d4f4', '#f032e6', '#fabed4', '#469990',
                     '#dcbeff', '#9A6324', '#fffac8', '#800000', '#aaffc3', '#000075', '#a9a9a9', '#000000']
        colours['cyclic_17'] = self._cyclic_colours(cyclic_17, months)

        names = ['viridis', 'viridis_r', 'plasma', 'plasma_r', 'batlow', 'batlow_r', 'batlowS']
        cmaps = [matplotlib.cm.viridis, matplotlib.cm.viridis_r, matplotlib.cm.plasma, matplotlib.cm.plasma_r,
                 cmc.batlow, cmc.batlow_r, cmc.batlowS]

        for name, cmap in zip(names, cmaps):
            colours[name] = self._cmap_colours(months, cmap)

        return colours

    def _cyclic_colours(self, cols, months):
        c_iter = itertools.cycle(cols)

        return {month: next(c_iter) for month in months}

    def _cmap_colours(self, months, cmap):
        normalised = np.linspace(0, 1, len(months))
        colours = cmap(normalised)
        hex_col = [matplotlib.colors.to_hex(color) for color in colours]

        colours = {}
        for month, colour in zip(months, hex_col):
            colours[month] = colour

        return colours

    def update_colour(self, cmap: str):
        self.colours = self._get_colours()[cmap]

        for month in range(1, 13):
            data = self.cds_months[month].data
            data['colour'] = np.full(len(data['year']), self.colours[month])
            self.cds_months[month].data.update(data)

    def get_last_month(self):
        return str(self.da.time[-1].dt.strftime('%Y-%m').values)
